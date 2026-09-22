"""``winnow demo``: the sixty-second check.

Feeds a synthetic ``Read`` result and a synthetic task through the real
PostToolUse path and prints what Claude would have seen. With ``--fake`` it
uses a keyword judge and needs no keys, so a new user can see the stub format
before configuring anything. Without ``--fake`` it uses whatever judge
``winnow doctor`` reports, which makes it the first real end-to-end call.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from winnow.config import Config
from winnow.hooks import Runtime, post_tool_use
from winnow.judge import JudgeResult, build_judge
from winnow.summarize import build_summarizer
from winnow.transcript import Task

TASK = "Change the retry backoff for the payments client to start at 2 seconds."
FILE_PATH = "services/config/settings.py"


def synthetic_file() -> str:
    lines: list[str] = ["# " + "-" * 70]
    lines += [f"# Copyright (c) 2026 Example Corp. Licensed under the Apache License 2.0. Line {i}." for i in range(1, 15)]
    lines += ["# " + "-" * 70, "", "import logging", "import os", "from dataclasses import dataclass", ""]
    lines += ["LOGGING = {", '    "version": 1,', '    "formatters": {']
    lines += [f'        "fmt{i}": {{"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},' for i in range(1, 21)]
    lines += ["    },", '    "handlers": {"console": {"class": "logging.StreamHandler"}},', "}", ""]
    lines += [
        "@dataclass",
        "class RetryPolicy:",
        "    max_attempts: int = 5",
        "    backoff_initial_s: float = 0.5",
        "    backoff_max_s: float = 30.0",
        "    jitter: float = 0.2",
        "",
        "PAYMENTS_RETRY = RetryPolicy(max_attempts=4, backoff_initial_s=0.5)",
        "SEARCH_RETRY = RetryPolicy(max_attempts=2)",
        "",
    ]
    lines += ["FEATURE_FLAGS = {"]
    lines += [f'    "flag_{i:02d}": {{"enabled": {str(i % 2 == 0)}, "rollout": {i * 3 % 100}}},' for i in range(1, 46)]
    lines += ["}", "", 'ENV = os.environ.get("APP_ENV", "dev")']
    return "\n".join(lines)


class KeywordJudge:
    """Keyless stand-in: a block is 'needed' if it mentions any keyword."""

    name = "fake-keyword"

    def __init__(self, keywords: tuple[str, ...]) -> None:
        self.keywords = tuple(k.lower() for k in keywords)

    def nouls(self, state: Any, questions: Mapping[str, Any]) -> JudgeResult:
        blocks = state.get("blocks", {}) if isinstance(state, dict) else {}
        probabilities: dict[str, float] = {}
        for qid in questions:
            if qid == "error_present":
                probabilities[qid] = 0.02
                continue
            text = str(blocks.get(qid, "")).lower()
            probabilities[qid] = 0.92 if any(k in text for k in self.keywords) else 0.06
        return JudgeResult(probabilities, self.name, None, None, 0)


class FirstLineSummarizer:
    name = "fake-first-line"

    def summarize(self, text: str, task: Task, describe: str) -> str | None:
        for line in text.splitlines():
            if line.strip():
                return f"(demo summary) starts with: {line.strip()[:80]}"
        return None


def run_demo(fake: bool) -> int:
    cfg = Config.from_env()
    if fake:
        runtime = Runtime(cfg, KeywordJudge(("retry", "backoff")), FirstLineSummarizer(), {"demo": True})
    else:
        try:
            judge = build_judge(cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"winnow demo: the judge could not start: {exc}")
            print("Run `winnow doctor`, or try `winnow demo --fake` to see the format without a key.")
            return 1
        if judge is None:
            print("winnow demo: WINNOW_JUDGE is off. Set it to typesafe or adapter, or run `winnow demo --fake`.")
            return 1
        runtime = Runtime(cfg, judge, build_summarizer(cfg), {"demo": True})

    text = synthetic_file()
    with tempfile.TemporaryDirectory() as tmp:
        transcript = Path(tmp) / "transcript.jsonl"
        transcript.write_text(json.dumps({"type": "user", "message": {"role": "user", "content": TASK}}) + "\n", encoding="utf-8")
        payload = {
            "hook_event_name": "PostToolUse",
            "session_id": "demo",
            "tool_use_id": "demo",
            "tool_name": "Read",
            "tool_input": {"file_path": FILE_PATH},
            "tool_response": {"type": "text", "file": {"filePath": FILE_PATH, "content": text, "numLines": text.count("\n") + 1, "startLine": 1, "totalLines": text.count("\n") + 1}},
            "transcript_path": str(transcript),
            "cwd": tmp,
        }
        result = post_tool_use(payload, runtime)

    print(f"Task:   {TASK}")
    print(f"Tool:   Read {FILE_PATH}  ({text.count(chr(10)) + 1} lines, {len(text)} chars)")
    print(f"Judge:  {runtime.judge.name}" + ("" if runtime.summarizer else "  (no summarizer)"))
    print()
    if result is None:
        print("Nothing was hidden. Either every block looked relevant, or the output was judged to contain an error.")
        print(f"See the last line of {cfg.log_path} for the per-block probabilities.")
        return 0
    content = result["hookSpecificOutput"]["updatedToolOutput"]["file"]["content"]
    print("What Claude would see:")
    print("-" * 72)
    print(content)
    print("-" * 72)
    hidden = text.count("\n") + 1 - sum(1 for line in content.splitlines() if not line.startswith("[winnow]"))
    print(f"{hidden} of {text.count(chr(10)) + 1} lines hidden; {len(text)} -> {len(content)} chars.")
    key = content.split("cached as key ")[1].split(".")[0] if "cached as key " in content else None
    if key:
        print(f"Restore with: winnow recall {key}")
    return 0
