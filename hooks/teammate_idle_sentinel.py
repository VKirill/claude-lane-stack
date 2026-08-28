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
_SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+")


def _payload_str(payload: dict, *keys: str) -> str:
    for key in keys:
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _session_dir(transcript_path: str) -> Path | None:
    """Parent TeammateIdle transcript is {session}.jsonl; teammates live under {session}/."""
    raw = Path(transcript_path).expanduser()
    if raw.suffix == ".jsonl":
        return raw.with_suffix("")
    if raw.is_dir():
        return raw
    return None


def resolve_teammate_transcript(payload: dict) -> Path | None:
    """Teammate's own jsonl. TeammateIdle.transcript_path is the parent session."""
    explicit = _payload_str(payload, "agent_transcript_path", "agentTranscriptPath")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None

    parent = _payload_str(payload, "transcript_path", "transcriptPath")
    if not parent:
        return None
    session = _session_dir(parent)
    if session is None:
        return None
    subdir = session / "subagents"
    if not subdir.is_dir():
        return None

    agent_id = _payload_str(payload, "agent_id", "agentId")
    if agent_id:
        for name in (f"agent-{agent_id}.jsonl", f"agent-a{agent_id}.jsonl"):
            cand = subdir / name
            if cand.is_file():
                return cand

    teammate = _payload_str(payload, "teammate_name", "teammateName")
    if not teammate or not _SAFE_NAME.fullmatch(teammate):
        return None
    matches = sorted(
        subdir.glob(f"agent-a{teammate}-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _assistant_from_jsonl(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
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
            return content
        if isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            joined = "".join(parts).strip()
            if joined:
                return joined
    return ""


def _disabled() -> bool:
    return os.environ.get("LANE_TEAMMATE_IDLE_SENTINEL", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def last_assistant_text(payload: dict) -> str:
    teammate_path = resolve_teammate_transcript(payload)
    if teammate_path is not None:
        text = _assistant_from_jsonl(teammate_path)
        if text:
            return text
    for key in ("last_assistant_message", "lastAssistantMessage"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw
    if _payload_str(payload, "teammate_name", "teammateName"):
        return ""
    parent = _payload_str(payload, "transcript_path", "transcriptPath")
    if not parent:
        return ""
    return _assistant_from_jsonl(Path(parent).expanduser())


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
