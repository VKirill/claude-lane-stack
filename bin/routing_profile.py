#!/usr/bin/env python3
"""Load project writer settings from agents-doctor routing.profile.yaml.

agents-doctor / adoc is the source of truth for which coder, model, and effort
the orchestrator and run-controller use. This module is shared by run-controller
and run-validate (stdlib only).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

KNOWN_WRITERS = frozenset({"kimi", "qwen", "agy", "grok", "codex", "cursor"})
# Where writers edit code for a daytime run.
# in_place  — project_cwd = repo (main checkout); PM commits main
# worktree  — always wt-create → project_cwd = .worktrees/<slug>
# auto      — worktree when score high or multi-write (skill default)
WORKSPACE_MODES = frozenset({"in_place", "worktree", "auto"})
DEFAULT_WORKSPACE_MODE = "auto"
DEFAULT_WORKTREE_MIN_SCORE = 4
DEFAULT_SESSION_MAX_TASKS = 10
HARD_SESSION_MAX_TASKS = 10
DEFAULT_MODELS = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.6-flash-high",
    "codex": "gpt-5.6-luna",
    "cursor": "composer-2.5",
}
DEFAULT_EFFORTS = {
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
    "codex": "max",
    "cursor": "medium",
}
# Speed tier: Codex ChatGPT credits + Cursor model -fast siblings / [fast=…].
SERVICE_TIERS = frozenset({"standard", "fast"})
DEFAULT_SERVICE_TIER = "standard"
# Providers that honor writer.service_tier / --service-tier.
SERVICE_TIER_PROVIDERS = frozenset({"codex", "cursor"})


def normalize_service_tier(value: Any, *, default: str = DEFAULT_SERVICE_TIER) -> str:
    """Map truthy/legacy strings → standard|fast."""
    if value is None:
        return default
    if isinstance(value, bool):
        return "fast" if value else "standard"
    raw = str(value).strip().lower()
    if raw in SERVICE_TIERS:
        return raw
    if raw in {"1", "true", "yes", "on"}:
        return "fast"
    if raw in {"0", "false", "no", "off", "default", "normal"}:
        return "standard"
    return default


def resolve_cursor_model(model: str, *, service_tier: str = DEFAULT_SERVICE_TIER) -> str:
    """Map Cursor model id ↔ fast/standard (-fast sibling or [fast=…] bracket)."""
    raw = (model or "").strip()
    if not raw:
        return DEFAULT_MODELS["cursor"]
    tier = normalize_service_tier(service_tier)
    bracket = ""
    base = raw
    if raw.endswith("]") and "[" in raw:
        base, _, inside = raw[:-1].partition("[")
        base = base.strip()
        bracket = inside.strip()
    # Normalize bracket fast= flag
    parts = [p.strip() for p in bracket.split(",") if p.strip()] if bracket else []
    parts = [p for p in parts if not p.lower().startswith("fast=")]
    if tier == "fast":
        if not base.endswith("-fast"):
            base = f"{base}-fast"
        # Keep bracket only if it had other params; slug -fast is enough for most.
    else:
        if base.endswith("-fast"):
            base = base[: -len("-fast")]
        if any(p.lower().startswith("fast=") for p in (bracket.split(",") if bracket else [])):
            parts.append("fast=false")
    if parts:
        return f"{base}[{','.join(parts)}]"
    return base


def find_routing_profile(start: Path) -> Path | None:
    """Walk up from start (project_cwd or run_dir) for .agents/routing.profile.yaml."""
    cur = start.expanduser().resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        path = candidate / ".agents" / "routing.profile.yaml"
        if path.is_file():
            return path
        # stop at filesystem root
        if candidate.parent == candidate:
            break
    return None


def _parse_simple_yaml_map(text: str) -> dict[str, Any]:
    """Minimal YAML subset parser for routing.profile.yaml (no full PyYAML dependency).

    Supports top-level maps and one nested map level under stages.* (stage blocks).
    """
    result: dict[str, Any] = {
        "lanes": {},
        "writer": {},
        "workspace": {},
        "stages": {},
        "notes": [],
    }
    section: str | None = None
    stage_name: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and line.endswith(":") and " " not in line.split(":", 1)[0]:
            key = line[:-1].strip()
            section = (
                key
                if key in {"lanes", "writer", "workspace", "stages", "notes", "ui"}
                else None
            )
            stage_name = None
            if section == "stages":
                result["stages"] = result.get("stages") or {}
            continue
        # Nested stage block under stages:
        if section == "stages" and indent == 2 and line.endswith(":") and ":" == line[-1]:
            maybe = line[:-1].strip()
            if maybe and " " not in maybe:
                stage_name = maybe
                result["stages"].setdefault(stage_name, {})
                continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # strip inline comments
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        value = value.strip("\"'")
        if section == "lanes" and indent >= 2:
            result["lanes"][key] = value
        elif section == "writer" and indent >= 2:
            result["writer"][key] = value
        elif section == "workspace" and indent >= 2:
            result["workspace"][key] = value
        elif section == "ui" and indent >= 2:
            result.setdefault("ui", {})
            result["ui"][key] = value
        elif section == "stages" and stage_name and indent >= 4:
            result["stages"][stage_name][key] = value
        elif section is None and indent == 0:
            result[key] = value
    return result


def load_routing_profile(start: Path) -> dict[str, Any]:
    """Return parsed profile dict (may be empty if missing)."""
    path = find_routing_profile(start)
    if path is None:
        return {
            "_path": None,
            "lanes": {},
            "writer": {},
            "workspace": {},
            "stages": {},
        }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "_path": str(path),
            "lanes": {},
            "writer": {},
            "workspace": {},
            "stages": {},
        }
    data = _parse_simple_yaml_map(text)
    data["_path"] = str(path)
    return data


def resolve_writer(
    start: Path,
    *,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
    provider_explicit: bool = False,
) -> dict[str, Any]:
    """Resolve provider/model/effort/service_tier from CLI + agents-doctor profile.

    When provider_explicit is False and provider is None/empty, use main_write.
    ``service_tier`` applies to codex + cursor (standard|fast); others ignore it.
    """
    profile = load_routing_profile(start)
    lanes = profile.get("lanes") if isinstance(profile.get("lanes"), dict) else {}
    writer = profile.get("writer") if isinstance(profile.get("writer"), dict) else {}
    main_write = lanes.get("main_write") or writer.get("provider")

    resolved_provider = provider
    if not provider_explicit or not resolved_provider:
        if main_write in KNOWN_WRITERS:
            resolved_provider = main_write
        elif resolved_provider not in KNOWN_WRITERS:
            resolved_provider = "kimi"

    if resolved_provider not in KNOWN_WRITERS:
        resolved_provider = "kimi"

    resolved_model = model or writer.get("model") or DEFAULT_MODELS.get(
        resolved_provider
    )
    resolved_effort = (
        reasoning_effort
        or writer.get("reasoning_effort")
        or writer.get("effort")
        or DEFAULT_EFFORTS.get(resolved_provider, "medium")
    )
    # Prefer explicit CLI; else writer.service_tier / writer.fast_mode
    profile_tier = writer.get("service_tier")
    if profile_tier is None and "fast_mode" in writer:
        profile_tier = writer.get("fast_mode")
    resolved_tier = normalize_service_tier(
        service_tier if service_tier is not None else profile_tier,
        default=DEFAULT_SERVICE_TIER,
    )
    if resolved_provider not in SERVICE_TIER_PROVIDERS:
        resolved_tier = DEFAULT_SERVICE_TIER
    if resolved_provider == "cursor":
        resolved_model = resolve_cursor_model(
            str(resolved_model or DEFAULT_MODELS["cursor"]),
            service_tier=resolved_tier,
        )
    return {
        "provider": resolved_provider,
        "model": resolved_model,
        "reasoning_effort": resolved_effort,
        "service_tier": resolved_tier,
        "fast_mode": resolved_tier == "fast",
        "main_write": main_write if main_write in KNOWN_WRITERS else None,
        "profile_path": profile.get("_path"),
        "profile": profile,
    }


def lane_matches_profile(task_lane: str, main_write: str | None) -> bool:
    """Task.lane must equal project main_write when profile is configured."""
    if not main_write or main_write not in KNOWN_WRITERS:
        return True
    # Allow exact match; ignore legacy role suffixes like kimi-coder → not supported
    return task_lane.strip() == main_write


def resolve_workspace(
    start: Path,
    *,
    score: int = 0,
    write_task_count: int = 1,
) -> dict[str, Any]:
    """Resolve effective workspace mode from agents-doctor profile.

    Returns:
      mode_setting — configured value (in_place|worktree|auto)
      effective     — concrete in_place|worktree after applying auto rules
      worktree_min_score, worktree_on_multi_write — auto thresholds
    """
    profile = load_routing_profile(start)
    raw = profile.get("workspace") if isinstance(profile.get("workspace"), dict) else {}
    mode_setting = str(raw.get("mode") or DEFAULT_WORKSPACE_MODE).strip().lower()
    if mode_setting not in WORKSPACE_MODES:
        mode_setting = DEFAULT_WORKSPACE_MODE

    try:
        min_score = int(raw.get("worktree_min_score") or DEFAULT_WORKTREE_MIN_SCORE)
    except (TypeError, ValueError):
        min_score = DEFAULT_WORKTREE_MIN_SCORE
    multi_raw = str(raw.get("worktree_on_multi_write", "true")).strip().lower()
    multi = multi_raw not in {"false", "0", "no", "off"}

    if mode_setting == "in_place":
        effective = "in_place"
    elif mode_setting == "worktree":
        effective = "worktree"
    else:
        # auto — same heuristics as orchestrator-lanes skill
        if score >= min_score or (multi and write_task_count >= 2):
            effective = "worktree"
        else:
            effective = "in_place"

    return {
        "mode_setting": mode_setting,
        "effective": effective,
        "worktree_min_score": min_score,
        "worktree_on_multi_write": multi,
        "session_max_tasks": clamp_session_max_tasks(raw.get("session_max_tasks")),
        "profile_path": profile.get("_path"),
    }


def clamp_session_max_tasks(value: Any, *, default: int = DEFAULT_SESSION_MAX_TASKS) -> int:
    """1 = new session per task; 10 = hard max (same slot until rotation)."""
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(HARD_SESSION_MAX_TASKS, parsed))


def resolve_session_max_tasks(start: Path) -> int:
    """Tasks per warm writer session from adoc profile, else env, else 10."""
    profile = load_routing_profile(start)
    raw = profile.get("workspace") if isinstance(profile.get("workspace"), dict) else {}
    if raw.get("session_max_tasks") not in (None, ""):
        return clamp_session_max_tasks(raw.get("session_max_tasks"))
    env = os.environ.get("LANE_SESSION_MAX_TASKS")
    if env:
        return clamp_session_max_tasks(env)
    return DEFAULT_SESSION_MAX_TASKS
