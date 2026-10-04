import datetime as dt
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "bin" / "agent-trash"
loader = importlib.machinery.SourceFileLoader("agent_trash", str(SCRIPT))
spec = importlib.util.spec_from_loader("agent_trash", loader)
agent_trash = importlib.util.module_from_spec(spec)
loader.exec_module(agent_trash)


class AgentTrashTest(unittest.TestCase):
    def test_moves_into_xdg_trash_with_a_record_and_unique_names(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            trash = Path(root) / "Trash"
            for _ in range(2):
                item = Path(root) / "a.txt"
                item.write_text("x")
                agent_trash.xdg_trash(item, trash)
                self.assertFalse(item.exists())
            self.assertEqual(sorted(p.name for p in (trash / "files").iterdir()), ["a.txt", "a.txt.2"])
            record = (trash / "info" / "a.txt.2.trashinfo").read_text()
            self.assertIn(f"Path={root}/a.txt", record)
            self.assertIn("DeletionDate=", record)

    def test_empties_only_entries_older_than_the_keep_period(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            trash = Path(root) / "Trash"
            (trash / "files" / "old").mkdir(parents=True)
            (trash / "info").mkdir()
            (trash / "info" / "old.trashinfo").write_text("[Trash Info]\nPath=/x/old\nDeletionDate=2020-01-01T00:00:00\n")
            fresh = Path(root) / "fresh"
            fresh.write_text("y")
            agent_trash.xdg_trash(fresh, trash)
            agent_trash.empty_old(trash, 7)
            self.assertEqual([p.name for p in (trash / "files").iterdir()], ["fresh"])
            self.assertEqual([p.name for p in (trash / "info").iterdir()], ["fresh.trashinfo"])

    def test_takes_rm_flags(self) -> None:
        self.assertEqual(agent_trash.parse(["-rf", "--", "-odd", "b"]), (True, False, ["-odd", "b"]))
        self.assertEqual(agent_trash.main(["-f", "/nonexistent/path"]), 0)
        self.assertEqual(agent_trash.main(["/nonexistent/path"]), 1)


if __name__ == "__main__":
    unittest.main()
