from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NIGHT_SHIFT = ROOT / "bin" / "night-shift"


class NightShiftTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.fake_home = self.root / "home"
        self.grok_home = self.fake_home / ".grok"
        self.grok_home.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "app.txt").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.txt"], cwd=self.repo, check=True)
        self._commit("initial")
        self.base = self.git("rev-parse", "HEAD")
        (self.repo / "app.txt").write_text("initial\nchanged\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.txt"], cwd=self.repo, check=True)
        self._commit("change")
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
                output = Path(args[args.index("--output-last-message") + 1])
                chunk = re.search(r"^Chunk-ID: (.+)$", prompt, re.MULTILINE)
                findings = []
                verdict = "passed"
                if (
                    os.environ.get("FAKE_SHIFT_FINDING") == "1"
                    and "Post-fix task re-review" not in prompt
                ):
                    verdict = "failed"
                    findings = [{
                        "severity": "P1",
                        "title": "Missing guard",
                        "summary": "The changed line needs a guard.",
                        "actionable": True,
                        "evidence": [{"path": "app.txt", "line": 2, "detail": "unguarded"}],
                        "scope": {"owns_paths": ["app.txt"], "never_touch": [".env*"]},
                        "verification": [{"command": "python3 --version", "timeout_sec": 300}],
                    }]
                output.write_text(json.dumps({
                    "schema_version": 1,
                    "chunk_id": chunk.group(1) if chunk else "missing",
                    "verdict": verdict,
                    "findings": findings,
                }), encoding="utf-8")
                """
            ),
            encoding="utf-8",
        )
        self.fake_codex.chmod(0o755)
        self.fake_grok = self.grok_home / "fake-grok"
        self.fake_grok.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import hashlib
                import json
                import os
                import re
                import sys
                from pathlib import Path

                args = sys.argv[1:]
                if "--version" in args:
                    print("grok 0.2.103-test (fake)")
                    raise SystemExit(0)
                prompt = Path(args[args.index("--prompt-file") + 1])
                rules = args[args.index("--rules") + 1]
                task_id = re.search(r"task_id=([^;]+)", rules).group(1)
                prompt_sha256 = hashlib.sha256(prompt.read_bytes()).hexdigest()
                target = Path.cwd() / "app.txt"
                target.write_text(target.read_text(encoding="utf-8") + "fixed\\n", encoding="utf-8")
                session_flag = "--session-id" if "--session-id" in args else "--resume"
                session_id = args[args.index(session_flag) + 1]
                print(json.dumps({"type": "session", "sessionId": session_id}), flush=True)
                print(json.dumps({"type": "text", "data": "fix complete\\n"}), flush=True)
                print(json.dumps({
                    "type": "text",
                    "data": (
                        "<<<LANE_REPORT:BEGIN>>>\\n"
                        "# Report\\n\\n"
                        f"TASK_ID: {task_id}\\n"
                        f"PROMPT_SHA256: {prompt_sha256}\\n"
                        "STATUS: complete\\n\\n"
                        "Implemented the bounded fix.\\n"
                        "<<<LANE_REPORT:END>>>\\n"
                    ),
                }), flush=True)
                print(json.dumps({
                    "type": "end",
                    "stopReason": "EndTurn",
                    "sessionId": session_id,
                }), flush=True)
                """
            ),
            encoding="utf-8",
        )
        self.fake_grok.chmod(0o755)

    def _commit(self, message: str) -> None:
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

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()

    def run_shift(self, *extra: str, finding: bool = False) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["LANE_BG_BACKEND"] = "nohup"
        env["HOME"] = str(self.fake_home)
        if finding:
            env["FAKE_SHIFT_FINDING"] = "1"
        return subprocess.run(
            [
                str(NIGHT_SHIFT),
                str(self.repo),
                "--day",
                "2026-07-18",
                "--since",
                self.base,
                "--codex-bin",
                str(self.fake_codex),
                *extra,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
            env=env,
        )

    def test_dry_run_does_not_create_review_or_worktree_state(self) -> None:
        result = self.run_shift("--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertFalse((self.repo / ".agents").exists())
        self.assertFalse((self.repo / ".worktrees").exists())

    def test_no_actionable_findings_does_not_create_worktree(self) -> None:
        result = self.run_shift()

        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        self.assertIn("no runnable findings", result.stdout)
        self.assertFalse((self.repo / ".worktrees").exists())

    def test_prepare_only_creates_isolated_v2_grok_tasks(self) -> None:
        result = self.run_shift("--prepare-only", finding=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        slug = "night-fixes-2026-07-18"
        worktree = self.repo / ".worktrees" / slug
        run_dir = self.repo / ".agents" / "runs" / slug
        self.assertTrue(worktree.is_dir())
        self.assertTrue((run_dir / "worktree.json").is_file())
        self.assertTrue((run_dir / "run.yaml").is_file())
        task = next((run_dir / "tasks").glob("*.yaml"))
        self.assertIn(str(worktree.resolve()), task.read_text())
        self.assertFalse((self.repo / ".agents" / "night-fix-state.json").exists())

    def test_full_shift_dispatches_verifies_rereviews_accepts_and_closes_finding(self) -> None:
        result = self.run_shift(
            "--grok-bin",
            str(self.fake_grok),
            "--poll-interval",
            "0.05",
            "--provider-timeout",
            "20",
            finding=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr + "\n" + result.stdout)
        slug = "night-fixes-2026-07-18"
        run_dir = self.repo / ".agents" / "runs" / slug
        task_path = next((run_dir / "tasks").glob("*.yaml"))
        task_id = __import__("yaml").safe_load(task_path.read_text())["id"]
        artifact = run_dir / "artifacts" / task_id
        acceptance = __import__("json").loads((artifact / "acceptance.json").read_text())
        self.assertTrue(acceptance["accepted"])
        review = __import__("json").loads((artifact / "review.json").read_text())
        self.assertEqual(review["verdict"], "passed")
        state = __import__("json").loads((run_dir / "night-fix-state.json").read_text())
        self.assertEqual(state["status"], "accepted")
        finding_path = next((self.repo / ".agents" / "findings").glob("*.json"))
        finding = __import__("json").loads(finding_path.read_text())
        self.assertEqual(finding["status"], "fixed")
        self.assertEqual(finding["closure"]["task_id"], task_id)
        self.assertTrue(finding["closure"]["acceptance"].endswith("acceptance.json"))
        self.assertTrue((self.repo / ".agents" / "night-fix-current.json").is_file())
        worktree = self.repo / ".worktrees" / slug
        self.assertIn("fixed", (worktree / "app.txt").read_text())
        self.assertNotIn("fixed", (self.repo / "app.txt").read_text())
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        closed_before = finding["closure"]["closed_at"]

        resumed = subprocess.run(
            [
                str(ROOT / "bin" / "night-fix-runner"),
                str(self.repo),
                "--run-dir",
                str(run_dir),
                "--grok-bin",
                str(self.fake_grok),
                "--codex-bin",
                str(self.fake_codex),
                "--poll-interval",
                "0.05",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env={
                **os.environ,
                "HOME": str(self.fake_home),
                "LANE_BG_BACKEND": "nohup",
            },
            timeout=30,
        )
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        self.assertEqual(head_after, head_before)
        finding_after = __import__("json").loads(finding_path.read_text())
        self.assertEqual(finding_after["closure"]["closed_at"], closed_before)


if __name__ == "__main__":
    unittest.main()
