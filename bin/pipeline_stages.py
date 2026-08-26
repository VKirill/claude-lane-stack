#!/usr/bin/env python3
"""Pipeline stages for Claude Lane Stack — plan critique + per-agent routing.

Source of truth lives under ``stages:`` in ``.agents/routing.profile.yaml``
(written by agents-doctor / adoc). Stages are *roles in the conveyor*, not
Claude subagents:

  plan (PM, fixed) → plan_critique → write → verify (L1, fixed) → night_review
                                      ↘ optional specialist (read-only)
  side role: onboard (project passport; adoc agent/model/effort/service_tier)

Coverage helper for the PM (Fable): did PLAN/owns_paths miss callers,
imports, or tests? Runs only on large/hard runs (score≥7, ≥3 write tasks,
or high_risk). Essay checks (thin PLAN, missing headings) are not the job.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KNOWN_STAGE_PROVIDERS = frozenset(
    {"structural", "kimi", "qwen", "agy", "grok", "codex", "cursor", "opencode"}
)
CRITIQUE_MODES = frozenset({"advisory", "gate"})
CRITIQUE_DECISIONS = frozenset({"ship", "revise", "revise_required"})
SPECIALIST_WHEN = frozenset({"high_risk", "always"})

PM_ACTION = {
    "ship": (
        "Dispatch after `run-validate --phase pre-dispatch`. "
        "No plan corrections required."
    ),
    "revise": (
        "Coverage gaps: add missed files to owns_paths / PLAN, then re-run "
        "`plan-critique`. Residual warnings may ship with an explicit reason "
        "(advisory) or `plan-critique --ack --note '…'` (gate)."
    ),
    "revise_required": (
        "MUST edit PLAN.md / SPEC.md / tasks/*.yaml to address error findings, "
        "then re-run `plan-critique` until decision is ship (or gate-ack with "
        "an explicit note). Do not start run-controller / writers yet."
    ),
}

DEFAULT_MODELS = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.6-flash-high",
    "codex": "gpt-5.6-luna",
    "cursor": "composer-2.5",
    "opencode": "alibaba-token-plan/qwen3.8-max-preview",
    "structural": "",
}
# Write-lane defaults (daytime implementer).
DEFAULT_WRITE_EFFORTS = {
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
    "codex": "max",
    "cursor": "medium",
    "opencode": "medium",
}
# Cheap plan-critique pass defaults.
DEFAULT_CRITIQUE_EFFORTS = {
    "qwen": "low",
    "kimi": "low",
    "grok": "low",
    "agy": "low",
    "cursor": "low",
    "codex": "low",
    "opencode": "low",
    "structural": "low",
}
DEFAULT_EFFORTS = DEFAULT_CRITIQUE_EFFORTS  # alias for critique
# project-onboard / project-onboarder defaults (adoc Stages → onboard).
DEFAULT_ONBOARD_MODEL = "gpt-5.6-terra"
DEFAULT_ONBOARD_EFFORT = "high"
DEFAULT_ONBOARD_EFFORTS = {
    "codex": "high",
    "cursor": "high",
    "opencode": "medium",
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
}
SERVICE_TIER_STAGE_PROVIDERS = frozenset({"codex", "cursor"})
DEFAULT_OPENCODE_WRITE_AGENT = "lane-writer"
DEFAULT_OPENCODE_CRITIQUE_AGENT = "lane-critic"
DEFAULT_OPENCODE_REVIEW_AGENT = "lane-reviewer"

_SPEC_STUB_MARKERS = (
    "record interfaces, invariants, constraints, and the definition of done here",
    "replace_me one paragraph",
    "replace_me stable apis",
    "replace_me what must keep working",
    "replace_me explicit non-goals",
    "replace_me observable acceptance",
)

_HEAVY_FULL_PACKAGE = re.compile(
    r"(?:^|[;&|]\s*)(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:build|test)(?:\s|$)",
    re.I,
)

_VAGUE_OBJECTIVE = re.compile(
    r"^(fix|improve|update|handle|do|work on|clean up)\b",
    re.I,
)


def default_stages(
    *,
    write_provider: str = "kimi",
    write_model: str | None = None,
    write_effort: str | None = None,
    night_enabled: bool = False,
    night_provider: str = "qwen",
) -> dict[str, Any]:
    """Return the full stages map with sensible defaults."""
    wp = write_provider if write_provider in KNOWN_STAGE_PROVIDERS - {"structural"} else "kimi"
    return {
        "plan_critique": {
            "enabled": True,
            "mode": "advisory",
            "provider": "structural",
            "model": "",
            "reasoning_effort": "low",
            "min_score": 7,
            "min_write_tasks": 3,
            "on_high_risk": True,
            "service_tier": "standard",
        },
        "write": {
            "provider": wp,
            "model": write_model or DEFAULT_MODELS.get(wp, ""),
            "reasoning_effort": write_effort
            or DEFAULT_WRITE_EFFORTS.get(wp, "medium"),
        },
        "night_review": {
            "enabled": bool(night_enabled),
            "provider": night_provider
            if night_provider in (KNOWN_STAGE_PROVIDERS - {"structural"})
            else "qwen",
            "model": DEFAULT_MODELS.get(
                night_provider
                if night_provider in (KNOWN_STAGE_PROVIDERS - {"structural"})
                else "qwen",
                "",
            ),
            "reasoning_effort": DEFAULT_WRITE_EFFORTS.get(
                night_provider
                if night_provider in (KNOWN_STAGE_PROVIDERS - {"structural"})
                else "qwen",
                "medium",
            ),
        },
        "specialist": {
            "enabled": False,
            "when": "high_risk",
            "provider": "codex",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
        },
        "onboard": {
            "provider": "codex",
            "model": DEFAULT_ONBOARD_MODEL,
            "reasoning_effort": DEFAULT_ONBOARD_EFFORT,
            "service_tier": "standard",
        },
    }


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def default_opencode_agent(stage_id: str = "write") -> str:
    if stage_id == "plan_critique":
        return DEFAULT_OPENCODE_CRITIQUE_AGENT
    if stage_id in {"night_review", "specialist"}:
        return DEFAULT_OPENCODE_REVIEW_AGENT
    return DEFAULT_OPENCODE_WRITE_AGENT


def _opencode_agent(block: dict[str, Any], *, default: str) -> dict[str, str]:
    raw = str(block.get("agent") or default).strip()
    return {"agent": raw or default}


def _effort_from_block(block: dict[str, Any], default: str) -> str:
    # Explicit empty stays empty (OpenCode model with no variants).
    if "reasoning_effort" in block:
        return str(block.get("reasoning_effort") or "").strip()
    if "effort" in block:
        return str(block.get("effort") or "").strip()
    return default


def _normalize_service_tier(block: dict[str, Any], provider: str) -> str:
    raw = block.get("service_tier")
    if raw is None and "fast_mode" in block:
        raw = "fast" if _as_bool(block.get("fast_mode"), False) else "standard"
    tier = str(raw or "standard").strip().lower()
    if tier not in {"standard", "fast"}:
        tier = "standard"
    if provider not in SERVICE_TIER_STAGE_PROVIDERS:
        return "standard"
    return tier


def normalize_stages(raw: dict[str, Any] | None, *, write_provider: str = "kimi") -> dict[str, Any]:
    """Merge partial stages dict with defaults; clamp enums."""
    base = default_stages(write_provider=write_provider)
    if not isinstance(raw, dict):
        return base

    pc = raw.get("plan_critique") if isinstance(raw.get("plan_critique"), dict) else {}
    write = raw.get("write") if isinstance(raw.get("write"), dict) else {}
    night = raw.get("night_review") if isinstance(raw.get("night_review"), dict) else {}
    spec = raw.get("specialist") if isinstance(raw.get("specialist"), dict) else {}
    onboard = raw.get("onboard") if isinstance(raw.get("onboard"), dict) else {}

    # plan_critique
    pc_provider = str(pc.get("provider") or base["plan_critique"]["provider"]).strip()
    if pc_provider not in KNOWN_STAGE_PROVIDERS:
        pc_provider = "structural"
    pc_mode = str(pc.get("mode") or base["plan_critique"]["mode"]).strip().lower()
    if pc_mode not in CRITIQUE_MODES:
        pc_mode = "advisory"
    base["plan_critique"] = {
        "enabled": _as_bool(pc.get("enabled"), True),
        "mode": pc_mode,
        "provider": pc_provider,
        "model": str(pc.get("model") or DEFAULT_MODELS.get(pc_provider, "")).strip(),
        "reasoning_effort": _effort_from_block(
            pc, DEFAULT_EFFORTS.get(pc_provider, "low")
        ),
        "min_score": max(0, _as_int(pc.get("min_score"), 7)),
        "min_write_tasks": max(1, _as_int(pc.get("min_write_tasks"), 3)),
        "on_high_risk": _as_bool(pc.get("on_high_risk"), True),
        "service_tier": _normalize_service_tier(pc, pc_provider),
        **(
            _opencode_agent(pc, default=default_opencode_agent("plan_critique"))
            if pc_provider == "opencode"
            else {}
        ),
    }
    if pc_provider == "structural":
        base["plan_critique"]["model"] = ""

    # write
    w_provider = str(write.get("provider") or write_provider or "kimi").strip()
    if w_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        w_provider = "kimi"
    base["write"] = {
        "provider": w_provider,
        "model": str(
            write.get("model") or DEFAULT_MODELS.get(w_provider, "")
        ).strip(),
        "reasoning_effort": _effort_from_block(
            write, DEFAULT_WRITE_EFFORTS.get(w_provider, "medium")
        ),
        **(
            _opencode_agent(write, default=default_opencode_agent("write"))
            if w_provider == "opencode"
            else {}
        ),
    }

    # night
    n_provider = str(night.get("provider") or base["night_review"]["provider"]).strip()
    if n_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        n_provider = "qwen"
    base["night_review"] = {
        "enabled": _as_bool(night.get("enabled"), False),
        "provider": n_provider,
        "model": str(
            night.get("model") or DEFAULT_MODELS.get(n_provider, "")
        ).strip(),
        "reasoning_effort": _effort_from_block(
            night, DEFAULT_WRITE_EFFORTS.get(n_provider, "medium")
        ),
        **(
            _opencode_agent(night, default=default_opencode_agent("night_review"))
            if n_provider == "opencode"
            else {}
        ),
    }

    # specialist
    s_provider = str(spec.get("provider") or "codex").strip()
    if s_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        s_provider = "codex"
    s_when = str(spec.get("when") or "high_risk").strip().lower()
    if s_when not in SPECIALIST_WHEN:
        s_when = "high_risk"
    base["specialist"] = {
        "enabled": _as_bool(spec.get("enabled"), False),
        "when": s_when,
        "provider": s_provider,
        "model": str(
            spec.get("model") or DEFAULT_MODELS.get(s_provider, "gpt-5.6-sol")
        ).strip(),
        "reasoning_effort": _effort_from_block(
            spec, DEFAULT_EFFORTS.get(s_provider, "high")
        ),
        **(
            _opencode_agent(spec, default=default_opencode_agent("specialist"))
            if s_provider == "opencode"
            else {}
        ),
    }

    # onboard (project passport — not part of daytime conveyor)
    o_provider = str(onboard.get("provider") or "codex").strip()
    if o_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        o_provider = "codex"
    o_default_model = (
        DEFAULT_ONBOARD_MODEL
        if o_provider == "codex"
        else DEFAULT_MODELS.get(o_provider, DEFAULT_ONBOARD_MODEL)
    )
    o_tier = _normalize_service_tier(onboard, o_provider)
    base["onboard"] = {
        "provider": o_provider,
        "model": str(onboard.get("model") or o_default_model).strip(),
        "reasoning_effort": _effort_from_block(
            onboard, DEFAULT_ONBOARD_EFFORTS.get(o_provider, DEFAULT_ONBOARD_EFFORT)
        ),
        "service_tier": o_tier,
        **(
            _opencode_agent(onboard, default=default_opencode_agent("onboard"))
            if o_provider == "opencode"
            else {}
        ),
    }
    return base


def stages_to_yaml_lines(stages: dict[str, Any]) -> list[str]:
    """Emit YAML lines for the stages: block (no leading stages: key)."""
    stages = normalize_stages(stages)
    lines: list[str] = ["stages:"]
    for name in ("plan_critique", "write", "night_review", "specialist", "onboard"):
        block = stages[name]
        lines.append(f"  {name}:")
        for key, value in block.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            else:
                rendered = str(value)
            if key == "model" and not rendered:
                continue
            if (
                key == "service_tier"
                and str(block.get("provider") or "") not in SERVICE_TIER_STAGE_PROVIDERS
            ):
                continue
            if key == "agent" and str(block.get("provider") or "") != "opencode":
                continue
            lines.append(f"    {key}: {rendered}")
    return lines


def load_stages_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Extract normalized stages from a parsed routing profile."""
    lanes = profile.get("lanes") if isinstance(profile.get("lanes"), dict) else {}
    writer = profile.get("writer") if isinstance(profile.get("writer"), dict) else {}
    write_provider = str(
        lanes.get("main_write") or writer.get("provider") or "kimi"
    ).strip()
    raw = profile.get("stages") if isinstance(profile.get("stages"), dict) else {}
    # If stages missing, seed write from writer section
    if not raw:
        return default_stages(
            write_provider=write_provider,
            write_model=writer.get("model"),
            write_effort=writer.get("reasoning_effort") or writer.get("effort"),
        )
    # Prefer explicit write.provider; fall back to main_write
    if "write" not in raw or not isinstance(raw.get("write"), dict):
        raw = dict(raw)
        raw["write"] = {
            "provider": write_provider,
            "model": writer.get("model"),
            "reasoning_effort": writer.get("reasoning_effort") or writer.get("effort"),
        }
    return normalize_stages(raw, write_provider=write_provider)


