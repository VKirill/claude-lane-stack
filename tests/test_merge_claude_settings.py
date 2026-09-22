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
    GITHUB_MARKETPLACE_REPO,
    PLUGIN_ID,
    MARKETPLACE_NAME,
    merge_plugin_marketplace,
    merge_typesafe_key,
    persist_known_marketplace,
    merge_stack_capabilities,
    merge_pm_stop_sentinel,
    merge_subagent_usage,
    merge_teammate_idle,
    merge_gitnexus_hooks,
    install_gitnexus_claude_files,
    GITNEXUS_CLI_PATH_LITERAL,
    GITNEXUS_HOOK_FILES,
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
        self.assertEqual(env["CLAUDE_CODE_ENABLE_FUNCTION_HOOKS"], "1")
        self.assertEqual(env["CLAUDE_CODE_SUBAGENT_MODEL"], "sonnet")
        self.assertEqual(env["ENABLE_TOOL_SEARCH"], "true")
        allow = out["permissions"]["allow"]
        for tool in (
            "SendMessage",
            "ListAgents",
            "TaskStop",
            "Monitor",
            "Artifact",
            "mcp__metamcp",
        ):
            self.assertIn(tool, allow)
        self.assertIn("mcp__gitnexus", allow)
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

    def test_merge_subagent_usage_on_subagent_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "session_ledger.py"
            hook.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            settings: dict = {"hooks": {}}
            out = merge_subagent_usage(settings, hook)
            entries = out["hooks"]["SubagentStop"]
            self.assertEqual(len(entries), 1)
            cmd = entries[0]["hooks"][0]["command"]
            self.assertIn("session_ledger.py usage", cmd)
            out2 = merge_subagent_usage(out, hook)
            self.assertEqual(len(out2["hooks"]["SubagentStop"]), 1)

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

    def test_merge_gitnexus_hooks_official_matchers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "gitnexus-hook.cjs"
            hook.write_text("module.exports = {}\n", encoding="utf-8")
            settings = {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Grep|Glob|Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'node "/old/gitnexus-hook.cjs"',
                                }
                            ],
                        }
                    ],
                    "PostToolUse": [
                        {
                            "matcher": "Bash|Edit|Write|MultiEdit",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": 'node "/old/gitnexus-hook.cjs"',
                                }
                            ],
                        },
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {"type": "command", "command": "/tmp/guardian.sh"}
                            ],
                        },
                    ],
                }
            }
            out = merge_gitnexus_hooks(settings, hook)
            pre = [e for e in out["hooks"]["PreToolUse"] if e.get("matcher") == "Grep|Glob|Bash"]
            self.assertEqual(len(pre), 1)
            self.assertIn("gitnexus-hook.cjs", pre[0]["hooks"][0]["command"])
            self.assertNotIn("/old/", pre[0]["hooks"][0]["command"])
            post_gn = [
                e
                for e in out["hooks"]["PostToolUse"]
                if e.get("matcher") == "Bash"
                and "gitnexus-hook" in e["hooks"][0]["command"]
            ]
            self.assertEqual(len(post_gn), 1)
            self.assertTrue(any(e.get("matcher") == "Edit|Write" for e in out["hooks"]["PostToolUse"]))
            out2 = merge_gitnexus_hooks(out, hook)
            pre2 = [
                e
                for e in out2["hooks"]["PreToolUse"]
                if "gitnexus-hook" in str(e)
            ]
            self.assertEqual(len(pre2), 1)

    def test_install_gitnexus_claude_files_pins_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "gitnexus"
            src = pkg / "hooks" / "claude"
            src.mkdir(parents=True)
            cli = pkg / "dist" / "cli" / "index.js"
            cli.parent.mkdir(parents=True)
            cli.write_text("module.exports = {}\n", encoding="utf-8")
            (src / "gitnexus-hook.cjs").write_text(
                GITNEXUS_CLI_PATH_LITERAL + "\n", encoding="utf-8"
            )
            dest = Path(tmp) / "dest"
            hook = install_gitnexus_claude_files(dest, src)
            self.assertIn("registry-query.cjs", GITNEXUS_HOOK_FILES)
            self.assertIsNotNone(hook)
            text = hook.read_text(encoding="utf-8")
            self.assertNotIn(GITNEXUS_CLI_PATH_LITERAL, text)
            self.assertIn(str(cli.resolve()), text)

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
        settings["enabledPlugins"]["fast-jev-compaction@fast-jev-compaction"] = True
        cleared = merge_plugin_marketplace(settings, ROOT)
        self.assertNotIn("fast-jev-compaction@fast-jev-compaction", cleared["enabledPlugins"])
        hooks = json.loads(
            (ROOT / "plugins" / "lane-stack" / "hooks" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(hooks["modules"], ["./lane-mods.ts"])
        self.assertIn("from './jev-router.js'", (ROOT / "plugins" / "lane-stack" / "hooks" / "lane-mods.ts").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "plugins" / "lane-stack" / "hooks" / "jev-router.ts").is_file())
        self.assertTrue((ROOT / "plugins" / "lane-stack" / "hooks" / "jev-route-core.ts").is_file())
        self.assertIn('"chat.params"', (ROOT / "profiles" / "opencode" / "opencode-lane" / "index.ts").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "profiles" / "opencode" / "opencode-lane.ts").is_file())
        self.assertTrue((ROOT / "profiles" / "opencode" / "opencode-lane" / "index.ts").is_file())
        self.assertIn("winnow serve --ensure", json.dumps(hooks))
        self.assertIn("skillranker-hook.sh", json.dumps(hooks))
        self.assertIn("skill_hint.py", (ROOT / "plugins" / "lane-stack" / "hooks" / "skillranker-hook.sh").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "plugins" / "lane-stack" / "hooks" / "skill_hint.py").is_file())
        self.assertTrue((ROOT / "plugins" / "lane-stack" / "hooks" / "write-skills.json").is_file())
        self.assertTrue(
            (ROOT / "plugins" / "lane-stack" / "fast-jev" / "src" / "compact.ts").is_file()
        )
        self.assertTrue(
            (ROOT / "plugins" / "lane-stack" / "winnow" / "sidecar" / "src" / "winnow" / "serve.py").is_file()
        )
        ours = out["extraKnownMarketplaces"][MARKETPLACE_NAME]
        self.assertEqual(ours["source"]["source"], "github")
        self.assertEqual(ours["source"]["repo"], GITHUB_MARKETPLACE_REPO)
        self.assertTrue(ours["autoUpdate"])
        self.assertNotIn("path", ours["source"])
        self.assertEqual(
            out["extraKnownMarketplaces"]["ponytail"]["source"]["repo"],
            "DietrichGebert/ponytail",
        )

    def test_typesafe_key_from_secrets_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            secrets = Path(raw)
            (secrets / "typesafe.env").write_text(
                "TYPESAFE_API_KEY=fixture-key\n", encoding="utf-8"
            )
            out = merge_typesafe_key({}, secrets)
            self.assertEqual(out["env"]["TYPESAFE_API_KEY"], "fixture-key")
            out["env"]["TYPESAFE_API_KEY"] = "kept"
            (secrets / "typesafe.env").write_text(
                "TYPESAFE_API_KEY=other\n", encoding="utf-8"
            )
            again = merge_typesafe_key(out, secrets)
            self.assertEqual(again["env"]["TYPESAFE_API_KEY"], "kept")
            empty = merge_typesafe_key({}, Path(raw) / "missing")
            self.assertNotIn("TYPESAFE_API_KEY", empty.get("env", {}))

    def test_merge_plugin_marketplace_local(self) -> None:
        out = merge_plugin_marketplace({}, ROOT, local=True)
        ours = out["extraKnownMarketplaces"][MARKETPLACE_NAME]
        self.assertEqual(ours["source"]["path"], str(ROOT))
        self.assertNotIn("autoUpdate", ours)

    def test_persist_known_marketplace_stamps_autoupdate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            claude = Path(raw)
            known = claude / "plugins" / "known_marketplaces.json"
            known.parent.mkdir(parents=True)
            known.write_text(
                json.dumps(
                    {
                        "ponytail": {
                            "source": {
                                "source": "github",
                                "repo": "DietrichGebert/ponytail",
                            },
                            "installLocation": "/tmp/ponytail",
                        },
                        MARKETPLACE_NAME: {
                            "source": {
                                "source": "directory",
                                "path": "/tmp/old-lane",
                            },
                            "installLocation": "/tmp/old-lane",
                        },
                    }
                ),
                encoding="utf-8",
            )
            persist_known_marketplace(claude, local=False, stack_root=ROOT)
            data = json.loads(known.read_text(encoding="utf-8"))
            ours = data[MARKETPLACE_NAME]
            self.assertEqual(ours["source"]["repo"], GITHUB_MARKETPLACE_REPO)
            self.assertTrue(ours["autoUpdate"])
            self.assertEqual(ours["installLocation"], "/tmp/old-lane")
            self.assertEqual(
                data["ponytail"]["source"]["repo"], "DietrichGebert/ponytail"
            )


if __name__ == "__main__":
    unittest.main()
