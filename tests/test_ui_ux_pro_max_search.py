from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "plugins" / "lane-stack" / "skills" / "ui-ux-pro-max" / "scripts" / "search.py"


class UiUxProMaxSearchTest(unittest.TestCase):
    def test_ux_domain_returns_hits(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SEARCH), "keyboard focus modal", "--domain", "ux", "-n", "2"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UI Pro Max Search Results", result.stdout)
        self.assertNotIn("Found: 0 results", result.stdout)


if __name__ == "__main__":
    unittest.main()
