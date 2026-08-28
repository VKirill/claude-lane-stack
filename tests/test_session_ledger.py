from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSION_LEDGER = ROOT / "hooks" / "session_ledger.py"


class SessionLedgerTest(unittest.TestCase):
    def test_lane_automation_never_writes_project_memory(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            project = Path(raw_tmp) / "project"
            project.mkdir()
            state = Path(raw_tmp) / "state"
            payload = {
                "session_id": "lane-automation-test",
                "cwd": str(project),
                "tool_name": "Write",
                "tool_input": {"file_path": str(project / "owned.py")},
            }
            env = os.environ.copy()
            env.update(
                {
                    "AGENT_HOOK_CLIENT": "grok",
                    "AGENT_LEDGER_STATE": str(state),
                    "CLAUDE_LANE_AUTOMATION": "1",
                }
            )

            for mode in ("record", "flush"):
                result = subprocess.run(
                    [sys.executable, str(SESSION_LEDGER), mode],
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    env=env,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            self.assertFalse((project / "PROGRESS.md").exists())
            self.assertFalse((project / ".agents").exists())
            self.assertFalse(state.exists())

    def test_usage_mode_skips_session_log(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            project = Path(raw_tmp) / "project"
            project.mkdir()
            transcript = Path(raw_tmp) / "sess.jsonl"
            transcript.write_text("{}\n", encoding="utf-8")
            payload = {
                "session_id": "usage-only",
                "cwd": str(project),
                "transcript_path": str(transcript),
            }
            env = os.environ.copy()
            env.update(
                {
                    "AGENT_HOOK_CLIENT": "claude",
                    "AGENT_LEDGER_STATE": str(Path(raw_tmp) / "state"),
                }
            )
            result = subprocess.run(
                [sys.executable, str(SESSION_LEDGER), "usage"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((project / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
