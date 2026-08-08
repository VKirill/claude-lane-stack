#!/usr/bin/env python3
"""SessionStart/SessionEnd helper: remember agent_type for statusLine routing.

Claude Code statusLine JSON sometimes omits agent_type. SessionStart always has
it for agent sessions — we stash it under ~/.agents/statusline/sessions/<id>.

statusLine (lane-statusline) then maps session_id → lane HUD vs claude-pulse.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# allow import of lane_statusline_lib from install bin
_CANDIDATE_BINS = (
    Path(__file__).resolve().parent.parent / "bin",
    Path.home() / ".agents" / "bin",
)
for _b in _CANDIDATE_BINS:
    if _b.is_dir() and str(_b) not in sys.path:
        sys.path.insert(0, str(_b))

try:
    from lane_statusline_lib import (  # noqa: E402
        DEFAULT_LANE_AGENTS,
        extract_agent_type,
        lane_agent_set,
        session_mark_path,
        write_session_agent,
    )
except ImportError:
    # minimal fallback if lib not installed yet
    def extract_agent_type(raw):  # type: ignore
        try:
            d = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return ""
        if not isinstance(d, dict):
            return ""
        return str(d.get("agent_type") or "").strip()

    def write_session_agent(session_id, agent):  # type: ignore
        return None

    def session_mark_path(session_id):  # type: ignore
        return Path.home() / ".agents" / "statusline" / "sessions" / f"{session_id}.json"

    DEFAULT_LANE_AGENTS = ("dev-orchestrator",)
    def lane_agent_set():  # type: ignore
        return set(DEFAULT_LANE_AGENTS)


def _session_id(data: dict) -> str:
    for key in ("session_id", "sessionId", "transcript_path", "transcriptPath"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            # transcript path → basename stem as id
            if "transcript" in key.lower() or val.endswith(".jsonl"):
                return Path(val).stem
            return val.strip()
    nested = data.get("data")
    if isinstance(nested, dict):
        return _session_id(nested)
    return ""


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0

    # SessionEnd: clear mark
    event = str(data.get("hook_event_name") or data.get("event") or "").lower()
    sid = _session_id(data)
    agent = extract_agent_type(data)

    if "end" in event and sid:
        path = session_mark_path(sid)
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        return 0

    if not agent or agent not in lane_agent_set():
        # non-lane session: ensure no stale mark if we know session id
        if sid:
            path = session_mark_path(sid)
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                pass
        return 0

    if sid:
        write_session_agent(sid, agent)
    else:
        # last-resort: write "active" stamp (short TTL used by statusline)
        try:
            root = Path.home() / ".agents" / "statusline"
            root.mkdir(parents=True, exist_ok=True)
            (root / "last_lane_agent.json").write_text(
                json.dumps({"agent_type": agent, "ts": time.time()}),
                encoding="utf-8",
            )
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
