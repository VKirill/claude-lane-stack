#!/usr/bin/env python3
"""UserPromptSubmit: the owner is at the keyboard (SMA atlas D2-6, «Daytime owner left alone», «Busy account skipped»).

A prompt a person typed (not a harness notification, a reminder or another thread's message) in a Claude Code session that carries no lane
marker is the owner working on his own account. The hook writes the time
(never the prompt) to ~/.agents/state/owner-presence.json as {"claude-code": {"at": <epoch ms>, "host": <hostname>}}. Lane Pilot reads the
file on every machine and keeps its writers off the provider while the owner was active in the last minutes, so the factory does not
take the account the owner is using. Lane sessions (any LANE_* marker) write nothing. No output, never blocks. Disable: LANE_OWNER_PRESENCE=0.
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
import time
from pathlib import Path

MARKERS = ("LANE_STACK_SESSION", "LANE_PILOT_AGENT_TYPE", "LANE_PILOT_ROLE", "LANE_PROMPT_FILE", "LANE_TASK_FILE", "LANE_CODEX_WORKER")
PROVIDER = "claude-code"
# Turns no person typed: harness notifications, reminders, messages of other threads and bots.
MACHINE_TURN = re.compile(r"^\s*(<task-notification>|<system-reminder>|\[SYSTEM NOTIFICATION|\[bb message from thread:|Lane Pilot:|You are the Lane Pilot |<command-)", re.I)


def typed_by_a_person(prompt: object) -> bool:
    return isinstance(prompt, str) and bool(prompt.strip()) and not MACHINE_TURN.match(prompt)


def model_list_probe(prompt: object, environ: dict[str, str]) -> bool:
    """BB's Claude Code provider reads the model list with an SDK query of "." outside any thread (provider-claude-code model-list.ts)."""
    return prompt == "." and not environ.get("BB_THREAD_ID") and environ.get("CLAUDE_CODE_ENTRYPOINT", "") != "cli"


def owner_session(environ: dict[str, str]) -> bool:
    return environ.get("LANE_OWNER_PRESENCE", "1") != "0" and not any(environ.get(name) for name in MARKERS)


def record(home: Path, now_ms: int, host: str, provider: str = PROVIDER) -> Path:
    path = home / ".agents" / "state" / "owner-presence.json"
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            current = {}
    except (OSError, ValueError):
        current = {}
    current[provider] = {"at": now_ms, "host": host}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(current), encoding="utf-8")
    os.replace(temp, path)
    return path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (OSError, ValueError):
        payload = {}
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    environ = dict(os.environ)
    if owner_session(environ) and typed_by_a_person(prompt) and not model_list_probe(prompt, environ):
        try:
            record(Path.home(), int(time.time() * 1000), socket.gethostname())
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
