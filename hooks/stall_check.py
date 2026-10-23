#!/usr/bin/env python3
"""PostToolUse: the stall rules of a lane session in Claude Code (SMA atlas D2-6, rule 12; the same rules as opencode-lane budget.ts).

A tool call is fingerprinted by its name, its input and the tail of its result. Per session the hook counts each fingerprint and says:
- the same failing call twice (not an edit): do not run it a third time, change the angle, name the class and sweep it offline;
- the same read or grep result three times: reuse it and take the next step;
- the same write or edit three times: edit with old/new strings, never rewrite the file;
- the same result of any other call three times: change the hypothesis before retrying.

Only lane sessions (LANE_STACK_SESSION, LANE_PILOT_AGENT_TYPE, LANE_PILOT_ROLE, LANE_PROMPT_FILE, LANE_TASK_FILE, LANE_CODEX_WORKER):
the owner's own sessions get nothing. Advice only: it never blocks. Disable: LANE_STALL_CHECK=0. State: ~/.agents/state/stall/<session>.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

MARKERS = ("LANE_STACK_SESSION", "LANE_PILOT_AGENT_TYPE", "LANE_PILOT_ROLE", "LANE_PROMPT_FILE", "LANE_TASK_FILE", "LANE_CODEX_WORKER")
CLASS_SWEEP = "Name the class of this failure, then sweep every similar place offline in one pass (read/grep, no reruns), fix the whole class, and run once to confirm."
EDIT_TOOLS = {"edit", "multiedit", "write", "notebookedit"}
READ_TOOLS = {"read", "grep", "glob"}
TAIL = 2000
# Volatile bits (times, durations, temp names, ids) do not make a result new.
VOLATILE = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\b|\b\d+(\.\d+)?\s?(ms|s)\b|/tmp/[\w.-]+|\b[0-9a-f]{12,}\b")


def lane_session(environ: dict[str, str]) -> bool:
    return environ.get("LANE_STALL_CHECK", "1") != "0" and any(environ.get(name) for name in MARKERS)


def result_text(response: object) -> str:
    if isinstance(response, str):
        return response
    try:
        return json.dumps(response, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(response)


def failed(response: object) -> bool:
    if isinstance(response, dict):
        if response.get("is_error") or response.get("error"):
            return True
        code = response.get("exit_code", response.get("exitCode", response.get("returncode")))
        if isinstance(code, int) and code != 0:
            return True
        if response.get("interrupted") is True:
            return True
    text = result_text(response)[-TAIL:].lower()
    return bool(re.search(r"\b(error|failed|traceback|exit code [1-9])\b", text)) and not re.search(r"\b0 failed\b", text)


def fingerprint(tool: str, tool_input: object, response: object) -> str:
    body = json.dumps({"tool": tool.lower(), "input": tool_input}, sort_keys=True, ensure_ascii=False) + VOLATILE.sub("#", result_text(response)[-TAIL:])
    return hashlib.sha1(body.encode("utf-8", "replace")).hexdigest()[:16]


def hint(tool: str, n: int, is_failed: bool) -> str:
    name = tool.lower()
    if is_failed and n == 2 and name not in EDIT_TOOLS:
        return f"[lane-stall class] The same {tool} call failed the same way twice. Do not run it a third time: change the angle. {CLASS_SWEEP}"
    if n < 3:
        return ""
    if name in READ_TOOLS:
        return f"[lane-stall] Identical {tool} result has already been returned {n} times. Reuse the earlier result and take the next task step; if you cannot proceed, report the concrete blocker instead of reading it again."
    if name in EDIT_TOOLS:
        return f"[lane-stall] {tool} on the same path with the same result {n} times. Existing files need a targeted edit (old_string/new_string), never a whole-file rewrite."
    return f"[lane-stall] Same {tool} result {n} times. Change the hypothesis before retrying. {CLASS_SWEEP}"


def state_path(session: str, home: Path) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session or "unknown")[:120]
    return home / ".agents" / "state" / "stall" / f"{safe}.json"


def observe(payload: dict, environ: dict[str, str], home: Path) -> str:
    if not lane_session(environ):
        return ""
    tool = str(payload.get("tool_name") or "")
    if not tool:
        return ""
    response = payload.get("tool_response", payload.get("tool_result"))
    fp = fingerprint(tool, payload.get("tool_input"), response)
    path = state_path(str(payload.get("session_id") or ""), home)
    try:
        counts = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(counts, dict):
            counts = {}
    except (OSError, ValueError):
        counts = {}
    counts[fp] = int(counts.get(fp, 0)) + 1
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Keep the file small: the last 300 fingerprints of the session.
        path.write_text(json.dumps(dict(list(counts.items())[-300:])), encoding="utf-8")
    except OSError:
        pass
    return hint(tool, counts[fp], failed(response))


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    text = observe(payload, dict(os.environ), Path.home())
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
