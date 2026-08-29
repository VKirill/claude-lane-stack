from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "lane-stack" / "hooks"))

from ensure_subagent_model import KEY, VALUE, ensure  # noqa: E402


class EnsureSubagentModelTest(unittest.TestCase):
    def test_writes_sonnet_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "settings.json"
            path.write_text('{"theme": "dark"}\n', encoding="utf-8")
            self.assertTrue(ensure(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["theme"], "dark")
            self.assertEqual(data["env"][KEY], VALUE)

    def test_does_not_clobber_existing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "settings.json"
            path.write_text(
                json.dumps({"env": {KEY: "haiku"}}),
                encoding="utf-8",
            )
            self.assertFalse(ensure(path))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["env"][KEY], "haiku")


if __name__ == "__main__":
    unittest.main()
