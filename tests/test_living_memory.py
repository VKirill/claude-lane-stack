from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
from living_memory import migrate_legacy, progress_path, resolve, PROGRESS, LESSONS  # noqa: E402


class LivingMemoryTest(unittest.TestCase):
    def test_resolve_prefers_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".agents").mkdir()
            (repo / ".agents" / PROGRESS).write_text("agents\n", encoding="utf-8")
            (repo / PROGRESS).write_text("root\n", encoding="utf-8")
            self.assertEqual(progress_path(repo).read_text(encoding="utf-8"), "agents\n")

    def test_resolve_falls_back_to_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / LESSONS).write_text("legacy\n", encoding="utf-8")
            self.assertEqual(resolve(repo, LESSONS), repo / LESSONS)

    def test_migrate_moves_root_into_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / PROGRESS).write_text("was root\n", encoding="utf-8")
            dest = migrate_legacy(repo, PROGRESS)
            self.assertEqual(dest, repo / ".agents" / PROGRESS)
            self.assertTrue(dest.is_file())
            self.assertFalse((repo / PROGRESS).exists())
            self.assertEqual(dest.read_text(encoding="utf-8"), "was root\n")


if __name__ == "__main__":
    unittest.main()
