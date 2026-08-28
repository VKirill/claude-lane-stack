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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BIN = Path(__file__).resolve().parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))

from routing_profile import resolve_agy_effort  # noqa: E402

KNOWN_STAGE_PROVIDERS = frozenset(
    {"structural", "kimi", "qwen", "agy", "grok", "codex", "cursor", "opencode"}
)
CRITIQUE_MODES = frozenset({"advisory", "gate"})
CRITIQUE_DECISIONS = frozenset({"ship", "revise", "revise_required"})
SPECIALIST_WHEN = frozenset({"high_risk", "always"})

PM_ACTION = {
    "ship": (
        "No reply needed. Dispatch after `run-validate --phase pre-dispatch`."
    ),
    "revise": (
        "Reply every warn/error id in artifacts/critique-reply.json "
        "(`take` or `skip` + note). Then dispatch. "
        "Bulk skip: `plan-critique --ack --note '…'`."
    ),
    "revise_required": (
        "Reply every error/warn id in artifacts/critique-reply.json "
        "before writers. `take` = edit PLAN/SPEC/tasks and re-run "
        "`plan-critique`. `skip` needs a note. "
        "Bulk: `plan-critique --ack --note '…'`."
    ),
}
_NOISE_PATH_PREFIXES = ("wiki/", "TODO/", "docs/")
_DEFAULT_FINDING_ACTION = {
    "owns_gap": "add_owns",
    "plan_path_unowned": "add_owns",
    "owns_overlap": "split_task",
    "fat_task": "split_task",
    "gold_plate": "drop_scope",
    "verify_heavy": "note",
    "verify_l2": "note",
    "missing_invariant": "fix_spec",
    "owns_empty": "fix_spec",
    "verify_missing": "fix_spec",
    "plan_missing": "fix_spec",
    "no_tasks": "fix_spec",
    "task_parse": "fix_spec",
    "bad_dag": "note",
}

DEFAULT_MODELS = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.7-flash-high",
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
    "agy": "high",
    "codex": "max",
    "cursor": "medium",
    "opencode": "medium",
}
# Cheap plan-critique pass defaults.
DEFAULT_CRITIQUE_EFFORTS = {
    "qwen": "low",
    "kimi": "low",
    "grok": "low",
    "agy": "high",
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
    "agy": "high",
}
SERVICE_TIER_STAGE_PROVIDERS = frozenset({"codex", "cursor"})
MEMORY_AUDIENCES = frozenset({"owner", "subagent", "export"})
MEMORY_SEARCH_ENGINES = frozenset({"auto", "fts5", "bm25"})
DEFAULT_MEMORY_CORE_BUDGET = 3072
DEFAULT_MEMORY_NOTE_BUDGET = 8000
DEFAULT_MEMORY_INDEX_BUDGET = 65536
DEFAULT_MEMORY_CONTEXT_BUDGET = 2500
DEFAULT_DOCS_MODEL = "gpt-5.6-luna"
DEFAULT_DOCS_EFFORT = "max"
DEFAULT_DOCS_PAGE_CAP = 0
DEFAULT_DOCS_SINCE = "yesterday"
DEFAULT_DOCS_HOUR = 5
DOCS_SINCE_CHOICES = ("yesterday", "24 hours ago", "7 days ago")
DEFAULT_OPENCODE_WRITE_AGENT = "lane-writer"
DEFAULT_OPENCODE_CRITIQUE_AGENT = "lane-critic"
DEFAULT_OPENCODE_REVIEW_AGENT = "lane-reviewer"
OPENCODE_STOCK_AGENTS = frozenset(
    {
        "build",
        "plan",
        "general",
        "explore",
        "scout",
        "compaction",
        "title",
        "summary",
    }
)

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


