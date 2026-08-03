#!/usr/bin/env python3
"""Load project writer settings from agents-doctor routing.profile.yaml.

agents-doctor / adoc is the source of truth for which coder, model, and effort
the orchestrator and run-controller use. This module is shared by run-controller
and run-validate (stdlib only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

KNOWN_WRITERS = frozenset({"kimi", "qwen", "agy", "grok", "codex"})
DEFAULT_MODELS = {
    "qwen": "qwen3.8-max-preview",
    "kimi": "kimi-code/k3-256k",
    "grok": "grok-4.5",
    "agy": "gemini-3.6-flash-high",
    "codex": "gpt-5.6-luna",
}
DEFAULT_EFFORTS = {
    "qwen": "medium",
    "kimi": "medium",
    "grok": "medium",
    "agy": "medium",
    "codex": "max",
}


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
    """Minimal YAML subset parser for routing.profile.yaml (no full PyYAML dependency)."""
    result: dict[str, Any] = {"lanes": {}, "writer": {}, "notes": []}
    section: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and line.endswith(":") and " " not in line.split(":", 1)[0]:
            key = line[:-1].strip()
            section = key if key in {"lanes", "writer", "notes"} else None
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
        elif section is None and indent == 0:
            result[key] = value
    return result


def load_routing_profile(start: Path) -> dict[str, Any]:
    """Return parsed profile dict (may be empty if missing)."""
    path = find_routing_profile(start)
    if path is None:
        return {"_path": None, "lanes": {}, "writer": {}}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"_path": str(path), "lanes": {}, "writer": {}}
    data = _parse_simple_yaml_map(text)
    data["_path"] = str(path)
    return data


def resolve_writer(
    start: Path,
    *,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    provider_explicit: bool = False,
) -> dict[str, Any]:
    """Resolve provider/model/effort from CLI overrides + agents-doctor profile.

    When provider_explicit is False and provider is None/empty, use main_write.
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
    return {
        "provider": resolved_provider,
        "model": resolved_model,
        "reasoning_effort": resolved_effort,
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
