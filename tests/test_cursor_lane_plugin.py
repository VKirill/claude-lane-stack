from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "profiles" / "cursor" / "lane-writer"
BEFORE_SHELL = PLUGIN / "scripts" / "before_shell.py"


class CursorLanePluginTest(unittest.TestCase):
    def test_manifest_and_mcp_are_isolated(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "lane-writer")
        mcp = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(set(mcp["mcpServers"]), {"gitnexus", "agentmemory"})
        self.assertTrue((PLUGIN / "agents" / "lane-writer.md").is_file())
        self.assertTrue((PLUGIN / "rules" / "lane-writer.mdc").is_file())

    def test_before_shell_denies_tests_only_on_lane(self) -> None:
        payload = json.dumps({"command": "npm run typecheck"}).encode()
        env = os.environ.copy()
        env.pop("LANE_TASK_FILE", None)
        idle = subprocess.run(
            [sys.executable, str(BEFORE_SHELL)],
            input=payload,
            capture_output=True,
            env=env,
            check=True,
        )
        self.assertEqual(json.loads(idle.stdout)["permission"], "allow")
        env["LANE_TASK_FILE"] = "/tmp/task.yaml"
        blocked = subprocess.run(
            [sys.executable, str(BEFORE_SHELL)],
            input=payload,
            capture_output=True,
            env=env,
            check=True,
        )
        self.assertEqual(json.loads(blocked.stdout)["permission"], "deny")
