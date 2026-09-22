from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "lane-stack" / "hooks" / "jev-route-core.ts"
INDEX = ROOT / "profiles" / "opencode" / "opencode-lane" / "index.ts"
WRAPPER = ROOT / "profiles" / "opencode" / "opencode-lane.ts"


def _node(script: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["LANE_LOG"] = "0"
    env["LANE_LOG_SRC"] = "test"
    return subprocess.run(
        ["node", "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


class JevRouteTest(unittest.TestCase):
    def test_apply_policy_and_model_suffix(self) -> None:
        script = (
            "import { assertRoutePolicy } from "
            f"{CORE.resolve().as_uri()!r}; "
            "assertRoutePolicy(); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_claude_and_opencode_wire_the_router(self) -> None:
        mods = (ROOT / "plugins" / "lane-stack" / "hooks" / "lane-mods.ts").read_text(
            encoding="utf-8"
        )
        router = (ROOT / "plugins" / "lane-stack" / "hooks" / "jev-router.ts").read_text(
            encoding="utf-8"
        )
        wrapper = WRAPPER.read_text(encoding="utf-8")
        oc = INDEX.read_text(encoding="utf-8")
        sticky = (ROOT / "profiles" / "opencode" / "opencode-lane" / "sticky.ts").read_text(
            encoding="utf-8"
        )
        self.assertIn("registerRouter", mods)
        self.assertIn("turn.step", router)
        self.assertIn("agent.spawn", router)
        self.assertEqual(router.count("{ ...e, model:"), 1)
        self.assertIn("yield* next({ ...e, effort: route.effort })", router)
        self.assertIn("model: route.subagent", router)
        self.assertIn("chat.params", oc)
        self.assertIn("OpenCodeLanePlugin", oc)
        self.assertIn("export { default }", wrapper)
        self.assertNotIn("STICKY_MARK", wrapper)
        self.assertIn("./opencode-lane/index.ts", wrapper)
        self.assertIn("swapModelEffort", oc)
        self.assertIn("LANE_JEV_EFFORT", oc)
        self.assertIn("LANE_JEV_EFFORT", router)
        self.assertIn("STICKY_MARK", sticky)
        self.assertIn("ensureStickyMessages", sticky)
        self.assertIn("LANE_TASK_FILE", sticky)
        self.assertIn("diagnoseFailure", oc)
        self.assertIn("skillHint", oc)
        self.assertIn("evidenceNotes", oc)
        self.assertIn("recordTool", oc)
        self.assertIn("sessionKey", oc)
        self.assertIn("laneLog", oc)
        install = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('opencode-lane/"*.ts', install)
        self.assertIn('rm -f "$HOME/.config/opencode/plugins/lane-context.ts"', install)
        hook = (ROOT / "plugins" / "lane-stack" / "hooks" / "skillranker-hook.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("skill_hint.py", hook)
        catalog = json.loads(
            (ROOT / "plugins" / "lane-stack" / "hooks" / "write-skills.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("writer-practices", catalog)

    def test_plugin_default_export_is_the_only_export(self) -> None:
        script = (
            "import plugin from "
            f"{WRAPPER.resolve().as_uri()!r}; "
            "import * as mod from "
            f"{WRAPPER.resolve().as_uri()!r}; "
            "if (typeof plugin !== 'function') throw new Error('default'); "
            "const extra = Object.keys(mod).filter((k) => k !== 'default'); "
            "if (extra.length) throw new Error('named ' + extra.join(',')); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_sticky_contract_replaces_prior_block(self) -> None:
        script = (
            "import { ensureStickyMessages, STICKY_MARK } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const messages = ["
            "  { info: { role: 'user' }, parts: [{ type: 'text', text: STICKY_MARK + '\\nold' }] },"
            "  { info: { role: 'assistant' }, parts: [{ type: 'text', text: 'ok' }] }"
            "]; "
            "ensureStickyMessages(messages, STICKY_MARK + '\\nnew'); "
            "if (messages.length !== 2) throw new Error('len ' + messages.length); "
            "if (!messages[1].parts[0].text.endsWith('new')) throw new Error('sticky'); "
            "if (messages[0].parts[0].text !== 'ok') throw new Error('kept'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_looks_failed_and_parse_acceptance(self) -> None:
        script = (
            "import { looksFailed, parseAcceptance } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "if (!looksFailed('AssertionError: expected 1')) throw new Error('fail'); "
            "if (looksFailed('compiled ok')) throw new Error('ok-false'); "
            "const items = parseAcceptance('owns_paths: [a]\\nacceptance:\\n  - first\\n  - second\\nnever_touch: [b]\\n'); "
            "if (items.join(',') !== 'first,second') throw new Error(String(items)); "
            "const five = parseAcceptance('acceptance:\\n  - a\\n  - b\\n  - c\\n  - d\\n  - e\\n'); "
            "if (five.join(',') !== 'a,b,c,d,e') throw new Error(String(five)); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_budget_fingerprint_counts_duplicates(self) -> None:
        script = (
            "import { toolFingerprint, recordTool } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const a = { command: 'pytest tests/test_x.py' }; "
            "const out = 'FAILED tests/test_x.py::test_x'; "
            "const fp = toolFingerprint('bash', a, out); "
            "if (fp !== toolFingerprint('bash', a, out)) throw new Error('stable'); "
            "if (fp === toolFingerprint('bash', a, out + '!')) throw new Error('hash'); "
            "const s = 'sess-budget'; "
            "const first = recordTool(s, 'bash', a, out); "
            "const second = recordTool(s, 'bash', a, out); "
            "if (first.n !== 1 || second.n !== 2) throw new Error(String(second.n)); "
            "if (first.fp !== second.fp) throw new Error('fp'); "
            "const head = 'x'.repeat(9000); "
            "const fail = head + '\\nFAILED'; "
            "const pass = head + '\\nPASSED'; "
            "if (toolFingerprint('bash', a, fail) === toolFingerprint('bash', a, pass)) throw new Error('tail'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_session_key_does_not_collapse_to_empty(self) -> None:
        script = (
            "import { sessionKey } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "if (sessionKey({}) !== 'unknown') throw new Error('empty-input ' + sessionKey({})); "
            "if (sessionKey({ sessionID: 'ses_a' }) !== 'ses_a') throw new Error('direct'); "
            "const prompts = new Map([['ses_b', 'fix the login form']]); "
            "const messages = [{ info: { role: 'user' }, parts: [{ type: 'text', text: 'please fix the login form now' }] }]; "
            "if (sessionKey({}, messages, prompts) !== 'ses_b') throw new Error('prompt-match'); "
            "const other = [{ info: { role: 'user' }, parts: [{ type: 'text', text: 'unrelated session prompt xyz' }] }]; "
            "const a = sessionKey({}, other, new Map()); "
            "const b = sessionKey({}, messages, new Map()); "
            "if (a === b) throw new Error('collided'); "
            "if (!a.startsWith('msg:')) throw new Error(a); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_bash_evidence_keeps_prior_test_output(self) -> None:
        script = (
            "import { collectBashEvidence } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const messages = ["
            "  { parts: [{ type: 'tool', tool: 'bash', state: { input: { command: 'pytest a.py' }, "
            "    output: '===== 1 passed in 0.1s ===== extra padding pad' } }] },"
            "  { parts: [{ type: 'tool', tool: 'read', state: { output: 'src file contents that are long enough xx' } }] }"
            "]; "
            "const text = collectBashEvidence(messages); "
            "if (!text.includes('1 passed')) throw new Error(text); "
            "if (text.includes('src file contents')) throw new Error('read-leaked'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_skill_phase_changes_with_recent_tools(self) -> None:
        script = (
            "import { skillPhase, askCacheKey } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const a = skillPhase('fix the login form', ['read']); "
            "const b = skillPhase('fix the login form', ['read', 'bash']); "
            "if (a === b) throw new Error('phase'); "
            "if (skillPhase('fix the login form', ['read']) !== a) throw new Error('stable'); "
            "const k = askCacheKey({ t: 1 }, { q: 2 }); "
            "if (k !== askCacheKey({ t: 1 }, { q: 2 })) throw new Error('cache'); "
            "if (k === askCacheKey({ t: 2 }, { q: 2 })) throw new Error('diff'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_skill_hint_hook_is_fail_open(self) -> None:
        hint = ROOT / "plugins" / "lane-stack" / "hooks" / "skill_hint.py"
        out = subprocess.run(
            ["python3", str(hint)],
            cwd=ROOT,
            input="",
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, "")


if __name__ == "__main__":
    unittest.main()
