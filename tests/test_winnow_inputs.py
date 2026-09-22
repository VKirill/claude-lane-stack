from __future__ import annotations

import json
import sys
from pathlib import Path


SIDECAR_SRC = Path(__file__).parents[1] / "plugins" / "lane-stack" / "winnow" / "sidecar" / "src"
sys.path.insert(0, str(SIDECAR_SRC))

from winnow.chunk import Block
from winnow.extract import trimmed_input
from winnow.hooks import _judge_window
from winnow.replay import iter_cases
from winnow.transcript import read_task, task_from_payload


def test_task_payload_preserves_full_request_and_intent() -> None:
    user_request = "user-start " + "u" * 2_000 + " user-end"
    assistant_intent = "assistant-start " + "a" * 2_000 + " assistant-end"

    task = task_from_payload({"task": {"user_request": user_request, "assistant_intent": assistant_intent}})

    assert task is not None
    assert task.user_request == user_request
    assert task.assistant_intent == assistant_intent


def test_judge_window_keeps_blocks_after_previous_character_budget() -> None:
    blocks = [
        Block("b001", 0, 1, 1, "first block"),
        Block("b002", 1, 2, 2, "last block after the old window"),
    ]

    assert _judge_window(blocks, max_chars=12) == blocks


def test_tool_input_keeps_all_fields_and_nested_values() -> None:
    tool_input = {
        "command": "c" * 2_000,
        "items": ["first", "last"],
        "nested": {"tail": "value"},
        "extra": "present",
    }

    assert trimmed_input("Bash", tool_input) == tool_input


def test_replay_case_preserves_full_task_fields(tmp_path: Path) -> None:
    user_request = "replay-user-start " + "u" * 2_000 + " replay-user-end"
    assistant_intent = "replay-assistant-start " + "a" * 2_000 + " replay-assistant-end"
    transcript = tmp_path / "session.jsonl"
    entries = [
        {"type": "user", "message": {"content": user_request}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": assistant_intent},
                    {"type": "tool_use", "id": "tool-1", "name": "Bash", "input": {"command": "printf ok"}},
                ]
            },
        },
        {
            "type": "user",
            "toolUseResult": {"stdout": "result"},
            "message": {"content": [{"type": "tool_result", "tool_use_id": "tool-1", "content": "result"}]},
        },
    ]
    transcript.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

    cases = list(iter_cases(transcript, tools=("Bash",), min_chars=1))

    assert len(cases) == 1
    assert cases[0].task == {"user_request": user_request, "assistant_intent": assistant_intent}


def test_large_transcript_keeps_task_before_old_two_megabyte_tail(tmp_path: Path) -> None:
    user_request = "large-transcript-user " + "u" * 2_000
    assistant_intent = "large-transcript-assistant " + "a" * 2_000
    transcript = tmp_path / "large-session.jsonl"
    entries = [
        {"type": "user", "message": {"content": user_request}},
        {"type": "assistant", "message": {"content": assistant_intent}},
        {"type": "progress", "payload": "x" * 2_100_000},
    ]
    transcript.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

    task = read_task(str(transcript))

    assert task.user_request == user_request
    assert task.assistant_intent == assistant_intent