def resolve_plan_critique(start: Path) -> dict[str, Any]:
    """Load plan_critique settings for a project path."""
    from routing_profile import load_routing_profile  # local import — same bin/

    profile = load_routing_profile(start)
    stages = load_stages_from_profile(profile)
    return {
        **stages["plan_critique"],
        "stages": stages,
        "profile_path": profile.get("_path"),
    }


def resolve_onboard(start: Path) -> dict[str, Any]:
    """Load onboard stage (provider/model/effort/service_tier) for a project path."""
    from routing_profile import load_routing_profile  # local import — same bin/

    profile = load_routing_profile(start)
    stages = load_stages_from_profile(profile)
    block = stages.get("onboard") or {}
    provider = str(block.get("provider") or "codex")
    model = str(block.get("model") or DEFAULT_ONBOARD_MODEL)
    # Cursor fast sibling when service_tier=fast
    if provider == "cursor":
        try:
            from routing_profile import resolve_cursor_model

            model = resolve_cursor_model(
                model, service_tier=str(block.get("service_tier") or "standard")
            )
        except Exception:  # noqa: BLE001
            pass
    return {
        "provider": provider,
        "model": model,
        "reasoning_effort": str(
            block.get("reasoning_effort") or DEFAULT_ONBOARD_EFFORT
        ),
        "service_tier": str(block.get("service_tier") or "standard"),
        "stages": stages,
        "profile_path": profile.get("_path"),
    }


