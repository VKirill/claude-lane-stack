from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "teammate_idle_sentinel.py"
sys_path_hooks = str(ROOT / "hooks")

import sys

sys.path.insert(0, sys_path_hooks)
from teammate_idle_sentinel import (  # noqa: E402
    decide,
    has_sentinel,
    last_assistant_text,
    resolve_teammate_transcript,
)


def run_hook(payload: dict, *, env_extra: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


class SentinelUnitTests(unittest.TestCase):
    def test_has_sentinel_variants(self) -> None:
        self.assertTrue(has_sentinel("...\nDONE .agents/team/a-report.md\n"))
        self.assertTrue(has_sentinel("FAILED no evidence"))
        self.assertTrue(has_sentinel("WAIT lead clarification on SEO"))
        self.assertTrue(has_sentinel("done path/ok.md"))  # case-insensitive
        self.assertFalse(has_sentinel("I am done with the analysis."))
        self.assertFalse(has_sentinel(""))
        self.assertFalse(has_sentinel("still looking at docker-compose"))

    def test_decide_allows_with_message(self) -> None:
        code, err = decide(
            {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "audit",
                "last_assistant_message": "Report ready.\nDONE .agents/team/audit.md",
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_decide_blocks_without_sentinel(self) -> None:
        code, err = decide(
            {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "baked-config-audit",
                "last_assistant_message": "Here is a long report without a close line.",
            }
        )
        self.assertEqual(code, 2)
        self.assertIn("DONE", err)
        self.assertIn("WAIT", err)

    def test_decide_disabled(self) -> None:
        os.environ["LANE_TEAMMATE_IDLE_SENTINEL"] = "0"
        try:
            code, err = decide(
                {
                    "hook_event_name": "TeammateIdle",
                    "last_assistant_message": "no sentinel",
                }
            )
            self.assertEqual(code, 0)
        finally:
            os.environ.pop("LANE_TEAMMATE_IDLE_SENTINEL", None)

    def test_transcript_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            line = {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Mid status.\nWAIT need lead on next scope"}
                    ]
                },
            }
            path.write_text(json.dumps(line) + "\n", encoding="utf-8")
            text = last_assistant_text(
                {"hook_event_name": "TeammateIdle", "transcript_path": str(path)}
            )
            self.assertIn("WAIT", text)
            code, _ = decide(
                {"hook_event_name": "TeammateIdle", "transcript_path": str(path)}
            )
            self.assertEqual(code, 0)

    def _assistant_line(self, text: str) -> str:
        return json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": text}]},
            }
        )

    def test_prefers_agent_transcript_over_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "sess.jsonl"
            agent = Path(tmp) / "agent.jsonl"
            parent.write_text(self._assistant_line("PM still planning") + "\n")
            agent.write_text(
                self._assistant_line("DONE accepted /tmp/run") + "\n"
            )
            payload = {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "rs-history-modal-scroll-jump",
                "transcript_path": str(parent),
                "agent_transcript_path": str(agent),
            }
            self.assertEqual(resolve_teammate_transcript(payload), agent)
            self.assertIn("DONE", last_assistant_text(payload))
            code, err = decide(payload)
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

    def test_resolves_teammate_jsonl_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "sess.jsonl"
            sub = Path(tmp) / "sess" / "subagents"
            sub.mkdir(parents=True)
            parent.write_text(self._assistant_line("PM last message") + "\n")
            (sub / "agent-ars-history-modal-scroll-jump-abc123.jsonl").write_text(
                self._assistant_line("DONE accepted /tmp/run") + "\n"
            )
            payload = {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "rs-history-modal-scroll-jump",
                "transcript_path": str(parent),
            }
            code, err = decide(payload)
            self.assertEqual(code, 0, err)
            self.assertIn("DONE", last_assistant_text(payload))

    def test_parent_transcript_alone_does_not_pass_for_teammate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "sess.jsonl"
            parent.write_text(
                self._assistant_line("DONE this is the PM close line") + "\n"
            )
            payload = {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "rs-openrouter-muse",
                "transcript_path": str(parent),
            }
            self.assertIsNone(resolve_teammate_transcript(payload))
            code, _ = decide(payload)
            self.assertEqual(code, 2)


class HookProcessTests(unittest.TestCase):
    def test_process_exit_2(self) -> None:
        r = run_hook(
            {
                "hook_event_name": "TeammateIdle",
                "teammate_name": "x",
                "last_assistant_message": "report without sentinel",
            }
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("DONE", r.stderr)

    def test_process_exit_0(self) -> None:
        r = run_hook(
            {
                "hook_event_name": "TeammateIdle",
                "last_assistant_message": "DONE /tmp/r.md",
            }
        )
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
