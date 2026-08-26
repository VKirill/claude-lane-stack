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
    PLUGIN_ID,
    MARKETPLACE_NAME,
    merge_plugin_marketplace,
    merge_stack_capabilities,
    merge_pm_stop_sentinel,
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

    def test_merge_pm_stop_keeps_other_stop_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "pm_stop_sentinel.py"
            hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            settings = {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 /tmp/session_ledger.py flush",
                                }
                            ]
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {"type": "command", "command": "/tmp/guardian.sh"}
                            ],
                        }
                    ],
                }
            }
            out = merge_pm_stop_sentinel(settings, hook)
            stop_cmds = [
                h["command"]
                for e in out["hooks"]["Stop"]
                for h in e.get("hooks", [])
                if isinstance(h, dict)
            ]
            self.assertTrue(any("session_ledger.py" in c for c in stop_cmds))
            self.assertTrue(any("pm_stop_sentinel.py" in c for c in stop_cmds))
            post = out["hooks"]["PostToolUse"]
            self.assertTrue(any(e.get("matcher") == "Edit|Write" for e in post))
            ours = [e for e in post if e.get("matcher") == "Agent|Task"]
            self.assertEqual(len(ours), 1)
            self.assertTrue(ours[0]["hooks"][0]["asyncRewake"])
            out2 = merge_pm_stop_sentinel(out, hook)
            stop_cmds2 = [
                h["command"]
                for e in out2["hooks"]["Stop"]
                for h in e.get("hooks", [])
                if isinstance(h, dict) and "pm_stop_sentinel.py" in str(h.get("command"))
            ]
            self.assertEqual(len(stop_cmds2), 1)

    def test_merge_plugin_marketplace(self) -> None:
        settings = {
            "enabledPlugins": {"ponytail@ponytail": True},
            "extraKnownMarketplaces": {
                "ponytail": {"source": {"source": "github", "repo": "DietrichGebert/ponytail"}}
            },
        }
        out = merge_plugin_marketplace(settings, ROOT)
        self.assertTrue(out["enabledPlugins"]["ponytail@ponytail"])
        self.assertTrue(out["enabledPlugins"][PLUGIN_ID])
        self.assertEqual(
            out["extraKnownMarketplaces"][MARKETPLACE_NAME]["source"]["path"],
            str(ROOT),
        )
        self.assertEqual(
            out["extraKnownMarketplaces"]["ponytail"]["source"]["repo"],
            "DietrichGebert/ponytail",
        )


if __name__ == "__main__":
    unittest.main()
