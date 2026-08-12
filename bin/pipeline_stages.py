#!/usr/bin/env python3
"""Pipeline stages for Claude Lane Stack — plan critique + per-agent routing.

Source of truth lives under ``stages:`` in ``.agents/routing.profile.yaml``
(written by agents-doctor / adoc). Stages are *roles in the conveyor*, not
Claude subagents:

  plan (PM, fixed) → plan_critique → write → verify (L1, fixed) → night_review
                                      ↘ optional specialist (read-only)
  side role: onboard (project passport; adoc agent/model/effort/service_tier)

Structural critique always runs when plan_critique is enabled. When
provider ≠ structural, ``plan-critique`` also runs a one-shot LLM pass and
writes a PM ``decision`` (ship | revise | revise_required) the orchestrator
must honor before dispatch.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KNOWN_STAGE_PROVIDERS = frozenset(
    {"structural", "kimi", "qwen", "agy", "grok", "codex", "cursor"}
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
        "Review findings; prefer fixing PLAN/SPEC/tasks, then re-run "
        "`plan-critique`. Residual warnings may ship only with an explicit "
        "reason in chat (advisory) or `plan-critique --ack --note '…'` (gate)."
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
}
# Cheap plan-critique pass defaults.
DEFAULT_CRITIQUE_EFFORTS = {
    "qwen": "low",
    "kimi": "low",
    "grok": "low",
    "agy": "low",
    "cursor": "low",
    "codex": "high",
    "structural": "low",
}
DEFAULT_EFFORTS = DEFAULT_CRITIQUE_EFFORTS  # alias for critique
# project-onboard / project-onboarder defaults (adoc Stages → onboard).
DEFAULT_ONBOARD_MODEL = "gpt-5.6-terra"
DEFAULT_ONBOARD_EFFORT = "high"
DEFAULT_ONBOARD_EFFORTS = {
    "codex": "high",
    "cursor": "high",
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
}
SERVICE_TIER_STAGE_PROVIDERS = frozenset({"codex", "cursor"})

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
        "reasoning_effort": str(
            pc.get("reasoning_effort")
            or pc.get("effort")
            or DEFAULT_EFFORTS.get(pc_provider, "low")
        ).strip(),
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
        "reasoning_effort": str(
            write.get("reasoning_effort")
            or write.get("effort")
            or DEFAULT_WRITE_EFFORTS.get(w_provider, "medium")
        ).strip(),
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
        "reasoning_effort": str(
            night.get("reasoning_effort")
            or night.get("effort")
            or DEFAULT_WRITE_EFFORTS.get(n_provider, "medium")
        ).strip(),
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
        "reasoning_effort": str(
            spec.get("reasoning_effort")
            or spec.get("effort")
            or DEFAULT_EFFORTS.get(s_provider, "high")
        ).strip(),
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
    o_tier_raw = onboard.get("service_tier")
    if o_tier_raw is None and "fast_mode" in onboard:
        o_tier_raw = "fast" if _as_bool(onboard.get("fast_mode"), False) else "standard"
    o_tier = str(o_tier_raw or "standard").strip().lower()
    if o_tier not in {"standard", "fast"}:
        o_tier = "standard"
    if o_provider not in SERVICE_TIER_STAGE_PROVIDERS:
        o_tier = "standard"
    base["onboard"] = {
        "provider": o_provider,
        "model": str(onboard.get("model") or o_default_model).strip(),
        "reasoning_effort": str(
            onboard.get("reasoning_effort")
            or onboard.get("effort")
            or DEFAULT_ONBOARD_EFFORTS.get(o_provider, DEFAULT_ONBOARD_EFFORT)
        ).strip(),
        "service_tier": o_tier,
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
            # service_tier only meaningful for codex/cursor onboard
            if (
                name == "onboard"
                and key == "service_tier"
                and str(block.get("provider") or "") not in SERVICE_TIER_STAGE_PROVIDERS
            ):
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
    else:
        try:
            plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(
                _finding(
                    "error",
                    "plan_unreadable",
                    "PLAN.md unreadable",
                    str(exc),
                    path="PLAN.md",
                )
            )
            plan_text = ""
        body = re.sub(r"(?m)^#.*$", "", plan_text).strip()
        if len(body) < 80:
            findings.append(
                _finding(
                    "error" if score >= 3 else "warn",
                    "plan_thin",
                    "PLAN.md is too thin",
                    "Add goals, out-of-scope, verification plan (L1 vs L2), and risk notes.",
                    path="PLAN.md",
                )
            )
        lowered = plan_text.lower()
        if "out of scope" not in lowered and "out-of-scope" not in lowered:
            findings.append(
                _finding(
                    "warn",
                    "plan_no_oos",
                    "PLAN.md lacks out-of-scope",
                    "Explicit non-goals reduce OFF-SPEC edits.",
                    path="PLAN.md",
                )
            )
        if "verif" not in lowered and "l1" not in lowered and "l2" not in lowered:
            findings.append(
                _finding(
                    "warn",
                    "plan_no_verify",
                    "PLAN.md lacks verification notes",
                    "Spell out L1 (per-task) vs L2 (pre-merge) checks.",
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

    # SPEC substance (same bar as run-validate for multi-task / high score)
    if score >= 7 or task_count >= 2:
        spec_path = run_dir / "SPEC.md"
        if not spec_path.is_file():
            findings.append(
                _finding(
                    "error",
                    "spec_missing",
                    "SPEC.md required",
                    "Required when score≥7 or ≥2 tasks.",
                    path="SPEC.md",
                )
            )
        else:
            try:
                spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                findings.append(
                    _finding(
                        "error",
                        "spec_unreadable",
                        "SPEC.md unreadable",
                        str(exc),
                        path="SPEC.md",
                    )
                )
                spec_text = ""
            lowered = spec_text.lower()
            for marker in _SPEC_STUB_MARKERS:
                if marker in lowered:
                    findings.append(
                        _finding(
                            "error",
                            "spec_stub",
                            "SPEC.md is still a template",
                            "Fill Goal, Interfaces, Invariants, Out of scope, Definition of done.",
                            path="SPEC.md",
                        )
                    )
                    break
            body = re.sub(r"(?m)^#.*$", "", spec_text).strip()
            if len(body) < 120:
                findings.append(
                    _finding(
                        "error",
                        "spec_thin",
                        "SPEC.md is too thin",
                        "Multi-task / high-score runs need a professional SPEC body.",
                        path="SPEC.md",
                    )
                )
            for heading in (
                "goal",
                "interface",
                "invariant",
                "out of scope",
                "definition of done",
            ):
                if heading not in lowered and heading.replace(" ", "-") not in lowered:
                    # soft — section titles vary
                    pass

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
        elif isinstance(owns, list) and len(owns) >= 12:
            findings.append(
                _finding(
                    "warn",
                    "owns_large",
                    f"Task {tid}: owns_paths is large ({len(owns)})",
                    "Prefer split when owns_paths ≥ 12 entries.",
                    path=str(path.relative_to(run_dir)),
                    task_id=tid,
                )
            )

        objective = str(task.get("objective") or "").strip()
        if len(objective) < 24:
            findings.append(
                _finding(
                    "warn",
                    "objective_thin",
                    f"Task {tid}: thin objective",
                    "Objective should be one clear shippable outcome.",
                    path=str(path.relative_to(run_dir)),
                    task_id=tid,
                )
            )
        elif _VAGUE_OBJECTIVE.match(objective) and len(objective) < 48:
            findings.append(
                _finding(
                    "info",
                    "objective_vague",
                    f"Task {tid}: vague objective start",
                    "Prefer concrete product outcomes over 'fix/improve'.",
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

        deps = task.get("depends_on") or []
        if isinstance(deps, list) and len(deps) > 3:
            findings.append(
                _finding(
                    "info",
                    "depends_many",
                    f"Task {tid}: many depends_on ({len(deps)})",
                    "Check whether every edge is a real compile/data dependency.",
                    path=str(path.relative_to(run_dir)),
                    task_id=tid,
                )
            )

    # Serial-looking DAG without real parallel opportunity note
    if task_count >= 3:
        independent = 0
        for task in tasks:
            deps = task.get("depends_on") or []
            if not deps:
                independent += 1
        if independent <= 1:
            findings.append(
                _finding(
                    "info",
                    "dag_serial",
                    "Mostly serial DAG",
                    "If owns_paths are disjoint, drop false depends_on to unlock parallel slots.",
                    path="tasks/",
                )
            )

    errors = sum(1 for f in findings if f["severity"] == "error")
    warns = sum(1 for f in findings if f["severity"] == "warn")
    status = "pass" if errors == 0 else "fail"
    result = {
        "schema_version": 1,
        "engine": "structural",
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
    llm = result.get("llm_pass") if isinstance(result.get("llm_pass"), dict) else {}
    llm_verdict = str(llm.get("verdict") or "").lower()
    if status == "fail" or errors > 0 or llm_verdict == "revise_required":
        return "revise_required"
    if warns > 0 or llm_verdict == "revise":
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


def _finding_key(f: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(f.get("code") or ""),
        str(f.get("path") or ""),
        str(f.get("task_id") or ""),
    )


def merge_llm_into_critique(
    structural: dict[str, Any],
    llm_payload: dict[str, Any] | None,
    *,
    provider: str,
    model: str = "",
    llm_error: str | None = None,
) -> dict[str, Any]:
    """Combine structural + LLM findings; recompute status/decision."""
    result = dict(structural)
    findings: list[dict[str, Any]] = [
        dict(f) for f in (structural.get("findings") or []) if isinstance(f, dict)
    ]
    seen = {_finding_key(f) for f in findings}

    if llm_error:
        result["engine"] = "structural+llm"
        result["llm_pass"] = {
            "status": "error",
            "provider": provider,
            "model": model or "",
            "error": llm_error,
            "verdict": None,
        }
        findings.append(
            _finding(
                "warn",
                "llm_pass_failed",
                f"LLM plan critique failed ({provider})",
                llm_error[:800],
                path="artifacts/critique.json",
            )
        )
    elif llm_payload is None:
        result["llm_pass"] = {
            "status": "skipped",
            "provider": provider or "structural",
            "model": model or "",
            "verdict": None,
        }
        if provider and provider != "structural":
            result["engine"] = "structural"
        else:
            result["engine"] = "structural"
    else:
        result["engine"] = "structural+llm"
        llm_findings_raw = llm_payload.get("findings") or []
        added = 0
        for item in llm_findings_raw:
            if not isinstance(item, dict):
                continue
            sev = str(item.get("severity") or "warn").lower()
            if sev not in {"error", "warn", "info"}:
                sev = "warn"
            code = str(item.get("code") or "llm_finding").strip() or "llm_finding"
            if not code.startswith("llm_") and code not in {
                "plan_thin",
                "spec_stub",
                "owns_empty",
                "verify_missing",
                "verify_heavy",
                "objective_thin",
            }:
                code = f"llm_{code}"
            f = _finding(
                sev,
                code,
                str(item.get("title") or code)[:200],
                str(item.get("detail") or item.get("summary") or "")[:2000],
                path=str(item.get("path")) if item.get("path") else None,
                task_id=str(item.get("task_id")) if item.get("task_id") else None,
            )
            action = item.get("action")
            if action:
                f["action"] = str(action)
            f["source"] = "llm"
            key = _finding_key(f)
            if key in seen:
                continue
            seen.add(key)
            findings.append(f)
            added += 1
            if added >= 12:
                break
        result["llm_pass"] = {
            "status": "ok",
            "provider": provider,
            "model": model or str(llm_payload.get("model") or ""),
            "verdict": str(llm_payload.get("verdict") or ""),
            "summary": str(llm_payload.get("summary") or ""),
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
    """Structural + optional LLM pass; always attaches decision."""
    run_dir = run_dir.expanduser().resolve()
    if settings is None:
        settings = resolve_plan_critique(run_dir)
    structural = structural_critique(run_dir)
    provider = str(settings.get("provider") or "structural").strip().lower()
    model = str(settings.get("model") or "").strip()
    effort = str(settings.get("reasoning_effort") or settings.get("effort") or "low")

    if (
        not invoke_llm
        or structural_only
        or provider in {"", "structural"}
        or not settings.get("enabled", True)
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
        "# Plan critique",
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
