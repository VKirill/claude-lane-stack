from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WT_CREATE = ROOT / "bin" / "wt-create"


class WorktreeCreateTest(unittest.TestCase):
    def test_uses_local_git_exclude_without_dirtying_tracked_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / ".gitignore").write_text("dist/\n", encoding="utf-8")
            (repo / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=repo, check=True)
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
                cwd=repo,
                check=True,
            )

            result = subprocess.run(
                [str(WT_CREATE), str(repo), "night-fixes-test"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((repo / ".gitignore").read_text(), "dist/\n")
            exclude = (repo / ".git" / "info" / "exclude").read_text()
            self.assertIn(".worktrees/", exclude.splitlines())
            status = subprocess.run(
                ["git", "status", "--short", "--", ".gitignore"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout
            self.assertEqual(status, "")


if __name__ == "__main__":
    unittest.main()
