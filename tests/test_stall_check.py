"""The stall rules of a lane session in Claude Code (hooks/stall_check.py, SMA atlas D2-6)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
import stall_check  # noqa: E402

LANE = {"LANE_PILOT_AGENT_TYPE": "lane-pilot-writer"}


class StallCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())

    def call(self, tool: str, tool_input: dict, response: object, env: dict | None = None, session: str = "s1") -> str:
        return stall_check.observe({"session_id": session, "tool_name": tool, "tool_input": tool_input, "tool_response": response}, env if env is not None else LANE, self.home)

    def test_the_same_failure_twice_asks_for_a_new_angle_and_a_class_sweep(self) -> None:
        failing = {"exit_code": 1, "stdout": "FAIL tests/a.test.ts at 10:42:01 in 1.2s"}
        self.assertEqual(self.call("Bash", {"command": "npm test"}, failing), "")
        second = self.call("Bash", {"command": "npm test"}, {"exit_code": 1, "stdout": "FAIL tests/a.test.ts at 10:43:17 in 1.4s"})
        self.assertIn("failed the same way twice", second)
        self.assertIn("Name the class", second)

    def test_three_identical_reads_and_writes_get_their_own_advice(self) -> None:
        for n in range(2):
            self.assertEqual(self.call("Read", {"file_path": "/a.ts"}, "content"), "")
        self.assertIn("Reuse the earlier result", self.call("Read", {"file_path": "/a.ts"}, "content"))
        for n in range(2):
            self.call("Write", {"file_path": "/b.ts", "content": "x"}, {"type": "update"})
        self.assertIn("never a whole-file rewrite", self.call("Write", {"file_path": "/b.ts", "content": "x"}, {"type": "update"}))

    def test_a_new_result_resets_nothing_but_counts_apart_and_sessions_are_separate(self) -> None:
        self.call("Bash", {"command": "ls"}, "a")
        self.call("Bash", {"command": "ls"}, "a")
        self.assertEqual(self.call("Bash", {"command": "ls"}, "b"), "")
        self.assertEqual(self.call("Bash", {"command": "ls"}, "a", session="s2"), "")
        self.assertIn("Change the hypothesis", self.call("Bash", {"command": "ls"}, "a"))

    def test_the_owners_own_session_and_the_switch_get_nothing(self) -> None:
        for _ in range(4):
            self.assertEqual(self.call("Bash", {"command": "npm test"}, {"exit_code": 1}, env={}), "")
            self.assertEqual(self.call("Bash", {"command": "npm test"}, {"exit_code": 1}, env={**LANE, "LANE_STALL_CHECK": "0"}), "")

    def test_the_hook_prints_post_tool_use_context_and_never_blocks(self) -> None:
        payload = json.dumps({"session_id": "s9", "tool_name": "Bash", "tool_input": {"command": "x"}, "tool_response": {"exit_code": 2}})
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.home), **LANE}
        outs = [subprocess.run([sys.executable, str(ROOT / "hooks/stall_check.py")], input=payload, capture_output=True, text=True, env=env) for _ in range(2)]
        self.assertEqual([out.returncode for out in outs], [0, 0])
        self.assertEqual(outs[0].stdout, "")
        self.assertEqual(json.loads(outs[1].stdout)["hookSpecificOutput"]["hookEventName"], "PostToolUse")


if __name__ == "__main__":
    unittest.main()
