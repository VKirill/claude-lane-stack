"""Normalize hook stdin payloads across Claude / Codex / Grok."""
from __future__ import annotations
import json, os, sys
from typing import Any

def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def detect_client(p: dict) -> str:
    env = os.environ.get("AGENT_HOOK_CLIENT", "").lower()
    if env in ("claude", "codex", "grok", ""):
        return env
    # Heuristics
    if "toolCall" in p and isinstance(p.get("toolCall"), dict):
        return ""
    if p.get("hookEventName") in ("pre_tool_use", "post_tool_use") or "toolName" in p:
        return "grok"
    if "agent_type" in p or "tool_name" in p:
        # Claude + Codex both use similar; codex often has session_id + tool_name
        return "claude" if os.environ.get("CLAUDE_PROJECT_DIR") or "agent_type" in p else "codex"
    return "claude"

def tool_name(p: dict) -> str:
    if isinstance(p.get("toolCall"), dict):
        return str(p["toolCall"].get("name") or "")
    for k in ("tool_name", "toolName", "tool"):
        if p.get(k):
            return str(p[k])
    ti = p.get("tool_input") or p.get("toolInput") or {}
    if isinstance(ti, dict) and ti.get("name"):
        return str(ti["name"])
    return ""

def tool_input(p: dict) -> dict:
    if isinstance(p.get("toolCall"), dict):
        args = p["toolCall"].get("args") or p["toolCall"].get("arguments") or {}
        return args if isinstance(args, dict) else {}
    ti = p.get("tool_input") or p.get("toolInput") or {}
    return ti if isinstance(ti, dict) else {}

def shell_command(p: dict) -> str:
    ti = tool_input(p)
    for k in ("command", "cmd", "CommandLine", "commandLine"):
        v = ti.get(k)
        if isinstance(v, str) and v.strip():
            return v
    #  sometimes nests
    for k in ("command", "cmd"):
        v = p.get(k)
        if isinstance(v, str):
            return v
    return ""

def file_path(p: dict) -> str:
    ti = tool_input(p)
    for k in ("file_path", "filePath", "path", "target_file", "TargetFile", "file"):
        v = ti.get(k)
        if isinstance(v, str) and v:
            return v
    # apply_patch may not have path
    return ""

def is_shell_tool(name: str) -> bool:
    n = name.lower()
    return n in {
        "bash", "run_terminal_command", "run_command", "shell",
        "execute", "terminal", "local_shell",
    }

def is_edit_tool(name: str) -> bool:
    n = name.lower()
    return n in {
        "edit", "write", "multiedit", "search_replace", "str_replace",
        "apply_patch", "replace_file_content", "multi_replace_file_content",
        "write_to_file", "create_file", "edit_file",
    }

def emit_allow(client: str) -> None:
    if client == "":
        print(json.dumps({"decision": "allow"}))
    elif client == "grok":
        print(json.dumps({"decision": "allow"}))
    # Claude/Codex: silent allow via exit 0 is fine
    sys.exit(0)

def emit_deny(client: str, reason: str) -> None:
    if client == "":
        print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
        sys.exit(0)
    if client == "grok":
        print(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False))
        sys.exit(2)
    # Claude + Codex compatible
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }, ensure_ascii=False))
    sys.exit(2)

def emit_post_block(client: str, reason: str) -> None:
    """PostToolUse quality feedback (Claude guardian style)."""
    if client in ("claude", "codex"):
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    elif client == "grok":
        # PostToolUse can't block on Grok; still print for UI/log
        print(json.dumps({"decision": "allow", "reason": reason, "systemMessage": reason}, ensure_ascii=False))
    else:
        #  PostToolUse expects {}
        print("{}")
        # Also write to stderr so agent sees it
        print(reason, file=sys.stderr)
    sys.exit(0)
