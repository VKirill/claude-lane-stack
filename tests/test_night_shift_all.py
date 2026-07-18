from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NIGHT_SHIFT_ALL = ROOT / "bin" / "night-shift-all"


class NightShiftAllTest(unittest.TestCase):
    def test_discovers_active_lane_project_in_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "README.md").write_text("fixture\n")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
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
            (repo / ".agents" / "runs").mkdir(parents=True)

            result = subprocess.run(
                [
                    str(NIGHT_SHIFT_ALL),
                    "--dry-run",
                    "--root",
                    str(root),
                    "--day",
                    "2026-07-18",
                    "--jobs",
                    "2",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(repo.resolve()), result.stdout)
            self.assertIn("Processed 1 of 1", result.stdout)
            self.assertFalse((repo / ".agents" / "session-log").exists())


if __name__ == "__main__":
    unittest.main()
