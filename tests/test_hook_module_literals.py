"""Claude Code refuses to load a function-hook module whose `$.env.get` takes anything but a literal name.

Claude Code 2.1.299 rejected lane-mods.ts over `$.env.get(name)` in fast-jev.ts (2026-10-14): the whole module
did not load, so /compact fell back to the built-in summary and winnow and jev-router were off too.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "plugins" / "lane-stack" / "hooks"
ENV_GET = re.compile(r"\$\.env\.get\(\s*([^)]*)\)")


class HookModuleLiteralsTest(unittest.TestCase):
    def test_env_get_takes_a_literal_name(self) -> None:
        bad = [
            f"{path.name}:{text[:match.start()].count(chr(10)) + 1}: {match.group(0)}"
            for path in sorted(HOOKS.glob("*.ts"))
            for text in [path.read_text(encoding="utf-8")]
            for match in ENV_GET.finditer(text)
            if not re.fullmatch(r"(['\"`])[A-Z0-9_]+\1", match.group(1).strip())
        ]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
