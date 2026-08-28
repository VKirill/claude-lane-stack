from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "pm_stop_sentinel.py"
sys.path.insert(0, str(ROOT / "hooks"))

from pm_stop_sentinel import (  # noqa: E402
    already_acked,
    decide_stop,
    decide_watch,
    is_supervisor_spawn,
    pick_controller,
    watch_run,
)


def _ctrl(dir_path: Path, slug: str, stage: str) -> Path:
    run = dir_path / ".agents" / "runs" / slug
    run.mkdir(parents=True, exist_ok=True)
    path = run / "controller.json"
    path.write_text(json.dumps({"stage": stage, "schema_version": 1}), encoding="utf-8")
    return path


class DecideStopTests(unittest.TestCase):
    def test_allows_stop_while_supervisor_inflight(self) -> None:
        code, err = decide_stop(
            {
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "background_tasks": [
                    {
                        "type": "subagent",
                        "agent_type": "run-supervisor",
                        "status": "running",
                    }
                ],
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_allows_user_leaving(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "owns-fix", "blocked")
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "agent_type": "dev-orchestrator",
                    "cwd": str(cwd),
                    "reason": "prompt_input_exit",
                    "last_assistant_message": "waiting",
                }
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

    def test_ignores_parked_rs_chips(self) -> None:
        code, err = decide_stop(
            {
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "background_tasks": [
                    {
                        "type": "teammate",
                        "name": "rs-money-finish",
                        "status": "idle",
                    },
                    {
                        "type": "subagent",
                        "agent_type": "run-supervisor",
                        "status": "completed",
                    },
                ],
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_allows_running_among_parked_rs_chips(self) -> None:
        code, err = decide_stop(
            {
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "background_tasks": [
                    {"type": "teammate", "name": "rs-auth-ux", "status": "idle"},
                    {
                        "type": "subagent",
                        "agent_type": "run-supervisor",
                        "name": "rs-db-pool-leak",
                        "status": "running",
                    },
                ],
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_allows_second_stop_while_supervisor_inflight(self) -> None:
        code, err = decide_stop(
            {
                "hook_event_name": "Stop",
                "agent_type": "dev-orchestrator",
                "stop_hook_active": True,
                "background_tasks": [
                    {"type": "subagent", "agent_type": "run-supervisor"}
                ],
                "cwd": "/tmp/no-such-lane-project",
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_pm_orphan_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "fix-login", "running")
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "agent_type": "dev-orchestrator",
                    "cwd": str(cwd),
                    "last_assistant_message": "waiting for progress",
                }
            )
            self.assertEqual(code, 2)
            self.assertIn("fix-login", err)
            self.assertIn("Re-dispatch", err)

    def test_pm_blocked_unacked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "owns-fix", "blocked")
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "agent_type": "dev-orchestrator",
                    "cwd": str(cwd),
                    "last_assistant_message": "supervisor finished, sitting idle",
                }
            )
            self.assertEqual(code, 2)
            self.assertIn("blocked", err)

    def test_pm_blocked_acked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "owns-fix", "blocked")
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "agent_type": "dev-orchestrator",
                    "cwd": str(cwd),
                    "last_assistant_message": (
                        "owns-fix blocked. DONE blocked .agents/runs/owns-fix/controller.json"
                    ),
                }
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

    def test_non_pm_ignores_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "old-run", "blocked")
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(cwd),
                    "last_assistant_message": "editing a file",
                }
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

    def test_disabled(self) -> None:
        os.environ["LANE_PM_STOP_SENTINEL"] = "0"
        try:
            code, err = decide_stop(
                {
                    "hook_event_name": "Stop",
                    "background_tasks": [
                        {"type": "subagent", "agent_type": "run-supervisor"}
                    ],
                }
            )
            self.assertEqual(code, 0)
        finally:
            os.environ.pop("LANE_PM_STOP_SENTINEL", None)


class SpawnAndWatchTests(unittest.TestCase):
    def test_supervisor_spawn_detect(self) -> None:
        self.assertTrue(
            is_supervisor_spawn(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Agent",
                    "tool_input": {
                        "subagent_type": "run-supervisor",
                        "prompt": "watch .agents/runs/fix-login",
                    },
                }
            )
        )
        self.assertFalse(
            is_supervisor_spawn(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Agent",
                    "tool_input": {"subagent_type": "Explore", "prompt": "find files"},
                }
            )
        )
        self.assertFalse(
            is_supervisor_spawn(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": "echo run-supervisor"},
                }
            )
        )

    def test_decide_watch_slug(self) -> None:
        spec = decide_watch(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Agent",
                "cwd": "/proj",
                "tool_input": {
                    "subagent_type": "run-supervisor",
                    "prompt": "Watch /proj/.agents/runs/fix-login/controller.json",
                },
            }
        )
        self.assertIsNotNone(spec)
        cwd, slug = spec
        self.assertEqual(str(cwd), "/proj")
        self.assertEqual(slug, "fix-login")

    def test_watch_wakes_on_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            path = _ctrl(cwd, "late-block", "running")

            def flip() -> None:
                time.sleep(0.15)
                path.write_text(json.dumps({"stage": "blocked"}), encoding="utf-8")

            threading.Thread(target=flip, daemon=True).start()
            code, err = watch_run(cwd, "late-block", timeout_s=2.0, poll_s=0.05)
            self.assertEqual(code, 2)
            self.assertIn("blocked", err)

    def test_pick_newest_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            old = _ctrl(cwd, "old", "accepted")
            os.utime(old, (time.time() - 120, time.time() - 120))
            new = _ctrl(cwd, "new", "blocked")
            picked = pick_controller(cwd)
            self.assertEqual(picked, new)

    def test_already_acked(self) -> None:
        self.assertTrue(
            already_acked(
                "fix-x DONE accepted .agents/runs/fix-x/controller.json",
                "fix-x",
                "accepted",
            )
        )
        self.assertFalse(already_acked("still waiting", "fix-x", "blocked"))


class HookProcessTests(unittest.TestCase):
    def test_process_stop_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _ctrl(cwd, "fix-login", "running")
            r = subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps(
                    {
                        "hook_event_name": "Stop",
                        "agent_type": "dev-orchestrator",
                        "cwd": str(cwd),
                        "last_assistant_message": "waiting for progress",
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("Re-dispatch", r.stderr)

    def test_process_explore_no_watch(self) -> None:
        r = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(
                {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Agent",
                    "tool_input": {"subagent_type": "Explore", "prompt": "x"},
                    "cwd": "/tmp",
                }
            ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
