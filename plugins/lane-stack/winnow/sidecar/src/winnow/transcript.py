"""Derive the "current task" from a Claude Code session transcript.

This is the state-engineering heart of winnow. The judge cannot decide whether a
block matters without knowing what the agent is trying to do, and Claude Code
does not hand the hook that information directly. We reconstruct it from the
tail of the session transcript (a JSONL file whose path arrives in every hook
payload): the last thing the user asked for, and the last thing the assistant
said it was about to do.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    user_request: str = ""
    assistant_intent: str = ""

    def as_state(self) -> dict[str, str]:
        return {
            "user_request": self.user_request,
            "assistant_intent": self.assistant_intent,
        }

    @property
    def is_empty(self) -> bool:
        return not (self.user_request or self.assistant_intent)


def _tail_bytes(path: str, max_bytes: int) -> bytes:
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > max_bytes:
            fh.seek(size - max_bytes)
            fh.readline()  # discard the partial line we landed in
        return fh.read()


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def _has_tool_result(content: object) -> bool:
    if not isinstance(content, list):
        return False
    return any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def transcript_for(payload: dict) -> str | None:
    """The transcript that describes the task behind a hook payload.

    Inside a subagent the hook's ``transcript_path`` is the parent session's
    file, whose last user message is whatever the human said to the
    orchestrator. The subagent's own transcript, at
    ``<session dir>/<session id>/subagents/agent-<agent id>.jsonl``, starts
    with the delegation prompt, which is the task that tool call is serving.
    """
    path = payload.get("transcript_path")
    agent_id = payload.get("agent_id")
    session_id = payload.get("session_id")
    if not path and session_id and payload.get("cwd"):
        # A function-hook call carries no transcript path; Claude Code's layout is predictable.
        path = guess_transcript_path(str(payload["cwd"]), str(session_id))
    if path and agent_id and session_id:
        candidate = os.path.join(os.path.dirname(str(path)), str(session_id), "subagents", f"agent-{agent_id}.jsonl")
        if os.path.exists(candidate):
            return candidate
    return str(path) if path else None


def guess_transcript_path(cwd: str, session_id: str) -> str:
    """Where Claude Code writes the transcript of ``session_id`` for a project at ``cwd``.

    The project directory is the working directory with every character that is
    not a letter or digit replaced by ``-`` (``C:\\Work\\app`` becomes ``C--Work-app``).
    """
    root = os.environ.get("WINNOW_TRANSCRIPTS_ROOT") or os.path.join(os.path.expanduser("~"), ".claude", "projects")
    return os.path.join(root, re.sub(r"[^A-Za-z0-9]", "-", cwd), f"{session_id}.jsonl")


def task_from_payload(payload: dict, *, max_chars: int = 1500) -> Task | None:
    """A task the caller reconstructed itself, or None.

    The function-hook module reads the live session and sends ``task`` as
    ``{"user_request": ..., "assistant_intent": ...}``; that beats reading the
    transcript file, which may lag or, in a subagent, be the parent's.
    """
    raw = payload.get("task")
    if not isinstance(raw, dict):
        return None
    user = str(raw.get("user_request") or "").strip()
    assistant = str(raw.get("assistant_intent") or "").strip()
    if not user and not assistant:
        return None
    return Task(_head(user, max_chars), _tail(assistant, max_chars))


def read_task(
    transcript_path: str | None,
    *,
    max_chars: int = 1500,
    max_bytes: int = 2_000_000,
) -> Task:
    """Return the latest user request and assistant intent from the transcript tail."""
    if not transcript_path or not os.path.exists(transcript_path):
        return Task()
    try:
        data = _tail_bytes(transcript_path, max_bytes)
    except OSError:
        return Task()

    user, assistant = "", ""
    for line in data.decode("utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        kind = entry.get("type")
        message = entry.get("message") or {}
        content = message.get("content") if isinstance(message, dict) else None
        if kind == "user":
            if entry.get("isMeta") or _has_tool_result(content):
                continue
            text = _text_of(content).strip()
            if text:
                user, assistant = text, ""
        elif kind == "assistant":
            text = _text_of(content).strip()
            if text:
                assistant = text
    # Keep the head of long messages: a delegation prompt says what to do in its first lines and
    # ends in details; the same holds for a long user request. The tail of an assistant message
    # is the more useful half, since that is where it says what it will do next.
    return Task(_head(user, max_chars), _tail(assistant, max_chars))


def _head(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _tail(text: str, limit: int) -> str:
    return text if len(text) <= limit else "…" + text[-(limit - 1) :].lstrip()
