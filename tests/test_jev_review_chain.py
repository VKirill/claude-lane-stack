#!/usr/bin/env python3
"""Independent contract tests for verify → Jev → same-session retry."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from jev_review import (  # noqa: E402
    AUDIT_MARK,
    apply_accept_review,
    merge_audit_into_prompt,
    path_owned,
    render_audit,
    review_changes,
)
from jev_slots import skill_prompt_block, suggest_write_skills  # noqa: E402


HOT = {
    "schema_version": 1,
    "verdict": "request_changes",
    "blocking": 1,
    "findings": [
        {
            "file": "apps/api/src/auth.py",
            "line": 12,
            "dimension": "security",
            "mechanism": "authorization",
            "severity": 2.2,
            "action": "request_changes",
            "hunk": "+allow_all = True",
        }
    ],
}


class JevReviewChainTest(unittest.TestCase):
    def test_path_owned_prefix(self) -> None:
        self.assertTrue(path_owned("apps/api/src/auth.py", ["apps/api/**"]))
        self.assertFalse(path_owned("apps/web/page.tsx", ["apps/api"]))
        self.assertTrue(path_owned("x.py", None))

    def test_owns_filter_skips_foreign_diff(self) -> None:
        diff = (
            "diff --git a/apps/web/page.tsx b/apps/web/page.tsx\n"
            "--- a/apps/web/page.tsx\n"
            "+++ b/apps/web/page.tsx\n"
            "@@ -1 +1 @@\n"
            "-a\n"
            "+b\n"
        )
        with (
            patch("jev_review.collect_diff", return_value=diff),
            patch("jev_review.jev_enabled", return_value=True),
        ):
            report = review_changes(Path("/tmp"), owns_paths=["apps/api"])
        self.assertEqual(report["verdict"], "skip")
        self.assertEqual(report["screenedFiles"], 0)

    def test_audit_names_file_mechanism_not_prose(self) -> None:
        text = render_audit(HOT)
        self.assertIn(AUDIT_MARK, text)
        self.assertIn("apps/api/src/auth.py:12", text)
        self.assertIn("authorization", text)
        self.assertIn("+allow_all = True", text)

    def test_first_request_changes_writes_audit_and_asks_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)
            with (
                patch("jev_review.accept_review_mode", return_value="retry"),
                patch("jev_review.jev_enabled", return_value=True),
                patch("jev_review.review_changes", return_value=HOT),
            ):
                decision = apply_accept_review(Path("/tmp"), artifact, attempt=1)
            self.assertEqual(decision["next"], "jev_retry")
            self.assertTrue((artifact / "jev-review.json").is_file())
            self.assertTrue((artifact / "jev-audit.md").is_file())
            self.assertIn(AUDIT_MARK, (artifact / "jev-audit.md").read_text())

    def test_second_attempt_blocks_without_new_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)
            with (
                patch("jev_review.accept_review_mode", return_value="retry"),
                patch("jev_review.jev_enabled", return_value=True),
                patch("jev_review.review_changes", return_value=HOT),
            ):
                decision = apply_accept_review(Path("/tmp"), artifact, attempt=2)
            self.assertEqual(decision["next"], "blocked")
            self.assertFalse((artifact / "jev-audit.md").is_file())

    def test_advisory_never_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)
            with (
                patch("jev_review.accept_review_mode", return_value="advisory"),
                patch("jev_review.jev_enabled", return_value=True),
                patch("jev_review.review_changes", return_value=HOT),
            ):
                decision = apply_accept_review(Path("/tmp"), artifact, attempt=1)
            self.assertEqual(decision["next"], "accept")
            self.assertFalse((artifact / "jev-audit.md").is_file())

    def test_review_error_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)
            with (
                patch("jev_review.accept_review_mode", return_value="retry"),
                patch("jev_review.jev_enabled", return_value=True),
                patch("jev_review.review_changes", side_effect=RuntimeError("boom")),
            ):
                decision = apply_accept_review(Path("/tmp"), artifact, attempt=1)
            self.assertEqual(decision["next"], "accept")
            self.assertEqual(decision["verdict"], "error")

    def test_merge_audit_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)
            (artifact / "jev-audit.md").write_text(
                render_audit(HOT), encoding="utf-8"
            )
            first = merge_audit_into_prompt(b"TASK\n", artifact)
            self.assertIn(AUDIT_MARK.encode(), first)
            self.assertTrue((artifact / "jev-audit.applied.md").is_file())
            second = merge_audit_into_prompt(first, artifact)
            self.assertEqual(first, second)

    def test_declared_skills_win_without_jev(self) -> None:
        names = suggest_write_skills({"skills": ["impeccable-ui", "none"]})
        self.assertEqual(names, ["impeccable-ui"])
        block = skill_prompt_block(names)
        self.assertIn("impeccable-ui", block)
        self.assertIn("~/.agents/skills/impeccable-ui/SKILL.md", block)

    def test_task_schema_allows_skills(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "task-v2.schema.json").read_text(encoding="utf-8")
        )
        self.assertIn("skills", schema["properties"])


if __name__ == "__main__":
    unittest.main()
