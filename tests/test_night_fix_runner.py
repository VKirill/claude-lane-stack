from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "bin" / "night-fix-runner"


def load_runner():
    loader = importlib.machinery.SourceFileLoader("night_fix_runner", str(RUNNER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class NightFixRunnerTest(unittest.TestCase):
    @staticmethod
    def plan_task(task_id: str, *, task_sha256: str, finding_id: str) -> dict[str, object]:
        return {
            "id": task_id,
            "path": f"/tmp/{task_id}.yaml",
            "risk": "high",
            "depends_on": [],
            "finding_id": finding_id,
            "finding_control_sha256": "f" * 64,
            "task_sha256": task_sha256,
            "review_required": True,
            "validation_error": None,
        }

    def test_verification_allowlist_rejects_shell_composition_and_unknown_tools(self) -> None:
        runner = load_runner()

        self.assertEqual(runner.verification_error("npm test", set()), None)
        self.assertEqual(runner.verification_error("python3 -m pytest tests", set()), None)
        self.assertIsNotNone(runner.verification_error("npm test && curl bad", set()))
        self.assertIsNotNone(runner.verification_error("npm test > result.txt", set()))
        self.assertIsNotNone(runner.verification_error("echo $(cat .env)", {"echo"}))
        self.assertIsNotNone(runner.verification_error("custom-check", set()))
        for command in (
            "npx --yes arbitrary-package",
            "npm exec arbitrary-package",
            "npm install arbitrary-package",
            "pnpm dlx arbitrary-package",
            "pnpm add arbitrary-package",
            "yarn dlx arbitrary-package",
            "yarn add arbitrary-package",
            "python3 /tmp/arbitrary.py",
            "python3 ../outside.py",
            "python3 $HOME/escape.py",
            "python3 ${HOME}/escape.py",
            "python3 ~/escape.py",
            "python3 tests/*.py",
            "npm test & curl bad",
            "node /tmp/arbitrary.mjs",
            "python3 -B -c 'print(1)'",
            "node --no-warnings -e 'console.log(1)'",
            "php -r 'phpinfo()'",
        ):
            with self.subTest(command=command):
                self.assertIsNotNone(runner.verification_error(command, set()))
        self.assertEqual(
            runner.verification_error("node --test tests/smoke.test.mjs", set()), None
        )
        self.assertEqual(
            runner.verification_error("custom-check --fast", {"custom-check"}), None
        )
        self.assertIsNotNone(runner.verification_error("curl example.test", {"curl"}))

    def test_dry_run_plan_is_non_mutating_and_binds_tasks_to_worktree(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            worktree = repo / ".worktrees" / "night-fixes-2026-07-18"
            run_dir = repo / ".agents" / "runs" / "night-fixes-2026-07-18"
            task_dir = run_dir / "tasks"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            worktree.mkdir(parents=True)
            task_dir.mkdir(parents=True)
            (run_dir / "worktree.json").write_text(
                yaml.safe_dump(
                    {
                        "slug": "night-fixes-2026-07-18",
                        "branch": "agent/night-fixes-2026-07-18",
                        "path": str(worktree),
                        "repo": str(repo),
                        "base": "a" * 40,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "run.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 2,
                        "slug": "night-fixes-2026-07-18",
                        "repo": str(repo),
                        "project_cwd": str(worktree),
                        "gate": "pre-merge",
                    }
                ),
                encoding="utf-8",
            )
            (task_dir / "001.yaml").write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 2,
                        "id": "001",
                        "lane": "grok",
                        "risk": "high",
                        "project_cwd": str(worktree),
                        "owns_paths": ["src/**"],
                        "depends_on": [],
                        "verify": "tests",
                        "verification": [
                            {
                                "command": "python3 -m pytest tests",
                                "cwd": str(worktree),
                                "timeout_sec": 600,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            plan = runner.build_plan(repo, run_dir, extra_executables=set())

            self.assertEqual(plan["worktree"], str(worktree.resolve()))
            self.assertEqual(plan["tasks"][0]["id"], "001")
            self.assertTrue(plan["tasks"][0]["review_required"])
            self.assertFalse((repo / ".agents" / "night-fix-state.json").exists())

            unsafe_task = yaml.safe_load((task_dir / "001.yaml").read_text())
            unsafe_task["verification"][0]["command"] = "npm test && curl bad"
            (task_dir / "001.yaml").write_text(
                yaml.safe_dump(unsafe_task, sort_keys=False), encoding="utf-8"
            )
            unsafe_plan = runner.build_plan(repo, run_dir, extra_executables=set())
            self.assertIn("shell composition", unsafe_plan["tasks"][0]["validation_error"])
            self.assertFalse((repo / ".agents" / "night-fix-state.json").exists())

    def test_auto_merge_requires_both_request_and_project_opt_in(self) -> None:
        runner = load_runner()

        self.assertFalse(runner.auto_merge_enabled({}, requested=True))
        self.assertFalse(runner.auto_merge_enabled({"auto_merge": True}, requested=False))
        self.assertTrue(runner.auto_merge_enabled({"auto_merge": True}, requested=True))

    def test_fixed_finding_requires_standardized_closure_receipts(self) -> None:
        import jsonschema

        schema = json.loads((ROOT / "schemas" / "finding-v1.schema.json").read_text())
        finding = {
            "schema_version": 1,
            "fingerprint": "a" * 64,
            "source_sha": "b" * 40,
            "source_task": "001",
            "source_attempt": 1,
            "source_chunk": "chunk-1",
            "severity": "P1",
            "title": "Broken gate",
            "summary": "The verification gate accepts empty commands.",
            "actionable": True,
            "evidence": [{"path": "bin/tool", "line": 1, "detail": "Empty passed."}],
            "scope": {"owns_paths": ["bin/tool"], "never_touch": [".env*"]},
            "verification": [{"command": "python3 -m unittest", "timeout_sec": 300}],
            "status": "fixed",
            "first_seen": "2026-07-18T00:00:00+00:00",
            "last_seen": "2026-07-18T01:00:00+00:00",
        }

        self.assertTrue(list(jsonschema.Draft202012Validator(schema).iter_errors(finding)))
        finding["closure"] = {
            "task_id": "fix-aaaaaaaaaaaa",
            "run": "night-fixes-2026-07-18",
            "acceptance": "/repo/.agents/runs/night/artifacts/fix/acceptance.json",
            "review": "/repo/.agents/runs/night/artifacts/fix/review.json",
            "commit_sha": None,
            "closed_at": "2026-07-18T01:00:00+00:00",
        }
        jsonschema.Draft202012Validator(schema).validate(finding)

    def test_unsafe_task_marks_canonical_finding_needs_human(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp)
            fingerprint = "c" * 64
            path = repo / ".agents" / "findings" / f"{fingerprint}.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps({"fingerprint": fingerprint, "status": "open", "last_seen": "old"})
            )

            runner.mark_finding_needs_human(
                repo, fingerprint, "fix-cccccccccccc", "unsafe verification"
            )

            finding = json.loads(path.read_text())
            self.assertEqual(finding["status"], "needs_human")
            self.assertNotEqual(finding["last_seen"], "old")

    def test_existing_state_atomically_adds_new_plan_tasks_and_preserves_progress(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            run_dir = repo / ".agents" / "runs" / "night"
            run_dir.mkdir(parents=True)
            first = self.plan_task("001", task_sha256="1" * 64, finding_id="a" * 64)
            plan = {
                "schema_version": 1,
                "repo": str(repo),
                "run_dir": str(run_dir),
                "slug": "night",
                "worktree": str(repo / ".worktrees" / "night"),
                "tasks": [first],
            }
            state = runner.load_or_create_state(repo, plan)
            state["tasks"]["001"]["stage"] = "accepted"
            state["tasks"]["001"]["attempts"] = 2
            runner.save_state(repo, state)

            second = self.plan_task("002", task_sha256="2" * 64, finding_id="b" * 64)
            resumed = runner.load_or_create_state(repo, {**plan, "tasks": [first, second]})

            self.assertEqual(resumed["tasks"]["001"]["stage"], "accepted")
            self.assertEqual(resumed["tasks"]["001"]["attempts"], 2)
            self.assertEqual(resumed["tasks"]["002"]["stage"], "pending")
            self.assertEqual(resumed["status"], "running")

    def test_existing_state_rejects_changed_or_removed_task_identity_without_rewrite(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            run_dir = repo / ".agents" / "runs" / "night"
            run_dir.mkdir(parents=True)
            first = self.plan_task("001", task_sha256="1" * 64, finding_id="a" * 64)
            second = self.plan_task("002", task_sha256="2" * 64, finding_id="b" * 64)
            plan = {
                "schema_version": 1,
                "repo": str(repo),
                "run_dir": str(run_dir),
                "slug": "night",
                "worktree": str(repo / ".worktrees" / "night"),
                "tasks": [first, second],
            }
            runner.load_or_create_state(repo, plan)
            state_file = run_dir / runner.STATE_NAME
            before = state_file.read_bytes()

            changed = self.plan_task("001", task_sha256="9" * 64, finding_id="a" * 64)
            with self.assertRaisesRegex(runner.RunnerError, "identity"):
                runner.load_or_create_state(repo, {**plan, "tasks": [changed, second]})
            self.assertEqual(state_file.read_bytes(), before)

            with self.assertRaisesRegex(runner.RunnerError, "removed"):
                runner.load_or_create_state(repo, {**plan, "tasks": [first]})
            self.assertEqual(state_file.read_bytes(), before)

    def test_accepted_task_resume_does_not_replay_provider_or_commit(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            run_dir = repo / ".agents" / "runs" / "night"
            worktree = repo / ".worktrees" / "night"
            artifact = run_dir / "artifacts" / "001"
            artifact.mkdir(parents=True)
            worktree.mkdir(parents=True)
            task_sha = "1" * 64
            (artifact / "acceptance.json").write_text(
                json.dumps(
                    {
                        "accepted": True,
                        "task_id": "001",
                        "task_sha256": task_sha,
                    }
                ),
                encoding="utf-8",
            )
            state = {
                "schema_version": 1,
                "repo": str(repo),
                "run_dir": str(run_dir),
                "slug": "night",
                "worktree": str(worktree),
                "status": "running",
                "tasks": {
                    "001": {
                        "stage": "accepted",
                        "attempts": 1,
                        "finding_id": "a" * 64,
                        "task_sha256": task_sha,
                        "commit_sha": "b" * 40,
                    }
                },
            }
            task = {
                "id": "001",
                "path": str(run_dir / "tasks" / "001.yaml"),
                "task_sha256": task_sha,
                "depends_on": [],
                "finding_id": "a" * 64,
                "validation_error": None,
            }

            with mock.patch.object(runner, "mark_finding_fixed") as close_finding, mock.patch.object(
                runner, "commit_task"
            ) as commit, mock.patch.object(
                runner, "run_command", side_effect=AssertionError("provider command must not run")
            ):
                completed = runner.process_task(
                    repo,
                    run_dir,
                    worktree,
                    task,
                    state,
                    poll_interval=0,
                    provider_timeout=1,
                    codex_bin=None,
                    grok_bin=None,
                )

            self.assertTrue(completed)
            close_finding.assert_called_once()
            commit.assert_not_called()

    def test_changed_canonical_finding_blocks_before_any_provider_command(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            run_dir = repo / ".agents" / "runs" / "night"
            worktree = repo / ".worktrees" / "night"
            task_path = run_dir / "tasks" / "fix.yaml"
            finding_id = "c" * 64
            task_path.parent.mkdir(parents=True)
            worktree.mkdir(parents=True)
            task_contract = {
                "interfaces": [f"source_finding_id: {finding_id}"],
                "owns_paths": ["src/app.py"],
                "never_touch": [".env*"],
                "verification": [
                    {"command": "python3 -m pytest tests", "cwd": str(worktree), "timeout_sec": 300}
                ],
            }
            control_sha = runner.task_finding_control_digest(task_contract, finding_id)
            task_contract["interfaces"].append(
                f"source_finding_control_sha256: {control_sha}"
            )
            task_path.write_text(yaml.safe_dump(task_contract), encoding="utf-8")
            finding_path = repo / ".agents" / "findings" / f"{finding_id}.json"
            finding_path.parent.mkdir(parents=True)
            finding_path.write_text(
                json.dumps(
                    {
                        "fingerprint": finding_id,
                        "status": "open",
                        "actionable": True,
                        "scope": {"owns_paths": ["src/changed.py"], "never_touch": [".env*"]},
                        "verification": [{"command": "python3 -m pytest tests", "timeout_sec": 300}],
                    }
                ),
                encoding="utf-8",
            )
            state = {
                "schema_version": 1,
                "repo": str(repo),
                "run_dir": str(run_dir),
                "slug": "night",
                "worktree": str(worktree),
                "status": "running",
                "tasks": {
                    "fix": {
                        "stage": "pending",
                        "attempts": 0,
                        "finding_id": finding_id,
                        "finding_control_sha256": control_sha,
                        "task_sha256": "d" * 64,
                    }
                },
            }
            task = {
                "id": "fix",
                "path": str(task_path),
                "depends_on": [],
                "finding_id": finding_id,
                "finding_control_sha256": control_sha,
                "validation_error": None,
            }

            with mock.patch.object(
                runner, "run_command", side_effect=AssertionError("provider command must not run")
            ):
                completed = runner.process_task(
                    repo,
                    run_dir,
                    worktree,
                    task,
                    state,
                    poll_interval=0,
                    provider_timeout=1,
                    codex_bin=None,
                    grok_bin=None,
                )

            self.assertFalse(completed)
            self.assertEqual(state["tasks"]["fix"]["stage"], "blocked")
            self.assertEqual(json.loads(finding_path.read_text())["status"], "needs_human")

            terminal = json.loads(finding_path.read_text())
            terminal["status"] = "dismissed"
            terminal["scope"] = {
                "owns_paths": ["src/app.py"],
                "never_touch": [".env*"],
            }
            finding_path.write_text(json.dumps(terminal), encoding="utf-8")
            state["tasks"]["fix"]["stage"] = "pending"
            with mock.patch.object(
                runner, "run_command", side_effect=AssertionError("provider command must not run")
            ):
                completed = runner.process_task(
                    repo,
                    run_dir,
                    worktree,
                    task,
                    state,
                    poll_interval=0,
                    provider_timeout=1,
                    codex_bin=None,
                    grok_bin=None,
                )

            self.assertFalse(completed)
            self.assertEqual(state["tasks"]["fix"]["stage"], "blocked")
            self.assertEqual(json.loads(finding_path.read_text())["status"], "needs_human")

    def test_commit_refuses_worktree_drift_after_review(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            worktree = Path(raw_tmp)
            subprocess.run(["git", "init", "-q"], cwd=worktree, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=worktree, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=worktree, check=True)
            target = worktree / "app.txt"
            target.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=worktree, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=worktree, check=True)
            target.write_text("reviewed\n", encoding="utf-8")
            reviewed_snapshot = runner.worktree_snapshot(worktree)
            head_before = runner.git_head(worktree)
            target.write_text("post-accept mutation\n", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after review"):
                runner.commit_task(
                    worktree, "fix", expected_snapshot=reviewed_snapshot
                )

            self.assertEqual(runner.git_head(worktree), head_before)
            self.assertEqual(target.read_text(encoding="utf-8"), "post-accept mutation\n")

    def test_commit_records_exact_reviewed_tree(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            worktree = Path(raw_tmp)
            subprocess.run(["git", "init", "-q"], cwd=worktree, check=True)
            target = worktree / "app.txt"
            target.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=worktree, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-qm",
                    "base",
                ],
                cwd=worktree,
                check=True,
            )
            target.write_text("reviewed\n", encoding="utf-8")
            reviewed_snapshot = runner.worktree_snapshot(worktree)

            commit_sha = runner.commit_task(
                worktree, "fix", expected_snapshot=reviewed_snapshot
            )

            self.assertEqual(commit_sha, runner.git_head(worktree))
            self.assertEqual(
                subprocess.run(
                    ["git", "show", f"{commit_sha}:app.txt"],
                    cwd=worktree,
                    text=True,
                    stdout=subprocess.PIPE,
                    check=True,
                ).stdout,
                "reviewed\n",
            )
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=worktree,
                    text=True,
                    stdout=subprocess.PIPE,
                    check=True,
                ).stdout,
                "",
            )

    def test_resume_finalizes_commit_applied_before_state_write(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "repo"
            worktree = root / "worktree"
            run_dir = repo / ".agents" / "runs" / "night"
            artifact = run_dir / "artifacts" / "001"
            artifact.mkdir(parents=True)
            worktree.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=worktree, check=True)
            target = worktree / "app.txt"
            target.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=worktree, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-qm",
                    "base",
                ],
                cwd=worktree,
                check=True,
            )
            target.write_text("reviewed\n", encoding="utf-8")
            reviewed_snapshot = runner.worktree_snapshot(worktree)
            pending = runner.prepare_task_commit(
                worktree, "001", expected_snapshot=reviewed_snapshot
            )
            self.assertIsNotNone(pending)
            assert pending is not None
            applied = runner.apply_task_commit(worktree, "001", pending)
            task_sha = "1" * 64
            (artifact / "acceptance.json").write_text(
                json.dumps(
                    {
                        "accepted": True,
                        "task_id": "001",
                        "task_sha256": task_sha,
                    }
                ),
                encoding="utf-8",
            )
            state = {
                "schema_version": 1,
                "repo": str(repo),
                "run_dir": str(run_dir),
                "slug": "night",
                "worktree": str(worktree),
                "status": "running",
                "tasks": {
                    "001": {
                        "stage": "committing",
                        "attempts": 1,
                        "finding_id": "a" * 64,
                        "task_sha256": task_sha,
                        "reviewed_snapshot": reviewed_snapshot,
                        "pending_commit": pending,
                    }
                },
            }
            task = {
                "id": "001",
                "path": str(run_dir / "tasks" / "001.yaml"),
                "task_sha256": task_sha,
                "depends_on": [],
                "finding_id": "a" * 64,
                "validation_error": None,
            }

            with mock.patch.object(runner, "mark_finding_fixed") as close_finding:
                completed = runner.process_task(
                    repo,
                    run_dir,
                    worktree,
                    task,
                    state,
                    poll_interval=0,
                    provider_timeout=1,
                    codex_bin=None,
                    grok_bin=None,
                )

            self.assertTrue(completed)
            self.assertEqual(state["tasks"]["001"]["stage"], "accepted")
            self.assertEqual(state["tasks"]["001"]["commit_sha"], applied)
            close_finding.assert_called_once()

    def test_resume_recovers_completed_merge_after_worktree_cleanup(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "app.txt").write_text("published\n", encoding="utf-8")
            subprocess.run(["git", "add", "app.txt"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-qm",
                    "published",
                ],
                cwd=repo,
                check=True,
            )
            published = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()
            run_dir = repo / ".agents" / "runs" / "night"
            run_dir.mkdir(parents=True)
            task_sha = "1" * 64
            state = {
                "schema_version": 1,
                "repo": str(repo.resolve()),
                "run_dir": str(run_dir.resolve()),
                "slug": "night",
                "worktree": str((repo / ".worktrees" / "night").resolve()),
                "status": "merging",
                "tasks": {
                    "001": {
                        "stage": "accepted",
                        "task_sha256": task_sha,
                    }
                },
            }
            runner.atomic_json(run_dir / runner.STATE_NAME, state)
            runner.atomic_json(run_dir / "finalize.json", {"status": "complete"})
            completed_at = "2026-07-18T12:00:00+00:00"
            runner.atomic_json(
                run_dir / "merge.json",
                {
                    "schema_version": 2,
                    "repo": str(repo.resolve()),
                    "run": "night",
                    "branch": "agent/night",
                    "base_sha": published,
                    "source_commit": published,
                    "merge_commit": published,
                    "published_commit": published,
                    "completed_at": completed_at,
                    "remote": {
                        "name": None,
                        "attempted": False,
                        "pushed": False,
                        "sha": None,
                        "error": None,
                    },
                    "accepted_tasks": [
                        {
                            "task_id": "001",
                            "task_sha256": task_sha,
                            "accepted": True,
                            "verification": "passed",
                            "review": "passed",
                        }
                    ],
                    "finalize": {
                        "attempted": True,
                        "status": "complete",
                        "receipt": str(run_dir / "finalize.json"),
                        "error": None,
                    },
                },
            )

            result = runner.run_fix_plan(
                Namespace(
                    repo=str(repo),
                    run_dir=str(run_dir),
                    slug=None,
                    dry_run=False,
                    auto_merge=False,
                    poll_interval=0,
                    provider_timeout=1,
                    codex_bin=None,
                    grok_bin=None,
                )
            )

            self.assertEqual(result, 0)
            recovered = json.loads((run_dir / runner.STATE_NAME).read_text())
            self.assertEqual(recovered["status"], "merged")
            self.assertEqual(recovered["merged_at"], completed_at)
            self.assertEqual(recovered["published_commit"], published)
            pointer = json.loads(
                (repo / ".agents" / "night-fix-current.json").read_text()
            )
            self.assertEqual(pointer["status"], "merged")


if __name__ == "__main__":
    unittest.main()
