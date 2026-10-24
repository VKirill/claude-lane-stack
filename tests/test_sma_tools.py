"""The SMA-map tools of Lane Stack: lane-plan, the new lane-memory verbs, the forge lint, role lines, the settings strip, subagent rules."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(BIN))
sys.path.insert(0, str(ROOT / "hooks"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = load("lane_plan", BIN / "lane-plan")
forge = load("lane_forge_lint", BIN / "lane-forge-lint")
import lane_memory as lm  # noqa: E402
import lane_role_lines as roles  # noqa: E402
import merge_claude_settings as merge  # noqa: E402


class LanePlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def test_roadmap_phases_uat_and_query(self) -> None:
        plan.phase_add(self.repo, "Login", "users sign in")
        plan.phase_add(self.repo, "Billing", "")
        row = plan.phase_add(self.repo, "Login fixes", "", after="1")
        self.assertEqual(row["n"], "1.1")
        plan.fill(self.repo, "UAT", phase="1", form=None, values={}, force=False)
        # An empty UAT is not a passed acceptance.
        with self.assertRaises(ValueError):
            plan.phase_complete(self.repo, "1")
        uat = plan.phase_folder(self.repo, "1") / "UAT.md"
        uat.write_text(uat.read_text().replace("- [ ] ", "- [x] sign in works"), encoding="utf-8")
        self.assertTrue(plan.phase_complete(self.repo, "1")["done"])
        self.assertEqual(plan.query(self.repo, "roadmap.next")["n"], "1.1")
        plan.phase_edit(self.repo, "2", "Payments", "pay")
        self.assertEqual(plan.query(self.repo, "phase.2.name"), "Payments")
        archived = plan.milestone_archive(self.repo, "v1")
        self.assertIn("Login", archived.read_text())
        self.assertNotIn("Login —", plan.roadmap_path(self.repo).read_text())

    def test_notes_inbox_wrap_and_state(self) -> None:
        plan.jot(self.repo, "note", "logo too big")
        plan.jot(self.repo, "seed", "dark mode")
        spike = plan.new_item(self.repo, "spike", "lazy images")
        self.assertEqual(plan.inbox(self.repo)["seeds"][-1].split(" ", 1)[1], "dark mode")
        spike.write_text(spike.read_text() + "\n## Decision\n\nuse loading=lazy\n", encoding="utf-8")
        draft = plan.wrap(self.repo, "spike", str(spike), "Lazy images")
        self.assertIn("name: lazy-images", draft.read_text())
        self.assertEqual(plan.state_set(self.repo, "phase", "1.1")["phase"], "1.1")


class LaneMemoryCareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.ts").write_text("x")
        lm.init_corpus(self.repo)
        (lm.corpus_dir(self.repo) / "n1.md").write_text(
            "---\nid: n1\nclaim: src/app.ts keeps the router\nmemory_type: semantic\ntruth_mode: factual\nstatus: active\nsensitivity: internal\n"
            "context_priority: normal\nretrieval:\n  areas: [router]\n  triggers: [router]\n---\nbody\n", encoding="utf-8")

    def test_mask_card_citations_fragments_and_miss(self) -> None:
        self.assertEqual(lm.mask_secrets("api_key=abc123 ok"), "[secret] ok")
        self.assertEqual([n["id"] for n in lm.card(self.repo, "src/app.ts")], ["n1"])
        self.assertEqual(lm.citations(self.repo)["n1"]["via"], {"card": 1})
        self.assertEqual([r["id"] for r in lm.fragments_for(self.repo, "the router setup")], ["n1"])
        self.assertEqual(lm.miss(self.repo, "where is the router", ["n1"])["must"], ["n1"])
        with self.assertRaises(ValueError):
            lm.miss(self.repo, "where is the router", ["n1"])
        self.assertIn("lane-memory:catalog", lm.emit(self.repo))
        self.assertTrue(any("n1" in line for line in lm.migrate(self.repo)))


class ForgeLintTest(unittest.TestCase):
    def test_lint(self) -> None:
        good = "---\nname: lazy-images\ndescription: Lazy-load product photos so switching stays fast. Use when photos load slowly.\n---\nsteps\n"
        self.assertEqual(forge.lint("skill", "lazy-images", good), [])
        self.assertTrue(any(f.startswith("forbidden_grant") for f in forge.lint("skill", "lazy-images", good + "tools: *\n")))
        self.assertEqual(forge.lint("workflow", "w", '{"id":"w","nodes":[1],"entry":"a","description":"d"}'), [])


class RoleLinesAndSettingsTest(unittest.TestCase):
    def test_appended_lines_survive_and_gsd_aliases_toggle(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        agents, stash, commands = tmp / "a", tmp / "s", tmp / "c"
        agents.mkdir()
        (agents / "r.md").write_text(f"v1\n\n{roles.MARK}\nmine\n")
        roles.save(agents, stash)
        (agents / "r.md").write_text("v2\n")
        roles.restore(agents, stash)
        self.assertIn("mine", (agents / "r.md").read_text())
        self.assertTrue((agents / "r.md").read_text().startswith("v2"))
        roles.gsd(commands, True)
        self.assertTrue((commands / "gsd-debug.md").exists())
        roles.gsd(commands, False)
        self.assertFalse((commands / "gsd-debug.md").exists())

    def test_strip_stack_keeps_foreign_hooks(self) -> None:
        settings = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /x/guard_shell.py"}, {"type": "command", "command": "my-own-hook"}]}]},
                    "statusLine": {"type": "command", "command": "python3 /x/lane-statusline"}, "enabledPlugins": {merge.PLUGIN_ID: True}}
        stripped, done = merge.strip_stack(settings)
        self.assertEqual(stripped["hooks"]["PreToolUse"][0]["hooks"], [{"type": "command", "command": "my-own-hook"}])
        self.assertNotIn(merge.PLUGIN_ID, stripped["enabledPlugins"])
        self.assertTrue(done)


class SubagentRulesTest(unittest.TestCase):
    def test_writer_gets_only_documentary_subagents_and_no_background(self) -> None:
        sma = load("sma_hooks_t", ROOT / "hooks" / "sma_hooks.py")
        os.environ["LANE_PILOT_ROLE"] = "writer"
        try:
            refused = sma.pretask_pack({}, {"subagent_type": "general-purpose", "prompt": "x"}, "s-test", str(ROOT))
            self.assertEqual(refused["hookSpecificOutput"]["permissionDecision"], "deny")
            allowed = sma.pretask_pack({}, {"subagent_type": "Explore", "prompt": "x"}, "s-test2", str(ROOT))
            self.assertNotEqual((allowed or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        finally:
            del os.environ["LANE_PILOT_ROLE"]
        background = sma.pretask_pack({}, {"subagent_type": "Explore", "prompt": "x", "run_in_background": True}, "s-test3", str(ROOT))
        self.assertIn("foreground", background["hookSpecificOutput"]["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
