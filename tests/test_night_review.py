from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NIGHT_REVIEW = ROOT / "bin" / "night-review"
NIGHT_REVIEW_ALL = ROOT / "bin" / "night-review-all"
NIGHT_ENGINE = ROOT / "bin" / "night-review-engine"
RUN_VALIDATE = ROOT / "bin" / "run-validate"


class NightReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self._write_commit("app.txt", "initial\n", "initial")
        self.base_sha = self.git("rev-parse", "HEAD")
        self._write_commit("app.txt", "initial\nchange\n", "[micro:missing-context] change")
        self.head_sha = self.git("rev-parse", "HEAD")
        self.codex_log = self.root / "codex.jsonl"
        self.codex_count = self.root / "codex.count"
        self.fake_codex = self.root / "fake-codex"
        self.fake_codex.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import re
                import sys
                from pathlib import Path

                args = sys.argv[1:]
                prompt = sys.stdin.read()
                output_schema = json.loads(
                    Path(args[args.index("--output-schema") + 1]).read_text(encoding="utf-8")
                )
                count_path = Path(os.environ["FAKE_CODEX_COUNT"])
                count = int(count_path.read_text()) + 1 if count_path.exists() else 1
                count_path.write_text(str(count))
                log_path = Path(os.environ["FAKE_CODEX_LOG"])
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "args": args,
                        "prompt": prompt,
                        "prompt_bytes": len(prompt.encode("utf-8")),
                        "output_schema": output_schema,
                        "automation_marker": os.environ.get(
                            "CLAUDE_LANE_AUTOMATION", "<unset>"
                        ),
                    }) + "\\n")
                if os.environ.get("FAKE_CODEX_FAIL_AT") == str(count):
                    print("forced provider failure", file=sys.stderr)
                    raise SystemExit(7)
                output = Path(args[args.index("--output-last-message") + 1])
                mode = os.environ.get("FAKE_CODEX_MODE", "none")
                if mode == "invalid":
                    output.write_text("{not-json", encoding="utf-8")
                    raise SystemExit(0)
                match = re.search(r"^Chunk-ID: (.+)$", prompt, re.MULTILINE)
                chunk_id = match.group(1) if match else "missing"
                findings = []
                verdict = "passed"
                if mode in {"finding", "blank_command", "broad_scope", "unanchored_scope"}:
                    verdict = "failed"
                    findings = [{
                        "severity": "P1",
                        "title": "Unsafe application behavior",
                        "summary": "The changed application path lacks a required guard.",
                        "actionable": True,
                        "evidence": [{
                            "path": "app.txt",
                            "line": 2,
                            "detail": "The new line is not guarded.",
                        }],
                        "scope": {
                            "owns_paths": (
                                ["**/*"] if mode == "broad_scope" else
                                ["src/**"] if mode == "unanchored_scope" else
                                ["app.txt"]
                            ),
                            "never_touch": [".env*"],
                        },
                        "verification": [{
                            "command": "   " if mode == "blank_command" else "python3 -m unittest -v",
                            "timeout_sec": 300,
                        }],
                    }]
                output.write_text(json.dumps({
                    "schema_version": 1,
                    "chunk_id": chunk_id,
                    "verdict": verdict,
                    "findings": findings,
                }), encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        self.fake_codex.chmod(0o755)

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.strip()

    def _write_commit(self, name: str, content: str, message: str) -> None:
        (self.repo / name).write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", name], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                message,
            ],
            cwd=self.repo,
            check=True,
        )

    def write_review_state(
        self,
        run_dir: Path,
        task_file: Path,
        project_cwd: Path,
        *,
        attempt: int = 1,
    ) -> None:
        task_id = str(__import__("yaml").safe_load(task_file.read_text())["id"])
        artifact = run_dir / "artifacts" / task_id
        artifact.mkdir(parents=True, exist_ok=True)
        (artifact / "state.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "task_id": task_id,
                    "task_sha256": hashlib.sha256(task_file.read_bytes()).hexdigest(),
                    "project_cwd": str(project_cwd.resolve()),
                    "current_attempt": attempt,
                    "attempt": attempt,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def run_review(
        self,
        *extra: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        merged_env.update(
            {
                "FAKE_CODEX_LOG": str(self.codex_log),
                "FAKE_CODEX_COUNT": str(self.codex_count),
            }
        )
        merged_env.update(env or {})
        return subprocess.run(
            [
                str(NIGHT_REVIEW),
                str(self.repo),
                "--since",
                self.base_sha,
                "--day",
                "2026-07-18",
                *extra,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=merged_env,
            timeout=30,
        )

    def test_dry_run_is_non_mutating_and_missing_task_context_does_not_abort(self) -> None:
        merge = self.repo / ".agents" / "runs" / "missing-run" / "MERGE.md"
        merge.parent.mkdir(parents=True)
        merge.write_text(f"merge commit: {self.head_sha}\n", encoding="utf-8")
        before = sorted(path.relative_to(self.repo) for path in self.repo.rglob("*"))

        result = self.run_review("--dry-run")

        after = sorted(path.relative_to(self.repo) for path in self.repo.rglob("*"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(after, before)
        self.assertIn("missing-context", result.stdout)
        self.assertIn("missing-run", result.stdout)
        self.assertIn("Task context unavailable", result.stdout)
        self.assertIn(self.head_sha, result.stdout)

    def test_valid_results_persist_idempotently_and_compile_v2_fix_task(self) -> None:
        result = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        findings = sorted((self.repo / ".agents" / "findings").glob("*.json"))
        self.assertEqual(len(findings), 1)
        finding = json.loads(findings[0].read_text())
        fingerprint = finding["fingerprint"]
        self.assertEqual(finding["source_sha"], self.head_sha)
        self.assertEqual(finding["status"], "open")

        run_dir = self.repo / ".agents" / "runs" / "night-fixes-2026-07-18"
        run = __import__("yaml").safe_load((run_dir / "run.yaml").read_text())
        self.assertEqual(run["gate"], "pre-merge")
        tasks = sorted((run_dir / "tasks").glob("*.yaml"))
        self.assertEqual(len(tasks), 1)
        task = __import__("yaml").safe_load(tasks[0].read_text())
        self.assertEqual(task["project_cwd"], str(self.repo.resolve()))
        self.assertEqual(task["verification"][0]["cwd"], str(self.repo.resolve()))
        self.assertTrue(task["verification"][0]["command"])
        self.assertIn(f"source_finding_id: {fingerprint}", task["interfaces"])
        validation = subprocess.run(
            [
                sys.executable,
                str(RUN_VALIDATE),
                "--run-dir",
                str(run_dir),
                "--phase",
                "pre-dispatch",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)

        invocations = [json.loads(line) for line in self.codex_log.read_text().splitlines()]
        args = invocations[0]["args"]
        self.assertIn("--ignore-user-config", args)
        self.assertIn("night-review", args)
        self.assertIn("gpt-5.6-sol", args)
        self.assertIn("model_reasoning_effort=xhigh", args)
        self.assertIn("read-only", args)
        self.assertIn("--output-schema", args)
        self.assertEqual(invocations[0]["automation_marker"], "1")

        def contains_unsupported_model_keyword(value: object) -> bool:
            if isinstance(value, dict):
                return bool({"allOf", "uniqueItems"} & value.keys()) or any(
                    contains_unsupported_model_keyword(item) for item in value.values()
                )
            if isinstance(value, list):
                return any(contains_unsupported_model_keyword(item) for item in value)
            return False

        self.assertFalse(
            contains_unsupported_model_keyword(invocations[0]["output_schema"])
        )

        def enum_and_const_nodes_have_types(value: object) -> bool:
            if isinstance(value, dict):
                if ("enum" in value or "const" in value) and "type" not in value:
                    return False
                return all(enum_and_const_nodes_have_types(item) for item in value.values())
            if isinstance(value, list):
                return all(enum_and_const_nodes_have_types(item) for item in value)
            return True

        self.assertTrue(
            enum_and_const_nodes_have_types(invocations[0]["output_schema"])
        )
        source_schema = json.loads(
            (ROOT / "schemas" / "night-review-result-v1.schema.json").read_text()
        )
        self.assertTrue(contains_unsupported_model_keyword(source_schema))

        repeated = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(len(list((self.repo / ".agents" / "findings").glob("*.json"))), 1)
        self.assertEqual(len(list((run_dir / "tasks").glob("*.yaml"))), 1)
        todo = (self.repo / ".agents" / "todos" / "INDEX.md").read_text()
        self.assertEqual(todo.count(f"finding-{fingerprint}"), 1)
        self.assertTrue((self.repo / ".agents" / "agent-notes" / "OPEN.md").is_file())
        checkpoint = json.loads(
            (self.repo / ".agents" / "night-review" / "checkpoint.json").read_text()
        )
        self.assertEqual(checkpoint["head_sha"], self.head_sha)
        latest_invocation = json.loads(self.codex_log.read_text().splitlines()[-1])
        self.assertIn("Unresolved finding carry-over", latest_invocation["prompt"])

    def test_fixed_finding_reopens_when_a_new_review_rediscovers_it(self) -> None:
        first = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        finding_path = next((self.repo / ".agents" / "findings").glob("*.json"))
        finding = json.loads(finding_path.read_text())
        finding["status"] = "fixed"
        finding["closure"] = {
            "task_id": "fix-old",
            "run": "night-fixes-old",
            "acceptance": "/tmp/old-acceptance.json",
            "review": "/tmp/old-review.json",
            "commit_sha": None,
            "closed_at": "2026-07-18T00:00:00+00:00",
        }
        finding_path.write_text(json.dumps(finding) + "\n", encoding="utf-8")
        self._write_commit(
            "app.txt", "initial\nchange\nregressed\n", "reintroduce reviewed behavior"
        )

        repeated = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )

        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        reopened = json.loads(finding_path.read_text())
        self.assertEqual(reopened["status"], "open")
        self.assertNotIn("closure", reopened)

    def test_invalid_output_creates_no_findings_tasks_or_checkpoint(self) -> None:
        result = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "invalid"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.repo / ".agents" / "findings").exists())
        self.assertFalse(
            (self.repo / ".agents" / "runs" / "night-fixes-2026-07-18").exists()
        )
        self.assertFalse(
            (self.repo / ".agents" / "night-review" / "checkpoint.json").exists()
        )
        self.assertTrue(
            (self.repo / ".agents" / "session-log" / "REVIEW-2026-07-18.failures.json").is_file()
        )

    def test_blank_verification_command_cannot_create_finding_or_task(self) -> None:
        result = self.run_review(
            "--project-cwd",
            str(self.repo),
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "blank_command"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("verification command may not be blank", result.stderr)
        self.assertFalse((self.repo / ".agents" / "findings").exists())

    def test_broad_generated_ownership_scope_is_rejected(self) -> None:
        result = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "broad_scope"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ownership scope", result.stderr.lower())
        self.assertFalse((self.repo / ".agents" / "findings").exists())

    def test_generated_ownership_scope_must_cover_its_evidence(self) -> None:
        result = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "unanchored_scope"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence path", result.stderr.lower())
        self.assertFalse((self.repo / ".agents" / "findings").exists())
        self.assertFalse((self.repo / ".agents" / "runs").exists())
        self.assertFalse(
            (self.repo / ".agents" / "night-review" / "checkpoint.json").exists()
        )

    def test_checkpoint_does_not_advance_when_a_later_chunk_fails(self) -> None:
        self._write_commit("other.txt", "second change\n", "second change")

        result = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_FAIL_AT": "2"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.codex_count.read_text(), "2")
        self.assertFalse(
            (self.repo / ".agents" / "night-review" / "checkpoint.json").exists()
        )
        self.assertFalse((self.repo / ".agents" / "findings").exists())

    def test_oversized_commit_is_split_into_bounded_chunks(self) -> None:
        self._write_commit("large.txt", "x" * 3000 + "\n", "large change")

        result = self.run_review(
            "--max-chunk-bytes",
            "900",
            "--codex-bin",
            str(self.fake_codex),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = [json.loads(line) for line in self.codex_log.read_text().splitlines()]
        self.assertGreater(len(invocations), 2)
        self.assertTrue(all(item["prompt_bytes"] <= 900 for item in invocations))
        self.assertTrue(
            (self.repo / ".agents" / "night-review" / "checkpoint.json").is_file()
        )

    def test_without_project_cwd_findings_persist_but_tasks_stay_pending(self) -> None:
        result = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list((self.repo / ".agents" / "findings").glob("*.json"))), 1)
        self.assertFalse(
            (self.repo / ".agents" / "runs" / "night-fixes-2026-07-18").exists()
        )
        self.assertIn("fix tasks pending", result.stdout)

    def test_run_slug_consumes_and_preserves_worktree_metadata(self) -> None:
        worktree = self.root / "fix-worktree"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-q",
                "-b",
                "agent/custom-night-fixes",
                str(worktree),
                "HEAD",
            ],
            cwd=self.repo,
            check=True,
        )
        run_dir = self.repo / ".agents" / "runs" / "custom-night-fixes"
        run_dir.mkdir(parents=True)
        metadata = {
            "slug": "custom-night-fixes",
            "branch": "agent/custom-night-fixes",
            "path": str(worktree),
            "base": self.head_sha,
            "repo": str(self.repo),
            "sentinel": "preserve-me",
        }
        metadata_path = run_dir / "worktree.json"
        metadata_path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")

        result = self.run_review(
            "--run-slug",
            "custom-night-fixes",
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(metadata_path.read_text()), metadata)
        run = __import__("yaml").safe_load((run_dir / "run.yaml").read_text())
        self.assertEqual(run["project_cwd"], str(worktree.resolve()))
        task_path = next((run_dir / "tasks").glob("*.yaml"))
        task = __import__("yaml").safe_load(task_path.read_text())
        self.assertEqual(task["project_cwd"], str(worktree.resolve()))

    def test_compile_fixes_uses_persisted_findings_without_second_codex_review(self) -> None:
        reviewed = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        invocation_count = len(self.codex_log.read_text().splitlines())

        worktree = self.root / "compile-worktree"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-q",
                "-b",
                "agent/compiled-night-fixes",
                str(worktree),
                "HEAD",
            ],
            cwd=self.repo,
            check=True,
        )
        run_dir = self.repo / ".agents" / "runs" / "compiled-night-fixes"
        run_dir.mkdir(parents=True)
        metadata = {
            "slug": "compiled-night-fixes",
            "branch": "agent/compiled-night-fixes",
            "path": str(worktree),
            "base": self.head_sha,
            "repo": str(self.repo),
        }
        (run_dir / "worktree.json").write_text(json.dumps(metadata) + "\n")

        compiled = subprocess.run(
            [
                sys.executable,
                str(NIGHT_ENGINE),
                "compile-fixes",
                str(self.repo),
                "--day",
                "2026-07-18",
                "--run-slug",
                "compiled-night-fixes",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.assertEqual(len(self.codex_log.read_text().splitlines()), invocation_count)
        task_path = next((run_dir / "tasks").glob("*.yaml"))
        task = __import__("yaml").safe_load(task_path.read_text())
        self.assertEqual(task["project_cwd"], str(worktree.resolve()))

    def test_needs_human_finding_is_not_compiled_for_grok(self) -> None:
        reviewed = self.run_review(
            "--codex-bin",
            str(self.fake_codex),
            env={"FAKE_CODEX_MODE": "finding"},
        )
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        finding_path = next((self.repo / ".agents" / "findings").glob("*.json"))
        finding = json.loads(finding_path.read_text())
        finding["status"] = "needs_human"
        finding_path.write_text(json.dumps(finding) + "\n")

        worktree = self.root / "human-worktree"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-q",
                "-b",
                "agent/human-night-fixes",
                str(worktree),
                "HEAD",
            ],
            cwd=self.repo,
            check=True,
        )
        run_dir = self.repo / ".agents" / "runs" / "human-night-fixes"
        run_dir.mkdir(parents=True)
        (run_dir / "worktree.json").write_text(
            json.dumps(
                {
                    "slug": "human-night-fixes",
                    "branch": "agent/human-night-fixes",
                    "path": str(worktree),
                    "base": self.head_sha,
                    "repo": str(self.repo),
                }
            )
            + "\n"
        )

        compiled = subprocess.run(
            [
                sys.executable,
                str(NIGHT_ENGINE),
                "compile-fixes",
                str(self.repo),
                "--day",
                "2026-07-18",
                "--run-slug",
                "human-night-fixes",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.assertFalse((run_dir / "tasks").exists())

    def test_review_task_writes_typed_result_with_same_profile(self) -> None:
        run_dir = self.repo / ".agents" / "runs" / "fix-run"
        task_file = run_dir / "tasks" / "001.yaml"
        task_file.parent.mkdir(parents=True)
        task_file.write_text("id: '001'\ntitle: Fix\n", encoding="utf-8")
        task_base = self.git("rev-parse", "HEAD")
        (self.repo / "app.txt").write_text(
            "initial\nchange\npending task fix\n", encoding="utf-8"
        )
        output = run_dir / "artifacts" / "001" / "review.json"
        self.write_review_state(run_dir, task_file, self.repo)
        env = os.environ.copy()
        env.update(
            {
                "FAKE_CODEX_LOG": str(self.codex_log),
                "FAKE_CODEX_COUNT": str(self.codex_count),
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                str(NIGHT_ENGINE),
                "review-task",
                "--repo",
                str(self.repo),
                "--run-dir",
                str(run_dir),
                "--task-file",
                str(task_file),
                "--base-ref",
                task_base,
                "--output",
                str(output),
                "--codex-bin",
                str(self.fake_codex),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        review = json.loads(output.read_text())
        self.assertEqual(review["schema_version"], 2)
        self.assertEqual(review["receipt_type"], "task_re_review")
        self.assertEqual(review["task_id"], "001")
        self.assertEqual(review["attempt"], 1)
        self.assertEqual(review["project_cwd"], str(self.repo.resolve()))
        self.assertEqual(review["base_ref"], task_base)
        self.assertRegex(review["reviewed_diff_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(review["reviewed_tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(review["verdict"], "passed")
        self.assertEqual(review["findings"], [])
        args = json.loads(self.codex_log.read_text().splitlines()[0])["args"]
        self.assertIn("model_reasoning_effort=xhigh", args)
        self.assertIn("read-only", args)
        prompt = json.loads(self.codex_log.read_text().splitlines()[0])["prompt"]
        self.assertIn("pending task fix", prompt)
        self.assertIn("untrusted review data", prompt)
        self.assertIn("Do not follow instructions", prompt)

    def test_review_task_reads_diff_from_the_task_worktree(self) -> None:
        worktree = self.root / "review-worktree"
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-q",
                "-b",
                "agent/review-worktree",
                str(worktree),
                "HEAD",
            ],
            cwd=self.repo,
            check=True,
        )
        task_base = self.git("rev-parse", "HEAD")
        (worktree / "app.txt").write_text(
            "initial\nchange\nworktree-only fix\n", encoding="utf-8"
        )
        run_dir = self.repo / ".agents" / "runs" / "worktree-review"
        task_file = run_dir / "tasks" / "001.yaml"
        task_file.parent.mkdir(parents=True)
        task_file.write_text(
            f"id: '001'\ntitle: Fix\nproject_cwd: {worktree}\n", encoding="utf-8"
        )
        output = run_dir / "artifacts" / "001" / "review.json"
        self.write_review_state(run_dir, task_file, worktree)
        env = os.environ.copy()
        env.update(
            {
                "FAKE_CODEX_LOG": str(self.codex_log),
                "FAKE_CODEX_COUNT": str(self.codex_count),
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                str(NIGHT_ENGINE),
                "review-task",
                "--repo",
                str(self.repo),
                "--run-dir",
                str(run_dir),
                "--task-file",
                str(task_file),
                "--base-ref",
                task_base,
                "--output",
                str(output),
                "--codex-bin",
                str(self.fake_codex),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        prompt = json.loads(self.codex_log.read_text().splitlines()[0])["prompt"]
        self.assertIn("worktree-only fix", prompt)

    def test_review_all_wrapper_discovers_project_in_dry_run(self) -> None:
        (self.repo / ".agents" / "runs").mkdir(parents=True)

        result = subprocess.run(
            [
                str(NIGHT_REVIEW_ALL),
                "--dry-run",
                "--root",
                str(self.root),
                "--day",
                "2026-07-18",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.repo), result.stdout)
        self.assertIn("Reviewed 1 of 1", result.stdout)
        self.assertFalse((self.repo / ".agents" / "session-log").exists())


if __name__ == "__main__":
    unittest.main()
