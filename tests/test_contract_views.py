from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


class ContractViewTests(unittest.TestCase):
    def test_heartbeat_does_not_append_to_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            run_dir = repo / ".agents" / "runs" / "demo"
            run_dir.mkdir(parents=True)
            status = run_dir / "STATUS.md"
            status.write_text("generated sentinel\n", encoding="utf-8")

            result = run(
                str(ROOT / "bin" / "lane-heartbeat"),
                "--repo", str(repo), "--run", "demo", "--task", "001",
                "--status", "running", "--note", "active",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(status.read_text(encoding="utf-8"), "generated sentinel\n")
            heartbeat = json.loads((run_dir / "artifacts" / "001" / "heartbeat.json").read_text())
            self.assertEqual(heartbeat["note"], "active")

    def test_heartbeat_rejects_path_segments(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            (repo / ".agents" / "runs").mkdir(parents=True)

            result = run(
                str(ROOT / "bin" / "lane-heartbeat"),
                "--repo",
                str(repo),
                "--run",
                "../escape",
                "--task",
                "001",
            )

            self.assertEqual(result.returncode, 2)
            self.assertFalse((repo / ".agents" / "escape").exists())

    def test_run_board_uses_v2_state_and_acceptance_and_rebuilds_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            run_dir = repo / ".agents" / "runs" / "demo"
            task_dir = run_dir / "tasks"
            artifact = run_dir / "artifacts" / "001"
            task_dir.mkdir(parents=True)
            artifact.mkdir(parents=True)
            (run_dir / "run.yaml").write_text("schema_version: 2\nslug: demo\n", encoding="utf-8")
            task_path = task_dir / "001.yaml"
            task_path.write_text(
                "schema_version: 2\nid: '001'\ntitle: Demo task\nstatus: done\nlane: grok\n",
                encoding="utf-8",
            )
            (artifact / "state.json").write_text(
                json.dumps({"schema_version": 2, "task_id": "001", "status": "awaiting_verification", "attempt": 1}),
                encoding="utf-8",
            )

            result = run(str(ROOT / "bin" / "run-board"), str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            board = (repo / ".agents" / "runs" / "BOARD.md").read_text(encoding="utf-8")
            self.assertIn("**running**", board)
            status = (run_dir / "STATUS.md").read_text(encoding="utf-8")
            self.assertIn("state.json and acceptance.json", status)
            self.assertNotIn("Heartbeats", status)

            (artifact / "acceptance.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "task_id": "001",
                    "task_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
                    "attempt": 1,
                    "provider_exit": 0,
                    "report": "complete",
                    "owns_check": "passed",
                    "verification": "passed",
                    "review": "not_required",
                    "accepted": True,
                    "accepted_at": "2026-07-18T00:00:00Z",
                }),
                encoding="utf-8",
            )
            run(str(ROOT / "bin" / "run-board"), str(repo))
            board = (repo / ".agents" / "runs" / "BOARD.md").read_text(encoding="utf-8")
            self.assertIn("**done**", board)

            (artifact / "state.json").write_text(
                json.dumps({"schema_version": 2, "task_id": "001", "status": "running", "attempt": 2}),
                encoding="utf-8",
            )
            run(str(ROOT / "bin" / "run-board"), str(repo))
            board = (repo / ".agents" / "runs" / "BOARD.md").read_text(encoding="utf-8")
            self.assertNotIn("**done**", board)

            (artifact / "acceptance.json").unlink()
            run(str(ROOT / "bin" / "run-board"), str(repo))
            board = (repo / ".agents" / "runs" / "BOARD.md").read_text(encoding="utf-8")
            self.assertNotIn("**done**", board)

    def test_stall_mark_updates_state_without_mutating_v2_task(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            run_dir = repo / ".agents" / "runs" / "demo"
            task_dir = run_dir / "tasks"
            artifact = run_dir / "artifacts" / "001"
            task_dir.mkdir(parents=True)
            artifact.mkdir(parents=True)
            task_text = "schema_version: 2\nid: '001'\ntitle: Demo\n"
            task_path = task_dir / "001.yaml"
            task_path.write_text(task_text, encoding="utf-8")
            (artifact / "state.json").write_text(
                json.dumps({"schema_version": 2, "task_id": "001", "status": "running", "attempt": 1}),
                encoding="utf-8",
            )

            result = run(str(ROOT / "bin" / "lane-stall-check"), str(repo), "--minutes", "0", "--mark")

            self.assertEqual(result.returncode, 2)
            self.assertEqual(task_path.read_text(encoding="utf-8"), task_text)
            state = json.loads((artifact / "state.json").read_text())
            self.assertEqual(state["status"], "stalled")

    def test_owns_check_writes_machine_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.email", "test@example.com", cwd=repo)
            run("git", "config", "user.name", "Test", cwd=repo)
            owned = repo / "src" / "owned.txt"
            owned.parent.mkdir(parents=True)
            owned.write_text("base\n", encoding="utf-8")
            run("git", "add", "src/owned.txt", cwd=repo)
            run("git", "commit", "-m", "base", cwd=repo)
            owned.write_text("changed\n", encoding="utf-8")
            task_dir = repo / ".agents" / "runs" / "demo" / "tasks"
            task_dir.mkdir(parents=True)
            task = task_dir / "001.yaml"
            task.write_text(
                f"schema_version: 2\nid: '001'\nproject_cwd: '{repo}'\nowns_paths:\n  - src/owned.txt\nnever_touch: []\n",
                encoding="utf-8",
            )

            result = run(str(ROOT / "bin" / "check-owns-paths"), str(task), "--cwd", str(repo))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((repo / ".agents" / "runs" / "demo" / "artifacts" / "001" / "owns-check.json").read_text())
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["changed_files"], ["src/owned.txt"])
            self.assertEqual(len(receipt["task_sha256"]), 64)

    def test_owns_check_fails_closed_when_git_inspection_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            task_dir = repo / ".agents" / "runs" / "demo" / "tasks"
            task_dir.mkdir(parents=True)
            task = task_dir / "001.yaml"
            task.write_text(
                f"schema_version: 2\nid: '001'\nproject_cwd: '{repo}'\nowns_paths:\n  - src/**\nnever_touch: []\n",
                encoding="utf-8",
            )

            result = run(str(ROOT / "bin" / "check-owns-paths"), str(task), "--cwd", str(repo))

            self.assertEqual(result.returncode, 2)
            self.assertIn("git", result.stderr.lower())
            receipt = json.loads(
                (repo / ".agents" / "runs" / "demo" / "artifacts" / "001" / "owns-check.json").read_text()
            )
            self.assertEqual(receipt["status"], "failed")
            self.assertIn("error", receipt)


if __name__ == "__main__":
    unittest.main()
