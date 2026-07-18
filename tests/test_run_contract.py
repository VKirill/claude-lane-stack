from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RUN_INIT = ROOT / "bin" / "run-init"
RUN_VALIDATE = ROOT / "bin" / "run-validate"


class RunContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=self.repo,
            check=True,
        )
        self.run_dir = self.repo / ".agents" / "runs" / "contract-test"

    def run_init(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RUN_INIT),
                str(self.repo),
                "contract-test",
                *extra,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def initialize(self) -> None:
        result = self.run_init("--gate", "pre-merge")
        self.assertEqual(result.returncode, 0, result.stderr)

    def write_task(
        self,
        task_id: str,
        *,
        owns_paths: list[str] | None = None,
        never_touch: list[str] | None = None,
        depends_on: list[str] | None = None,
        project_cwd: str | None = None,
        risk: str = "medium",
        verify: str = "tests",
        verification: list[dict[str, object]] | None = None,
    ) -> Path:
        if verification is None:
            verification = [
                {
                    "command": "true",
                    "cwd": str(self.repo.resolve()),
                    "timeout_sec": 30,
                }
            ]
        task = {
            "schema_version": 2,
            "id": task_id,
            "title": f"Task {task_id}",
            "risk": risk,
            "lane": "grok",
            "project_cwd": project_cwd or str(self.repo.resolve()),
            "read_first": ["AGENTS.md"],
            "interfaces": [],
            "invariants": ["Preserve unrelated work"],
            "out_of_scope": [],
            "expected_outputs": [f"Product output for task {task_id}"],
            "owns_paths": owns_paths or [f"src/{task_id}/**"],
            "never_touch": never_touch or [".env*"],
            "depends_on": depends_on or [],
            "objective": f"Implement task {task_id}",
            "acceptance": ["Focused verification passes"],
            "verify": verify,
            "verification": verification,
        }
        path = self.run_dir / "tasks" / f"{task_id}.yaml"
        path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        return path

    def run_validate(self, phase: str = "pre-dispatch") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RUN_VALIDATE),
                "--run-dir",
                str(self.run_dir),
                "--phase",
                phase,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def accept_task(self, task_path: Path) -> None:
        task_id = yaml.safe_load(task_path.read_text())["id"]
        artifact = self.run_dir / "artifacts" / task_id
        artifact.mkdir(parents=True, exist_ok=True)
        acceptance = {
            "schema_version": 2,
            "task_id": task_id,
            "task_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
            "attempt": 1,
            "provider_exit": 0,
            "report": "complete",
            "report_sha256": "a" * 64,
            "owns_check": "passed",
            "verification": "passed",
            "review": "not_required",
            "accepted": True,
            "accepted_at": "2026-07-18T00:00:00Z",
        }
        (artifact / "acceptance.json").write_text(
            json.dumps(acceptance) + "\n", encoding="utf-8"
        )
        (artifact / "state.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "task_id": task_id,
                    "task_sha256": acceptance["task_sha256"],
                    "status": "accepted",
                    "accepted": True,
                    "current_attempt": 1,
                    "attempt": 1,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_run_init_creates_v2_contract_and_refuses_existing(self) -> None:
        result = self.run_init(
            "--score",
            "8",
            "--provider-pool",
            "5",
            "--verification-pool",
            "2",
            "--gate",
            "pre-merge",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.run_dir)
        self.assertTrue((self.run_dir / "tasks").is_dir())
        self.assertTrue((self.run_dir / "artifacts").is_dir())
        for name in ("PLAN.md", "SPEC.md", "STATUS.md"):
            self.assertTrue((self.run_dir / name).is_file(), name)

        run = yaml.safe_load((self.run_dir / "run.yaml").read_text())
        self.assertEqual(run["schema_version"], 2)
        self.assertEqual(run["slug"], "contract-test")
        self.assertEqual(run["repo"], str(self.repo.resolve()))
        self.assertEqual(run["project_cwd"], str(self.repo.resolve()))
        self.assertTrue(Path(run["project_cwd"]).is_absolute())
        self.assertEqual(run["score"], 8)
        self.assertEqual(run["pools"], {"provider": 5, "verification": 2})
        self.assertEqual(run["gate"], "pre-merge")
        self.assertEqual(
            run["finalize"],
            {
                "progress_now": None,
                "close_next": [],
                "close_open": [],
            },
        )
        expected_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        self.assertEqual(run["base_sha"], expected_sha)

        generated_task_path = self.run_dir / "tasks" / "001.yaml"
        generated_task = yaml.safe_load(generated_task_path.read_text())
        self.assertEqual(generated_task["schema_version"], 2)
        self.assertEqual(generated_task["project_cwd"], str(self.repo.resolve()))
        self.assertIn("REPLACE_ME", generated_task["owns_paths"][0])
        placeholder = self.run_validate()
        self.assertEqual(placeholder.returncode, 2)
        for field in ("title", "expected_outputs[0]", "owns_paths[0]", "objective", "acceptance[0]", "verification[0].command"):
            self.assertIn(f"unresolved placeholder at {field}", placeholder.stderr)

        sentinel = self.run_dir / "sentinel"
        sentinel.write_text("preserve", encoding="utf-8")
        repeated = self.run_init()
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already exists", repeated.stderr)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_run_init_rejects_out_of_range_pool_without_creating_run(self) -> None:
        result = self.run_init("--provider-pool", "11")

        self.assertEqual(result.returncode, 2)
        self.assertIn("1 to 10", result.stderr)
        self.assertFalse(self.run_dir.exists())

    def test_run_init_quotes_custom_project_cwd_in_generated_task(self) -> None:
        project_cwd = self.root / 'work " tree'
        project_cwd.mkdir()

        result = self.run_init("--project-cwd", str(project_cwd))

        self.assertEqual(result.returncode, 0, result.stderr)
        task = yaml.safe_load((self.run_dir / "tasks" / "001.yaml").read_text())
        self.assertEqual(task["project_cwd"], str(project_cwd.resolve()))
        self.assertEqual(task["verification"][0]["cwd"], str(project_cwd.resolve()))

    def test_run_init_adopts_only_a_pristine_worktree_run_directory(self) -> None:
        worktree = self.repo / ".worktrees" / "contract-test"
        worktree.mkdir(parents=True)
        self.run_dir.mkdir(parents=True)
        metadata = {
            "slug": "contract-test",
            "branch": "agent/contract-test",
            "path": str(worktree.resolve()),
            "base": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip(),
            "repo": str(self.repo.resolve()),
        }
        (self.run_dir / "worktree.json").write_text(
            json.dumps(metadata) + "\n", encoding="utf-8"
        )

        result = self.run_init("--adopt-worktree")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads((self.run_dir / "worktree.json").read_text()), metadata
        )
        run = yaml.safe_load((self.run_dir / "run.yaml").read_text())
        task = yaml.safe_load((self.run_dir / "tasks" / "001.yaml").read_text())
        self.assertEqual(run["project_cwd"], str(worktree.resolve()))
        self.assertEqual(task["project_cwd"], str(worktree.resolve()))
        self.assertEqual(task["verification"][0]["cwd"], str(worktree.resolve()))

        repeated = self.run_init("--adopt-worktree")
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("already initialized", repeated.stderr)

    def test_run_init_refuses_to_adopt_unknown_existing_files(self) -> None:
        worktree = self.repo / ".worktrees" / "contract-test"
        worktree.mkdir(parents=True)
        self.run_dir.mkdir(parents=True)
        (self.run_dir / "worktree.json").write_text(
            json.dumps(
                {
                    "slug": "contract-test",
                    "branch": "agent/contract-test",
                    "path": str(worktree.resolve()),
                    "base": "deadbeef",
                    "repo": str(self.repo.resolve()),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.run_dir / "unexpected.txt").write_text("preserve\n", encoding="utf-8")

        result = self.run_init("--adopt-worktree")

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot adopt non-pristine run directory", result.stderr)
        self.assertEqual((self.run_dir / "unexpected.txt").read_text(), "preserve\n")
        self.assertFalse((self.run_dir / "run.yaml").exists())

    def test_valid_run_passes_pre_dispatch(self) -> None:
        self.initialize()
        self.write_task("001")
        self.write_task("002", depends_on=["001"])

        result = self.run_validate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid pre-dispatch", result.stdout)

    def test_rejects_overlapping_owns_paths(self) -> None:
        self.initialize()
        self.write_task("001", owns_paths=["src/api/**"])
        self.write_task("002", owns_paths=["src/api/client.py"])

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("owns_paths overlap", result.stderr)

    def test_rejects_dependency_cycle(self) -> None:
        self.initialize()
        self.write_task("001", depends_on=["002"])
        self.write_task("002", depends_on=["001"])

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("dependency cycle", result.stderr)

    def test_rejects_unknown_dependency(self) -> None:
        self.initialize()
        self.write_task("001", depends_on=["missing-task"])

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown dependency", result.stderr)

    def test_rejects_never_touch_conflict(self) -> None:
        self.initialize()
        self.write_task("001", owns_paths=["config/**"])
        self.write_task("002", never_touch=["config/secrets/**"])

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("never_touch conflict", result.stderr)

    def test_rejects_relative_verification_cwd(self) -> None:
        self.initialize()
        self.write_task(
            "001",
            verification=[
                {"command": "true", "cwd": "relative/path", "timeout_sec": 30}
            ],
        )

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("verification", result.stderr)
        self.assertIn("cwd", result.stderr)

    def test_rejects_relative_project_cwd(self) -> None:
        self.initialize()
        self.write_task("001", project_cwd="relative/project")

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("project_cwd", result.stderr)

    def test_rejects_verification_cwd_outside_project(self) -> None:
        self.initialize()
        outside = self.root / "outside"
        outside.mkdir()
        self.write_task(
            "001",
            verification=[
                {"command": "true", "cwd": str(outside), "timeout_sec": 30}
            ],
        )

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("escapes project_cwd", result.stderr)

    def test_rejects_empty_verification_for_tests(self) -> None:
        self.initialize()
        self.write_task("001", verify="tests", verification=[])

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("verification", result.stderr)

    def test_pre_merge_requires_acceptance(self) -> None:
        self.initialize()
        self.write_task("001")

        result = self.run_validate("pre-merge")

        self.assertEqual(result.returncode, 2)
        self.assertIn("acceptance.json", result.stderr)

    def test_accepted_pre_merge_requires_current_task_hash(self) -> None:
        self.initialize()
        task = self.write_task("001")
        self.accept_task(task)

        accepted = self.run_validate("pre-merge")

        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn("valid pre-merge", accepted.stdout)

        task.write_text(task.read_text() + "\n", encoding="utf-8")
        stale = self.run_validate("pre-merge")
        self.assertEqual(stale.returncode, 2)
        self.assertIn("task_sha256 is stale", stale.stderr)

    def test_pre_merge_rejects_acceptance_from_a_previous_attempt(self) -> None:
        self.initialize()
        task = self.write_task("001")
        self.accept_task(task)
        state_path = self.run_dir / "artifacts" / "001" / "state.json"
        state = json.loads(state_path.read_text())
        state["current_attempt"] = 2
        state["attempt"] = 2
        state["status"] = "running"
        state["accepted"] = False
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        result = self.run_validate("pre-merge")

        self.assertEqual(result.returncode, 2)
        self.assertIn("acceptance attempt is stale", result.stderr)

    def test_pre_merge_rejects_incomplete_machine_gate(self) -> None:
        self.initialize()
        task = self.write_task("001")
        self.accept_task(task)
        acceptance_path = self.run_dir / "artifacts" / "001" / "acceptance.json"
        acceptance = json.loads(acceptance_path.read_text())
        acceptance["provider_exit"] = 1
        acceptance_path.write_text(json.dumps(acceptance) + "\n", encoding="utf-8")

        result = self.run_validate("pre-merge")

        self.assertEqual(result.returncode, 2)
        self.assertIn("provider_exit", result.stderr)

    def test_pre_merge_gate_requires_review_for_high_risk_task(self) -> None:
        self.initialize()
        task = self.write_task("001", risk="high")
        self.accept_task(task)

        rejected = self.run_validate("pre-merge")

        self.assertEqual(rejected.returncode, 2)
        self.assertIn("requires review: passed", rejected.stderr)
        acceptance_path = self.run_dir / "artifacts" / "001" / "acceptance.json"
        acceptance = json.loads(acceptance_path.read_text())
        acceptance["review"] = "passed"
        acceptance_path.write_text(json.dumps(acceptance) + "\n", encoding="utf-8")
        accepted = self.run_validate("pre-merge")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_legacy_run_has_clear_unsupported_error(self) -> None:
        self.initialize()
        (self.run_dir / "run.yaml").write_text(
            "slug: contract-test\nproject_cwd: /tmp\n", encoding="utf-8"
        )

        result = self.run_validate()

        self.assertEqual(result.returncode, 2)
        self.assertIn("schema v1 unsupported for strict validation", result.stderr)


if __name__ == "__main__":
    unittest.main()
