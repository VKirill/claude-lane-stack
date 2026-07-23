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
CONTROLLER = ROOT / "bin" / "run-controller"


class RunControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_dir = self.root / "repo" / ".agents" / "runs" / "demo"
        self.tasks_dir = self.run_dir / "tasks"
        self.project = self.root / "worktree"
        self.tasks_dir.mkdir(parents=True)
        self.project.mkdir()
        self.fake_state = self.root / "fake-state.json"
        self.fake_log = self.root / "actions.jsonl"
        self.fake_plan = self.root / "plan.json"
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1, "002": 4, "003": 1}}),
            encoding="utf-8",
        )
        self.fake_lane_ctl = self.root / "fake-lane-ctl"
        self.fake_lane_ctl.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                import time
                import fcntl
                from pathlib import Path

                args = sys.argv[1:]
                action = args[0]
                exit_code = 0
                task_id = None
                if "--task-id" in args:
                    task_id = args[args.index("--task-id") + 1]
                if task_id is None and "--task-file" in args:
                    task_file = Path(args[args.index("--task-file") + 1])
                    for line in task_file.read_text(encoding="utf-8").splitlines():
                        if line.startswith("id:"):
                            task_id = line.split(":", 1)[1].strip().strip("'\\\"")
                            break
                state_path = Path(os.environ["FAKE_CTL_STATE"])
                log_path = Path(os.environ["FAKE_CTL_LOG"])
                plan = json.loads(Path(os.environ["FAKE_CTL_PLAN"]).read_text())
                state = json.loads(state_path.read_text()) if state_path.exists() else {}

                def record(kind, **extra):
                    with log_path.open("a", encoding="utf-8") as handle:
                        handle.write(
                            json.dumps({"action": kind, "task_id": task_id, **extra}) + "\\n"
                        )

                if action == "start":
                    if task_id in plan.get("start_error", []):
                        record("start")
                        print("forced start failure", file=sys.stderr)
                        raise SystemExit(7)
                    selected_provider = args[args.index("--provider") + 1]
                    state[task_id] = {
                        "status": "running",
                        "attempt": 1,
                        "polls": 0,
                        "provider": selected_provider,
                    }
                    record("start")
                    payload = {"status": "started", "task_id": task_id, "attempt": 1}
                elif action == "status":
                    if task_id in plan.get("status_error", []):
                        print("forced status failure", file=sys.stderr)
                        raise SystemExit(7)
                    item = state.get(task_id, {"status": "not_started", "attempt": 0, "polls": 0})
                    if item["status"] == "running":
                        item["polls"] += 1
                        if task_id in plan.get("lose_state_after_start", []):
                            item["status"] = "not_started"
                        finish_after = plan.get("finish_after", {}).get(task_id, 1)
                        if item["status"] == "running" and item["polls"] >= finish_after:
                            if task_id in plan.get("stall_first", []) and item["attempt"] == 1:
                                item["status"] = "stalled"
                            elif task_id in plan.get("cancel_first", []) and item["attempt"] == 1:
                                item["status"] = "cancelled"
                            elif item.get("provider") == "codex" and task_id in plan.get("fallback_fail", []):
                                item["status"] = "failed"
                            elif item.get("provider") in {"agy", "grok", "qwen"} and task_id in plan.get("fail_always", []):
                                item["status"] = "failed"
                            elif task_id in plan.get("fail_first", []) and item["attempt"] == 1:
                                item["status"] = "provider_failed"
                            else:
                                item["status"] = "awaiting_verification"
                    state[task_id] = item
                    payload = {
                        "schema_version": 2,
                        "task_id": task_id,
                        "status": item["status"],
                        "accepted": item["status"] == "accepted",
                        "attempt": item["attempt"],
                        "provider": {
                            "name": item.get("provider", "grok"),
                            "model": (
                                "gpt-5.6-sol"
                                if item.get("provider") == "codex"
                                else "gemini-3.6-flash-high"
                                if item.get("provider") == "agy"
                                else "qwen3.8-max-preview"
                                if item.get("provider") == "qwen"
                                else "grok-4.5"
                            ),
                            "failure_class": (
                                f"{item.get('provider')}_bootstrap_transient"
                                if item["status"] == "failed"
                                and item.get("provider") in {"agy", "grok", "qwen"}
                                and task_id in plan.get("eligible_failure", [])
                                else "codex_provider_failed"
                                if item["status"] == "failed" and item.get("provider") == "codex"
                                else None
                            ),
                            "failure_retryable": item["status"] == "failed",
                            "fallback_eligible": (
                                item["status"] == "failed"
                                and item.get("provider") in {"agy", "grok", "qwen"}
                                and task_id in plan.get("eligible_failure", [])
                            ),
                        },
                    }
                elif action == "retry":
                    item = state[task_id]
                    item.update(status="running", attempt=item["attempt"] + 1, polls=0)
                    retry_details = {}
                    if plan.get("record_retry_peers"):
                        retry_details["other_running"] = sorted(
                            other_id
                            for other_id, other in state.items()
                            if other_id != task_id and other.get("status") == "running"
                        )
                    record("retry", **retry_details)
                    payload = {"status": "started", "task_id": task_id, "attempt": item["attempt"]}
                elif action == "fallback":
                    item = state[task_id]
                    item.update(
                        status="running",
                        attempt=item["attempt"] + 1,
                        polls=0,
                        provider="codex",
                    )
                    record(
                        "fallback",
                        provider="codex",
                        model="gpt-5.6-sol",
                        reasoning_effort="high",
                    )
                    payload = {
                        "status": "started",
                        "task_id": task_id,
                        "attempt": item["attempt"],
                        "provider": "codex",
                    }
                elif action == "cancel":
                    item = state[task_id]
                    item["status"] = "cancelled"
                    record("cancel")
                    payload = {"status": "cancelled", "task_id": task_id}
                elif action == "verify":
                    delay = plan.get("verify_delay", {}).get(task_id, 0)
                    if delay:
                        record("verify_begin")
                        time.sleep(delay)
                        state = json.loads(state_path.read_text())
                    item = state[task_id]
                    if task_id in plan.get("verify_fail_always", []) or (
                        task_id in plan.get("verify_fail_first", []) and item["attempt"] == 1
                    ):
                        item["status"] = "verification_failed"
                        exit_code = 1
                    else:
                        item["status"] = "verified"
                    record("verify")
                    if delay:
                        record("verify_end")
                    payload = {
                        "status": "failed" if exit_code else "passed",
                        "task_id": task_id,
                        "detail": "x" * int(plan.get("verify_output_bytes", 0)),
                    }
                elif action == "accept":
                    if task_id in plan.get("accept_error", []):
                        record("accept")
                        print("forced accept failure", file=sys.stderr)
                        raise SystemExit(7)
                    state[task_id]["status"] = "accepted"
                    record("accept")
                    payload = {"status": "accepted", "task_id": task_id, "accepted": True}
                else:
                    raise SystemExit(2)
                lock_path = state_path.with_suffix(".lock")
                with lock_path.open("a+", encoding="utf-8") as lock:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    latest = json.loads(state_path.read_text()) if state_path.exists() else {}
                    if task_id in state:
                        latest[task_id] = state[task_id]
                    temporary = state_path.with_name(f".{state_path.name}.{os.getpid()}.tmp")
                    temporary.write_text(json.dumps(latest), encoding="utf-8")
                    os.replace(temporary, state_path)
                if action == "verify" and task_id in plan.get("verify_invalid_json", []):
                    print("not-json")
                else:
                    print(json.dumps(payload))
                raise SystemExit(exit_code)
                """
            ),
            encoding="utf-8",
        )
        self.fake_lane_ctl.chmod(0o755)
        self.fake_owns = self.root / "fake-check-owns"
        self.fake_owns.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                from pathlib import Path

                task_id = None
                for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
                    if line.startswith("id:"):
                        task_id = line.split(":", 1)[1].strip().strip("'\\\"")
                        break
                with Path(os.environ["FAKE_CTL_LOG"]).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"action": "owns", "task_id": task_id}) + "\\n")
                """
            ),
            encoding="utf-8",
        )
        self.fake_owns.chmod(0o755)
        self.fake_run_validate = self.root / "fake-run-validate"
        self.fake_run_validate.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys

                if os.environ.get("FAKE_VALIDATE_FAIL") == "1":
                    print("forced pre-dispatch failure", file=sys.stderr)
                    raise SystemExit(2)
                print("valid")
                """
            ),
            encoding="utf-8",
        )
        self.fake_run_validate.chmod(0o755)

    def write_run(self, provider_slots: int = 2, *, gate: str = "none", verification_slots: int = 2) -> None:
        self.run_dir.joinpath("run.yaml").write_text(
            "schema_version: 2\n"
            "slug: demo\n"
            f"repo: {json.dumps(str(self.run_dir.parents[2]))}\n"
            f"project_cwd: {json.dumps(str(self.project))}\n"
            "base_sha: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'\n"
            "created_at: '2026-07-18T00:00:00Z'\n"
            "score: 8\n"
            "pools:\n"
            f"  provider: {provider_slots}\n"
            f"  verification: {verification_slots}\n"
            f"gate: {gate}\n"
            "finalize:\n"
            "  progress_now: null\n"
            "  close_next: []\n"
            "  close_open: []\n",
            encoding="utf-8",
        )

    def write_task(self, task_id: str, depends_on: list[str] | None = None) -> Path:
        path = self.tasks_dir / f"{task_id}.yaml"
        dependencies = depends_on or []
        path.write_text(
            "schema_version: 2\n"
            f"id: '{task_id}'\n"
            f"project_cwd: {json.dumps(str(self.project))}\n"
            f"depends_on: {json.dumps(dependencies)}\n",
            encoding="utf-8",
        )
        return path

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "FAKE_CTL_STATE": str(self.fake_state),
                "FAKE_CTL_LOG": str(self.fake_log),
                "FAKE_CTL_PLAN": str(self.fake_plan),
                "LANE_BG_BACKEND": "nohup",
            }
        )
        return env

    def run_controller(self, *extra: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(CONTROLLER),
                "run",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
                "--poll-interval",
                "0.01",
                "--heartbeat-interval",
                "1",
                "--retry-backoff",
                "0",
                *extra,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=check,
            timeout=10,
        )

    def actions(self) -> list[dict[str, str]]:
        return [json.loads(line) for line in self.fake_log.read_text().splitlines()]

    def test_provider_cap_and_dag_release_are_progressive(self) -> None:
        self.write_run(provider_slots=2)
        self.write_task("001")
        self.write_task("002")
        self.write_task("003", ["001"])

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "accepted")
        self.assertEqual(receipt["tasks"]["001"]["provider"], "qwen")
        self.assertEqual(receipt["tasks"]["001"]["model"], "qwen3.8-max-preview")
        self.assertEqual(receipt["counts"], {"total": 3, "accepted": 3, "blocked": 0, "running": 0, "pending": 0})
        actions = self.actions()
        active: set[str] = set()
        maximum = 0
        for action in actions:
            if action["action"] == "start":
                active.add(action["task_id"])
                maximum = max(maximum, len(active))
            elif action["action"] == "accept":
                active.discard(action["task_id"])
        self.assertLessEqual(maximum, 2)
        start_003 = actions.index({"action": "start", "task_id": "003"})
        accept_001 = actions.index({"action": "accept", "task_id": "001"})
        accept_002 = actions.index({"action": "accept", "task_id": "002"})
        self.assertLess(accept_001, start_003)
        self.assertLess(start_003, accept_002)

    def test_explicit_agy_writer_remains_selectable(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")

        result = self.run_controller("--provider", "agy")

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["tasks"]["001"]["provider"], "agy")
        self.assertEqual(
            receipt["tasks"]["001"]["model"], "gemini-3.6-flash-high"
        )

    def test_explicit_qwen_writer_remains_selectable(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")

        result = self.run_controller("--provider", "qwen")

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["tasks"]["001"]["provider"], "qwen")
        self.assertEqual(receipt["tasks"]["001"]["model"], "qwen3.8-max-preview")

    def test_outcome_manifest_written_on_accept(self) -> None:
        self.write_run(provider_slots=2)
        self.write_task("001")
        self.write_task("002")
        self.write_task("003", ["001"])
        artifact_dir = self.run_dir / "artifacts" / "001"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "owns-check.json").write_text(
            json.dumps(
                {
                    "changed_files": ["src/a.py", "tests/test_a.py"],
                    "violations": [],
                    "never_touch_hits": [],
                    "status": "passed",
                }
            ),
            encoding="utf-8",
        )
        report_body = b"STATUS: complete\n"
        (artifact_dir / "report.md").write_bytes(report_body)
        report_sha = hashlib.sha256(report_body).hexdigest()

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        for task_id in ("001", "002", "003"):
            outcome_path = self.run_dir / "artifacts" / task_id / "outcome.json"
            self.assertTrue(outcome_path.is_file(), f"missing outcome for {task_id}")
            outcome = json.loads(outcome_path.read_text())
            self.assertEqual(outcome["schema_version"], 1)
            self.assertEqual(outcome["task_id"], task_id)
            self.assertEqual(outcome["stage"], "accepted")
            self.assertEqual(outcome["exit_status"], "completed")
            self.assertIsNone(outcome["failure_class"])
            self.assertEqual(outcome["attempts"], 1)
            self.assertEqual(outcome["run_dir"], str(self.run_dir))
        first = json.loads(
            (self.run_dir / "artifacts" / "001" / "outcome.json").read_text()
        )
        self.assertEqual(first["files_changed"], ["src/a.py", "tests/test_a.py"])
        self.assertEqual(first["owns_paths_violations"], [])
        self.assertEqual(first["report_sha256"], report_sha)
        self.assertEqual(
            first["report_path"], str(self.run_dir / "artifacts" / "001" / "report.md")
        )
        second = json.loads(
            (self.run_dir / "artifacts" / "002" / "outcome.json").read_text()
        )
        self.assertEqual(second["files_changed"], [])
        self.assertIsNone(second["report_sha256"])

    def test_outcome_manifest_records_crashed_failure(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "fail_always": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1, result.stderr)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["tasks"]["001"]["stage"], "blocked")
        outcome_path = self.run_dir / "artifacts" / "001" / "outcome.json"
        self.assertTrue(outcome_path.is_file())
        outcome = json.loads(outcome_path.read_text())
        self.assertEqual(outcome["stage"], "blocked")
        self.assertEqual(outcome["exit_status"], "crashed")
        self.assertEqual(outcome["failure_class"], "failed")
        self.assertEqual(outcome["attempts"], 2)
        self.assertEqual(outcome["files_changed"], [])

    def test_large_verification_result_does_not_block_acceptance(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps(
                {
                    "finish_after": {"001": 1},
                    "verify_output_bytes": 2_000_000,
                }
            ),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "accepted")

    def test_pre_dispatch_validation_fails_before_provider_start(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        env = self.env()
        env["FAKE_VALIDATE_FAIL"] = "1"

        result = subprocess.run(
            [
                str(CONTROLLER),
                "run",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("run-validate failed", result.stderr)
        self.assertFalse(self.fake_log.exists())
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")

    def test_retryable_provider_failure_is_retried_once_then_accepted(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "fail_first": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.actions()
        self.assertEqual(
            [action for action in actions if action["action"] == "retry"],
            [{"action": "retry", "task_id": "001"}],
        )
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["tasks"]["001"]["retries"], 1)
        self.assertEqual(receipt["tasks"]["001"]["stage"], "accepted")

    def test_transient_retry_wait_is_persisted_without_blocking_sleep(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "fail_first": ["001"]}),
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [
                str(CONTROLLER),
                "run",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
                "--poll-interval",
                "0.01",
                "--retry-backoff",
                "30",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 5
        task_state = None
        while time.monotonic() < deadline:
            if (self.run_dir / "controller.json").is_file():
                receipt = json.loads((self.run_dir / "controller.json").read_text())
                task_state = receipt["tasks"]["001"]
                if task_state["stage"] == "retry_wait":
                    break
            time.sleep(0.02)
        self.assertIsNotNone(task_state)
        self.assertEqual(task_state["stage"], "retry_wait")
        self.assertIsInstance(task_state["retry_not_before"], str)
        self.assertEqual(
            [action["action"] for action in self.actions()],
            ["start"],
        )
        process.terminate()
        process.communicate(timeout=3)

    def test_due_retry_waits_for_provider_capacity(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.write_task("002")
        self.fake_plan.write_text(
            json.dumps(
                {
                    "finish_after": {"001": 1, "002": 30},
                    "fail_first": ["001"],
                    "record_retry_peers": True,
                }
            ),
            encoding="utf-8",
        )

        result = self.run_controller("--retry-backoff", "0.05")

        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.actions()
        retry = next(
            item
            for item in actions
            if item["action"] == "retry" and item["task_id"] == "001"
        )
        self.assertEqual(retry["other_running"], [])

    def test_stalled_provider_is_cancelled_before_retry(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "stall_first": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [action["action"] for action in self.actions()],
            ["start", "cancel", "retry", "owns", "verify", "accept"],
        )

    def test_cancelled_provider_is_retried_once(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "cancel_first": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [action["action"] for action in self.actions()],
            ["start", "retry", "owns", "verify", "accept"],
        )

    def test_provider_state_loss_blocks_instead_of_spinning(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"lose_state_after_start": ["001"]}), encoding="utf-8"
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "blocked")
        self.assertEqual(receipt["tasks"]["001"]["stage"], "blocked")
        self.assertIn("not_started", receipt["last_event"]["detail"])

    def test_verification_failure_retries_once_before_accept(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps(
                {"finish_after": {"001": 1}, "verify_fail_first": ["001"]}
            ),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.actions()
        self.assertEqual(
            [action["action"] for action in actions],
            ["start", "owns", "verify", "retry", "owns", "verify", "accept"],
        )
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["tasks"]["001"]["retries"], 1)
        self.assertEqual(receipt["stage"], "accepted")

    def test_second_verification_failure_blocks_without_accept(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps(
                {"finish_after": {"001": 1}, "verify_fail_always": ["001"]}
            ),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            [action["action"] for action in self.actions()],
            ["start", "owns", "verify", "retry", "owns", "verify"],
        )
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "blocked")
        self.assertEqual(receipt["tasks"]["001"]["retries"], 1)

    def test_second_retryable_failure_blocks_run_and_returns_nonzero(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "fail_always": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        actions = self.actions()
        self.assertEqual(
            [action for action in actions if action["action"] == "retry"],
            [{"action": "retry", "task_id": "001"}],
        )
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "blocked")
        self.assertEqual(receipt["tasks"]["001"]["stage"], "blocked")
        self.assertEqual(receipt["next_action"], "operator_intervention")

    def test_second_eligible_grok_failure_falls_back_to_codex_sol_high(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps(
                {
                    "finish_after": {"001": 1},
                    "fail_always": ["001"],
                    "eligible_failure": ["001"],
                }
            ),
            encoding="utf-8",
        )

        result = self.run_controller("--retry-backoff", "0")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [action["action"] for action in self.actions()],
            ["start", "retry", "fallback", "owns", "verify", "accept"],
        )
        fallback = self.actions()[2]
        self.assertEqual(fallback["provider"], "codex")
        self.assertEqual(fallback["model"], "gpt-5.6-sol")
        self.assertEqual(fallback["reasoning_effort"], "high")
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        task = receipt["tasks"]["001"]
        self.assertEqual(task["retries"], 1)
        self.assertEqual(task["fallbacks"], 1)
        self.assertEqual(task["provider"], "codex")
        self.assertEqual(task["model"], "gpt-5.6-sol")
        self.assertEqual(task["stage"], "accepted")

    def test_duplicate_controller_lock_fails_fast(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 100000}}), encoding="utf-8"
        )
        command = [
            str(CONTROLLER),
            "run",
            "--run-dir",
            str(self.run_dir),
            "--lane-ctl",
            str(self.fake_lane_ctl),
            "--check-owns-paths",
            str(self.fake_owns),
            "--run-validate",
            str(self.fake_run_validate),
            "--poll-interval",
            "0.01",
        ]
        first = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
        )
        self.addCleanup(lambda: first.poll() is None and first.kill())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            receipt_path = self.run_dir / "controller.json"
            if receipt_path.is_file() and json.loads(receipt_path.read_text())["counts"].get("running") == 1:
                break
            time.sleep(0.02)
        else:
            self.fail("first controller did not acquire the run")

        second = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
            timeout=3,
        )

        self.assertEqual(second.returncode, 1)
        self.assertIn("already active", second.stderr)
        self.assertIsNone(first.poll())
        first.terminate()
        first.communicate(timeout=3)

    def test_accepted_receipt_resumes_idempotently_and_status_is_read_only(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        first = self.run_controller()
        self.assertEqual(first.returncode, 0, first.stderr)
        action_lines = self.fake_log.read_text(encoding="utf-8")

        resumed = self.run_controller()

        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(resumed.stdout, "")
        self.assertEqual(self.fake_log.read_text(encoding="utf-8"), action_lines)
        receipt_path = self.run_dir / "controller.json"
        before = receipt_path.read_bytes()
        status = subprocess.run(
            [str(CONTROLLER), "status", "--run-dir", str(self.run_dir), "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["stage"], "accepted")
        self.assertEqual(receipt_path.read_bytes(), before)

    def test_inconsistent_accepted_receipt_fails_closed_without_mutation(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        first = self.run_controller()
        self.assertEqual(first.returncode, 0, first.stderr)
        receipt_path = self.run_dir / "controller.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["tasks"]["001"]["stage"] = "running"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        before = receipt_path.read_bytes()

        watched = subprocess.run(
            [
                str(CONTROLLER),
                "watch",
                "--run-dir",
                str(self.run_dir),
                "--timeout",
                "0",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        resumed = self.run_controller()

        self.assertEqual(watched.returncode, 1, watched.stderr)
        self.assertEqual(json.loads(watched.stdout)["stage"], "failed")
        self.assertIn("inconsistent", json.loads(watched.stdout)["last_event"]["detail"])
        self.assertEqual(resumed.returncode, 1)
        self.assertIn("inconsistent", resumed.stderr)
        self.assertEqual(receipt_path.read_bytes(), before)

    def test_malformed_running_receipt_is_replaced_by_terminal_failure(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        receipt_path = self.run_dir / "controller.json"
        receipt_path.write_text(
            json.dumps({"schema_version": 1, "stage": "running", "tasks": {"001": {}}}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["tasks"]["001"]["stage"], "pending")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertIn("receipt", receipt["last_event"]["detail"])

    def test_running_receipt_resumes_without_duplicate_start(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 100000}}), encoding="utf-8"
        )
        command = [
            str(CONTROLLER),
            "run",
            "--run-dir",
            str(self.run_dir),
            "--lane-ctl",
            str(self.fake_lane_ctl),
            "--check-owns-paths",
            str(self.fake_owns),
            "--run-validate",
            str(self.fake_run_validate),
            "--poll-interval",
            "0.01",
        ]
        interrupted = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.fake_log.is_file() and {"action": "start", "task_id": "001"} in self.actions():
                break
            time.sleep(0.02)
        else:
            interrupted.kill()
            interrupted.communicate()
            self.fail("controller did not start the lane")
        interrupted.terminate()
        interrupted.communicate(timeout=3)
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}}), encoding="utf-8"
        )

        resumed = self.run_controller()

        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(
            [action for action in self.actions() if action["action"] == "start"],
            [{"action": "start", "task_id": "001"}],
        )
        self.assertEqual(
            json.loads((self.run_dir / "controller.json").read_text())["stage"],
            "accepted",
        )

    def test_durable_start_is_idempotent_and_watch_reaches_terminal(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 20}}), encoding="utf-8"
        )
        command = [
            str(CONTROLLER),
            "start",
            "--run-dir",
            str(self.run_dir),
            "--lane-ctl",
            str(self.fake_lane_ctl),
            "--check-owns-paths",
            str(self.fake_owns),
            "--run-validate",
            str(self.fake_run_validate),
            "--poll-interval",
            "0.02",
            "--lane-bg",
            str(ROOT / "bin" / "lane-bg"),
        ]

        first = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
            timeout=3,
        )
        second = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
            timeout=3,
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_payload = json.loads(first.stdout)
        second_payload = json.loads(second.stdout)
        self.assertEqual(first_payload["status"], "started")
        self.assertEqual(second_payload["status"], "already_running")
        self.assertEqual(second_payload["pid"], first_payload["pid"])
        self.assertTrue(Path(first_payload["log"]).is_file())
        watch = None
        for _ in range(40):
            watch = subprocess.run(
                [
                    str(CONTROLLER),
                    "watch",
                    "--run-dir",
                    str(self.run_dir),
                    "--timeout",
                    "5",
                    "--poll-interval",
                    "0.02",
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=6,
            )
            if watch.returncode != 2:
                break
        assert watch is not None
        self.assertEqual(watch.returncode, 0, watch.stderr)
        self.assertEqual(json.loads(watch.stdout)["stage"], "accepted")

    def test_watch_exit_codes_are_read_only_and_timeout_is_bounded(self) -> None:
        receipt_path = self.run_dir / "controller.json"
        receipt_path.write_text(
            json.dumps({"schema_version": 1, "stage": "running"}), encoding="utf-8"
        )
        before = receipt_path.read_bytes()
        running = subprocess.run(
            [
                str(CONTROLLER),
                "watch",
                "--run-dir",
                str(self.run_dir),
                "--timeout",
                "0.05",
                "--poll-interval",
                "0.01",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2,
        )
        self.assertEqual(running.returncode, 2, running.stderr)
        self.assertEqual(receipt_path.read_bytes(), before)

        receipt_path.write_text(
            json.dumps({"schema_version": 1, "stage": "blocked"}), encoding="utf-8"
        )
        blocked = subprocess.run(
            [str(CONTROLLER), "watch", "--run-dir", str(self.run_dir), "--timeout", "1", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(blocked.returncode, 1, blocked.stderr)

        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "stage": "accepted",
                    "next_action": "complete",
                    "counts": {"total": 1, "accepted": 1},
                    "tasks": {"001": {"stage": "accepted"}},
                }
            ),
            encoding="utf-8",
        )
        accepted = subprocess.run(
            [str(CONTROLLER), "watch", "--run-dir", str(self.run_dir), "--timeout", "1", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        invalid = subprocess.run(
            [str(CONTROLLER), "watch", "--run-dir", str(self.run_dir), "--timeout", "301", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("between 0 and 300", invalid.stderr)

    def test_watch_ignores_nonterminal_transitions_until_terminal(self) -> None:
        receipt_path = self.run_dir / "controller.json"
        receipt_path.write_text(
            json.dumps({"schema_version": 1, "stage": "running", "last_event": None}),
            encoding="utf-8",
        )
        writer = subprocess.Popen(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """\
                    import json
                    import os
                    import sys
                    import time
                    from pathlib import Path

                    path = Path(sys.argv[1])
                    def replace(value):
                        temporary = path.with_suffix(".next")
                        temporary.write_text(json.dumps(value), encoding="utf-8")
                        os.replace(temporary, path)

                    time.sleep(0.05)
                    replace({"schema_version": 1, "stage": "running", "last_event": {"event": "task_started"}})
                    time.sleep(0.15)
                    replace({
                        "schema_version": 1,
                        "stage": "accepted",
                        "next_action": "complete",
                        "counts": {"total": 1, "accepted": 1},
                        "tasks": {"001": {"stage": "accepted"}},
                        "last_event": {"event": "run_accepted"},
                    })
                    """
                ),
                str(receipt_path),
            ]
        )
        self.addCleanup(lambda: writer.poll() is None and writer.kill())
        started_at = time.monotonic()

        watched = subprocess.run(
            [
                str(CONTROLLER),
                "watch",
                "--run-dir",
                str(self.run_dir),
                "--timeout",
                "1",
                "--poll-interval",
                "0.01",
                "--json",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=2,
        )
        writer.wait(timeout=2)

        self.assertEqual(watched.returncode, 0, watched.stderr)
        self.assertEqual(json.loads(watched.stdout)["stage"], "accepted")
        self.assertGreaterEqual(time.monotonic() - started_at, 0.15)

    def test_human_watch_streams_observed_progress_before_terminal(self) -> None:
        receipt_path = self.run_dir / "controller.json"
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "stage": "running",
                    "counts": {"total": 1, "accepted": 0},
                    "last_event": {"event": "task_started", "task_id": "001"},
                }
            ),
            encoding="utf-8",
        )
        watched = subprocess.Popen(
            [
                str(CONTROLLER),
                "watch",
                "--run-dir",
                str(self.run_dir),
                "--timeout",
                "1",
                "--poll-interval",
                "0.01",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(lambda: watched.poll() is None and watched.kill())
        assert watched.stdout is not None
        first = json.loads(watched.stdout.readline())

        self.assertIsNone(watched.poll())
        self.assertEqual(first["type"], "watch")
        self.assertEqual(first["last_event"]["event"], "task_started")

        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "stage": "accepted",
                    "next_action": "complete",
                    "counts": {"total": 1, "accepted": 1},
                    "tasks": {"001": {"stage": "accepted"}},
                    "last_event": {"event": "run_accepted"},
                }
            ),
            encoding="utf-8",
        )
        stdout, stderr = watched.communicate(timeout=2)

        self.assertEqual(watched.returncode, 0, stderr)
        self.assertIn('"event": "run_accepted"', stdout)

    def test_start_persists_failed_receipt_for_stale_exit_and_requires_reset(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 100000}}), encoding="utf-8"
        )
        interrupted = subprocess.Popen(
            [
                str(CONTROLLER),
                "run",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
                "--poll-interval",
                "0.01",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.fake_log.is_file() and {"action": "start", "task_id": "001"} in self.actions():
                break
            time.sleep(0.02)
        else:
            interrupted.kill()
            interrupted.communicate()
            self.fail("controller did not start the lane")
        interrupted.terminate()
        interrupted.communicate(timeout=3)
        controller_dir = self.run_dir / "controller"
        (controller_dir / "lane-bg.pid").write_text("99999999\n", encoding="utf-8")
        (controller_dir / "lane-bg.exit").write_text("143\n", encoding="utf-8")

        resumed = subprocess.run(
            [
                str(CONTROLLER),
                "start",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
                "--lane-bg",
                str(ROOT / "bin" / "lane-bg"),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
            timeout=3,
        )

        self.assertEqual(resumed.returncode, 1, resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)["stage"], "failed")
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertIn("exited 143", receipt["last_event"]["detail"])
        self.assertEqual(receipt["next_action"], "operator_intervention")
        self.assertEqual(
            [event for event in self.actions() if event["action"] == "start"],
            [{"action": "start", "task_id": "001"}],
        )

    def test_durable_status_error_writes_failed_receipt_and_watch_returns_one(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"status_error": ["001"]}), encoding="utf-8"
        )
        started = subprocess.run(
            [
                str(CONTROLLER),
                "start",
                "--run-dir",
                str(self.run_dir),
                "--lane-ctl",
                str(self.fake_lane_ctl),
                "--check-owns-paths",
                str(self.fake_owns),
                "--run-validate",
                str(self.fake_run_validate),
                "--poll-interval",
                "0.01",
                "--lane-bg",
                str(ROOT / "bin" / "lane-bg"),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env(),
            check=False,
            timeout=3,
        )
        self.assertEqual(started.returncode, 0, started.stderr)

        watch = None
        for _ in range(20):
            watch = subprocess.run(
                [
                    str(CONTROLLER),
                    "watch",
                    "--run-dir",
                    str(self.run_dir),
                    "--timeout",
                    "1",
                    "--poll-interval",
                    "0.02",
                    "--json",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=2,
            )
            if watch.returncode != 2:
                break
        assert watch is not None
        self.assertEqual(watch.returncode, 1, watch.stderr)
        self.assertEqual(json.loads(watch.stdout)["stage"], "failed")
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertEqual(receipt["next_action"], "operator_intervention")

    def test_start_action_error_fails_closed(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(json.dumps({"start_error": ["001"]}), encoding="utf-8")

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertIn("start 001 failed", receipt["last_event"]["detail"])

    def test_invalid_verify_result_fails_closed(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps(
                {"finish_after": {"001": 1}, "verify_invalid_json": ["001"]}
            ),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertIn("invalid JSON", receipt["last_event"]["detail"])

    def test_accept_action_error_fails_closed(self) -> None:
        self.write_run(provider_slots=1)
        self.write_task("001")
        self.fake_plan.write_text(
            json.dumps({"finish_after": {"001": 1}, "accept_error": ["001"]}),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(receipt["last_event"]["event"], "controller_failed")
        self.assertIn("accept 001 failed", receipt["last_event"]["detail"])

    def test_pre_merge_review_gate_fails_before_provider_dispatch(self) -> None:
        self.write_run(provider_slots=1, gate="pre-merge")
        self.write_task("001")

        result = self.run_controller()

        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.fake_log.exists())
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "failed")
        self.assertEqual(
            receipt["last_event"]["detail"],
            "explicit_review_gate_requires_operator",
        )
        self.assertEqual(receipt["counts"]["pending"], 1)

    def test_provider_refills_while_slow_verification_uses_separate_bounded_pool(self) -> None:
        self.write_run(provider_slots=1, verification_slots=1)
        self.write_task("001")
        self.write_task("002")
        self.fake_plan.write_text(
            json.dumps(
                {
                    "finish_after": {"001": 1, "002": 1},
                    "verify_delay": {"001": 0.25, "002": 0.25},
                }
            ),
            encoding="utf-8",
        )

        result = self.run_controller()

        self.assertEqual(result.returncode, 0, result.stderr)
        actions = self.actions()
        self.assertLess(
            actions.index({"action": "start", "task_id": "002"}),
            actions.index({"action": "verify_end", "task_id": "001"}),
        )
        verifying: set[str] = set()
        maximum = 0
        for event in actions:
            if event["action"] == "verify_begin":
                verifying.add(event["task_id"])
                maximum = max(maximum, len(verifying))
            elif event["action"] == "verify_end":
                verifying.discard(event["task_id"])
        self.assertEqual(maximum, 1)
        receipt = json.loads((self.run_dir / "controller.json").read_text())
        self.assertEqual(receipt["stage"], "accepted")


if __name__ == "__main__":
    unittest.main()
