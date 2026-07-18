from __future__ import annotations

import hashlib
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
                if "--version" in args:
                    print(os.environ.get("FAKE_VERSION_TEXT", "grok 0.2.103-test (fake)"))
                    raise SystemExit(0)
                streaming = "--output-format" in args and args[
                    args.index("--output-format") + 1
                ] == "streaming-json"

                def emit(payload):
                    print(json.dumps(payload), flush=True)

                if os.environ.get("FAKE_PID_FILE"):
                    Path(os.environ["FAKE_PID_FILE"]).write_text(str(os.getpid()), encoding="utf-8")
                if os.environ.get("FAKE_ENV_LOG"):
                    Path(os.environ["FAKE_ENV_LOG"]).write_text(
                        ",".join(
                            (
                                os.environ.get("GROK_CLAUDE_HOOKS_ENABLED", "<unset>"),
                                os.environ.get("CLAUDE_LANE_AUTOMATION", "<unset>"),
                            )
                        ),
                        encoding="utf-8",
                    )
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
                            if streaming:
                                emit({"type": "thought", "data": "provider pulse"})
                            else:
                                print("provider pulse", flush=True)
                            time.sleep(min(pulse, max(0, deadline - time.monotonic())))
                    else:
                        time.sleep(duration)

                exit_code = int(os.environ.get("FAKE_EXIT", "0"))
                if os.environ.get("FAKE_STDERR"):
                    print(os.environ["FAKE_STDERR"], file=sys.stderr, flush=True)
                if streaming:
                    mode = os.environ.get("FAKE_STREAM_MODE", "valid")
                    session_flag = "--session-id" if "--session-id" in args else "--resume"
                    session_id = args[args.index(session_flag) + 1]
                    model = args[args.index("--model") + 1]
                    if mode == "malformed":
                        print("not-json", flush=True)
                    else:
                        text_size = int(os.environ.get("FAKE_TEXT_SIZE", "0"))
                        text_data = "x" * text_size if text_size else "provider complete"
                        emit({"type": "text", "data": text_data})
                        if exit_code != 0 or mode == "error":
                            emit({"type": "error", "message": "provider failed"})
                        elif mode != "missing-end":
                            emit(
                                {
                                    "type": "end",
                                    "stopReason": os.environ.get("FAKE_STOP_REASON", "EndTurn"),
                                    "sessionId": session_id,
                                    "requestId": "request-test",
                                    "num_turns": 2,
                                    "usage": {
                                        "input_tokens": 10,
                                        "cache_read_input_tokens": 3,
                                        "output_tokens": 4,
                                        "reasoning_tokens": 2,
                                        "total_tokens": 17,
                                    },
                                    "modelUsage": {
                                        model: {
                                            "inputTokens": 10,
                                            "outputTokens": 4,
                                            "modelCalls": 2,
                                            "costUSD": 0.01,
                                        }
                                    },
                                    "total_cost_usd": 0.01,
                                    "total_cost_usd_ticks": 100000000,
                                }
                            )
                else:
                    print("provider complete")
                raise SystemExit(exit_code)
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
        binary: Path | None = None,
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
            str(binary or self.fake_provider),
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
        self.assertIn("--no-subagents", first)
        self.assertEqual(first[first.index("--sandbox") + 1], "workspace")
        self.assertEqual(first[first.index("--output-format") + 1], "streaming-json")
        rules = first[first.index("--rules") + 1]
        self.assertIn("task_id=001", rules)
        self.assertIn(f"workspace={self.cwd}", rules)
        expected_prompt_sha = hashlib.sha256(b"Implement task 001\n").hexdigest()
        self.assertIn(f"prompt_sha256={expected_prompt_sha}", rules)
        self.assertIn("owns_paths", rules)
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

    def test_session_without_workspace_sandbox_is_rotated(self) -> None:
        self._run("grok", "001")
        state_path = self.run_dir / "sessions.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        first_id = state["sessions"]["grok:grok:0"]["session_id"]
        state["sessions"]["grok:grok:0"].pop("sandbox", None)
        state_path.write_text(json.dumps(state), encoding="utf-8")

        self._run("grok", "002")

        active = self._state()["sessions"]["grok:grok:0"]
        self.assertNotEqual(active["session_id"], first_id)
        self.assertEqual(active["sandbox"], "workspace")
        self.assertEqual(self._state()["history"][0]["rotation_reason"], "sandbox_changed")

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

    def test_grok_writer_disables_claude_compat_hooks(self) -> None:
        env_log = self.root / "provider-env.txt"

        result = self._run(
            "grok",
            "hooks-001",
            extra_env={"FAKE_ENV_LOG": str(env_log)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(env_log.read_text(encoding="utf-8"), "0,1")

    def test_streaming_result_writes_sanitized_runtime_receipt(self) -> None:
        result = self._run("grok", "receipt-001")

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["provider"], "grok")
        self.assertEqual(receipt["provider_version"], "0.2.103-test")
        self.assertEqual(receipt["model"], "test-model")
        self.assertEqual(receipt["reasoning_effort"], "high")
        self.assertEqual(receipt["sandbox"], "workspace")
        self.assertFalse(receipt["subagents_enabled"])
        self.assertEqual(receipt["session_id"], self._state()["sessions"]["grok:grok:0"]["session_id"])
        self.assertEqual(receipt["provider_exit_code"], 0)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["stop_reason"], "EndTurn")
        self.assertEqual(receipt["usage"]["total_tokens"], 17)
        self.assertEqual(receipt["total_cost_usd_ticks"], 100000000)
        self.assertNotIn("request_id", receipt)

    def test_provider_control_strings_cannot_leak_into_runtime_artifacts(self) -> None:
        secret = "secret-customer-token"
        result = self._run(
            "grok",
            "control-string-001",
            extra_env={
                "FAKE_VERSION_TEXT": f"grok 9.8.7 {secret}",
                "FAKE_STOP_REASON": secret,
            },
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        receipt_source = (self.root / "runtime.json").read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        diagnostic = (self.root / "task-control-string-001.log").read_text(
            encoding="utf-8"
        )
        self.assertEqual(receipt["provider_version"], "9.8.7")
        self.assertEqual(receipt["stop_reason"], "Other")
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(
            receipt["protocol_error"],
            "unsuccessful terminal reason: Other",
        )
        self.assertNotIn(secret, receipt_source)
        self.assertNotIn(secret, diagnostic)

    def test_malformed_stream_fails_closed_and_invalidates_session(self) -> None:
        result = self._run(
            "grok",
            "malformed-001",
            extra_env={"FAKE_STREAM_MODE": "malformed"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_65")
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertFalse(receipt["protocol_valid"])
        self.assertEqual(receipt["provider_exit_code"], 0)
        self.assertEqual(receipt["exit_code"], 65)
        self.assertEqual(receipt["protocol_error"], "malformed streaming-json")
        diagnostic = (self.root / "task-malformed-001.log").read_text(encoding="utf-8")
        self.assertIn("grok protocol error", diagnostic)
        self.assertNotIn("not-json", diagnostic)

    def test_missing_end_event_fails_closed(self) -> None:
        result = self._run(
            "grok",
            "missing-end-001",
            extra_env={"FAKE_STREAM_MODE": "missing-end"},
            check=False,
        )

        self.assertEqual(result.returncode, 65, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["protocol_error"], "stream ended without an end event")

    def test_unsuccessful_terminal_reasons_fail_closed(self) -> None:
        for index, stop_reason in enumerate(("Cancelled", "Error", "MaxTokens"), start=1):
            with self.subTest(stop_reason=stop_reason):
                result = self._run(
                    "grok",
                    f"terminal-failure-{index}",
                    extra_env={"FAKE_STOP_REASON": stop_reason},
                    check=False,
                )

                self.assertEqual(result.returncode, 65, result.stderr)
                receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
                self.assertFalse(receipt["protocol_valid"])
                expected_reason = stop_reason if stop_reason in {"Cancelled", "Error"} else "Other"
                self.assertEqual(receipt["stop_reason"], expected_reason)
                self.assertEqual(
                    receipt["protocol_error"],
                    f"unsuccessful terminal reason: {expected_reason}",
                )

    def test_provider_stderr_is_diagnostic_not_structured_output(self) -> None:
        result = self._run(
            "grok",
            "stderr-001",
            extra_env={"FAKE_STDERR": "provider warning with sensitive detail"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["protocol_valid"])
        diagnostic = (self.root / "task-stderr-001.log").read_text(encoding="utf-8")
        self.assertIn("grok stderr", diagnostic)
        self.assertNotIn("sensitive detail", diagnostic)

    def test_launch_exception_writes_sanitized_failure_receipt(self) -> None:
        broken_provider = self.root / "broken-provider-secret-token"
        broken_provider.write_text("not an executable format\n", encoding="utf-8")
        broken_provider.chmod(0o755)

        result = self._run(
            "grok",
            "launch-failure-001",
            binary=broken_provider,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        active = self._state()["sessions"]["grok:grok:0"]
        self.assertTrue(active["invalid"])
        self.assertEqual(active["invalid_reason"], "provider_exit_125")
        receipt_path = self.root / "runtime.json"
        self.assertTrue(receipt_path.is_file())
        receipt_source = receipt_path.read_text(encoding="utf-8")
        receipt = json.loads(receipt_source)
        self.assertEqual(receipt["provider_exit_code"], 125)
        self.assertEqual(receipt["exit_code"], 125)
        self.assertEqual(receipt["failure_class"], "OSError")
        self.assertFalse(receipt["protocol_valid"])
        self.assertNotIn("failure_message", receipt)
        self.assertNotIn("secret-token", receipt_source)
        self.assertNotIn("Exec format", receipt_source)

    def test_provider_log_is_bounded_without_hiding_live_output(self) -> None:
        result = self._run(
            "grok",
            "large-output-001",
            extra_env={"FAKE_TEXT_SIZE": str(1024 * 1024 + 100)},
        )

        self.assertIn("x" * 100, result.stdout)
        self.assertLessEqual((self.root / "task-large-output-001.log").stat().st_size, 1024 * 1024)
        receipt = json.loads((self.root / "runtime.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["log_truncated"])

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
        self.assertIn("GROK_EVENT thought", result.stdout)
        self.assertNotIn("provider pulse", result.stdout)
        self.assertNotIn("IDLE timeout", result.stderr)

if __name__ == "__main__":
    unittest.main()
