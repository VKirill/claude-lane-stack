#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
RUNNER = ROOT / "bin" / "jev-review"

from jev_review import (  # noqa: E402
    collect_diff,
    parse_changed_files,
    parse_hunks,
    review_changes,
    screen_file,
    skip_path,
)


class JevReviewTest(unittest.TestCase):
    def test_parse_hunks(self) -> None:
        hunks = parse_hunks(
            "@@ -1,2 +10,3 @@\n+added\n context\n@@ -4,1 +20,1 @@\n-old\n"
        )
        self.assertEqual(len(hunks), 2)
        self.assertEqual(hunks[0]["id"], "hunk_1")
        self.assertEqual(hunks[0]["startLine"], 10)
        self.assertEqual(hunks[1]["startLine"], 20)

    def test_parse_hunks_keeps_full_patch(self) -> None:
        tail = "tail marker"
        patch_text = "@@ -1 +1 @@\n" + ("+line\n" * 700) + f"+{tail}\n"
        self.assertTrue(parse_hunks(patch_text)[0]["patch"].endswith(f"+{tail}"))

    def test_collect_diff_does_not_duplicate_staged_changes(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout="DIFF\n", stderr="")
        with patch("jev_review.subprocess.run", return_value=result) as run:
            self.assertEqual(collect_diff(Path("/tmp")), "DIFF\n")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], "HEAD")

    def test_screen_file_sends_full_patch_and_all_tests(self) -> None:
        tail = "PATCH_TAIL" * 900
        tests = [
            {"path": f"tests/test_{index}.py", "patch": f"test {index} {tail}"}
            for index in range(7)
        ]
        response = {"answers": {name: {"noul": 0.1} for name in (
            "correctness", "security", "reliability", "compatibility", "testGap"
        )}}
        with patch("jev_review.call_jev", return_value=response) as call:
            screen_file({"path": "app.py", "patch": tail}, tests)
        state = call.call_args.args[0]
        self.assertTrue(state["file"]["patch"].endswith("PATCH_TAIL"))
        self.assertEqual(len(state["changedTests"]), 7)
        self.assertTrue(state["changedTests"][-1]["patch"].endswith("PATCH_TAIL"))

    def test_parse_changed_files_skips_binary(self) -> None:
        diff = (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
            "diff --git a/x.png b/x.png\n"
            "Binary files a/x.png and b/x.png differ\n"
        )
        files = parse_changed_files(diff)
        self.assertEqual([item["path"] for item in files], ["app.py"])

    def test_skip_lockfile(self) -> None:
        self.assertTrue(skip_path("pnpm-lock.yaml"))
        self.assertTrue(skip_path("dist/out.js"))
        self.assertFalse(skip_path("bin/jev_review.py"))

    def test_review_clean_when_screen_low(self) -> None:
        diff = (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1,1 +1,2 @@\n"
            " keep\n"
            "+print(1)\n"
        )
        zeros = {name: 0.1 for name in (
            "correctness", "security", "reliability", "compatibility", "testGap"
        )}
        with (
            patch("jev_review.collect_diff", return_value=diff),
            patch("jev_review.jev_enabled", return_value=True),
            patch("jev_review.screen_file", return_value=zeros),
        ):
            report = review_changes(Path("/tmp"))
        self.assertEqual(report["verdict"], "clean")
        self.assertEqual(report["screenedFiles"], 1)
        self.assertEqual(report["findings"], [])

    def test_review_request_changes(self) -> None:
        diff = (
            "diff --git a/auth.py b/auth.py\n"
            "--- a/auth.py\n"
            "+++ b/auth.py\n"
            "@@ -1,1 +4,2 @@\n"
            "-check()\n"
            "+pass\n"
        )
        high = {
            "correctness": 0.1,
            "security": 0.9,
            "reliability": 0.1,
            "compatibility": 0.1,
            "testGap": 0.1,
        }
        finding = {
            "file": "auth.py",
            "dimension": "security",
            "line": 4,
            "severity": 2.4,
            "action": "request_changes",
        }
        with (
            patch("jev_review.collect_diff", return_value=diff),
            patch("jev_review.jev_enabled", return_value=True),
            patch("jev_review.screen_file", return_value=high),
            patch("jev_review.profile_file", return_value={"file": "auth.py", "category": "behavior"}),
            patch("jev_review.locate_signal", return_value=finding),
        ):
            report = review_changes(Path("/tmp"))
        self.assertEqual(report["verdict"], "request_changes")
        self.assertEqual(report["blocking"], 1)

    def test_cli_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "a.py"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "i"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            env = os.environ.copy()
            env["LANE_JEV"] = "0"
            result = subprocess.run(
                [str(RUNNER), "--project-cwd", str(repo)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertIn(report["verdict"], {"skip", "disabled"})


if __name__ == "__main__":
    unittest.main()