# ── Structural critique ─────────────────────────────────────────────────────


def _load_yaml_safe(path: Path) -> dict[str, Any] | None:
    try:
        import yaml
    except ImportError:
        return None
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, Exception):  # noqa: BLE001
        return None
    return value if isinstance(value, dict) else None


def _finding(
    severity: str,
    code: str,
    title: str,
    detail: str,
    *,
    path: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,  # error | warn | info
        "code": code,
        "title": title,
        "detail": detail,
        "path": path,
        "task_id": task_id,
    }


_GENERIC_STEMS = frozenset(
    {
        "index",
        "main",
        "app",
        "utils",
        "util",
        "types",
        "type",
        "const",
        "constants",
        "config",
        "settings",
        "style",
        "styles",
        "test",
        "spec",
        "init",
    }
)
_SKIP_SCAN_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".agents",
        "dist",
        "build",
        "vendor",
        "__pycache__",
        ".venv",
        ".tox",
        "coverage",
    }
)
_PATH_IN_TEXT = re.compile(
    r"(?<![\w./])((?:[\w.-]+/){1,8}[\w.-]+\.[A-Za-z][\w.-]{0,12})"
)
_REVIEW_LANES = frozenset({"verify", "review", "night", "critique"})


def _write_task_count(tasks: list[dict[str, Any]]) -> int:
    n = 0
    for task in tasks:
        lane = str(task.get("lane") or "write").strip().lower()
        if lane not in _REVIEW_LANES:
            n += 1
    return n


