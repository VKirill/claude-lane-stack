from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from merge_claude_settings import (  # noqa: E402
    merge_stack_capabilities,
    merge_teammate_idle,
    load_settings,
    write_settings,
)


class MergeStackCapabilitiesTests(unittest.TestCase):
    def test_env_defaults_and_tools(self) -> None:
        settings: dict = {"theme": "dark", "permissions": {"allow": ["Bash(*)"]}}
        out = merge_stack_capabilities(settings)
        self.assertEqual(out["theme"], "dark")
        env = out["env"]
        self.assertEqual(env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "1")
        self.assertEqual(env["ENABLE_TOOL_SEARCH"], "true")
        allow = out["permissions"]["allow"]
        for tool in ("SendMessage", "ListAgents", "TaskStop", "Monitor", "Artifact"):
            self.assertIn(tool, allow)
        # idempotent
        out2 = merge_stack_capabilities(out)
        self.assertEqual(allow.count("SendMessage"), 1)
        self.assertIs(out2, out)

    def test_does_not_clobber_user_env(self) -> None:
        settings = {
            "env": {
                "ENABLE_TOOL_SEARCH": "false",
                "CUSTOM": "1",
            }
        }
        out = merge_stack_capabilities(settings)
        self.assertEqual(out["env"]["ENABLE_TOOL_SEARCH"], "false")
        self.assertEqual(out["env"]["CUSTOM"], "1")
        self.assertIn("MCP_TIMEOUT", out["env"])

    def test_cross_session_inbound_opt_in(self) -> None:
        settings: dict = {}
        os.environ["LANE_CROSS_SESSION_INBOUND"] = "accept"
        os.environ["LANE_CROSS_SESSION_DIALOG_EXPIRY"] = "10"
        try:
            out = merge_stack_capabilities(settings)
            self.assertEqual(out["crossSessionInbound"], "accept")
            self.assertEqual(out["dialogExpiry"], 10)
        finally:
            os.environ.pop("LANE_CROSS_SESSION_INBOUND", None)
            os.environ.pop("LANE_CROSS_SESSION_DIALOG_EXPIRY", None)

    def test_roundtrip_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            settings = merge_stack_capabilities({"permissions": {"allow": []}})
            write_settings(path, settings)
            loaded = load_settings(path)
            self.assertIn("SendMessage", loaded["permissions"]["allow"])

    def test_merge_teammate_idle_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "teammate_idle_sentinel.py"
            hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            settings: dict = {"hooks": {}}
            out = merge_teammate_idle(settings, hook)
            entries = out["hooks"]["TeammateIdle"]
            self.assertEqual(len(entries), 1)
            cmd = entries[0]["hooks"][0]["command"]
            self.assertIn("teammate_idle_sentinel.py", cmd)
            out2 = merge_teammate_idle(out, hook)
            self.assertEqual(len(out2["hooks"]["TeammateIdle"]), 1)


if __name__ == "__main__":
    unittest.main()
