#!/usr/bin/env python3
"""TeammateIdle: require DONE|FAILED|WAIT before a teammate parks.

Exit 0  — allow idle (sentinel present, or hook disabled).
Exit 2  — keep teammate working; stderr is fed back as the next instruction.

Stack one-shot Agents (run-supervisor, …) do not fire TeammateIdle.
Disable: LANE_TEAMMATE_IDLE_SENTINEL=0
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Last non-empty line matching, or any line in the tail (models bury DONE).
SENTINEL_RE = re.compile(
    r"(?m)^\s*(DONE|FAILED|WAIT)(?:\s+|$)(.*)$",
    re.IGNORECASE,
)
TAIL_CHARS = 6000


def _disabled() -> bool:
    return os.environ.get("LANE_TEAMMATE_IDLE_SENTINEL", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def last_assistant_text(payload: dict) -> str:
    for key in ("last_assistant_message", "lastAssistantMessage"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw
    # Fallback: transcript may lag; best-effort only.
    path = payload.get("transcript_path") or payload.get("agent_transcript_path")
    if not isinstance(path, str) or not path.strip():
        return ""
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # Prefer jsonl assistant text blocks from the end.
    chunks: list[str] = []
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str) and content.strip():
            chunks.append(content)
        elif isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            joined = "".join(parts).strip()
            if joined:
                chunks.append(joined)
        if chunks:
            break
    return chunks[0] if chunks else ""


def has_sentinel(text: str) -> bool:
    if not text or not text.strip():
        return False
    tail = text[-TAIL_CHARS:] if len(text) > TAIL_CHARS else text
    return SENTINEL_RE.search(tail) is not None


def decide(payload: dict) -> tuple[int, str]:
    """Return (exit_code, stderr_message)."""
    if _disabled():
        return 0, ""
    if not isinstance(payload, dict):
        return 0, ""
    event = str(payload.get("hook_event_name") or payload.get("hookEventName") or "")
    if event and event not in {"TeammateIdle", "teammate_idle"}:
        return 0, ""
    text = last_assistant_text(payload)
    if has_sentinel(text):
        return 0, ""
    name = payload.get("teammate_name") or payload.get("agent_type") or "teammate"
    msg = (
        f"lane teammate_idle_sentinel: @{name} cannot go idle without a close line. "
        "End this turn with one of:\n"
        "  DONE <report-path>   — final report on disk (preferred under .agents/)\n"
        "  FAILED <reason>     — give up this assignment\n"
        "  WAIT <why>          — mid-dialogue park; waiting for lead/next ask\n"
        "Then stop. Do not idle silently."
    )
    return 2, msg


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    code, err = decide(payload if isinstance(payload, dict) else {})
    if err:
        print(err, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
