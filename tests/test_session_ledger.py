from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_clean_empty_session_does_not_create_a_log(self) -> None:
        # A-022: `## main` is a clean status -sb, not the phrase "nothing to commit".
        hooks = str(ROOT / "hooks")
        if hooks not in sys.path:
            sys.path.insert(0, hooks)
        with tempfile.TemporaryDirectory(prefix="ledger-empty-") as td:
            root = Path(td)
            env = {
                **os.environ,
                "AGENT_LEDGER_STATE": str(root / "state"),
                "CLAUDE_LANE_AUTOMATION": "0",
            }
            with patch.dict(os.environ, env, clear=False):
                if "session_ledger" in sys.modules:
                    del sys.modules["session_ledger"]
                ledger = importlib.import_module("session_ledger")
                with patch.object(ledger, "do_usage"), patch.object(ledger, "project_root", return_value=root), patch.object(ledger, "git_snapshot", return_value="## main"), patch.dict(sys.modules, {"lane_memory": types.SimpleNamespace(enabled=lambda _root: False)}):
                    ledger.do_flush({"session_id": "empty-fixture", "cwd": td})
                    self.assertEqual(list((root / ".agents" / "session-log").glob("*/*.md")), [])
                    ledger.do_record({
                        "session_id": "busy-fixture",
                        "cwd": td,
                        "tool_name": "Bash",
                        "tool_input": {"command": "printf fixture"},
                    })
                    ledger.do_flush({"session_id": "busy-fixture", "cwd": td})
            self.assertEqual(len(list((root / ".agents" / "session-log").glob("*/*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
