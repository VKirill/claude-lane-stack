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
        self.project_cwd = self.root / "worktree"
        self.project_cwd.mkdir()
        self.provider_args = self.root / "provider-args.jsonl"
        self.provider = self.root / "fake-grok"
        self.provider.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                import time
                from pathlib import Path

                with Path(os.environ["FAKE_ARGS_LOG"]).open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(sys.argv[1:]) + "\\n")
                print("fake provider start", flush=True)
                time.sleep(float(os.environ.get("FAKE_SLEEP", "0.05")))
                print("fake provider done", flush=True)
                raise SystemExit(int(os.environ.get("FAKE_EXIT", "0")))
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
