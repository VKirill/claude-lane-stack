from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_CTL = ROOT / "bin" / "lane-ctl"
WRITER = ROOT / "agents" / "grok" / "writer.md"


class LaneCtlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_dir = self.root / ".agents" / "runs" / "test-run"
        self.tasks_dir = self.run_dir / "tasks"
        self.tasks_dir.mkdir(parents=True)
        (self.root / ".agents" / "night-shift.yaml").write_text(
            'verification_executables: ["true", "printf", "sleep"]\n',
            encoding="utf-8",
        )
        self.project_cwd = self.root / "worktree"
        self.project_cwd.mkdir()
        self.fake_home = self.root / "home"
        self.grok_home = self.fake_home / ".grok"
        self.grok_home.mkdir(parents=True)
        (self.fake_home / ".codex").mkdir()
        (self.fake_home / ".codex" / "auth.json").write_text(
            "{}\n", encoding="utf-8"
        )
        self.provider_args = self.project_cwd / "provider-args.jsonl"
        self.provider = self.project_cwd / "fake-provider"
        self.provider.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import hashlib
                import json
                import os
                import re
                import sys
                import time
                from pathlib import Path

                args = sys.argv[1:]
                if "--version" in args:
                    print("grok 0.2.103-test (fake)")
                    raise SystemExit(0)

                with Path(os.environ["FAKE_ARGS_LOG"]).open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(args) + "\\n")

                if args and args[0] == "exec":
                    prompt = sys.stdin.read()
                    task_id = re.search(r"task_id=([^;]+)", prompt).group(1)
                    prompt_sha256 = re.search(
                        r"prompt_sha256=([0-9a-f]{64})", prompt
                    ).group(1)
                    report_text = (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n"
                        "SUMMARY: fake Codex fallback\\n"
                        "<<<LANE_REPORT:END>>>"
                    )
                    print(json.dumps({"type": "thread.started", "thread_id": "codex-thread"}), flush=True)
                    print(json.dumps({"type": "turn.started"}), flush=True)
                    print(
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {"type": "agent_message", "text": report_text},
                            }
                        ),
                        flush=True,
                    )
                    print(
                        json.dumps(
                            {
                                "type": "turn.completed",
                                "usage": {"input_tokens": 10, "output_tokens": 5},
                            }
                        ),
                        flush=True,
                    )
                    raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))
                streaming = "--output-format" in args and args[
                    args.index("--output-format") + 1
                ] == "streaming-json"
                session_flag = "--session-id" if "--session-id" in args else "--resume"
                session_id = args[args.index(session_flag) + 1]

                def emit(payload):
                    print(json.dumps(payload), flush=True)

                if streaming:
                    emit({"type": "session", "sessionId": session_id})
                    emit({"type": "text", "data": "fake provider start\\n"})
                else:
                    print("fake provider start", flush=True)
                time.sleep(float(os.environ.get("FAKE_SLEEP", "0.05")))
                exit_code = int(os.environ.get("FAKE_EXIT", "0"))
                if os.environ.get("FAKE_STDERR"):
                    print(os.environ["FAKE_STDERR"], file=sys.stderr, flush=True)
                report_text = None
                if streaming and exit_code == 0:
                    prompt_path = Path(args[args.index("--prompt-file") + 1])
                    rules = args[args.index("--rules") + 1]
                    task_id = re.search(r"task_id=([^;]+)", rules).group(1)
                    report_mode = os.environ.get("FAKE_REPORT", "complete")
                    if report_mode != "missing":
                        report_status = (
                            "complete" if report_mode == "complete" else report_mode
                        )
                        prompt_sha256 = hashlib.sha256(
                            prompt_path.read_bytes()
                        ).hexdigest()
                        report_text = (
                            "<<<LANE_REPORT:BEGIN>>>\\n"
                            f"TASK_ID: {task_id}\\n"
                            f"PROMPT_SHA256: {prompt_sha256}\\n"
                            f"STATUS: {report_status}\\n"
                            "SUMMARY: fake lane-ctl report\\n"
                            "<<<LANE_REPORT:END>>>\\n"
                        )
                if streaming:
                    emit({"type": "text", "data": "fake provider done\\n"})
                    if report_text is not None:
                        emit({"type": "text", "data": report_text})
                    if exit_code == 0:
                        emit(
                            {
                                "type": "end",
                                "stopReason": "EndTurn",
                                "sessionId": session_id,
                                "modelUsage": {
                                    args[args.index("--model") + 1]: {
                                        "inputTokens": 10,
                                        "outputTokens": 5,
                                        "modelCalls": 1,
                                    }
                                },
                            }
                        )
                    else:
                        emit({"type": "error", "message": "fake provider failed"})
                else:
                    print("fake provider done", flush=True)
                raise SystemExit(exit_code)
                """
            ),
            encoding="utf-8",
        )
        self.provider.chmod(0o755)

    def write_task(
        self,
        task_id: str = "001",
        *,
        verification: list[str] | None = None,
    ) -> Path:
        commands = verification or []
        verification_yaml = "\n".join(
            f"  - {json.dumps(command)}" for command in commands
        )
        raw = (
            f"id: {json.dumps(task_id)}\n"
            "title: Test task\n"
            f"project_cwd: {json.dumps(str(self.project_cwd))}\n"
            "owns_paths:\n"
            "  - example.txt\n"
            "verification:\n"
            f"{verification_yaml if verification_yaml else '  []'}\n"
        )
        task_file = self.tasks_dir / f"{task_id}.yaml"
        task_file.write_text(raw, encoding="utf-8")
        return task_file

    def write_v2_task(
        self,
        task_id: str = "001",
        *,
        verification: list[dict] | None = None,
        verify: str = "tests",
        risk: str = "low",
        with_run_contract: bool = True,
    ) -> Path:
        if with_run_contract:
            (self.run_dir / "run.yaml").write_text(
                "schema_version: 2\n", encoding="utf-8"
            )
        entries = []
        for entry in verification or []:
            if isinstance(entry, dict):
                normalized = dict(entry)
                cwd = normalized.get("cwd")
                if isinstance(cwd, str) and not Path(cwd).is_absolute():
                    normalized["cwd"] = str((self.project_cwd / cwd).resolve())
                entries.append(normalized)
            else:
                entries.append(entry)
        raw = (
            "schema_version: 2\n"
            f"id: {json.dumps(task_id)}\n"
            "title: Schema v2 test task\n"
            "status: done\n"
            f"risk: {risk}\n"
            f"verify: {verify}\n"
            f"project_cwd: {json.dumps(str(self.project_cwd))}\n"
            "owns_paths:\n"
            "  - example.txt\n"
            f"verification: {json.dumps(entries)}\n"
        )
        task_file = self.tasks_dir / f"{task_id}.yaml"
        task_file.write_text(raw, encoding="utf-8")
        return task_file

    def run_ctl(
        self,
        *args: str,
        check: bool = True,
        env: dict[str, str] | None = None,
        timeout: float = 15,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(LANE_CTL), *args]
        merged_env = os.environ.copy()
        merged_env["LANE_BG_BACKEND"] = "nohup"
        merged_env["HOME"] = str(self.fake_home)
        merged_env["FAKE_ARGS_LOG"] = str(self.provider_args)
        merged_env.update(env or {})
        return subprocess.run(
            command,
            cwd=ROOT,
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
            timeout=timeout,
        )

    def start(
        self,
        task_file: Path,
        task_id: str = "001",
        *,
        check: bool = True,
        env: dict[str, str] | None = None,
        include_task_id: bool = True,
        include_model: bool = True,
        **kwargs: str,
    ):
        args = [
            "start",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            "--binary",
            str(self.provider),
            "--pool-size",
            "1",
            "--idle",
            "5",
            "--max-runtime",
            "15",
        ]
        if include_task_id:
            args[3:3] = ["--task-id", task_id]
        if include_model:
            args.extend(["--model", "test-model"])
        for name, value in kwargs.items():
            args.extend([f"--{name.replace('_', '-')}", value])
        return self.run_ctl(*args, check=check, env=env)

    def wait_status(self, task_id: str = "001", timeout: float = 10) -> dict:
        deadline = time.monotonic() + timeout
        last: dict = {}
        while time.monotonic() < deadline:
            result = self.run_ctl(
                "status",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                task_id,
                "--json",
                check=False,
            )
            if result.returncode == 0:
                last = json.loads(result.stdout)
                if last["status"] not in {"running", "unknown"}:
                    return last
            time.sleep(0.05)
        self.fail(f"lane did not finish: {last}")

    def init_git_project(self) -> str:
        subprocess.run(["git", "init", "-q"], cwd=self.project_cwd, check=True)
        subprocess.run(
            ["git", "config", "user.email", "lane-ctl@example.test"],
            cwd=self.project_cwd,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Lane Ctl Test"],
            cwd=self.project_cwd,
            check=True,
        )
        (self.project_cwd / "example.txt").write_text(
            "baseline\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "example.txt"], cwd=self.project_cwd, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "baseline"],
            cwd=self.project_cwd,
            check=True,
        )
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.project_cwd,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def review_state_digests(self, base_ref: str) -> tuple[str, str]:
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "--binary",
                "--full-index",
                base_ref,
                "--",
            ],
            cwd=self.project_cwd,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=self.project_cwd,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.split(b"\0")
        tree = hashlib.sha256()
        tree.update(b"lane-review-tree-v1\0")
        tree.update(base_ref.encode("ascii") + b"\0")
        tree.update(len(diff).to_bytes(8, "big"))
        tree.update(diff)
        for raw_path in sorted(path for path in untracked if path):
            path = self.project_cwd / os.fsdecode(raw_path)
            if path.is_symlink():
                kind = b"l"
                content = os.fsencode(os.readlink(path))
            else:
                kind = b"x" if path.stat().st_mode & 0o111 else b"f"
                content = path.read_bytes()
            tree.update(len(raw_path).to_bytes(8, "big"))
            tree.update(raw_path)
            tree.update(kind)
            tree.update(len(content).to_bytes(8, "big"))
            tree.update(content)
        return hashlib.sha256(diff).hexdigest(), tree.hexdigest()

    def write_review_receipt(
        self,
        artifact: Path,
        state: dict,
        base_ref: str,
        *,
        attempt: int,
    ) -> dict:
        diff_sha256, tree_sha256 = self.review_state_digests(base_ref)
        receipt = {
            "schema_version": 2,
            "receipt_type": "task_re_review",
            "task_id": state["task_id"],
            "task_sha256": state["task_sha256"],
            "attempt": attempt,
            "project_cwd": str(self.project_cwd),
            "base_ref": base_ref,
            "reviewed_diff_sha256": diff_sha256,
            "reviewed_tree_sha256": tree_sha256,
            "verdict": "passed",
            "findings": [],
            "reviewed_at": "2026-07-18T12:00:00+00:00",
        }
        (artifact / "review.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        return receipt

    def test_rejects_task_path_escape_and_project_mismatch(self) -> None:
        outside = self.root / "outside.yaml"
        outside.write_text(
            f'id: "001"\nproject_cwd: {json.dumps(str(self.project_cwd))}\n',
            encoding="utf-8",
        )
        escaped = self.start(outside, check=False)
        self.assertEqual(escaped.returncode, 2)
        self.assertIn("RUN_DIR/tasks", escaped.stderr)

        task_file = self.write_task()
        other = self.root / "other-worktree"
        other.mkdir()
        mismatch = self.run_ctl(
            "start",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(other),
            "--binary",
            str(self.provider),
            check=False,
        )
        self.assertEqual(mismatch.returncode, 2)
        self.assertIn("project_cwd", mismatch.stderr)

    def test_start_detaches_builds_deterministic_prompt_and_status_finishes(self) -> None:
        task_file = self.write_task(verification=["true"])
        raw_task = task_file.read_text(encoding="utf-8")
        started_at = time.monotonic()
        result = self.start(
            task_file,
            env={"FAKE_SLEEP": "0.2"},
            include_task_id=False,
            include_model=False,
        )
        self.assertLess(time.monotonic() - started_at, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "started")

        artifact = self.run_dir / "artifacts" / "001"
        prompt = (artifact / "prompt.md").read_text(encoding="utf-8")
        self.assertTrue(prompt.startswith(WRITER.read_text(encoding="utf-8").rstrip()))
        self.assertTrue(prompt.endswith(raw_task))

        status = self.wait_status()
        self.assertEqual(status["status"], "awaiting_verification")
        self.assertEqual(status["exit_code"], 0)
        self.assertTrue(status["heartbeat"]["exists"])
        self.assertTrue((artifact / "control.json").is_file())
        control = json.loads((artifact / "control.json").read_text(encoding="utf-8"))
        self.assertIn("grok-4.5", control["argv"])

        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        verified = json.loads(
            self.run_ctl(
                "status",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                "001",
                "--json",
            ).stdout
        )
        self.assertEqual(verified["status"], "verified")

    def test_retry_replays_recorded_argv_vector(self) -> None:
        task_file = self.write_task()
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        control_path = self.run_dir / "artifacts" / "001" / "control.json"
        before = json.loads(control_path.read_text(encoding="utf-8"))
        recorded = before["argv"]

        retried = self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
        )
        self.assertEqual(json.loads(retried.stdout)["status"], "started")
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        after = json.loads(control_path.read_text(encoding="utf-8"))
        self.assertEqual(after["argv"], recorded)
        self.assertEqual(after["attempt"], 2)
        self.assertEqual(len(self.provider_args.read_text().splitlines()), 2)

        rejected = self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("retry limit reached", rejected.stderr)

    def test_retry_rejects_rehashed_duplicate_option(self) -> None:
        task_file = self.write_task()
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        control_path = self.run_dir / "artifacts" / "001" / "control.json"
        control = json.loads(control_path.read_text(encoding="utf-8"))
        control["argv"].extend(["--binary", "/bin/true"])
        canonical = json.dumps(
            control["argv"], ensure_ascii=False, separators=(",", ":")
        )
        control["argv_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        control_path.write_text(json.dumps(control), encoding="utf-8")

        rejected = self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )

        self.assertEqual(rejected.returncode, 2)
        self.assertIn("duplicate option", rejected.stderr)
        self.assertEqual(len(self.provider_args.read_text().splitlines()), 1)

    def test_retry_rejects_tampered_prompt(self) -> None:
        task_file = self.write_task()
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        prompt = self.run_dir / "artifacts" / "001" / "prompt.md"
        prompt.write_text("tampered prompt\n", encoding="utf-8")

        retried = self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )

        self.assertEqual(retried.returncode, 2)
        self.assertIn("prompt checksum mismatch", retried.stderr)

    def test_five_detached_lanes_use_pool_five_and_finish_independently(self) -> None:
        task_files = [self.write_task(f"00{index}") for index in range(1, 6)]
        launched_at = time.monotonic()
        starts = [
            self.start(
                task_file,
                task_id=f"00{index}",
                env={"FAKE_SLEEP": "4"},
                pool_size="5",
            )
            for index, task_file in enumerate(task_files, 1)
        ]
        launch_elapsed = time.monotonic() - launched_at
        self.assertLess(launch_elapsed, 3.5)
        self.assertTrue(all(json.loads(item.stdout)["status"] == "started" for item in starts))

        statuses = [self.wait_status(f"00{index}") for index in range(1, 6)]
        self.assertEqual([item["exit_code"] for item in statuses], [0] * 5)
        for index in range(1, 6):
            artifact = self.run_dir / "artifacts" / f"00{index}"
            self.assertEqual((artifact / "lane-bg.exit").read_text().strip(), "0")
            self.assertIn("fake provider done", (artifact / "provider.out").read_text())
            self.assertTrue((artifact / "control.json").is_file())
        sessions = json.loads((self.run_dir / "sessions.json").read_text())
        self.assertEqual(sessions["defaults"]["pool_size"], 5)
        self.assertEqual(len(sessions["sessions"]), 5)

    def test_nonzero_provider_exit_is_preserved_through_lane_exec(self) -> None:
        task_file = self.write_task()
        self.start(task_file, env={"FAKE_EXIT": "7"})
        status = self.wait_status()
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["exit_code"], 7)
        artifact = self.run_dir / "artifacts" / "001"
        self.assertEqual((artifact / "lane-bg.exit").read_text().strip(), "7")
        event_types = [
            event["type"]
            for event in json.loads(
                self.run_ctl(
                    "events",
                    "--run-dir",
                    str(self.run_dir),
                    "--task-id",
                    "001",
                    "--json",
                ).stdout
            )
        ]
        self.assertIn("exit", event_types)

    def test_cancel_terminates_the_recorded_detached_process(self) -> None:
        task_file = self.write_task()
        self.start(task_file, env={"FAKE_SLEEP": "30"})
        self.addCleanup(
            lambda: self.run_ctl(
                "cancel",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                "001",
                check=False,
            )
        )
        running = self.run_ctl(
            "status",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--json",
        )
        self.assertTrue(json.loads(running.stdout)["running"])

        cancelled = self.run_ctl(
            "cancel",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
        )
        payload = json.loads(cancelled.stdout)
        self.assertEqual(payload["status"], "cancelled")
        self.assertFalse(payload["running"])
        control = json.loads(
            (self.run_dir / "artifacts" / "001" / "control.json").read_text()
        )
        self.assertIn("cancel_requested_at", control)

    def test_verify_uses_task_commands_and_writes_evidence(self) -> None:
        marker = self.project_cwd / "marker.txt"
        commands = [
            "printf 'verified output\\n'",
            f"printf marker > {marker.name} && test -s {marker.name}",
        ]
        task_file = self.write_task(verification=commands)
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        result = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["pool_size"], 2)
        self.assertEqual([item["command"] for item in payload["commands"]], commands)
        artifact = self.run_dir / "artifacts" / "001"
        self.assertTrue((artifact / "verified.txt").is_file())
        evidence = (artifact / "verified.txt").read_text(encoding="utf-8")
        self.assertIn("verified output", evidence)
        self.assertEqual(
            json.loads((artifact / "verification.json").read_text())["status"],
            "passed",
        )

        too_wide = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            "--verify-pool-size",
            "11",
            check=False,
        )
        self.assertEqual(too_wide.returncode, 2)
        self.assertIn("between 1 and 10", too_wide.stderr)

    def test_legacy_smoke_verify_with_empty_snapshot_fails_closed(self) -> None:
        for task_id, verify_level in (("001", "smoke"), ("002", "tests")):
            with self.subTest(verify=verify_level):
                task_file = self.write_task(task_id, verification=[])
                task_file.write_text(
                    task_file.read_text(encoding="utf-8")
                    + f"verify: {verify_level}\n",
                    encoding="utf-8",
                )
                self.start(task_file, task_id=task_id)
                self.assertEqual(
                    self.wait_status(task_id)["status"], "awaiting_verification"
                )
                artifact = self.run_dir / "artifacts" / task_id
                control = json.loads((artifact / "control.json").read_text())
                self.assertEqual(control["verification_commands"], [])

                # Receipts written by older lane-ctl versions must not keep a
                # smoke/tests task green once the recorded snapshot is known
                # to be empty.
                (artifact / "verification.json").write_text(
                    json.dumps(
                        {
                            "status": "passed",
                            "attempt": control["attempt"],
                            "commands": [],
                        }
                    ),
                    encoding="utf-8",
                )
                (artifact / "verified.txt").write_text(
                    f"attempt={control['attempt']}\n", encoding="utf-8"
                )
                stale_status = self.wait_status(task_id)
                self.assertEqual(stale_status["status"], "awaiting_verification")
                self.assertFalse(stale_status["verification"]["verified"])

                rejected = self.run_ctl(
                    "verify",
                    "--run-dir",
                    str(self.run_dir),
                    "--task-file",
                    str(task_file),
                    "--project-cwd",
                    str(self.project_cwd),
                    check=False,
                )
                self.assertEqual(rejected.returncode, 2)
                self.assertIn(
                    "requires at least one verification command", rejected.stderr
                )
                self.assertTrue((artifact / "verification.json").exists())
                self.assertTrue((artifact / "verified.txt").exists())

                accepted = self.run_ctl(
                    "accept",
                    "--run-dir",
                    str(self.run_dir),
                    "--task-id",
                    task_id,
                    check=False,
                )
                self.assertEqual(accepted.returncode, 2)
                self.assertFalse((artifact / "acceptance.json").exists())

    def test_legacy_verify_none_preserves_empty_snapshot_compatibility(self) -> None:
        task_file = self.write_task(verification=[])
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")

        verified = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        payload = json.loads(verified.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["commands"], [])
        artifact = self.run_dir / "artifacts" / "001"
        self.assertTrue((artifact / "verified.txt").is_file())
        self.assertEqual(
            json.loads((artifact / "verification.json").read_text())["status"],
            "passed",
        )

    def test_verify_requires_completed_provider_and_uses_start_snapshot(self) -> None:
        task_file = self.write_task(verification=["printf original > snapshot.txt"])
        before_start = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(before_start.returncode, 2)

        self.start(task_file, env={"FAKE_SLEEP": "1"})
        while_running = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(while_running.returncode, 2)
        self.assertIn("provider is running", while_running.stderr)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")

        task_file.write_text(
            task_file.read_text(encoding="utf-8").replace(
                "printf original > snapshot.txt",
                "printf changed > changed.txt",
            ),
            encoding="utf-8",
        )
        verified = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        payload = json.loads(verified.stdout)
        self.assertEqual(payload["attempt"], 1)
        self.assertTrue((self.project_cwd / "snapshot.txt").is_file())
        self.assertFalse((self.project_cwd / "changed.txt").exists())

    def test_verify_times_out_and_rejects_pool_symlink_escape(self) -> None:
        task_file = self.write_task(verification=["sleep 2"])
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        timed_out = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            "--command-timeout",
            "1",
            check=False,
        )
        self.assertEqual(timed_out.returncode, 1)
        result = json.loads(timed_out.stdout)
        self.assertEqual(result["commands"][0]["exit_code"], 124)

        pool = self.run_dir / "artifacts" / ".verification-pool"
        for child in pool.iterdir():
            child.unlink()
        pool.rmdir()
        outside = self.root / "outside-pool"
        outside.mkdir()
        pool.symlink_to(outside, target_is_directory=True)
        escaped = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(escaped.returncode, 2)
        self.assertIn("verification pool path", escaped.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_v2_requires_run_contract_and_freezes_task_yaml(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}],
            with_run_contract=False,
        )
        missing_run = self.start(task_file, check=False)
        self.assertEqual(missing_run.returncode, 2)
        self.assertIn("require RUN_DIR/run.yaml", missing_run.stderr)

        (self.run_dir / "run.yaml").write_text(
            "schema_version: 2\n", encoding="utf-8"
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["status"], "awaiting_verification")
        self.assertEqual(
            state["task_sha256"], hashlib.sha256(task_file.read_bytes()).hexdigest()
        )

        task_file.write_text(
            task_file.read_text(encoding="utf-8").replace(
                "Schema v2 test task", "mutated task"
            ),
            encoding="utf-8",
        )
        retried = self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(retried.returncode, 2)
        self.assertIn("sha256 mismatch", retried.stderr)
        verified = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(verified.returncode, 2)
        self.assertIn("sha256 mismatch", verified.stderr)

    def test_v2_retry_preserves_attempt_directories(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}]
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        artifact = self.run_dir / "artifacts" / "001"
        attempt_one = artifact / "attempts" / "01"
        original_control = (attempt_one / "control.json").read_bytes()
        original_prompt = (attempt_one / "prompt.md").read_bytes()
        original_output = (attempt_one / "provider.out").read_bytes()
        original_report = (artifact / "report.md").read_bytes()

        self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
        )
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        attempt_two = artifact / "attempts" / "02"
        state = json.loads((artifact / "state.json").read_text())
        self.assertEqual(state["current_attempt"], 2)
        self.assertEqual((attempt_one / "control.json").read_bytes(), original_control)
        self.assertEqual((attempt_one / "prompt.md").read_bytes(), original_prompt)
        self.assertEqual((attempt_one / "provider.out").read_bytes(), original_output)
        self.assertEqual((attempt_one / "report.md").read_bytes(), original_report)
        self.assertEqual(
            json.loads((attempt_one / "runtime.json").read_text())["attempt"], 1
        )
        self.assertEqual(
            json.loads((attempt_two / "runtime.json").read_text())["attempt"], 2
        )
        for attempt_dir in (attempt_one, attempt_two):
            for name in (
                "control.json",
                "prompt.md",
                "provider.out",
                "lane-exec.log",
                "lane-bg.exit",
            ):
                self.assertTrue((attempt_dir / name).is_file(), f"{attempt_dir}/{name}")
        self.assertFalse((artifact / "control.json").exists())

    def test_v2_codex_sol_high_fallback_keeps_normal_acceptance_chain(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "true", "cwd": ".", "timeout_sec": 5}],
            verify="tests",
        )
        failure_env = {
            "FAKE_EXIT": "1",
            "FAKE_STDERR": "Settings fetch failed after 3 attempts private-detail",
        }
        self.start(
            task_file,
            env=failure_env,
            model="grok-4.5",
        )
        first = self.wait_status()
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["provider"]["name"], "grok")
        self.assertEqual(first["provider"]["failure_class"], "grok_bootstrap_transient")
        self.assertTrue(first["provider"]["fallback_eligible"])

        self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            env=failure_env,
        )
        second = self.wait_status()
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(second["status"], "failed")

        self.run_ctl(
            "fallback",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--binary",
            str(self.provider),
        )
        ready = self.wait_status()
        self.assertEqual(ready["attempt"], 3)
        self.assertEqual(ready["status"], "awaiting_verification")
        self.assertEqual(ready["provider"]["name"], "codex")
        self.assertEqual(ready["provider"]["model"], "gpt-5.6-sol")

        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": state["task_sha256"],
                    "scope": "task",
                    "scope_task_ids": ["001"],
                }
            ),
            encoding="utf-8",
        )
        accepted = json.loads(
            self.run_ctl(
                "accept",
                "--run-dir",
                str(self.run_dir),
                "--task-file",
                str(task_file),
                "--project-cwd",
                str(self.project_cwd),
            ).stdout
        )
        self.assertTrue(accepted["accepted"])
        self.assertEqual(accepted["provider"], "codex")
        self.assertEqual(accepted["model"], "gpt-5.6-sol")
        self.assertEqual(accepted["attempt"], 3)

    def test_v2_status_rejects_stale_previous_attempt_verification(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}]
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
        )
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        attempt_two = artifact / "attempts" / "02"
        (attempt_two / "verification.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "task_id": "001",
                    "task_sha256": state["task_sha256"],
                    "task_file": str(task_file),
                    "project_cwd": str(self.project_cwd),
                    "attempt": 1,
                    "status": "passed",
                    "commands": [],
                }
            ),
            encoding="utf-8",
        )

        status = json.loads(
            self.run_ctl(
                "status",
                "--run-dir",
                str(self.run_dir),
                "--task-id",
                "001",
                "--json",
            ).stdout
        )
        self.assertEqual(status["status"], "awaiting_verification")
        self.assertFalse(status["verification"]["verified"])

    def test_v2_status_requires_complete_provider_report(self) -> None:
        cases = (
            (
                "001",
                "missing",
                "failed",
                "provider_exit_nonzero",
                False,
                "retry",
            ),
            (
                "002",
                "partial",
                "provider_incomplete",
                "report_incomplete",
                False,
                "retry",
            ),
            (
                "003",
                "complete",
                "awaiting_verification",
                "provider_complete",
                True,
                "verify",
            ),
        )
        for task_id, report_mode, expected, reason, complete, next_action in cases:
            with self.subTest(task_id=task_id):
                task_file = self.write_v2_task(
                    task_id,
                    verification=[
                        {"command": "true", "cwd": ".", "timeout_sec": 5}
                    ],
                )
                self.start(
                    task_file,
                    task_id=task_id,
                    env={"FAKE_REPORT": report_mode},
                )

                status = self.wait_status(task_id)
                self.assertEqual(status["status"], expected)
                self.assertEqual(status["reason"], reason)
                self.assertIs(status["report_complete"], complete)
                self.assertEqual(status["next_action"], next_action)
                self.assertIs(status["report"]["complete"], complete)

    def test_v2_tampered_report_fails_status_verify_and_accept_closed(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "true", "cwd": ".", "timeout_sec": 5}]
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        artifact = self.run_dir / "artifacts" / "001"
        with (artifact / "report.md").open("a", encoding="utf-8") as handle:
            handle.write("TAMPERED: true\n")

        status = self.wait_status()
        self.assertEqual(status["status"], "provider_incomplete")
        self.assertFalse(status["report"]["trusted"])
        self.assertEqual(status["report"]["reason"], "report_digest_mismatch")

        verified = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(verified.returncode, 2)
        self.assertIn("report_digest_mismatch", verified.stderr)
        accepted = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(accepted.returncode, 2)
        self.assertIn("report_digest_mismatch", accepted.stderr)

    def test_v2_structured_verification_honors_cwd_and_timeout(self) -> None:
        nested = self.project_cwd / "nested"
        nested.mkdir()
        (nested / "test_marker.py").write_text(
            textwrap.dedent(
                """\
                import unittest
                from pathlib import Path

                class MarkerTest(unittest.TestCase):
                    def test_marker(self):
                        Path("marker.txt").write_text("nested", encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        (self.project_cwd / "test_slow.py").write_text(
            textwrap.dedent(
                """\
                import time
                import unittest

                class SlowTest(unittest.TestCase):
                    def test_slow(self):
                        time.sleep(2)
                """
            ),
            encoding="utf-8",
        )
        task_file = self.write_v2_task(
            verification=[
                {
                    "command": "python3 -m unittest -v test_marker.py",
                    "cwd": "nested",
                    "timeout_sec": 5,
                },
                {
                    "command": "python3 -m unittest -v test_slow.py",
                    "cwd": ".",
                    "timeout_sec": 1,
                },
            ]
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        started = time.monotonic()
        verified = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(verified.returncode, 1)
        self.assertLess(time.monotonic() - started, 2)
        payload = json.loads(verified.stdout)
        self.assertEqual(payload["commands"][0]["resolved_cwd"], str(nested))
        self.assertEqual(payload["commands"][1]["timeout_sec"], 1)
        self.assertEqual(payload["commands"][1]["exit_code"], 124)
        self.assertEqual((nested / "marker.txt").read_text(), "nested")
        state = json.loads(
            (self.run_dir / "artifacts" / "001" / "state.json").read_text()
        )
        self.assertEqual(state["status"], "verification_failed")

    def test_v2_rejects_shell_composition_before_provider_launch(self) -> None:
        marker = self.project_cwd / "unsafe-verification-ran"
        task_file = self.write_v2_task(
            verification=[
                {
                    "command": f"true && touch {marker.name}",
                    "cwd": ".",
                    "timeout_sec": 5,
                }
            ]
        )

        rejected = self.start(task_file, check=False)

        self.assertEqual(rejected.returncode, 2)
        self.assertIn("shell composition", rejected.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse(self.provider_args.exists())

    def test_v2_verify_rejects_vacuous_smoke_contract(self) -> None:
        task_file = self.write_v2_task(verification=[], verify="smoke")
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        rejected = self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("requires at least one verification command", rejected.stderr)
        attempt = self.run_dir / "artifacts" / "001" / "attempts" / "01"
        self.assertFalse((attempt / "verification.json").exists())

        legacy_strings = self.write_v2_task(
            "002",
            verification=["true"],  # type: ignore[list-item]
            verify="tests",
        )
        rejected_schema = self.start(
            legacy_strings,
            task_id="002",
            check=False,
        )
        self.assertEqual(rejected_schema.returncode, 2)
        self.assertIn("string verification commands are legacy-only", rejected_schema.stderr)
        self.assertFalse(
            (self.run_dir / "artifacts" / "002" / "state.json").exists()
        )

    def test_v2_acceptance_gate_writes_exact_receipt_and_done_state(self) -> None:
        base_ref = self.init_git_project()
        (self.project_cwd / "example.txt").write_text(
            "baseline\nreviewed fix\n", encoding="utf-8"
        )
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}],
            risk="high",
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        artifact = self.run_dir / "artifacts" / "001"
        missing_evidence = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(missing_evidence.returncode, 2)

        state = json.loads((artifact / "state.json").read_text())
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": "wrong",
                    "scope": "task",
                    "scope_task_ids": ["001"],
                }
            ),
            encoding="utf-8",
        )
        wrong_hash = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(wrong_hash.returncode, 2)
        self.assertIn("task_sha256", wrong_hash.stderr)
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": state["task_sha256"],
                    "scope": "run",
                    "scope_task_ids": ["001", "ghost"],
                }
            ),
            encoding="utf-8",
        )
        wrong_scope = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(wrong_scope.returncode, 2)
        self.assertIn("scope_task_ids", wrong_scope.stderr)
        owns_receipt = json.loads((artifact / "owns-check.json").read_text())
        owns_receipt.update(scope="task", scope_task_ids=["001"])
        (artifact / "owns-check.json").write_text(
            json.dumps(owns_receipt), encoding="utf-8"
        )
        missing_review = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            check=False,
        )
        self.assertEqual(missing_review.returncode, 2)
        self.assertIn("review.json", missing_review.stderr)
        self.write_review_receipt(artifact, state, base_ref, attempt=1)

        accepted = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        receipt = json.loads(accepted.stdout)
        self.assertEqual(
            set(receipt),
            {
                "schema_version",
                "task_id",
                "task_sha256",
                "attempt",
                "provider_exit",
                "provider",
                "model",
                "report",
                "report_sha256",
                "owns_check",
                "verification",
                "review",
                "accepted",
                "accepted_at",
            },
        )
        self.assertEqual(receipt["review"], "passed")
        runtime = json.loads(
            (artifact / "attempts" / "01" / "runtime.json").read_text()
        )
        self.assertEqual(receipt["report_sha256"], runtime["report_sha256"])
        self.assertTrue(receipt["accepted"])
        self.assertEqual(
            json.loads((artifact / "acceptance.json").read_text()), receipt
        )
        final_state = json.loads((artifact / "state.json").read_text())
        self.assertEqual(final_state["status"], "accepted")
        self.assertTrue(final_state["accepted"])
        self.assertEqual(self.wait_status()["status"], "accepted")

        review_path = artifact / "review.json"
        valid_review = json.loads(review_path.read_text())
        mismatched_review = dict(valid_review)
        mismatched_review["task_id"] = "other-task"
        review_path.write_text(json.dumps(mismatched_review), encoding="utf-8")
        self.assertEqual(self.wait_status()["status"], "verified")
        self.assertFalse(json.loads((artifact / "state.json").read_text())["accepted"])
        review_path.write_text(json.dumps(valid_review), encoding="utf-8")
        self.assertEqual(self.wait_status()["status"], "accepted")

        (artifact / "acceptance.json").unlink()
        self.assertEqual(self.wait_status()["status"], "verified")
        repaired_state = json.loads((artifact / "state.json").read_text())
        self.assertFalse(repaired_state["accepted"])

    def test_v2_accept_rejects_incomplete_review_receipt(self) -> None:
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}],
            risk="high",
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": state["task_sha256"],
                    "scope": "task",
                    "scope_task_ids": ["001"],
                }
            ),
            encoding="utf-8",
        )
        (artifact / "review.json").write_text(
            json.dumps({"verdict": "passed", "findings": []}),
            encoding="utf-8",
        )

        rejected = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("review.json fields", rejected.stderr)
        self.assertFalse((artifact / "acceptance.json").exists())

    def test_v2_accept_rejects_review_from_previous_attempt(self) -> None:
        base_ref = self.init_git_project()
        (self.project_cwd / "example.txt").write_text(
            "baseline\nreviewed fix\n", encoding="utf-8"
        )
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}],
            risk="high",
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "retry",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
        )
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": state["task_sha256"],
                    "scope": "task",
                    "scope_task_ids": ["001"],
                }
            ),
            encoding="utf-8",
        )
        self.write_review_receipt(artifact, state, base_ref, attempt=1)

        rejected = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("attempt is not current", rejected.stderr)
        self.assertFalse((artifact / "acceptance.json").exists())

    def test_v2_accept_rejects_post_review_worktree_edit(self) -> None:
        base_ref = self.init_git_project()
        (self.project_cwd / "example.txt").write_text(
            "baseline\nreviewed fix\n", encoding="utf-8"
        )
        untracked = self.project_cwd / "new-file.txt"
        untracked.write_text("reviewed new file\n", encoding="utf-8")
        task_file = self.write_v2_task(
            verification=[{"command": "node --version", "cwd": ".", "timeout_sec": 5}],
            risk="high",
        )
        self.start(task_file)
        self.assertEqual(self.wait_status()["status"], "awaiting_verification")
        self.run_ctl(
            "verify",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
        )
        artifact = self.run_dir / "artifacts" / "001"
        state = json.loads((artifact / "state.json").read_text())
        (artifact / "owns-check.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "status": "passed",
                    "exit_code": 0,
                    "cwd": str(self.project_cwd),
                    "task_sha256": state["task_sha256"],
                    "scope": "task",
                    "scope_task_ids": ["001"],
                }
            ),
            encoding="utf-8",
        )
        diff_sha256, tree_sha256 = self.review_state_digests(base_ref)
        (artifact / "review.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "receipt_type": "task_re_review",
                    "task_id": "001",
                    "task_sha256": state["task_sha256"],
                    "attempt": 1,
                    "project_cwd": str(self.project_cwd),
                    "base_ref": base_ref,
                    "reviewed_diff_sha256": diff_sha256,
                    "reviewed_tree_sha256": tree_sha256,
                    "verdict": "passed",
                    "findings": [],
                    "reviewed_at": "2026-07-18T12:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        with untracked.open("a", encoding="utf-8") as fh:
            fh.write("post-review edit\n")
        current_diff, current_tree = self.review_state_digests(base_ref)
        self.assertEqual(current_diff, diff_sha256)
        self.assertNotEqual(current_tree, tree_sha256)

        rejected = self.run_ctl(
            "accept",
            "--run-dir",
            str(self.run_dir),
            "--task-file",
            str(task_file),
            "--project-cwd",
            str(self.project_cwd),
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("reviewed worktree digest", rejected.stderr)
        self.assertFalse((artifact / "acceptance.json").exists())

    def test_tail_and_events_are_bounded_to_known_artifacts(self) -> None:
        artifact = self.run_dir / "artifacts" / "001"
        artifact.mkdir(parents=True)
        (artifact / "lane-bg.supervisor.log").write_text(
            "one\ntwo\nthree\n", encoding="utf-8"
        )
        tailed = self.run_ctl(
            "tail",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--source",
            "supervisor",
            "--lines",
            "2",
        )
        self.assertEqual(tailed.stdout, "two\nthree\n")
        outside_log = self.root / "outside.log"
        outside_log.write_text("secret\n", encoding="utf-8")
        (artifact / "lane-bg.supervisor.log").unlink()
        (artifact / "lane-bg.supervisor.log").symlink_to(outside_log)
        symlinked = self.run_ctl(
            "tail",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--source",
            "supervisor",
            check=False,
        )
        self.assertEqual(symlinked.returncode, 2)
        self.assertNotIn("secret", symlinked.stdout)
        rejected = self.run_ctl(
            "tail",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--source",
            "../../outside",
            check=False,
        )
        self.assertEqual(rejected.returncode, 2)

        events = self.run_dir / "events.jsonl"
        events.write_text(
            json.dumps({"type": "start", "task_id": "001"})
            + "\n"
            + json.dumps({"type": "start", "task_id": "002"})
            + "\n",
            encoding="utf-8",
        )
        filtered = self.run_ctl(
            "events",
            "--run-dir",
            str(self.run_dir),
            "--task-id",
            "001",
            "--json",
        )
        payload = json.loads(filtered.stdout)
        self.assertEqual([event["task_id"] for event in payload], ["001"])


if __name__ == "__main__":
    unittest.main()
