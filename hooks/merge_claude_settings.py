#!/usr/bin/env python3
"""Merge the lane-stack guard into Claude settings without replacing user config."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any


MATCHER = "Bash|Edit|Write|MultiEdit|NotebookEdit"
GUARD_COMMAND = re.compile(
    r"(?:^|[\s/])(?:guard_shell\.py|guard-orchestrator-no-direct-edits\.sh)"
    r"(?:['\"])?(?:\s|$)"
)


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    settings = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict):
        raise ValueError(f"{path}: settings root must be an object")
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path}: hooks must be an object")
    pre_tool_use = hooks.get("PreToolUse", [])
    if not isinstance(pre_tool_use, list):
        raise ValueError(f"{path}: hooks.PreToolUse must be an array")
    return settings


def is_guard(hook: object) -> bool:
    return (
        isinstance(hook, dict)
        and isinstance(hook.get("command"), str)
        and GUARD_COMMAND.search(hook["command"]) is not None
    )


def merge_guard(settings: dict[str, Any], guard_path: Path) -> dict[str, Any]:
    hooks = settings.setdefault("hooks", {})
    entries = hooks.setdefault("PreToolUse", [])
    guard = {
        "type": "command",
        "command": f"AGENT_HOOK_CLIENT=claude {shlex.quote(str(guard_path))}",
        "timeout": 2,
    }
    merged: list[object] = []
    found = False
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            merged.append(entry)
            continue
        remaining = [hook for hook in entry["hooks"] if not is_guard(hook)]
        if len(remaining) == len(entry["hooks"]):
            merged.append(entry)
        elif not found:
            if remaining:
                merged.append({**entry, "hooks": remaining})
            merged.append({"matcher": MATCHER, "hooks": [guard]})
            found = True
        elif remaining:
            merged.append({**entry, "hooks": remaining})
    if not found:
        merged.append({"matcher": MATCHER, "hooks": [guard]})
    hooks["PreToolUse"] = merged
    return settings


def write_settings(path: Path, settings: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as output:
        json.dump(settings, output, indent=2)
        output.write("\n")
        temporary = Path(output.name)
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("settings", type=Path)
    parser.add_argument("guard", type=Path, nargs="?")
    args = parser.parse_args()
    settings = load_settings(args.settings)
    if args.check:
        return 0
    if args.guard is None:
        parser.error("guard path is required unless --check is used")
    write_settings(args.settings, merge_guard(settings, args.guard))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
