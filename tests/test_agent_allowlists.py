from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "plugins" / "lane-stack" / "agents"


def _agent_allowlist(path: Path) -> list[str]:
    tools = next(
        line.removeprefix("tools:").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("tools:")
    )
    match = re.search(r"Agent\(([^)]*)\)", tools)
    return [item.strip() for item in match.group(1).split(",")] if match else []


class AgentAllowlistTest(unittest.TestCase):
    def test_plugin_agent_allowlist_uses_shipped_namespace_and_keeps_builtins(self) -> None:
        builtins = {"Explore", "Plan", "general-purpose"}
        shipped = {
            f"lane-stack:{path.stem}" for path in AGENTS.glob("*.md")
        }

        allowlist = _agent_allowlist(AGENTS / "dev-orchestrator.md")
        self.assertEqual(set(allowlist) & builtins, builtins)
        self.assertTrue(set(allowlist) - builtins)
        for path in AGENTS.glob("*.md"):
            for name in _agent_allowlist(path):
                if name in builtins:
                    continue
                self.assertTrue(name.startswith("lane-stack:"), path.name)
                self.assertIn(name, shipped, path.name)


if __name__ == "__main__":
    unittest.main()