STAGE_ORDER = (
    "plan_critique",
    "write",
    "night_review",
    "specialist",
    "onboard",
    "memory",
    "docs",
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
            "provider": "agy",
            "model": DEFAULT_MODELS.get("agy", "gemini-3.7-flash-high"),
            "reasoning_effort": DEFAULT_CRITIQUE_EFFORTS.get("agy", "high"),
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
        "memory": {
            "enabled": False,
            "maintain": True,
            "inject": True,
            "provider": "codex",
            "model": DEFAULT_ONBOARD_MODEL,
            "reasoning_effort": DEFAULT_ONBOARD_EFFORT,
            "service_tier": "standard",
            "audience": "subagent",
            "search_engine": "auto",
            "core_budget": 3072,
            "note_budget": 8000,
            "index_budget": 65536,
            "context_budget": 2500,
            "personal_bot": "",
        },
        "docs": {
            "enabled": False,
            "maintain": True,
            "provider": "codex",
            "model": DEFAULT_DOCS_MODEL,
            "reasoning_effort": DEFAULT_DOCS_EFFORT,
            "service_tier": "fast",
            "page_cap": DEFAULT_DOCS_PAGE_CAP,
            "since": DEFAULT_DOCS_SINCE,
            "hour": DEFAULT_DOCS_HOUR,
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


def resolve_opencode_agent(stage_id: str, current: str = "") -> str:
    """Role default, unless the user already picked a non-stock agent."""
    default = default_opencode_agent(stage_id)
    raw = (current or "").strip()
    if not raw or raw in OPENCODE_STOCK_AGENTS:
        return default
    return raw


def _opencode_agent(block: dict[str, Any], *, default: str) -> dict[str, str]:
    raw = str(block.get("agent") or "").strip()
    if not raw or raw in OPENCODE_STOCK_AGENTS:
        raw = default
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
    memory = raw.get("memory") if isinstance(raw.get("memory"), dict) else {}
    docs = raw.get("docs") if isinstance(raw.get("docs"), dict) else {}

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

    # memory — SMA-style fact corpus; off unless the project opts in
    m_provider = str(memory.get("provider") or "codex").strip()
    if m_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        m_provider = "codex"
    m_default_model = (
        DEFAULT_ONBOARD_MODEL
        if m_provider == "codex"
        else DEFAULT_MODELS.get(m_provider, DEFAULT_ONBOARD_MODEL)
    )
    m_aud = str(memory.get("audience") or "subagent").strip().lower()
    if m_aud not in MEMORY_AUDIENCES:
        m_aud = "subagent"
    m_engine = str(memory.get("search_engine") or "auto").strip().lower()
    if m_engine not in MEMORY_SEARCH_ENGINES:
        m_engine = "auto"

    def _memory_budget(key: str, default: int) -> int:
        n = _as_int(memory.get(key), default)
        return default if n <= 0 else n

    base["memory"] = {
        "enabled": _as_bool(memory.get("enabled"), False),
        "maintain": _as_bool(memory.get("maintain"), True),
        "inject": _as_bool(memory.get("inject"), True),
        "provider": m_provider,
        "model": str(memory.get("model") or m_default_model).strip(),
        "reasoning_effort": _effort_from_block(
            memory, DEFAULT_ONBOARD_EFFORTS.get(m_provider, DEFAULT_ONBOARD_EFFORT)
        ),
        "service_tier": _normalize_service_tier(memory, m_provider),
        "audience": m_aud,
        "search_engine": m_engine,
        "core_budget": _memory_budget("core_budget", DEFAULT_MEMORY_CORE_BUDGET),
        "note_budget": _memory_budget("note_budget", DEFAULT_MEMORY_NOTE_BUDGET),
        "index_budget": _memory_budget("index_budget", DEFAULT_MEMORY_INDEX_BUDGET),
        "context_budget": _memory_budget(
            "context_budget", DEFAULT_MEMORY_CONTEXT_BUDGET
        ),
        "personal_bot": str(memory.get("personal_bot") or "").strip(),
        **(
            _opencode_agent(memory, default=default_opencode_agent("memory"))
            if m_provider == "opencode"
            else {}
        ),
    }

    # docs — living docs/; off unless the project opts in
    d_provider = str(docs.get("provider") or "codex").strip()
    if d_provider not in (KNOWN_STAGE_PROVIDERS - {"structural"}):
        d_provider = "codex"
    d_default_model = (
        DEFAULT_DOCS_MODEL
        if d_provider == "codex"
        else DEFAULT_MODELS.get(d_provider, DEFAULT_DOCS_MODEL)
    )
    d_since = str(docs.get("since") or DEFAULT_DOCS_SINCE).strip() or DEFAULT_DOCS_SINCE
    if d_since not in DOCS_SINCE_CHOICES:
        d_since = DEFAULT_DOCS_SINCE
    d_cap = _as_int(docs.get("page_cap"), DEFAULT_DOCS_PAGE_CAP)
    if d_cap < 0:
        d_cap = DEFAULT_DOCS_PAGE_CAP
    d_hour = _as_int(docs.get("hour"), DEFAULT_DOCS_HOUR)
    if d_hour < 0 or d_hour > 23:
        d_hour = DEFAULT_DOCS_HOUR
    d_effort_default = (
        DEFAULT_DOCS_EFFORT
        if d_provider == "codex"
        else DEFAULT_ONBOARD_EFFORTS.get(d_provider, DEFAULT_DOCS_EFFORT)
    )
    d_tier_default = "fast" if d_provider == "codex" else "standard"
    base["docs"] = {
        "enabled": _as_bool(docs.get("enabled"), False),
        "maintain": _as_bool(docs.get("maintain"), True),
        "provider": d_provider,
        "model": str(docs.get("model") or d_default_model).strip(),
        "reasoning_effort": _effort_from_block(docs, d_effort_default),
        "service_tier": (
            _normalize_service_tier(docs, d_provider)
            if "service_tier" in docs or "fast_mode" in docs
            else _normalize_service_tier(
                {"service_tier": d_tier_default}, d_provider
            )
        ),
        "page_cap": d_cap,
        "since": d_since,
        "hour": d_hour,
        **(
            _opencode_agent(docs, default=default_opencode_agent("docs"))
            if d_provider == "opencode"
            else {}
        ),
    }
    for block in base.values():
        if isinstance(block, dict) and str(block.get("provider") or "") == "agy":
            block["reasoning_effort"] = resolve_agy_effort(
                str(block.get("model") or ""),
                str(block.get("reasoning_effort") or ""),
            )
    return base


def merge_stage_seed(
    seed: dict[str, Any], existing: dict[str, Any] | None
) -> dict[str, Any]:
    """Defaults first; existing values win. New stage keys stay from seed."""
    prev = existing if isinstance(existing, dict) else {}
    out: dict[str, Any] = {}
    for name in STAGE_ORDER:
        base = seed.get(name) if isinstance(seed.get(name), dict) else {}
        old = prev.get(name) if isinstance(prev.get(name), dict) else {}
        out[name] = {**base, **old}
    return out


_STAGES_BLOCK = re.compile(r"(?ms)^stages:.*?(?=^notes:|\Z)")


def migrate_profile_stages(profile_path: Path) -> list[str]:
    """Write any new stage blocks into an existing profile. Returns names added."""
    if not profile_path.is_file():
        return []
    try:
        text = profile_path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        from routing_profile import load_routing_profile
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from routing_profile import load_routing_profile
    data = load_routing_profile(profile_path.parent)
    raw = data.get("stages") if isinstance(data.get("stages"), dict) else {}
    missing = [name for name in STAGE_ORDER if name not in raw]
    if not missing:
        return []
    writer = data.get("writer") if isinstance(data.get("writer"), dict) else {}
    lanes = data.get("lanes") if isinstance(data.get("lanes"), dict) else {}
    write_provider = str(lanes.get("main_write") or writer.get("provider") or "kimi")
    block = "\n".join(
        stages_to_yaml_lines(normalize_stages(raw, write_provider=write_provider))
    ) + "\n"
    if _STAGES_BLOCK.search(text):
        new_text = _STAGES_BLOCK.sub(block, text, count=1)
    elif re.search(r"(?m)^notes:", text):
        new_text = re.sub(r"(?m)^notes:", block + "notes:", text, count=1)
    else:
        new_text = text.rstrip() + "\n" + block
    if new_text == text:
        return []
    profile_path.write_text(new_text, encoding="utf-8")
    return missing


def stages_to_yaml_lines(stages: dict[str, Any]) -> list[str]:
    """Emit YAML lines for the stages: block (no leading stages: key)."""
    stages = normalize_stages(stages)
    lines: list[str] = ["stages:"]
    for name in STAGE_ORDER:
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


def resolve_memory(start: Path) -> dict[str, Any]:
    """Load stages.memory (opt-in SMA corpus). Default enabled=false."""
    from routing_profile import load_routing_profile  # local import — same bin/

    profile = load_routing_profile(start)
    stages = load_stages_from_profile(profile)
    block = stages.get("memory") or {}
    return {
        **block,
        "stages": stages,
        "profile_path": profile.get("_path"),
    }


def resolve_docs(start: Path) -> dict[str, Any]:
    """Load stages.docs (opt-in living docs/). Default enabled=false."""
    from routing_profile import load_routing_profile  # local import — same bin/

    profile = load_routing_profile(start)
    stages = load_stages_from_profile(profile)
    block = stages.get("docs") or {}
    return {
        **block,
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


def _is_noise_path(path: str) -> bool:
    rel = _norm_own(path)
    if any(rel.startswith(prefix) for prefix in _NOISE_PATH_PREFIXES):
        return True
    return "/docs/" in rel


def _finding_key(finding: dict[str, Any]) -> str:
    raw = str(
        finding.get("path") or finding.get("task_id") or finding.get("title") or "x"
    )
    key = re.sub(r"[^\w./-]+", "_", raw).strip("._")
    return key[:80] or "x"


def assign_finding_id(finding: dict[str, Any]) -> str:
    source = str(finding.get("source") or "structural")
    code = str(finding.get("code") or "note")
    return f"{source}:{code}:{_finding_key(finding)}"


def _finding(
    severity: str,
    code: str,
    title: str,
    detail: str,
    *,
    path: str | None = None,
    task_id: str | None = None,
    source: str = "structural",
    action: str | None = None,
) -> dict[str, Any]:
    finding = {
        "severity": severity if severity in {"error", "warn", "info"} else "warn",
        "code": code,
        "title": title,
        "detail": detail,
        "path": path,
        "task_id": task_id,
        "source": source,
        "action": action or _DEFAULT_FINDING_ACTION.get(code, "note"),
    }
    if code in {"owns_gap", "plan_path_unowned"} and _is_noise_path(path or ""):
        finding["severity"] = "info"
    finding["id"] = assign_finding_id(finding)
    return finding


def stamp_findings(result: dict[str, Any]) -> dict[str, Any]:
    """Stable ids, noise demote, summary refresh. Safe to call twice."""
    findings: list[dict[str, Any]] = [
        f for f in (result.get("findings") or []) if isinstance(f, dict)
    ]
    for finding in findings:
        code = str(finding.get("code") or "note")
        if not finding.get("source"):
            finding["source"] = "structural"
        if not finding.get("action"):
            finding["action"] = _DEFAULT_FINDING_ACTION.get(code, "note")
        if code in {"owns_gap", "plan_path_unowned"} and _is_noise_path(
            str(finding.get("path") or "")
        ):
            finding["severity"] = "info"
        finding["id"] = assign_finding_id(finding)
    result["findings"] = findings
    errors = sum(1 for f in findings if f.get("severity") == "error")
    warns = sum(1 for f in findings if f.get("severity") == "warn")
    infos = sum(1 for f in findings if f.get("severity") == "info")
    result["summary"] = {"errors": errors, "warnings": warns, "infos": infos}
    if str(result.get("status") or "").lower() != "ack":
        result["status"] = "pass" if errors == 0 else "fail"
    return result


def inbox_required(result: dict[str, Any]) -> list[dict[str, Any]]:
    stamp_findings(result)
    return [
        f
        for f in (result.get("findings") or [])
        if isinstance(f, dict) and f.get("severity") in {"error", "warn"}
    ]


def load_critique_reply(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "artifacts" / "critique-reply.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_critique_reply(run_dir: Path, items: list[dict[str, Any]]) -> Path:
    art = run_dir / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    path = art / "critique-reply.json"
    path.write_text(
        json.dumps({"schema_version": 1, "items": items}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return path


def critique_inbox_errors(run_dir: Path, result: dict[str, Any]) -> list[str]:
    needed = inbox_required(result)
    if not needed:
        return []
    reply = load_critique_reply(run_dir)
    items = {
        str(item.get("id")): item
        for item in ((reply or {}).get("items") or [])
        if isinstance(item, dict) and item.get("id")
    }
    missing: list[str] = []
    bad: list[str] = []
    for finding in needed:
        fid = str(finding.get("id") or "")
        item = items.get(fid)
        if item is None:
            missing.append(fid)
            continue
        verdict = str(item.get("verdict") or "").strip().lower()
        note = str(item.get("note") or "").strip()
        if verdict not in {"take", "skip"}:
            bad.append(f"{fid}: verdict must be take|skip")
        elif verdict == "skip" and not note:
            bad.append(f"{fid}: skip requires note")
    errors: list[str] = []
    if missing:
        shown = ", ".join(missing[:8])
        extra = f" (+{len(missing) - 8})" if len(missing) > 8 else ""
        errors.append(
            "plan_critique inbox open — write artifacts/critique-reply.json "
            f"take|skip for: {shown}{extra}"
        )
    errors.extend(f"plan_critique reply {msg}" for msg in bad)
    return errors


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
    stamp_findings(result)
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
    """Attach LLM review. New findings join the inbox (source=llm)."""
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
            "verdict": llm_payload.get("verdict"),
            "summary": _clean_llm_summary(str(llm_payload.get("summary") or "")),
        }
        raw_llm = llm_payload.get("findings")
        if isinstance(raw_llm, list):
            for item in raw_llm[:7]:
                if not isinstance(item, dict):
                    continue
                findings.append(
                    _finding(
                        str(item.get("severity") or "warn"),
                        str(item.get("code") or "note"),
                        str(item.get("title") or "Plan remark")[:120],
                        str(item.get("detail") or "")[:400],
                        path=str(item.get("path") or "") or None,
                        task_id=str(item.get("task_id") or "") or None,
                        source="llm",
                        action=str(item.get("action") or "") or None,
                    )
                )

    result["findings"] = findings
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
    if provider == "agy":
        effort = resolve_agy_effort(model, effort)
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
        if f.get("id"):
            lines.append(f"- id: `{f.get('id')}`")
        lines.append(f"- code: `{f.get('code')}`")
        lines.append(f"- where: `{loc}`")
        if f.get("action"):
            lines.append(f"- action: `{f.get('action')}`")
        if f.get("source"):
            lines.append(f"- source: `{f.get('source')}`")
        lines.append(f"- {f.get('detail')}")
        lines.append("")
    needed = inbox_required(result)
    if needed:
        lines.append("---")
        lines.append("")
        lines.append(
            f"{len(needed)} inbox item(s). Write `artifacts/critique-reply.json` "
            "with `{id, verdict: take|skip, note}` per id. "
            "`skip` requires note. Bulk: `plan-critique --ack --note '...'`."
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
    try:
        from usage_ledger import record_critique_result

        record_critique_result(
            run_dir,
            result,
            mode=str((resolve_plan_critique(run_dir) or {}).get("mode") or ""),
        )
    except Exception:
        pass

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
    """Bulk-skip remaining inbox items (same note on every id)."""
    result = load_critique(run_dir)
    if result is None:
        result = structural_critique(run_dir)
    result["status"] = "ack"
    result["acked_by"] = by
    result["ack_note"] = note
    result["acked_at"] = datetime.now(timezone.utc).isoformat()
    attach_decision(result)
    write_critique_reply(
        run_dir,
        [
            {"id": str(f.get("id")), "verdict": "skip", "note": note}
            for f in inbox_required(result)
        ],
    )
    write_critique_artifacts(run_dir, result)
    return result


def critique_gate_errors(run_dir: Path, settings: dict[str, Any]) -> list[str]:
    """Block dispatch on unreplied inbox ids when plan_critique is enabled."""
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
        return []
    return critique_inbox_errors(run_dir, result)
