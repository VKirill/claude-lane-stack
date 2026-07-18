#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINALIZE = ROOT / "bin" / "run-finalize"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunFinalizeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.run_dir = self.repo / ".agents" / "runs" / "demo"
        self.open_path = self.repo / ".agents" / "agent-notes" / "OPEN.md"
        self.progress = self.repo / "PROGRESS.md"
        self.run_dir.mkdir(parents=True)
        self.open_path.parent.mkdir(parents=True)
        self.progress.write_text(
            "# PROGRESS\n\n"
            "## Now\n- Old focus\n\n"
            "## Blocked\n- Nothing\n\n"
            "## Next\n- [ ] Ship exact item\n- [ ] Keep this item\n\n"
            "<!-- auto:session-ledger -->\n"
            "## Auto (session ledger)\n"
            "- [ ] This auto checkbox must stay untouched\n"
            "<!-- /auto:session-ledger -->\n",
            encoding="utf-8",
        )
        self.open_path.write_text(
            "# Agent notes\n\n## Open\n- [ ] Close exact debt\n- [ ] Keep debt\n",
            encoding="utf-8",
        )
        (self.run_dir / "merge.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "repo": str(self.repo.resolve()),
                    "run": "demo",
                    "branch": "agent/demo",
                    "base_sha": "1" * 40,
                    "source_commit": "2" * 40,
                    "merge_commit": "3" * 40,
                    "remote": {"name": None, "attempted": False, "pushed": False, "sha": None, "error": None},
                    "accepted_tasks": [],
                    "verification_summary": {"total": 0, "passed": 0, "failed": 0},
                    "local_install": {"installed_at": None, "source_sha": None, "matches_merge": False},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.fake_bin = Path(self.temp.name) / "bin"
        self.fake_bin.mkdir()
        fake_board = self.fake_bin / "run-board"
        fake_board.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$1\" >> \"${RUN_BOARD_LOG:?}\"\n"
            "grep -A1 '^## Now$' \"$1/PROGRESS.md\" | tail -n1 >> \"${RUN_BOARD_PROGRESS_LOG:?}\"\n",
            encoding="utf-8",
        )
        fake_board.chmod(0o755)
        self.board_log = Path(self.temp.name) / "board.log"
        self.board_progress_log = Path(self.temp.name) / "board-progress.log"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def invoke(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = f"{self.fake_bin}:{env['PATH']}"
        env["RUN_BOARD_LOG"] = str(self.board_log)
        env["RUN_BOARD_PROGRESS_LOG"] = str(self.board_progress_log)
        return subprocess.run(
            [str(FINALIZE), "--run-dir", str(self.run_dir), *args],
            cwd=self.repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_updates_exact_lines_preserves_auto_block_and_is_idempotent(self) -> None:
        auto_before = self.progress.read_text(encoding="utf-8").split("<!-- auto:session-ledger -->", 1)[1]
        result = self.invoke(
            "--progress-now",
            "Merged demo is ready",
            "--close-next",
            "Ship exact item",
            "--close-open",
            "Close exact debt",
        )
        self.assertIn("FINALIZED=", result.stdout)
        progress_after = self.progress.read_text(encoding="utf-8")
        open_after = self.open_path.read_text(encoding="utf-8")
        self.assertIn("## Now\n- Merged demo is ready\n", progress_after)
        self.assertIn("- [x] Ship exact item", progress_after)
        self.assertIn("- [ ] Keep this item", progress_after)
        self.assertEqual(progress_after.split("<!-- auto:session-ledger -->", 1)[1], auto_before)
        self.assertIn("- [x] Close exact debt", open_after)
        self.assertIn("- [ ] Keep debt", open_after)

        receipt_path = self.run_dir / "finalize.json"
        receipt_before = receipt_path.read_bytes()
        progress_hash = sha256(self.progress)
        open_hash = sha256(self.open_path)
        receipt = json.loads(receipt_before)
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["run"], "demo")
        self.assertEqual(receipt["files"]["progress"]["after_sha256"], progress_hash)
        self.assertEqual(receipt["files"]["open_notes"]["after_sha256"], open_hash)
        self.assertEqual([a["type"] for a in receipt["actions"]], ["progress_now", "close_next", "close_open"])

        self.invoke(
            "--progress-now",
            "Merged demo is ready",
            "--close-next",
            "Ship exact item",
            "--close-open",
            "Close exact debt",
        )
        self.assertEqual(sha256(self.progress), progress_hash)
        self.assertEqual(sha256(self.open_path), open_hash)
        self.assertEqual(receipt_path.read_bytes(), receipt_before)
        self.assertEqual(self.board_log.read_text(encoding="utf-8").splitlines(), [str(self.repo), str(self.repo)])
        self.assertEqual(
            self.board_progress_log.read_text(encoding="utf-8").splitlines(),
            ["- Merged demo is ready", "- Merged demo is ready"],
        )

    def test_uses_run_yaml_finalize_defaults(self) -> None:
        (self.run_dir / "run.yaml").write_text(
            "schema_version: 2\n"
            "finalize:\n"
            "  progress_now: Defaults were applied\n"
            "  close_next:\n"
            "    - Ship exact item\n"
            "  close_open:\n"
            "    - Close exact debt\n",
            encoding="utf-8",
        )

        self.invoke()

        self.assertIn("## Now\n- Defaults were applied\n", self.progress.read_text(encoding="utf-8"))
        self.assertIn("- [x] Ship exact item", self.progress.read_text(encoding="utf-8"))
        self.assertIn("- [x] Close exact debt", self.open_path.read_text(encoding="utf-8"))

    def test_rejects_invalid_merge_receipt_without_mutation(self) -> None:
        before_progress = self.progress.read_bytes()
        before_open = self.open_path.read_bytes()
        (self.run_dir / "merge.json").write_text('{"schema_version": 1}\n', encoding="utf-8")

        result = self.invoke("--progress-now", "Must not apply", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge.json", result.stderr)
        self.assertEqual(self.progress.read_bytes(), before_progress)
        self.assertEqual(self.open_path.read_bytes(), before_open)
        self.assertFalse((self.run_dir / "finalize.json").exists())
        self.assertFalse(self.board_log.exists())

    def test_missing_exact_checkbox_fails_without_partial_write(self) -> None:
        before_progress = self.progress.read_bytes()

        result = self.invoke(
            "--progress-now", "Must not partially apply", "--close-next", "Missing item", check=False
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing item", result.stderr)
        self.assertEqual(self.progress.read_bytes(), before_progress)
        receipt = json.loads((self.run_dir / "finalize.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["files"]["progress"]["before_sha256"], sha256(self.progress))
        self.assertEqual(receipt["files"]["progress"]["after_sha256"], sha256(self.progress))


if __name__ == "__main__":
    unittest.main()