def critique_should_run(
    run: dict[str, Any],
    write_count: int,
    settings: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Large/hard runs only. Small UI tweaks skip the helper."""
    settings = settings or {}
    min_score = max(0, _as_int(settings.get("min_score"), 7))
    min_writes = max(1, _as_int(settings.get("min_write_tasks"), 3))
    try:
        score = int(run.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    if score >= min_score:
        return True, f"score {score}>={min_score}"
    if write_count >= min_writes:
        return True, f"{write_count} write tasks >={min_writes}"
    if _as_bool(settings.get("on_high_risk"), True):
        risk = str(run.get("risk") or "").strip().lower()
        if risk in {"high", "critical"}:
            return True, f"risk={risk}"
        hrp = run.get("high_risk_paths") or []
        if isinstance(hrp, list) and hrp:
            return True, "high_risk_paths set"
    return False, f"score {score}<{min_score} and {write_count} write tasks<{min_writes}"


def _repo_root(run_dir: Path, run: dict[str, Any]) -> Path | None:
    for key in ("project_cwd", "repo"):
        raw = run.get(key)
        if raw:
            path = Path(str(raw)).expanduser()
            if path.is_dir():
                return path
    for parent in (run_dir, *run_dir.parents):
        if (parent / ".git").exists():
            return parent
    return None


def _norm_own(raw: str) -> str:
    return str(raw or "").strip().lstrip("./")


def _owns_cover(owned: list[str], rel: str) -> bool:
    rel_n = _norm_own(rel)
    for own in owned:
        if not own:
            continue
        if rel_n == own or rel_n.startswith(own.rstrip("/") + "/"):
            return True
        if own.endswith("/**") and rel_n.startswith(own[:-3]):
            return True
    return False


def _needles_for_own(own: str) -> list[str]:
    own_n = _norm_own(own)
    path = Path(own_n)
    needles = [own_n, path.name]
    stem = path.stem
    if stem and stem.lower() not in _GENERIC_STEMS:
        if path.suffix == ".py":
            mod = own_n[: -len(path.suffix)].replace("/", ".")
            needles.extend([f"from {mod}", f"import {mod}"])
        needles.append(stem)
    # unique, keep order
    seen: set[str] = set()
    out: list[str] = []
    for needle in needles:
        if needle and needle not in seen:
            seen.add(needle)
            out.append(needle)
    return out


def _rg_files(root: Path, needle: str, limit: int = 16) -> list[Path]:
    rg = shutil.which("rg")
    if not rg:
        return []
    cmd = [
        rg,
        "-l",
        "-F",
        needle,
        "--max-count",
        "1",
        "--glob",
        "!.git",
        "--glob",
        "!node_modules",
        "--glob",
        "!.agents",
        "--glob",
        "!dist",
        "--glob",
        "!.venv",
        str(root),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=8, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    hits: list[Path] = []
    if proc is not None:
        for line in (proc.stdout or "").splitlines():
            candidate = Path(line.strip())
            if candidate.is_file():
                hits.append(candidate)
            if len(hits) >= limit:
                return hits
        return hits
    scanned = 0
    for path in root.rglob("*"):
        if not path.is_file() or any(part in _SKIP_SCAN_DIRS for part in path.parts):
            continue
        scanned += 1
        if scanned > 4000:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in text:
            hits.append(path)
        if len(hits) >= limit:
            break
    return hits


def _paths_overlap(left: str, right: str) -> bool:
    a, b = _norm_own(left), _norm_own(right)
    if not a or not b:
        return False
    if a.endswith("/**"):
        a = a[:-3]
    if b.endswith("/**"):
        b = b[:-3]
    a, b = a.rstrip("/"), b.rstrip("/")
    if a == b:
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def _owns_overlap_findings(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    write: list[tuple[str, list[str]]] = []
    for task in tasks:
        lane = str(task.get("lane") or "write").strip().lower()
        if lane in _REVIEW_LANES:
            continue
        raw = task.get("owns_paths") or []
        if not isinstance(raw, list):
            continue
        paths = [_norm_own(str(p)) for p in raw if str(p).strip()]
        if paths:
            write.append((str(task.get("id") or "?"), paths))
    findings: list[dict[str, Any]] = []
    for i, (aid, apaths) in enumerate(write):
        for bid, bpaths in write[i + 1 :]:
            hit = next(
                (
                    (a, b)
                    for a in apaths
                    for b in bpaths
                    if _paths_overlap(a, b)
                ),
                None,
            )
            if hit is None:
                continue
            findings.append(
                _finding(
                    "error",
                    "owns_overlap",
                    f"Tasks {aid} and {bid} overlap owns_paths",
                    f"{hit[0]} overlaps {hit[1]}. Parallel writers need disjoint owns.",
                    path="tasks/",
                    task_id=aid,
                )
            )
    return findings


def _sibling_test_paths(root: Path, own: str) -> list[str]:
    own_n = _norm_own(own)
    path = Path(own_n)
    stem = path.stem
    if not stem or stem.lower() in _GENERIC_STEMS:
        return []
    parent = str(path.parent).replace("\\", "/")
    parent = "" if parent == "." else parent
    candidates = [
        f"tests/test_{stem}.py",
        f"test_{stem}.py",
        f"{own_n}.test.ts",
        f"{own_n}.spec.ts",
        f"{parent}/{stem}.test.ts" if parent else f"{stem}.test.ts",
        f"{parent}/{stem}.spec.ts" if parent else f"{stem}.spec.ts",
        f"{parent}/__tests__/{stem}.test.ts" if parent else f"__tests__/{stem}.test.ts",
        f"{parent}/{stem}.test.js" if parent else f"{stem}.test.js",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for rel in candidates:
        rel_n = _norm_own(rel)
        if rel_n in seen:
            continue
        seen.add(rel_n)
        if (root / rel_n).is_file():
            found.append(rel_n)
    return found


_SYM_DECL = re.compile(
    r"^(?:export\s+(?:async\s+)?(?:function|class|const|let)\s+|async\s+def\s+|def\s+|class\s+|function\s+)([A-Za-z_][\w]*)",
    re.M,
)


def _symbols_in_file(path: Path, *, limit: int = 2) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for match in _SYM_DECL.finditer(text):
        name = match.group(1)
        if name in seen or name.lower() in _GENERIC_STEMS:
            continue
        seen.add(name)
        names.append(name)
        if len(names) >= limit:
            break
    return names


def _json_object_from_stdout(text: str) -> dict[str, Any] | None:
    start = (text or "").find("{")
    if start < 0:
        return None
    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _gitnexus_argv() -> list[str] | None:
    direct = shutil.which("gitnexus")
    if direct:
        return [direct]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "gitnexus"]
    return None


def _collect_paths_from_impact(payload: dict[str, Any]) -> list[str]:
    files: list[str] = []
    by_depth = payload.get("byDepth")
    items: list[Any] = []
    if isinstance(by_depth, dict):
        for value in by_depth.values():
            if isinstance(value, list):
                items.extend(value)
    elif isinstance(by_depth, list):
        items = by_depth
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("file", "file_path", "path"):
            raw = item.get(key)
            if raw:
                files.append(str(raw).lstrip("./"))
                break
    return files


def gitnexus_caller_files(
    root: Path,
    *,
    symbol: str,
    file_path: str,
    timeout: float = 8.0,
) -> list[str]:
    """Upstream callers of a symbol via `gitnexus impact`. Empty if no index."""
    if not (root / ".gitnexus").is_dir():
        return []
    argv = _gitnexus_argv()
    if not argv or not symbol:
        return []
    cmd = [
        *argv,
        "impact",
        symbol,
        "-d",
        "upstream",
        "--depth",
        "1",
        "--include-tests",
        "-l",
        "12",
        "-r",
        root.name,
    ]
    if file_path:
        cmd.extend(["-f", file_path])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    payload = _json_object_from_stdout(proc.stdout or "")
    if not payload or payload.get("error"):
        return []
    return _collect_paths_from_impact(payload)


def coverage_findings(
    run_dir: Path,
    run: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Missed files: imports/callers of owns_paths not listed on any task."""
    root = _repo_root(run_dir, run)
    if root is None:
        return []
    owned: list[str] = []
    for task in tasks:
        raw = task.get("owns_paths") or []
        if isinstance(raw, list):
            owned.extend(_norm_own(str(p)) for p in raw if str(p).strip())
    if not owned:
        return []

    mentioned: set[str] = set()
    for rel in ("PLAN.md", "SPEC.md"):
        path = run_dir / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _PATH_IN_TEXT.findall(text):
            mentioned.add(_norm_own(match))

    findings: list[dict[str, Any]] = []
    seen_gap: set[str] = set()

    def _add_gap(rel: str, own: str, why: str) -> None:
        if _owns_cover(owned, rel) or rel in seen_gap:
            return
        if any(part in _SKIP_SCAN_DIRS for part in Path(rel).parts):
            return
        seen_gap.add(rel)
        findings.append(
            _finding(
                "warn",
                "owns_gap",
                f"Possible missed file: {rel}",
                f"{why} Add it to a task or mark out of scope in PLAN.",
                path=rel,
            )
        )

    scanned = 0
    gn_budget = 20.0
    gn_started = datetime.now(timezone.utc).timestamp()
    for own in owned:
        if len(findings) >= 10:
            break
        if scanned >= 8:
            break
        if Path(own).stem.lower() in _GENERIC_STEMS:
            continue
        target = root / own
        if not target.is_file():
            continue
        scanned += 1
        for rel in _sibling_test_paths(root, own):
            _add_gap(rel, own, f"Sibling test of {own} is not in any owns_paths.")
        if datetime.now(timezone.utc).timestamp() - gn_started < gn_budget:
            symbols = _symbols_in_file(target) or (
                [Path(own).stem] if Path(own).stem.lower() not in _GENERIC_STEMS else []
            )
            for symbol in symbols[:2]:
                for rel in gitnexus_caller_files(root, symbol=symbol, file_path=own):
                    _add_gap(
                        rel,
                        own,
                        f"GitNexus caller of {symbol} ({own}) is not in any owns_paths.",
                    )
                if len(findings) >= 10:
                    break
        for needle in _needles_for_own(own)[:3]:
            if len(needle) < 4:
                continue
            for hit in _rg_files(root, needle):
                try:
                    rel = str(hit.resolve().relative_to(root.resolve()))
                except ValueError:
                    continue
                _add_gap(rel, own, f"References {own} but is not in any owns_paths.")
                if len(findings) >= 10:
                    break
            if len(findings) >= 10:
                break

    for mention in sorted(mentioned):
        if _owns_cover(owned, mention):
            continue
        if (root / mention).is_file() and mention not in seen_gap:
            seen_gap.add(mention)
            findings.append(
                _finding(
                    "warn",
                    "plan_path_unowned",
                    f"PLAN/SPEC names {mention} but no task owns it",
                    "Add to owns_paths or drop the path from the plan.",
                    path=mention,
                )
            )
        if len(findings) >= 10:
            break
    return findings


def _skipped_critique(
    run_dir: Path,
    *,
    reason: str,
    score: int,
    task_count: int,
) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "engine": "skipped",
        "status": "pass",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "score": score,
        "task_count": task_count,
        "skip_reason": reason,
        "summary": {"errors": 0, "warnings": 0, "infos": 0},
        "findings": [],
        "llm_pass": {"status": "skipped", "provider": "below_bar"},
        "acked_by": None,
        "ack_note": None,
    }
    attach_decision(result)
    result["pm_action"] = (
        "Coverage helper skipped (small/simple run). "
        "Dispatch after `run-validate --phase pre-dispatch`."
    )
    return result


