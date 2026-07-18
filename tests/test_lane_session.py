from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE_SESSION = ROOT / "bin" / "lane-session"
LANE_EXEC = ROOT / "bin" / "lane-exec"

class LaneSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_dir = self.root / ".agents" / "runs" / "warm-run"
        self.run_dir.mkdir(parents=True)
        self.cwd = self.root / "worktree"
        self.cwd.mkdir()
        self.args_log = self.root / "provider-args.jsonl"
        self.conversations = self.root / "conversations"
        self.conversations.mkdir()
        self.fake_provider = self.root / "fake-provider"
        self.fake_provider.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import subprocess
                import sys
                import time
                import uuid
                from pathlib import Path

                args = sys.argv[1:]
                if os.environ.get("FAKE_PID_FILE"):
                    Path(os.environ["FAKE_PID_FILE"]).write_text(str(os.getpid()), encoding="utf-8")
                if os.environ.get("FAKE_CHILD_PID_FILE"):
                    child = subprocess.Popen(
                        [sys.executable, "-c", "import time; time.sleep(30)"]
                    )
                    Path(os.environ["FAKE_CHILD_PID_FILE"]).write_text(
                        str(child.pid), encoding="utf-8"
                    )
                log = Path(os.environ["FAKE_ARGS_LOG"])
                with log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(args) + "\\n")

                if os.environ.get("FAKE_PROVIDER_KIND") == "" and "--conversation" not in args:
                    conversations = Path(os.environ["UNUSED_REMOVED"])
                    conversations.mkdir(parents=True, exist_ok=True)
                    db = conversations / f"{uuid.uuid4()}.db"
                    with db.open("a+", encoding="utf-8") as fh:
                        fh.write("open")
                        fh.flush()
                        time.sleep(float(os.environ.get("FAKE_SLEEP", "0.35")))
                else:
                    duration = float(os.environ.get("FAKE_SLEEP", "0"))
                    pulse = float(os.environ.get("FAKE_PULSE", "0"))
                    if pulse > 0:
                        deadline = time.monotonic() + duration
                        while time.monotonic() < deadline:
                            print("provider pulse", flush=True)
                            time.sleep(min(pulse, max(0, deadline - time.monotonic())))
                    else:
                        time.sleep(duration)

                print("provider complete")
                raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))
                """
            ),
            encoding="utf-8",
        )
        self.fake_provider.chmod(0o755)

    def _run(
        self,
        provider: str,
        task_id: str,
        *,
        role: str | None = None,
        max_tasks: int = 7,
        pool_size: int | None = 2,
        sleep: float | None = None,
        exit_code: int = 0,
        run_dir: Path | None = None,
        extra_env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        prompt = self.root / f"task-{task_id}.md"
        prompt.write_text(f"Implement task {task_id}\n", encoding="utf-8")
        output = self.root / f"task-{task_id}.log"
        env = os.environ.copy()
        env.update(
            {
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": provider,
                "FAKE_SLEEP": str(
                    sleep if sleep is not None else (0.35 if provider == "" else 0)
                ),
                "FAKE_EXIT": str(exit_code),
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        env.update(extra_env or {})
        command = [
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            provider,
            "--run-dir",
            str(run_dir or self.run_dir),
            "--task-id",
            task_id,
            "--role",
            role or ("lane-frontend" if provider == "" else "grok"),
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(output),
            "--binary",
            str(self.fake_provider),
            "--model",
            "test-model",
            "--max-tasks",
            str(max_tasks),
        ]
        if pool_size is not None:
            command.extend(["--pool-size", str(pool_size)])
        result = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=check,
        )
        return result

    def _calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.args_log.read_text().splitlines()]

    def _state(self) -> dict:
        return json.loads((self.run_dir / "sessions.json").read_text())

    def test_provider_pool_defaults_to_five_and_accepts_ten(self) -> None:
        self._run("grok", "default-pool", pool_size=None)
        self.assertEqual(self._state()["defaults"]["pool_size"], 5)

        second_run = self.root / ".agents" / "runs" / "ten-pool"
        second_run.mkdir(parents=True)
        self._run("grok", "ten-pool", pool_size=10, run_dir=second_run)
        state = json.loads((second_run / "sessions.json").read_text())
        self.assertEqual(state["defaults"]["pool_size"], 10)

        rejected = self._run("grok", "too-wide", pool_size=11, check=False)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("pool-size must be between 1 and 10", rejected.stderr)

    def test_read_only_xdg_runtime_falls_back_to_user_tmp(self) -> None:
        unusable = self.root / "runtime-is-a-file"
        unusable.write_text("not a directory\n", encoding="utf-8")

        result = self._run(
            "grok",
            "runtime-fallback",
            extra_env={"XDG_RUNTIME_DIR": str(unusable)},
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._state()["sessions"]["grok:grok:0"]["status"], "idle")

    def test_grok_reuses_session_then_rotates_at_task_limit(self) -> None:
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "002", max_tasks=2)
        self._run("grok", "003", max_tasks=2)

        first, second, third = self._calls()
        self.assertIn("--no-auto-update", first)
        self.assertIn("--prompt-file", first)
        self.assertNotIn("--single", first)
        first_id = first[first.index("--session-id") + 1]
        self.assertEqual(second[second.index("--resume") + 1], first_id)
        third_id = third[third.index("--session-id") + 1]
        self.assertNotEqual(third_id, first_id)

        state = self._state()
        active = state["sessions"]["grok:grok:0"]
        self.assertEqual(active["session_id"], third_id)
        self.assertEqual(active["tasks"], ["003"])
        self.assertEqual(state["history"][0]["tasks"], ["001", "002"])
        self.assertEqual(state["history"][0]["rotation_reason"], "task_limit")


    def test_parallel_tasks_use_distinct_pool_sessions(self) -> None:
        prompt1 = self.root / "parallel-001.md"
        prompt2 = self.root / "parallel-002.md"
        prompt1.write_text("Task 001\n", encoding="utf-8")
        prompt2.write_text("Task 002\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "0.6",
                "UNUSED_REMOVED": str(self.conversations),
            }
        )

        def command(task_id: str, prompt: Path) -> list[str]:
            return [
                sys.executable,
                str(LANE_SESSION),
                "run",
                "--provider",
                "grok",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                task_id,
                "--role",
                "grok",
                "--cwd",
                str(self.cwd),
                "--prompt-file",
                str(prompt),
                "--output",
                str(self.root / f"parallel-{task_id}.log"),
                "--binary",
                str(self.fake_provider),
                "--model",
                "test-model",
                "--pool-size",
                "2",
            ]

        first = subprocess.Popen(command("001", prompt1), env=env)
        time.sleep(0.1)
        second = subprocess.Popen(command("002", prompt2), env=env)
        self.assertEqual(first.wait(timeout=10), 0)
        self.assertEqual(second.wait(timeout=10), 0)

        calls = self._calls()
        session_ids = {
            call[call.index("--session-id") + 1]
            for call in calls
            if "--session-id" in call
        }
        self.assertEqual(len(session_ids), 2)
        self.assertEqual(set(self._state()["sessions"]), {"grok:grok:0", "grok:grok:1"})

    def test_failed_provider_session_is_rotated_before_next_task(self) -> None:
        failed = self._run("grok", "001", exit_code=9, check=False)
        self.assertEqual(failed.returncode, 9)
        self._run("grok", "002")

        first, second = self._calls()
        failed_id = first[first.index("--session-id") + 1]
        next_id = second[second.index("--session-id") + 1]
        self.assertNotEqual(next_id, failed_id)
        self.assertNotIn("--resume", second)

        state = self._state()
        self.assertEqual(state["history"][0]["rotation_reason"], "provider_exit_9")
        self.assertEqual(state["sessions"]["grok:grok:0"]["tasks"], ["002"])
        self.assertFalse((self.run_dir / ".sessions.lock").exists())
        self.assertFalse((self.run_dir / ".session-locks").exists())

    def test_two_runs_in_same_worktree_never_resume_each_others_session(self) -> None:
        second_run = self.root / ".agents" / "runs" / "vk-bot"
        second_run.mkdir(parents=True)

        self._run("grok", "ui-001", run_dir=self.run_dir)
        self._run("grok", "bot-001", run_dir=second_run)
        self._run("grok", "ui-002", run_dir=self.run_dir)
        self._run("grok", "bot-002", run_dir=second_run)

        ui_first, bot_first, ui_second, bot_second = self._calls()
        ui_id = ui_first[ui_first.index("--session-id") + 1]
        bot_id = bot_first[bot_first.index("--session-id") + 1]
        self.assertNotEqual(ui_id, bot_id)
        self.assertEqual(ui_second[ui_second.index("--resume") + 1], ui_id)
        self.assertEqual(bot_second[bot_second.index("--resume") + 1], bot_id)
        self.assertTrue(all("--continue" not in call for call in self._calls()))


    def test_copied_session_state_cannot_cross_run_boundary(self) -> None:
        second_run = self.root / ".agents" / "runs" / "copied-run"
        second_run.mkdir(parents=True)

        self._run("grok", "001", run_dir=self.run_dir)
        shutil.copy2(self.run_dir / "sessions.json", second_run / "sessions.json")
        self._run("grok", "002", run_dir=second_run)

        first, second = self._calls()
        first_id = first[first.index("--session-id") + 1]
        self.assertNotIn("--resume", second)
        second_id = second[second.index("--session-id") + 1]
        self.assertNotEqual(first_id, second_id)
        copied_state = json.loads((second_run / "sessions.json").read_text())
        self.assertEqual(copied_state["history"][0]["rotation_reason"], "run_dir_changed")

    def test_provider_output_is_streamed_through_wrapper_stdout(self) -> None:
        result = self._run("grok", "001")
        self.assertIn("provider complete", result.stdout)

    def test_repeated_task_id_still_counts_toward_rotation_limit(self) -> None:
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "001", max_tasks=2)
        self._run("grok", "001", max_tasks=2)

        first, second, third = self._calls()
        first_id = first[first.index("--session-id") + 1]
        self.assertEqual(second[second.index("--resume") + 1], first_id)
        third_id = third[third.index("--session-id") + 1]
        self.assertNotEqual(third_id, first_id)
        state = self._state()
        self.assertEqual(state["history"][0]["success_count"], 2)


    def test_sigterm_stops_provider_and_invalidates_session(self) -> None:
        prompt = self.root / "signal-task.md"
        prompt.write_text("Wait for termination\n", encoding="utf-8")
        provider_pid = self.root / "provider.pid"
        child_pid_file = self.root / "provider-child.pid"
        env = os.environ.copy()
        env.update(
            {
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "30",
                "FAKE_PID_FILE": str(provider_pid),
                "FAKE_CHILD_PID_FILE": str(child_pid_file),
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        command = [
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            "grok",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "signal-001",
            "--role",
            "grok",
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(self.root / "signal-task.log"),
            "--binary",
            str(self.fake_provider),
            "--model",
            "test-model",
        ]
        manager = subprocess.Popen(command, env=env)
        deadline = time.monotonic() + 5
        while not provider_pid.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(provider_pid.exists())
        deadline = time.monotonic() + 5
        while not child_pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(child_pid_file.exists())
        provider_process_pid = int(provider_pid.read_text())
        tool_child_pid = int(child_pid_file.read_text())

        os.kill(manager.pid, signal.SIGTERM)
        self.assertEqual(manager.wait(timeout=5), 143)
        for pid, label in (
            (provider_process_pid, "provider"),
            (tool_child_pid, "provider tool child"),
        ):
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"{label} survived lane-session SIGTERM")

        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_143")

    def test_lane_exec_observes_streamed_provider_activity(self) -> None:
        prompt = self.root / "long-task.md"
        prompt.write_text("Stay active\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "FAKE_ARGS_LOG": str(self.args_log),
                "FAKE_PROVIDER_KIND": "grok",
                "FAKE_SLEEP": "6",
                "FAKE_PULSE": "0.5",
                "UNUSED_REMOVED": str(self.conversations),
            }
        )
        command = [
            sys.executable,
            str(LANE_EXEC),
            "--idle",
            "5",
            "--max",
            "12",
            "--",
            sys.executable,
            str(LANE_SESSION),
            "run",
            "--provider",
            "grok",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "long-001",
            "--role",
            "grok",
            "--cwd",
            str(self.cwd),
            "--prompt-file",
            str(prompt),
            "--output",
            str(self.root / "long-task.log"),
            "--binary",
            str(self.fake_provider),
            "--model",
            "test-model",
        ]
        result = subprocess.run(
            command,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("provider pulse", result.stdout)
        self.assertNotIn("IDLE timeout", result.stderr)

if __name__ == "__main__":
    unittest.main()
