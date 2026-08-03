from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from handoff_lib import (  # noqa: E402
    CONTRACT_NO_RETRY_CLASSES,
    build_handoff,
    classify_verify_failure,
    write_handoff,
)


class HandoffLibTest(unittest.TestCase):
    def test_classify_missing_script(self) -> None:
        detail = (
            "python3: can't open file '/x/worktrees/t/.agents/runs/t/artifacts/001/check.py': "
            "[Errno 2] No such file or directory\n"
        )
        self.assertEqual(
            classify_verify_failure(detail), "verification_script_missing"
        )
        self.assertIn(
            "verification_script_missing", CONTRACT_NO_RETRY_CLASSES
        )

    def test_classify_generic_verify(self) -> None:
        self.assertEqual(
            classify_verify_failure("AssertionError: foo missing"),
            "verification_failed",
        )
        self.assertNotIn("verification_failed", CONTRACT_NO_RETRY_CLASSES)

    def test_write_handoff_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".agents" / "runs" / "demo").mkdir(parents=True)
            (repo / ".agents" / "routing.profile.yaml").write_text(
                "lanes:\n  main_write: kimi\nwriter:\n  model: m\nworkspace:\n  mode: in_place\n",
                encoding="utf-8",
            )
            (repo / "PROGRESS.md").write_text(
                "# P\n\n## Now\n- shipping feature X\n\n## Next\n- y\n",
                encoding="utf-8",
            )
            ctrl = {
                "schema_version": 1,
                "stage": "blocked",
                "project_cwd": str(repo),
                "run_dir": str(repo / ".agents" / "runs" / "demo"),
                "counts": {"total": 1, "accepted": 0, "blocked": 1, "running": 0, "pending": 0},
                "next_action": "operator_intervention",
                "tasks": {
                    "001": {
                        "stage": "blocked",
                        "last_failure_class": "verification_script_missing",
                        "provider": "kimi",
                    }
                },
            }
            (repo / ".agents" / "runs" / "demo" / "controller.json").write_text(
                json.dumps(ctrl), encoding="utf-8"
            )
            path = write_handoff(repo)
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 1)
            self.assertEqual(data["profile"]["main_write"], "kimi")
            self.assertEqual(data["profile"]["workspace_mode"], "in_place")
            self.assertTrue(data["blocked"])
            self.assertEqual(data["blocked"][0]["next_act"], "fix_contract")
            self.assertIn("shipping feature X", data["now"])
            md = repo / ".agents" / "HANDOFF.md"
            self.assertTrue(md.is_file())
            self.assertIn("fix_contract", md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