def structural_critique(run_dir: Path) -> dict[str, Any]:
    """Deterministic plan/task quality review. No LLM required."""
    run_dir = run_dir.expanduser().resolve()
    findings: list[dict[str, Any]] = []
    run = _load_yaml_safe(run_dir / "run.yaml") or {}
    try:
        score = int(run.get("score") or 0)
    except (TypeError, ValueError):
        score = 0

    plan_path = run_dir / "PLAN.md"
    if not plan_path.is_file():
        findings.append(
            _finding(
                "error",
                "plan_missing",
                "PLAN.md missing",
                "Every run needs PLAN.md with goals, DAG, out-of-scope, verification.",
                path="PLAN.md",
            )
        )
    task_paths = sorted((run_dir / "tasks").glob("*.yaml"))
    task_count = len(task_paths)
    if task_count == 0:
        findings.append(
            _finding(
                "error",
                "no_tasks",
                "No task YAML files",
                "Add tasks/*.yaml before pre-dispatch.",
                path="tasks/",
            )
        )

    tasks: list[dict[str, Any]] = []
    for path in task_paths:
        task = _load_yaml_safe(path)
        if task is None:
            findings.append(
                _finding(
                    "error",
                    "task_parse",
                    f"Cannot parse {path.name}",
                    "Task YAML must be a mapping.",
                    path=str(path.relative_to(run_dir)),
                )
            )
            continue
        tasks.append(task)
        tid = str(task.get("id") or path.stem)
        owns = task.get("owns_paths") or []
        if not isinstance(owns, list) or not owns:
            findings.append(
                _finding(
                    "error",
                    "owns_empty",
                    f"Task {tid}: empty owns_paths",
                    "Every write task needs explicit file ownership.",
                    path=str(path.relative_to(run_dir)),
                    task_id=tid,
                )
            )

        verification = task.get("verification") or []
        if not isinstance(verification, list) or not verification:
            findings.append(
                _finding(
                    "error",
                    "verify_missing",
                    f"Task {tid}: no verification[]",
                    "L1 focused checks are required before accept.",
                    path=str(path.relative_to(run_dir)),
                    task_id=tid,
                )
            )
        elif task_count > 1 and isinstance(verification, list):
            for index, item in enumerate(verification):
                if not isinstance(item, dict):
                    continue
                cmd = str(item.get("command") or "")
                try:
                    raw_to = item.get("timeout_sec")
                    timeout = int(raw_to) if raw_to is not None and raw_to != "" else 0
                except (TypeError, ValueError):
                    timeout = 0
                # Missing timeout is fine (runtime default 900). Only flag
                # explicit huge timeouts with heavy commands as L2-shaped.
                if (timeout > 900) or _HEAVY_FULL_PACKAGE.search(cmd):
                    findings.append(
                        _finding(
                            "error" if score >= 7 else "warn",
                            "verify_heavy",
                            f"Task {tid}: verification[{index}] looks like L2",
                            "Use focused L1 paths/suites; full suite is L2 at pre-merge.",
                            path=str(path.relative_to(run_dir)),
                            task_id=tid,
                        )
                    )

    findings.extend(_owns_overlap_findings(tasks))
    findings.extend(coverage_findings(run_dir, run, tasks))

    errors = sum(1 for f in findings if f["severity"] == "error")
    warns = sum(1 for f in findings if f["severity"] == "warn")
    status = "pass" if errors == 0 else "fail"
    result = {
        "schema_version": 1,
        "engine": "coverage",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "score": score,
        "task_count": task_count,
        "summary": {
            "errors": errors,
            "warnings": warns,
            "infos": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
        "llm_pass": {"status": "skipped", "provider": "structural"},
        "acked_by": None,
        "ack_note": None,
    }
    return attach_decision(result)


def compute_decision(result: dict[str, Any]) -> str:
    """Map critique status/findings → PM decision.

    - revise_required: any error, status fail, or LLM verdict revise_required
    - revise: warnings only (or LLM verdict revise)
    - ship: clean / acked
    """
    status = str(result.get("status") or "").lower()
    if status == "ack":
        return "ship"
    findings = result.get("findings") if isinstance(result.get("findings"), list) else []
    errors = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "error")
    warns = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") == "warn")
    if status == "fail" or errors > 0:
        return "revise_required"
    if warns > 0:
        return "revise"
    return "ship"


