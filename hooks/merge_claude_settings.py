#!/usr/bin/env python3
"""Merge the lane-stack guard + statusLine into Claude settings without wiping user config."""

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
    if hooks is not None and not isinstance(hooks, dict):
        raise ValueError(f"{path}: hooks must be an object")
    if isinstance(hooks, dict):
        pre_tool_use = hooks.get("PreToolUse", [])
        if pre_tool_use is not None and not isinstance(pre_tool_use, list):
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
    # Always absolute: Claude runs hooks with cwd=project, so relative paths like
    # "hooks/guard_shell.py" fail as /bin/sh: hooks/guard_shell.py: not found.
    guard_abs = str(Path(guard_path).expanduser().resolve())
    guard = {
        "type": "command",
        "command": f"AGENT_HOOK_CLIENT=claude {shlex.quote(guard_abs)}",
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


def merge_statusline(settings: dict[str, Any], statusline_path: Path) -> dict[str, Any]:
    """Wire lane-statusline router (pulse for normal, HUD for orchestrators).

    Overwrites previous lane-statusline / claude-pulse statusLine; leaves other
    custom statusLine commands alone only if LANE_STATUSLINE_FORCE=0.
    Default: always set (install owns the status line for stack users).
    """
    force = os.environ.get("LANE_STATUSLINE_FORCE", "1").strip() not in {
        "0",
        "false",
        "no",
    }
    existing = settings.get("statusLine")
    if not force and isinstance(existing, dict):
        cmd = str(existing.get("command") or "")
        ours = "lane-statusline" in cmd or "claude_status" in cmd or "claude-pulse" in cmd
        if cmd and not ours:
            return settings

    path = statusline_path.expanduser().resolve()
    settings["statusLine"] = {
        "type": "command",
        "command": f"python3 {shlex.quote(str(path))}",
        "padding": 0,
    }
    return settings


SESSION_MARK_RE = re.compile(r"lane_statusline_session\.py")


def merge_session_mark(settings: dict[str, Any], mark_path: Path) -> dict[str, Any]:
    """Ensure SessionStart/SessionEnd run the agent→session mark for statusLine routing."""
    hooks = settings.setdefault("hooks", {})
    cmd = f"python3 {shlex.quote(str(mark_path.expanduser().resolve()))}"
    entry = {
        "hooks": [
            {
                "type": "command",
                "command": cmd,
                "timeout": 2,
            }
        ]
    }
    for event in ("SessionStart", "SessionEnd"):
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            hooks[event] = [entry]
            continue
        cleaned: list[object] = []
        for item in entries:
            if not isinstance(item, dict):
                cleaned.append(item)
                continue
            hlist = item.get("hooks")
            if not isinstance(hlist, list):
                cleaned.append(item)
                continue
            remaining = [
                h
                for h in hlist
                if not (
                    isinstance(h, dict)
                    and isinstance(h.get("command"), str)
                    and SESSION_MARK_RE.search(h["command"])
                )
            ]
            if remaining:
                cleaned.append({**item, "hooks": remaining})
        cleaned.append(entry)
        hooks[event] = cleaned
    return settings


# Stack env keys we own (setdefaults only — never clobber user overrides).
STACK_ENV_DEFAULTS: dict[str, str] = {
    # Agent teams + tool search (Claude Code 2.1.x capability surface)
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "ENABLE_TOOL_SEARCH": "true",
    # Generous MCP timeouts for long lane-ctl / lane-exec side tools
    "MCP_TOOL_TIMEOUT": "600000",
    "MCP_TIMEOUT": "60000",
    # Keep attribution noise out of git
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
}

# Tools the solo PM + supervisors need for correct close / peer messaging
# (Claude Code 2.1.224+ SendMessage/ListAgents, TaskStop for stuck agents).
STACK_PERMISSION_ALLOW_EXTRA = (
    "SendMessage",
    "ListAgents",
    "TaskStop",
    "Monitor",
    "Artifact",
)


def merge_stack_capabilities(settings: dict[str, Any]) -> dict[str, Any]:
    """Wire Claude Code capabilities the lane stack expects.

    - env: peer messaging / agent-teams / tool search defaults (setdefault)
    - permissions.allow: ensure SendMessage, ListAgents, TaskStop are not missing
    - crossSessionInbound: only when LANE_CROSS_SESSION_INBOUND is set
      (accept|hold|refuse). Default: leave unset so Claude Code mode-based
      defaults apply (safer for bypassPermissions sessions).
    """
    env = settings.setdefault("env", {})
    if not isinstance(env, dict):
        env = {}
        settings["env"] = env
    for key, value in STACK_ENV_DEFAULTS.items():
        env.setdefault(key, value)

    # Optional peer-messaging policy from install env (explicit opt-in).
    inbound = os.environ.get("LANE_CROSS_SESSION_INBOUND", "").strip().lower()
    if inbound in {"accept", "hold", "refuse"}:
        settings["crossSessionInbound"] = inbound

    # dialogExpiry for held peer messages (minutes as string or number — CC accepts)
    expiry = os.environ.get("LANE_CROSS_SESSION_DIALOG_EXPIRY", "").strip()
    if expiry:
        try:
            settings["dialogExpiry"] = int(expiry)
        except ValueError:
            settings["dialogExpiry"] = expiry

    perms = settings.setdefault("permissions", {})
    if not isinstance(perms, dict):
        perms = {}
        settings["permissions"] = perms
    allow = perms.setdefault("allow", [])
    if not isinstance(allow, list):
        allow = []
        perms["allow"] = allow
    existing = {str(x) for x in allow}
    for tool in STACK_PERMISSION_ALLOW_EXTRA:
        if tool not in existing and f"{tool}(*)" not in existing:
            allow.append(tool)
            existing.add(tool)

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
    parser.add_argument(
        "--statusline",
        type=Path,
        default=None,
        help="path to lane-statusline binary (wires Claude Code statusLine)",
    )
    parser.add_argument(
        "--session-mark",
        type=Path,
        default=None,
        help="path to lane_statusline_session.py (SessionStart/End agent mark)",
    )
    parser.add_argument("settings", type=Path)
    parser.add_argument("guard", type=Path, nargs="?")
    args = parser.parse_args()
    settings = load_settings(args.settings)
    if args.check:
        return 0
    if args.guard is None:
        parser.error("guard path is required unless --check is used")
    settings = merge_guard(settings, args.guard)
    settings = merge_stack_capabilities(settings)
    if args.statusline is not None:
        settings = merge_statusline(settings, args.statusline)
    mark = args.session_mark
    if mark is None and args.statusline is not None:
        # default: hooks/lane_statusline_session.py next to this file
        candidate = Path(__file__).resolve().parent / "lane_statusline_session.py"
        if candidate.is_file():
            mark = candidate
    if mark is not None and mark.is_file():
        settings = merge_session_mark(settings, mark)
    write_settings(args.settings, settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
