"""The SMA session hooks and terminal coordination (hooks/sma_hooks.py, hooks/lane_coord.py)."""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "sma_hooks.py"
sys.path.insert(0, str(ROOT / "hooks"))
import lane_coord  # noqa: E402


def call(event: str, payload: dict, env: dict) -> dict | None:
    out = subprocess.run([sys.executable, str(HOOK), event], input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30).stdout.strip()
    return json.loads(out) if out else None


class SmaHooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        Path(self.tmp, "a.ts").write_text("x\n")
        self.env = {**os.environ, "LANE_COORD_HOME": str(Path(self.tmp, "coord")), "LANE_STACK_SESSION": "1", "HOME": self.tmp}

    def test_a_file_claimed_by_a_live_window_is_refused_to_another(self) -> None:
        for sid in ("s1", "s2"):
            call("SessionStart", {"session_id": sid, "cwd": self.tmp, "source": "startup"}, self.env)
        edit = lambda sid: call("PreToolUse", {"session_id": sid, "cwd": self.tmp, "tool_name": "Edit", "tool_input": {"file_path": f"{self.tmp}/a.ts"}}, self.env)
        self.assertIsNone(edit("s1"))
        refused = edit("s2")
        self.assertEqual(refused["hookSpecificOutput"]["permissionDecision"], "deny")
        call("SessionEnd", {"session_id": "s1", "cwd": self.tmp}, self.env)
        self.assertIsNone(edit("s2"))

    def test_plain_sessions_are_left_alone_unless_coord_is_switched_on(self) -> None:
        env = {k: v for k, v in self.env.items() if k != "LANE_STACK_SESSION"}
        self.assertIsNone(call("PreToolUse", {"session_id": "p", "cwd": self.tmp, "tool_name": "Edit", "tool_input": {"file_path": f"{self.tmp}/a.ts"}}, env))
        Path(self.tmp, ".agents", "config").mkdir(parents=True)
        Path(self.tmp, ".agents", "config", "coord.json").write_text('{"plain_sessions": true}')
        self.assertTrue(lane_coord.coord_enabled({"HOME": self.tmp}))
        self.assertFalse(lane_coord.coord_enabled({"HOME": self.tmp, "LANE_COORD": "0"}))

    def test_git_airbag_saves_uncommitted_work_before_a_destructive_command(self) -> None:
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"], cwd=self.tmp, check=True)
        Path(self.tmp, "a.ts").write_text("changed\n")
        call("PreToolUse", {"session_id": "s1", "cwd": self.tmp, "tool_name": "Bash", "tool_input": {"command": "git checkout -- a.ts"}}, self.env)
        refs = subprocess.run(["git", "for-each-ref", "refs/lane-airbag/"], cwd=self.tmp, capture_output=True, text=True).stdout
        self.assertIn("refs/lane-airbag/", refs)
        advice = call("PostToolUse", {"session_id": "s1", "cwd": self.tmp, "tool_name": "Bash"}, self.env)
        self.assertIn("git-airbag", advice["hookSpecificOutput"]["additionalContext"])

    def test_subagent_cap(self) -> None:
        env = {**self.env, "LANE_SUBAGENT_CAP": "1"}
        first = call("PreToolUse", {"session_id": "s1", "cwd": self.tmp, "tool_name": "Task", "tool_input": {"prompt": "do x", "subagent_type": "general"}}, env)
        self.assertIn("[context pack]", first["hookSpecificOutput"]["updatedInput"]["prompt"])
        second = call("PreToolUse", {"session_id": "s1", "cwd": self.tmp, "tool_name": "Task", "tool_input": {"prompt": "do y"}}, env)
        self.assertEqual(second["hookSpecificOutput"]["permissionDecision"], "deny")


class ClaimRaceTest(unittest.TestCase):
    def test_atomic_claim_refusal_denies_the_edit(self) -> None:
        # A-018: both windows can miss foreign_holder; only the claim lock may allow the edit.
        import sma_hooks

        with tempfile.TemporaryDirectory(prefix="coord-race-") as td, patch.dict(os.environ, {"LANE_COORD_HOME": td}), patch.object(lane_coord, "repo_root", return_value=td):
            lane_coord.register("a", cwd=td)
            lane_coord.register("b", cwd=td)
            original = lane_coord.foreign_holder
            barrier = threading.Barrier(2)

            def before(*args):
                result = original(*args)
                barrier.wait(timeout=3)
                return result

            def worker(sid):
                return sma_hooks.stream_claims({"tool": "edit", "path": "src/shared.ts", "sid": sid, "cwd": td})

            with patch.object(lane_coord, "foreign_holder", side_effect=before):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(worker, ["a", "b"]))
        denies = sum(deny is not None for deny, _advice in results)
        self.assertEqual(denies, 1)


class LaneCoordTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        os.environ["LANE_COORD_HOME"] = str(Path(self.tmp, "coord"))

    def test_file_prefix_is_not_a_claim_collision(self) -> None:
        # A-019: src/app.ts is not a directory prefix of src/app.tsx.
        self.assertFalse(lane_coord._overlap("src/app.ts", "src/app.tsx"))
        self.assertTrue(lane_coord._overlap("src/app.ts", "src/app.ts"))
        self.assertTrue(lane_coord._overlap("src/", "src/app.ts"))
        self.assertTrue(lane_coord._overlap("src/**", "src/app.ts"))

    def test_claims_are_atomic_and_collide_on_overlapping_globs(self) -> None:
        lane_coord.register("a", cwd=self.tmp)
        lane_coord.register("b", cwd=self.tmp)
        self.assertTrue(lane_coord.claim("a", ["src/**"], self.tmp)["ok"])
        self.assertFalse(lane_coord.claim("b", ["src/x.ts", "docs/y.md"], self.tmp)["ok"])
        self.assertTrue(lane_coord.claim("b", ["docs/y.md"], self.tmp)["ok"])
        self.assertEqual(lane_coord.force_clear("src/**", "window a is gone", self.tmp), 1)

    def test_counters_journal_state_and_names(self) -> None:
        self.assertEqual([lane_coord.next_slot("port", self.tmp) for _ in range(2)], [1, 2])
        self.assertTrue(lane_coord.consume("port", 7, self.tmp))
        self.assertEqual(lane_coord.next_slot("port", self.tmp), 8)
        lane_coord.journal("w", "turn", {"files": ["a"]}, self.tmp)
        lane_coord.journal("w", "turn", {"files": ["b"]}, self.tmp)
        self.assertTrue(lane_coord.chain_ok("w", self.tmp))
        state = Path(self.tmp, "STATE.md")
        state.write_text("# Notes\nkeep me\n")
        lane_coord.state_section(str(state), "phase 2 running")
        self.assertIn("keep me", state.read_text())
        self.assertEqual(lane_coord.state_section(str(state)), "phase 2 running")
        self.assertEqual(lane_coord.machine_name("Fix the Login page!"), "fix-the-login-page")


if __name__ == "__main__":
    unittest.main()