def attach_decision(result: dict[str, Any]) -> dict[str, Any]:
    """Mutate/return result with decision + pm_action fields."""
    decision = compute_decision(result)
    if decision not in CRITIQUE_DECISIONS:
        decision = "revise_required"
    result["decision"] = decision
    result["pm_action"] = PM_ACTION[decision]
    return result


_LLM_SUMMARY_NOISE = (
    "outcome.json",
    "run-validate",
    "acceptance.json",
    "schema enum",
    "provider enum",
)


def _clean_llm_summary(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    if any(token in lowered for token in _LLM_SUMMARY_NOISE):
        return ""
    return raw[:400]


def merge_llm_into_critique(
    structural: dict[str, Any],
    llm_payload: dict[str, Any] | None,
    *,
    provider: str,
    model: str = "",
    llm_error: str | None = None,
) -> dict[str, Any]:
    """Attach an optional LLM summary. Findings/decision stay structural."""
    result = dict(structural)
    findings: list[dict[str, Any]] = [
        dict(f) for f in (structural.get("findings") or []) if isinstance(f, dict)
    ]

    if llm_error:
        result["engine"] = "coverage"
        result["llm_pass"] = {
            "status": "error",
            "provider": provider,
            "model": model or "",
            "error": llm_error,
            "verdict": None,
        }
    elif llm_payload is None:
        result["engine"] = "coverage"
        result["llm_pass"] = {
            "status": "skipped",
            "provider": provider or "structural",
            "model": model or "",
            "verdict": None,
        }
    else:
        result["engine"] = "coverage"
        result["llm_pass"] = {
            "status": "ok",
            "provider": provider,
            "model": model or str(llm_payload.get("model") or ""),
            "verdict": None,
            "summary": _clean_llm_summary(str(llm_payload.get("summary") or "")),
        }

    # Recompute summary/status from merged findings
    errors = sum(1 for f in findings if f.get("severity") == "error")
    warns = sum(1 for f in findings if f.get("severity") == "warn")
    infos = sum(1 for f in findings if f.get("severity") == "info")
    result["findings"] = findings
    result["summary"] = {"errors": errors, "warnings": warns, "infos": infos}
    if str(result.get("status") or "").lower() != "ack":
        result["status"] = "pass" if errors == 0 else "fail"
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return attach_decision(result)


def run_full_critique(
    run_dir: Path,
    *,
    settings: dict[str, Any] | None = None,
    structural_only: bool = False,
    timeout: int = 180,
    invoke_llm: bool = True,
) -> dict[str, Any]:
    """Coverage helper + optional LLM; skip below complexity bar."""
    run_dir = run_dir.expanduser().resolve()
    if settings is None:
        settings = resolve_plan_critique(run_dir)
    run = _load_yaml_safe(run_dir / "run.yaml") or {}
    task_files = sorted((run_dir / "tasks").glob("*.yaml")) if (run_dir / "tasks").is_dir() else []
    loaded_tasks: list[dict[str, Any]] = []
    for path in task_files:
        task = _load_yaml_safe(path)
        if isinstance(task, dict):
            loaded_tasks.append(task)
    try:
        score = int(run.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    applies, why = critique_should_run(
        run, _write_task_count(loaded_tasks), settings
    )
    if not applies:
        return _skipped_critique(
            run_dir, reason=why, score=score, task_count=len(loaded_tasks)
        )
    structural = structural_critique(run_dir)
    provider = str(settings.get("provider") or "structural").strip().lower()
    model = str(settings.get("model") or "").strip()
    effort = str(settings.get("reasoning_effort") or settings.get("effort") or "low")
    needs_compress = any(
        isinstance(item, dict) and item.get("severity") in {"error", "warn"}
        for item in (structural.get("findings") or [])
    )

    if (
        not invoke_llm
        or structural_only
        or provider in {"", "structural"}
        or not settings.get("enabled", True)
        or not needs_compress
    ):
        return merge_llm_into_critique(
            structural, None, provider="structural", model=""
        )

    try:
        from plan_critique_llm import (  # type: ignore  # noqa: WPS433
            LlmCritiqueError,
            invoke_llm_critique,
        )
    except ImportError:
        # Same-directory import when launched as script
        import sys

        bin_dir = str(Path(__file__).resolve().parent)
        if bin_dir not in sys.path:
            sys.path.insert(0, bin_dir)
        from plan_critique_llm import (  # type: ignore
            LlmCritiqueError,
            invoke_llm_critique,
        )

    try:
        llm_payload = invoke_llm_critique(
            run_dir,
            structural,
            provider=provider,
            model=model,
            effort=effort,
            timeout=timeout,
            service_tier=str(settings.get("service_tier") or "standard"),
            agent=str(settings.get("agent") or ""),
        )
        return merge_llm_into_critique(
            structural, llm_payload, provider=provider, model=model
        )
    except Exception as exc:  # noqa: BLE001 — surface as llm_pass error
        # LlmCritiqueError and unexpected failures both become soft findings
        err = str(exc)
        if "LlmCritiqueError" not in type(exc).__name__ and not isinstance(
            exc, Exception
        ):
            err = f"{type(exc).__name__}: {exc}"
        return merge_llm_into_critique(
            structural,
            None,
            provider=provider,
            model=model,
            llm_error=err,
        )


def critique_to_markdown(result: dict[str, Any]) -> str:
    """Human-readable critique report with PM decision banner."""
    decision = str(result.get("decision") or compute_decision(result))
    pm_action = str(result.get("pm_action") or PM_ACTION.get(decision, ""))
    llm = result.get("llm_pass") if isinstance(result.get("llm_pass"), dict) else {}
    lines = [
        "# Coverage auditor",
        "",
        f"## PM decision: **`{decision}`**",
        "",
        pm_action,
        "",
        f"- engine: `{result.get('engine')}`",
        f"- status: **{result.get('status')}**",
        f"- score: {result.get('score')}  ·  tasks: {result.get('task_count')}",
        f"- errors: {result.get('summary', {}).get('errors', 0)}  ·  "
        f"warnings: {result.get('summary', {}).get('warnings', 0)}",
        f"- llm_pass: `{llm.get('status', 'n/a')}`"
        + (f" ({llm.get('provider')}" + (f"/{llm.get('model')}" if llm.get("model") else "") + ")" if llm.get("provider") else ""),
        "",
    ]
    if llm.get("summary"):
        lines.append(f"**LLM summary:** {llm['summary']}")
        lines.append("")
    findings = result.get("findings") or []
    if not findings:
        lines.append("No findings. Plan looks dispatch-ready.")
        lines.append("")
        return "\n".join(lines)

    order = {"error": 0, "warn": 1, "info": 2}
    sorted_f = sorted(
        findings,
        key=lambda f: (order.get(str(f.get("severity")), 9), str(f.get("code"))),
    )
    for f in sorted_f:
        sev = str(f.get("severity", "info")).upper()
        loc = f.get("path") or f.get("task_id") or "—"
        lines.append(f"## [{sev}] {f.get('title')}")
        lines.append("")
        lines.append(f"- code: `{f.get('code')}`")
        lines.append(f"- where: `{loc}`")
        if f.get("action"):
            lines.append(f"- action: `{f.get('action')}`")
        if f.get("source"):
            lines.append(f"- source: `{f.get('source')}`")
        lines.append(f"- {f.get('detail')}")
        lines.append("")
    if decision == "revise_required" or result.get("status") == "fail":
        lines.append("---")
        lines.append("")
        lines.append(
            "Fix findings, re-run `plan-critique`, or acknowledge with "
            "`plan-critique --ack --note '...'` when mode is `gate`."
        )
        lines.append("")
    return "\n".join(lines)


def write_critique_artifacts(
    run_dir: Path,
    result: dict[str, Any],
    *,
    recommended_provider: str = "structural",
    recommended_model: str = "",
) -> tuple[Path, Path, Path | None]:
    """Write critique.json, critique.md (+ optional prompt for debugging)."""
    result = attach_decision(result)
    art = run_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    json_path = art / "critique.json"
    md_path = art / "critique.md"
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(critique_to_markdown(result), encoding="utf-8")

    prompt_path: Path | None = None
    # Keep a debug prompt only when LLM was requested but not successfully run
    llm = result.get("llm_pass") if isinstance(result.get("llm_pass"), dict) else {}
    stale_prompt = art / "critique-prompt.md"
    if llm.get("status") == "ok" and stale_prompt.is_file():
        try:
            stale_prompt.unlink()
        except OSError:
            pass
    elif (
        recommended_provider
        and recommended_provider != "structural"
        and llm.get("status") in {None, "skipped", "error"}
    ):
        prompt_path = stale_prompt
        try:
            from plan_critique_llm import build_llm_prompt  # type: ignore

            prompt_path.write_text(
                build_llm_prompt(
                    run_dir,
                    result,
                    provider=recommended_provider,
                    model=recommended_model,
                ),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            prompt_path.write_text(
                _llm_prompt_fallback(
                    run_dir, result, recommended_provider, recommended_model
                ),
                encoding="utf-8",
            )
    return json_path, md_path, prompt_path


def _llm_prompt_fallback(
    run_dir: Path,
    result: dict[str, Any],
    provider: str,
    model: str,
) -> str:
    return (
        f"# LLM plan critique pass (fallback prompt)\n\n"
        f"Provider: **{provider}**"
        + (f" · model `{model}`" if model else "")
        + "\n\n"
        "You are a read-only plan reviewer. Do **not** edit product code.\n"
        "Review PLAN.md, SPEC.md, and tasks/*.yaml. Reply with JSON "
        "{verdict, summary, findings[]}.\n\n"
        + critique_to_markdown(result)
        + f"\nRun dir: `{run_dir}`\n"
    )


def load_critique(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "artifacts" / "critique.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # Backfill decision for older artifacts
    if "decision" not in data:
        attach_decision(data)
    return data


def ack_critique(run_dir: Path, *, note: str, by: str = "pm") -> dict[str, Any]:
    """Mark a failed critique as acknowledged for gate mode."""
    result = load_critique(run_dir)
    if result is None:
        result = structural_critique(run_dir)
    result["status"] = "ack"
    result["acked_by"] = by
    result["ack_note"] = note
    result["acked_at"] = datetime.now(timezone.utc).isoformat()
    attach_decision(result)
    write_critique_artifacts(run_dir, result)
    return result


def critique_gate_errors(run_dir: Path, settings: dict[str, Any]) -> list[str]:
    """Return validation errors for pre-dispatch when plan_critique is enabled."""
    if not settings.get("enabled"):
        return []
    mode = str(settings.get("mode") or "advisory").lower()
    result = load_critique(run_dir)
    if result is None:
        if mode == "gate":
            return [
                "plan_critique mode=gate requires artifacts/critique.json — "
                "run `plan-critique --run-dir <run>` before pre-dispatch"
            ]
        # advisory: soft — no hard fail
        return []
    status = str(result.get("status") or "").lower()
    decision = str(result.get("decision") or compute_decision(result)).lower()
    if mode == "gate" and status not in {"pass", "ack"}:
        errors = (result.get("summary") or {}).get("errors", "?")
        return [
            f"plan_critique gate blocked: critique status={status!r} "
            f"decision={decision!r} (errors={errors}). Fix PLAN/SPEC/tasks and "
            f"re-run plan-critique, or `plan-critique --ack --note '...'` "
            f"with an explicit reason"
        ]
    if mode == "gate" and decision == "revise_required" and status != "ack":
        return [
            f"plan_critique gate blocked: decision=revise_required. "
            f"Apply pm_action from artifacts/critique.json, re-run plan-critique"
        ]
    return []
