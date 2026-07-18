from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STALL_CHECK = ROOT / "bin" / "lane-stall-check"


class LaneStallCheckTest(unittest.TestCase):
    def test_merged_runs_are_not_reported_or_mutated_as_stalled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            merged = repo / ".agents" / "runs" / "merged"
            active = repo / ".agents" / "runs" / "active"
            for run_dir in (merged, active):
                (run_dir / "tasks").mkdir(parents=True)
                task = run_dir / "tasks" / "001-task.yaml"
                task.write_text('id: "001"\nstatus: running\n', encoding="utf-8")
                old = time.time() - 3600
                os.utime(task, (old, old))
            (merged / "MERGE.md").write_text("merged\n", encoding="utf-8")

            result = subprocess.run(
                [str(STALL_CHECK), str(repo), "--minutes", "5", "--mark"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("active task 001", result.stdout)
            self.assertNotIn("merged task 001", result.stdout)
            self.assertIn(
                "status: running",
                (merged / "tasks" / "001-task.yaml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "status: stalled",
                (active / "tasks" / "001-task.yaml").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
