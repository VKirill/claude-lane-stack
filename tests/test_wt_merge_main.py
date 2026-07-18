#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MERGE = ROOT / "bin" / "wt-merge-main"


def run(*args: str, cwd: Path, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [*args],
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class WtMergeMainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.home = self.base / "home"
        self.repo.mkdir()
        self.home.mkdir()
        run("git", "init", "-b", "main", cwd=self.repo)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.repo)
        run("git", "config", "user.name", "Test User", cwd=self.repo)
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)
        run("git", "commit", "-m", "base", cwd=self.repo)
        self.base_sha = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare_run(self, *, schema_version: int = 2, accepted: bool = True) -> str:
        run_dir = self.repo / ".agents" / "runs" / "demo"
        task_dir = run_dir / "tasks"
        artifact_dir = run_dir / "artifacts" / "001"
        task_dir.mkdir(parents=True)
        artifact_dir.mkdir(parents=True)
        if schema_version == 2:
            (run_dir / "run.yaml").write_text(
                "schema_version: 2\n"
                "slug: demo\n"
                f"repo: {json.dumps(str(self.repo.resolve()))}\n"
                f"project_cwd: {json.dumps(str(self.repo.resolve()))}\n"
                f"base_sha: {self.base_sha}\n"
                "created_at: '2026-07-18T10:00:00Z'\n"
                "score: 4\n"
                "pools:\n  provider: 5\n  verification: 2\n"
                "gate: none\n"
                "finalize:\n  progress_now: null\n  close_next: []\n  close_open: []\n",
                encoding="utf-8",
            )
        else:
            (run_dir / "run.yaml").write_text(
                f"schema_version: 1\nslug: demo\nbase_sha: {self.base_sha}\nfinalize:\n"
                "  progress_now: null\n  close_next: []\n  close_open: []\n",
                encoding="utf-8",
            )
        task_path = task_dir / "001-feature.yaml"
        if schema_version == 2:
            task_path.write_text(
                "schema_version: 2\n"
                "id: '001'\n"
                "title: Feature\n"
                "risk: low\n"
                "lane: grok\n"
                f"project_cwd: {json.dumps(str(self.repo.resolve()))}\n"
                "read_first: []\n"
                "interfaces: []\n"
                "invariants: []\n"
                "out_of_scope: []\n"
                "expected_outputs:\n  - feature.txt\n"
                "owns_paths:\n  - feature.txt\n"
                "never_touch: []\n"
                "depends_on: []\n"
                "objective: Create the feature output.\n"
                "acceptance:\n  - feature.txt exists\n"
                "verify: none\n"
                "verification: []\n",
                encoding="utf-8",
            )
        else:
            task_path.write_text(
                'id: "001"\nschema_version: 1\ntitle: Feature\nstatus: done\n',
                encoding="utf-8",
            )
        if schema_version == 2 and accepted:
            task_sha256 = hashlib.sha256(task_path.read_bytes()).hexdigest()
            (artifact_dir / "acceptance.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "task_id": "001",
                        "attempt": 2,
                        "task_sha256": task_sha256,
                        "provider_exit": 0,
                        "report": "complete",
                        "owns_check": "passed",
                        "verification": "passed",
                        "review": "not_required",
                        "accepted": True,
                        "accepted_at": "2026-07-18T10:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (artifact_dir / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "task_id": "001",
                        "task_sha256": task_sha256,
                        "status": "accepted",
                        "accepted": True,
                        "current_attempt": 2,
                        "attempt": 2,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        run("git", "add", ".agents", cwd=self.repo)
        run("git", "commit", "-m", "add run contract", cwd=self.repo)

        run("git", "checkout", "-b", "agent/demo", cwd=self.repo)
        (self.repo / "feature.txt").write_text("done\n", encoding="utf-8")
        run("git", "add", "feature.txt", cwd=self.repo)
        run("git", "commit", "-m", "feature", cwd=self.repo)
        source_commit = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout.strip()
        run("git", "checkout", "main", cwd=self.repo)
        return source_commit

    def test_writes_schema_v2_receipt_without_remote(self) -> None:
        source_commit = self.prepare_run()
        install_dir = self.home / ".agents"
        install_dir.mkdir(parents=True)
        (install_dir / "install.json").write_text(
            json.dumps({"installed_at": "2026-07-18T09:00:00Z", "source_sha": source_commit}) + "\n",
            encoding="utf-8",
        )

        result = run(str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)})
        self.assertIn("MERGED=", result.stdout)
        receipt = json.loads((self.repo / ".agents/runs/demo/merge.json").read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_version"], 2)
        self.assertEqual(receipt["repo"], str(self.repo.resolve()))
        self.assertEqual(receipt["run"], "demo")
        self.assertEqual(receipt["branch"], "agent/demo")
        self.assertEqual(receipt["base_sha"], self.base_sha)
        self.assertEqual(receipt["source_commit"], source_commit)
        self.assertRegex(receipt["merge_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(
            receipt["remote"],
            {"name": None, "attempted": False, "pushed": False, "sha": None, "error": None},
        )
        self.assertEqual(receipt["accepted_tasks"][0]["task_id"], "001")
        self.assertEqual(receipt["accepted_tasks"][0]["attempt"], 2)
        self.assertEqual(receipt["verification_summary"]["passed"], 1)
        self.assertEqual(receipt["verification_summary"]["failed"], 0)
        self.assertEqual(receipt["local_install"]["installed_at"], "2026-07-18T09:00:00Z")
        self.assertEqual(receipt["local_install"]["source_sha"], source_commit)
        self.assertFalse(receipt["local_install"]["matches_merge"])
        self.assertTrue((self.repo / ".agents/runs/demo/finalize.json").is_file())
        self.assertEqual(receipt["finalize"]["status"], "complete")
        self.assertTrue(receipt["finalize"]["receipt"].endswith("/finalize.json"))
        merge_md = (self.repo / ".agents/runs/demo/MERGE.md").read_text(encoding="utf-8")
        self.assertIn(receipt["merge_commit"][:12], merge_md)
        self.assertLessEqual(len(merge_md.splitlines()), 12)

    def test_refuses_schema_v2_task_without_acceptance_receipt(self) -> None:
        self.prepare_run(accepted=False)
        before = run("git", "rev-parse", "main", cwd=self.repo).stdout.strip()

        result = run(
            str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)}, check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("acceptance.json", result.stderr.lower())
        self.assertEqual(run("git", "rev-parse", "main", cwd=self.repo).stdout.strip(), before)
        self.assertFalse((self.repo / ".agents/runs/demo/merge.json").exists())
        self.assertFalse((self.repo / ".agents/runs/demo/MERGE.md").exists())

    def test_refuses_stale_schema_v2_acceptance_receipt(self) -> None:
        self.prepare_run()
        task_path = self.repo / ".agents/runs/demo/tasks/001-feature.yaml"
        task_path.write_text(task_path.read_text(encoding="utf-8") + "acceptance:\n  - Changed after accept\n", encoding="utf-8")
        before = run("git", "rev-parse", "main", cwd=self.repo).stdout.strip()

        result = run(
            str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)}, check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task_sha256", result.stderr)
        self.assertEqual(run("git", "rev-parse", "main", cwd=self.repo).stdout.strip(), before)

    def test_legacy_task_remains_mergeable(self) -> None:
        self.prepare_run(schema_version=1, accepted=False)
        result = run(str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)})
        self.assertEqual(result.returncode, 0)
        receipt = json.loads((self.repo / ".agents/runs/demo/merge.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["accepted_tasks"], [])
        self.assertEqual(receipt["verification_summary"]["total"], 0)

    def test_pushes_main_and_records_remote_sha(self) -> None:
        source_commit = self.prepare_run()
        bare = self.base / "origin.git"
        run("git", "init", "--bare", str(bare), cwd=self.base)
        run("git", "remote", "add", "origin", str(bare), cwd=self.repo)
        run("git", "push", "-u", "origin", "main", cwd=self.repo)

        result = run(str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)})

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.repo / ".agents/runs/demo/merge.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["source_commit"], source_commit)
        self.assertEqual(receipt["remote"]["name"], "origin")
        self.assertTrue(receipt["remote"]["attempted"])
        self.assertTrue(receipt["remote"]["pushed"])
        self.assertEqual(receipt["remote"]["sha"], receipt["merge_commit"])
        self.assertIsNone(receipt["remote"]["error"])
        remote_sha = run("git", "--git-dir", str(bare), "rev-parse", "refs/heads/main", cwd=self.base).stdout.strip()
        self.assertEqual(remote_sha, receipt["merge_commit"])

    def test_records_finalize_failure_after_merge(self) -> None:
        self.prepare_run()
        run_dir = self.repo / ".agents/runs/demo"
        run_yaml = run_dir / "run.yaml"
        run_yaml.write_text(
            run_yaml.read_text(encoding="utf-8").replace(
                "progress_now: null", "progress_now: Cannot update a missing PROGRESS file"
            ),
            encoding="utf-8",
        )
        run("git", "add", str(run_yaml.relative_to(self.repo)), cwd=self.repo)
        run("git", "commit", "-m", "configure failing finalize", cwd=self.repo)
        bare = self.base / "origin.git"
        run("git", "init", "--bare", str(bare), cwd=self.base)
        run("git", "remote", "add", "origin", str(bare), cwd=self.repo)
        run("git", "push", "-u", "origin", "main", cwd=self.repo)
        remote_before = run(
            "git", "--git-dir", str(bare), "rev-parse", "refs/heads/main", cwd=self.base
        ).stdout.strip()

        result = run(
            str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)}, check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run-finalize failed", result.stderr)
        self.assertTrue((self.repo / "feature.txt").is_file())
        receipt = json.loads((run_dir / "merge.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["finalize"]["status"], "failed")
        self.assertTrue(receipt["finalize"]["receipt"].endswith("/finalize.json"))
        self.assertIn("PROGRESS.md", receipt["finalize"]["error"])
        finalize = json.loads((run_dir / "finalize.json").read_text(encoding="utf-8"))
        self.assertEqual(finalize["status"], "failed")
        self.assertTrue(run("git", "show-ref", "--verify", "refs/heads/agent/demo", cwd=self.repo, check=False).returncode == 0)
        remote_after = run(
            "git", "--git-dir", str(bare), "rev-parse", "refs/heads/main", cwd=self.base
        ).stdout.strip()
        self.assertEqual(remote_after, remote_before)

    def test_flow_style_v2_run_still_uses_the_strict_gate(self) -> None:
        self.prepare_run()
        run_yaml = self.repo / ".agents" / "runs" / "demo" / "run.yaml"
        contract = yaml.safe_load(run_yaml.read_text(encoding="utf-8"))
        run_yaml.write_text(
            yaml.safe_dump(contract, default_flow_style=True, sort_keys=False),
            encoding="utf-8",
        )
        run("git", "add", str(run_yaml.relative_to(self.repo)), cwd=self.repo)
        run("git", "commit", "-m", "use flow-style run contract", cwd=self.repo)

        result = run(str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)})

        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.repo / ".agents" / "runs" / "demo" / "merge.json").read_text())
        self.assertEqual(receipt["accepted_tasks"][0]["task_id"], "001")

    def test_schema_v2_refuses_and_preserves_dirty_worktree(self) -> None:
        self.prepare_run()
        (self.repo / ".git" / "info" / "exclude").write_text(".worktrees/\n", encoding="utf-8")
        worktree = self.repo / ".worktrees" / "demo"
        worktree.parent.mkdir()
        run("git", "worktree", "add", str(worktree), "agent/demo", cwd=self.repo)
        dirty = worktree / "uncommitted.txt"
        dirty.write_text("preserve me\n", encoding="utf-8")
        before = run("git", "rev-parse", "agent/demo", cwd=self.repo).stdout.strip()
        main_before = run("git", "rev-parse", "main", cwd=self.repo).stdout.strip()

        result = run(str(MERGE), str(self.repo), "demo", cwd=self.repo, env={"HOME": str(self.home)}, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema-v2", result.stderr.lower())
        self.assertIn("dirty", result.stderr.lower())
        self.assertEqual(run("git", "rev-parse", "agent/demo", cwd=self.repo).stdout.strip(), before)
        self.assertEqual(run("git", "rev-parse", "main", cwd=self.repo).stdout.strip(), main_before)
        self.assertEqual(dirty.read_text(encoding="utf-8"), "preserve me\n")
        self.assertTrue(worktree.is_dir())

    def test_legacy_run_retains_auto_commit_compatibility(self) -> None:
        self.prepare_run(schema_version=1, accepted=False)
        (self.repo / ".git" / "info" / "exclude").write_text(".worktrees/\n", encoding="utf-8")
        worktree = self.repo / ".worktrees" / "demo"
        worktree.parent.mkdir()
        run("git", "worktree", "add", str(worktree), "agent/demo", cwd=self.repo)
        (worktree / "legacy-uncommitted.txt").write_text("legacy\n", encoding="utf-8")

        result = run(
            str(MERGE),
            str(self.repo),
            "demo",
            cwd=self.repo,
            env={"HOME": str(self.home)},
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.repo / "legacy-uncommitted.txt").read_text(encoding="utf-8"),
            "legacy\n",
        )


if __name__ == "__main__":
    unittest.main()
