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
    def test_opencode_routes_the_task_after_the_writer_contract(self) -> None:
        out = _node(f"""
            import {{ OpenCodeLanePlugin }} from {INDEX.as_uri()!r};
            import assert from 'node:assert/strict';
            process.env.LANE_OPENCODE_JEV = '0';
            process.env.LANE_JEV_EFFORT = '1';
            process.env.TYPESAFE_API_KEY = 'fixture-key';
            process.env.LANE_STACK_ROOT = {str(ROOT)!r};
            const tasks = [];
            globalThis.fetch = async (url, request) => {{
                if (String(url).endsWith('/health')) return new Response('ok');
                const body = JSON.parse(request.body);
                tasks.push(body.state.task);
                return new Response(JSON.stringify({{ answers: {{
                    tier: {{ choice: 'standard', confidence: 0.9 }},
                    effort: {{ choice: 'high', confidence: 0.9 }},
                    risk: {{ noul: 0.1 }}
                }} }}));
            }};
            const hooks = await OpenCodeLanePlugin();
            const input = {{ sessionID: 'same-warm-session' }};
            const prefix = 'GENERAL WRITER INSTRUCTIONS\\n'.repeat(250);
            const marker = '\\n--- RAW TASK YAML (verbatim) ---\\n';
            async function route(text) {{
                await hooks['chat.message'](input, {{ parts: [
                    {{ type: 'text', text }},
                    {{ type: 'text', text: 'synthetic noise', synthetic: true }}
                ] }});
                const params = {{ options: {{}} }};
                const model = {{ id: 'cursor-acp/grok-4.7-medium' }};
                await hooks['chat.params']({{ ...input, model }}, params);
                assert.equal(model.id, 'cursor-acp/grok-4.7-high');
                return tasks.at(-1);
            }}
            const first = 'schema_version: 2\\nid: "001"\\nrisk: low\\n' +
                'read_first:\\n' + '  - context.ts\\n'.repeat(150) +
                'objective: Forward templateData.shareChat\\nacceptance: [preserve preview]';
            assert.equal(await route(prefix + marker + first), first);
            const second = 'schema_version: 2\\nid: "002"\\nrisk: high\\n' +
                'objective: Resolve concurrent lease fencing\\nowns_paths: [lease.ts]';
            assert.equal(await route(prefix + marker + second), second);
            assert.equal(tasks.length, 2, 'a new task in a warm session must be reclassified');
            await route(prefix + marker + second);
            assert.equal(tasks.length, 2, 'unchanged task keeps the cached route');
            assert.equal(await route('Fix the local typo'), 'Fix the local typo');
            const large = 'schema_version: 2\\n' + 'a'.repeat(15000) + '\\nobjective: Keep this goal';
            assert.equal(await route(prefix + marker + large), large);
            assert.ok(tasks.every(task => !task.includes('GENERAL WRITER') && !task.includes('synthetic noise')));
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_opencode_transform_preserves_large_history_without_compaction(self) -> None:
        env = os.environ.copy()
        env["LANE_LOG"] = "0"
        env["LANE_LOG_SRC"] = "test"
        out = subprocess.run(
            ["bun", "-e", f"""
            import {{ OpenCodeLanePlugin }} from {INDEX.as_uri()!r};
            import {{ mkdtempSync, writeFileSync, rmSync }} from 'node:fs';
            import assert from 'node:assert/strict';
            process.env.LANE_OPENCODE_JEV = '1';
            process.env.TYPESAFE_API_KEY = 'fixture-key';
            process.env.LANE_STACK_ROOT = {str(ROOT)!r};
            const dir = mkdtempSync('/tmp/opencode-no-history-compact-');
            process.env.LANE_TASK_FILE = dir + '/task.yaml';
            writeFileSync(process.env.LANE_TASK_FILE, 'acceptance:\\n  - preserve tool output\\n');
            const requests = [];
            globalThis.fetch = async (url, request) => {{
                if (String(url).endsWith('/health')) return new Response('ok');
                requests.push(JSON.parse(request.body));
                return new Response(JSON.stringify({{ answers: {{
                    c0: {{ choice: 'supports', confidence: 1 }},
                    call_t1: {{ noul: 0 }}, result_t1: {{ noul: 0 }}
                }} }}));
            }};
            try {{
                const hooks = await OpenCodeLanePlugin();
                const toolOutput = 'pytest\\n3 passed\\n'.repeat(2500);
                const messages = Array.from({{ length: 10 }}, (_, i) => ({{
                    info: {{ role: i % 2 ? 'assistant' : 'user' }},
                    parts: [{{ type: 'text', text: 'history ' + i }}]
                }}));
                messages[1] = {{
                    info: {{ role: 'assistant' }},
                    parts: [{{
                        type: 'tool', tool: 'bash', callID: 'call-large-history',
                        state: {{ status: 'completed', input: {{ command: 'printf x' }}, output: toolOutput }}
                    }}]
                }};
                const before = JSON.stringify(messages.slice(0, 10));
                const originalToolOutput = messages[1].parts[0].state.output;
                await hooks['experimental.chat.messages.transform'](
                    {{ sessionID: 'large-history-no-compact' }}, {{ messages }}
                );
                assert.equal(JSON.stringify(messages.slice(0, 10)), before);
                assert.equal(messages[1].parts[0].state.output, originalToolOutput);
                assert.equal(requests.length, 1, 'evidence may ask Jev, history compaction must not');
                assert.ok(requests[0].state.criteria);
                assert.ok(messages.some(message => message.parts.some(part =>
                    part.synthetic && part.text.includes('LANE CONTRACT (live)'))));
                assert.ok(messages.some(message => message.parts.some(part =>
                    typeof part.text === 'string' &&
                    part.text.includes('all listed acceptance criteria have supporting tool output'))));
            }} finally {{
                rmSync(dir, {{ recursive: true, force: true }});
            }}
        """],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_diagnosis_requires_failed_exit_not_error_words(self) -> None:
        diagnose = ROOT / "profiles/opencode/opencode-lane/diagnose.ts"
        out = _node(f"""
            import {{ diagnoseFailure }} from {diagnose.as_uri()!r};
            import assert from 'node:assert/strict';
            process.env.LANE_OPENCODE_JEV = '1';
            process.env.TYPESAFE_API_KEY = 'fixture-key';
            process.env.TEST_SECRET = 'private-env-value';
            process.env.LANE_STACK_ROOT = {str(ROOT)!r};
            let calls = 0;
            globalThis.fetch = async (_url, request) => {{
                calls++;
                for (const secret of ['private-env-value', 'private-password']) {{
                    assert.ok(!request.body.includes(secret), 'credential reached Jev');
                }}
                return new Response(JSON.stringify({{ answers: {{
                    kind: {{ choice: 'code', confidence: 0.9 }}
                }} }}));
            }};
            const source = 'expect(result.error).toBe("failed"); // AssertionError';
            for (const exit of [undefined, null, 0, '1', NaN, Infinity, 1.5]) {{
                assert.equal(await diagnoseFailure('fix test', source, exit), '');
            }}
            assert.equal(await diagnoseFailure('fix test', 'private document contents', 1), '');
            assert.equal(calls, 0, 'successful reads must not spend tokens on diagnosis');
            assert.match(await diagnoseFailure('fix private-env-value',
                'AssertionError: expected 1, got 2 password=private-password', 1), /diagnose.*code/);
            assert.equal(calls, 1);
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_jev_consumers_keep_full_tasks_results_and_criteria(self) -> None:
        modules = ROOT / "profiles/opencode/opencode-lane"
        out = _node(f"""
            import {{ skillHint, skillPhase }} from {(modules / 'skill-hint.ts').as_uri()!r};
            import {{ recordTool, recentAttempts, repeatHint }} from {(modules / 'budget.ts').as_uri()!r};
            import {{ evidenceNotes }} from {(modules / 'evidence.ts').as_uri()!r};
            import {{ diagnoseFailure }} from {(modules / 'diagnose.ts').as_uri()!r};
            import {{ mkdtempSync, writeFileSync, rmSync }} from 'node:fs';
            import assert from 'node:assert/strict';
            process.env.LANE_STACK_ROOT = {str(ROOT)!r};
            process.env.LANE_OPENCODE_JEV = '1';
            process.env.TYPESAFE_API_KEY = 'fixture-key';
            process.env.TEST_SECRET = 'private-test-value';
            const task = 'Task context\\n'.repeat(2000) + 'FINAL GOAL';
            const result = 'Earlier test output\\n'.repeat(1000) + 'AssertionError: LAST FAILURE';
            const requests = [];
            globalThis.fetch = async (_url, request) => {{
                requests.push(JSON.parse(request.body));
                return new Response(JSON.stringify({{ answers: {{
                    need: {{ noul: 0 }}, skill: {{ choice: 'none', confidence: 1 }},
                    kind: {{ choice: 'same_loop', confidence: 1 }}
                }} }}));
            }};
            assert.notEqual(skillPhase(task), skillPhase(task + 'CHANGED'));
            await skillHint('full-skills', task);
            const afterFirstHint = requests.length;
            await skillHint('full-skills', task, ['read']);
            await skillHint('full-skills', task, ['grep', 'shell']);
            assert.equal(requests.length, afterFirstHint, 'skill hint must not re-ask on every tool');
            assert.equal(requests.at(-1).state.task, task);
            await diagnoseFailure(task, result + ' password=private-test-value', 1);
            assert.equal(requests.at(-1).state.task, task);
            assert.ok(requests.at(-1).state.output.includes('LAST FAILURE'));
            assert.ok(!requests.at(-1).state.output.includes('private-test-value'));
            const command = 'long command '.repeat(100) + 'FINAL ARGUMENT';
            for (let i = 0; i < 10; i++) recordTool('full-budget', 'shell', {{ command }}, result + i);
            assert.equal(recentAttempts('full-budget').length, 10);
            await repeatHint(task, 'shell', result, 3, 'full-budget');
            assert.equal(requests.at(-1).state.output, result);
            assert.equal(requests.at(-1).state.prior.length, 10);
            assert.ok(requests.at(-1).state.prior[0].cmd.endsWith('FINAL ARGUMENT|'));
            assert.equal(requests.at(-1).state.prior[0].tail, result + '0');
            const dir = mkdtempSync('/tmp/lane-evidence-full-');
            try {{
                process.env.LANE_TASK_FILE = dir + '/task.yaml';
                const yaml = 'acceptance:\\n' + Array.from({{ length: 12 }}, (_, i) => '  - criterion ' + i).join('\\n');
                writeFileSync(process.env.LANE_TASK_FILE, yaml);
                const messages = Array.from({{ length: 7 }}, (_, i) => ({{ parts: [{{
                    type: 'tool', tool: 'shell', state: {{ input: {{ command }}, output: result }}
                }}] }}));
                await evidenceNotes('full-evidence', messages);
                const state = requests.at(-1).state;
                assert.equal(state.criteria.length, 12);
                assert.ok(state.evidence.includes('LAST FAILURE'));
                assert.ok(state.evidence.length <= 4000);
                const count = requests.length;
                writeFileSync(process.env.LANE_TASK_FILE, yaml + '\\n  - new acceptance criterion');
                await evidenceNotes('full-evidence', messages);
                assert.equal(requests.length, count + 1);
                assert.equal(requests.at(-1).state.criteria.length, 13);
            }} finally {{ rmSync(dir, {{ recursive: true, force: true }}); }}
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_lane_log_preserves_async_session_and_redacts_errors(self) -> None:
        log = ROOT / "profiles/opencode/opencode-lane/log.ts"
        out = _node(f"""
            import {{ laneLog, withLaneSession, setLaneLogSink }} from {log.as_uri()!r};
            import {{ mkdtempSync, readFileSync, rmSync }} from 'node:fs';
            import {{ tmpdir }} from 'node:os';
            import assert from 'node:assert/strict';
            const root = mkdtempSync(tmpdir() + '/lane-log-session-');
            try {{
                process.env.HOME = root;
                process.env.LANE_PROMPT_FILE = root + '/prompt.md';
                process.env.LANE_LOG = '1';
                process.env.TEST_API_KEY = 'private-test-key';
                const native = [];
                setLaneLogSink((row) => {{ native.push(row); return Promise.reject(new Error('offline')); }});
                await Promise.all(['one', 'two'].map((id) => withLaneSession(id, async () => {{
                    await new Promise(resolve => setTimeout(resolve, id === 'one' ? 10 : 1));
                    laneLog({{ mod: id, ok: false, err: 'failed private-test-key Bearer other-token',
                        data: {{ password: 'hidden', url: 'https://user:pass@example.com' }} }});
                }})));
                const raw = readFileSync(root + '/opencode-lane.jsonl', 'utf8');
                for (const secret of ['private-test-key', 'other-token', 'hidden', 'user:pass']) assert.ok(!raw.includes(secret));
                const rows = raw.trim().split('\\n').map(JSON.parse);
                assert.equal(rows.length, 2);
                for (const row of rows) assert.equal(row.session, row.mod);
                assert.equal(native.length, 2);
                assert.ok(!JSON.stringify(native).includes('private-test-key'));
            }} finally {{ rmSync(root, {{ recursive: true, force: true }}); }}
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_lane_log_falls_back_when_attempt_directory_is_unwritable(self) -> None:
        log = ROOT / "profiles/opencode/opencode-lane/log.ts"
        out = _node(f"""
            import {{ laneLog, setLaneSession }} from {log.as_uri()!r};
            import {{ mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync }} from 'node:fs';
            import {{ tmpdir }} from 'node:os';
            import assert from 'node:assert/strict';
            const root = mkdtempSync(tmpdir() + '/lane-log-');
            try {{
                process.env.HOME = root;
                process.env.LANE_LOG = '1';
                process.env.LANE_TASK_FILE = root + '/runs/demo/tasks/001.yaml';
                process.env.LANE_PROMPT_FILE = root + '/attempt/prompt.md';
                setLaneSession('session-one');
                laneLog({{ mod: 'budget', ok: true }});
                const primary = JSON.parse(readFileSync(root + '/attempt/opencode-lane.jsonl', 'utf8'));
                assert.equal(primary.session, 'session-one');
                // A file in place of the parent reliably simulates an unwritable destination,
                // even when tests run as root (chmod alone would not).
                writeFileSync(root + '/blocked', '');
                process.env.LANE_PROMPT_FILE = root + '/blocked/prompt.md';
                laneLog({{ mod: 'budget', ok: true }});
                const fallback = root + '/.config/opencode/opencode-lane.jsonl';
                const row = JSON.parse(readFileSync(fallback, 'utf8'));
                assert.equal(row.task, '001');
                assert.equal(row.session, 'session-one');
                assert.equal(row.log_origin, root + '/blocked/opencode-lane.jsonl');
                process.env.LANE_LOG = '0';
                laneLog({{ mod: 'budget', ok: true }});
                assert.equal(readFileSync(fallback, 'utf8').trim().split('\\n').length, 1);
                process.env.LANE_LOG = '1';
                process.env.HOME = root + '/blocked';
                assert.doesNotThrow(() => laneLog({{ mod: 'budget', ok: true }}));
            }} finally {{ rmSync(root, {{ recursive: true, force: true }}); }}
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

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
        self.assertIn("claudeSessionEffort", router)
        self.assertIn("yield* next({ ...e, effort: nextEffort })", router)
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
        self.assertIn("dumpedToolNote", sticky)
        self.assertIn("LANE_TASK_FILE", sticky)
        self.assertIn("dumpedToolNote", oc)
        self.assertIn("lastAssistantText", oc)
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
            "import { ensureStickyMessages, formatStickyContract, STICKY_MARK } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const messages = ["
            "  { info: { role: 'user' }, parts: [{ type: 'text', text: STICKY_MARK + '\\nold' }] },"
            "  { info: { role: 'assistant' }, parts: [{ type: 'text', text: 'ok' }] }"
            "]; "
            "ensureStickyMessages(messages, STICKY_MARK + '\\nnew'); "
            "if (messages.length !== 2) throw new Error('len ' + messages.length); "
            "if (!messages[1].parts[0].text.endsWith('new')) throw new Error('sticky'); "
            "if (messages[0].parts[0].text !== 'ok') throw new Error('kept'); "
            "const task = 'x'.repeat(20000) + 'TAIL'; "
            "if (!formatStickyContract(task, 'task.yaml').endsWith(task)) throw new Error('cut task'); "
            "const looped = 'keep\\n- HARD RULE: git checkout -- file and redo\\n- git restore -- file\\nkeep2'; "
            "const stripped = formatStickyContract(looped, 'task.yaml'); "
            "if (stripped.includes('git checkout')) throw new Error('kept checkout'); "
            "if (stripped.includes('git restore')) throw new Error('kept restore'); "
            "if (!stripped.includes('keep2')) throw new Error('dropped body'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_guard_blocks_existing_write_and_git_restore(self) -> None:
        script = (
            "import { mkdirSync, writeFileSync, rmSync } from 'node:fs'; "
            "import { join } from 'node:path'; "
            "import { tmpdir } from 'node:os'; "
            "import { guardTool } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const dir = join(tmpdir(), 'lane-guard-' + Date.now()); "
            "mkdirSync(dir); "
            "const existing = join(dir, 'a.ts'); "
            "writeFileSync(existing, 'old\\n'.repeat(20)); "
            "try { "
            "  const blocked = guardTool('write', { path: existing, content: 'x' }, dir); "
            "  if (!blocked.includes('write blocked')) throw new Error('exist ' + blocked); "
            "  const fresh = guardTool('write', { path: join(dir, 'new.ts'), content: 'x' }, dir); "
            "  if (fresh) throw new Error('new ' + fresh); "
            "  const git = guardTool('bash', { command: 'git checkout -- a.ts' }, dir); "
            "  if (!git.includes('git checkout')) throw new Error('git ' + git); "
            "  const ok = guardTool('bash', { command: 'git diff -- a.ts' }, dir); "
            "  if (ok) throw new Error('diff ' + ok); "
            "} finally { rmSync(dir, { recursive: true, force: true }); } "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_dumped_tool_json_gets_sticky_note(self) -> None:
        script = (
            "import { dumpedToolNote, lastAssistantText } from "
            f"{INDEX.resolve().as_uri()!r}; "
            "const dump = lastAssistantText(["
            "  { info: { role: 'user' }, parts: [{ type: 'text', text: 'go' }] },"
            "  { info: { role: 'assistant' }, parts: [{ type: 'text', "
            "text: 'Инструменты Cursor здесь недоступны.\\n{\\\"name\\\":\\\"bash\\\",\\\"command\\\":\\\"ls\\\"}' }] }"
            "]); "
            "const note = dumpedToolNote(dump); "
            "if (!note.includes('JSON-in-chat')) throw new Error('miss ' + note); "
            "if (dumpedToolNote('STATUS: complete')) throw new Error('false-pos'); "
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
            "import { toolFingerprint, recordTool, toolRepeatN } from "
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
            "const w = 'sess-write-path'; "
            "const w1 = recordTool(w, 'write', { path: 'a.ts', content: 'one' }, 'ok'); "
            "const w2 = recordTool(w, 'write', { path: 'a.ts', content: 'two' }, 'ok'); "
            "if (w1.n !== 1 || w2.n !== 2) throw new Error('path-n ' + w2.n); "
            "if (w1.fp === w2.fp) throw new Error('write-fp-collapsed'); "
            "if (toolRepeatN(w, 'write', { path: 'a.ts' }) !== 2) throw new Error('path-lookup'); "
            "console.log('ok')"
        )
        out = _node(script)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok", out.stdout)

    def test_repeated_reads_get_a_hint_without_a_model_call(self) -> None:
        budget = ROOT / "profiles/opencode/opencode-lane/budget.ts"
        out = _node(f"""
            import {{ repeatHint }} from {budget.as_uri()!r};
            import assert from 'node:assert/strict';
            globalThis.fetch = () => {{ throw new Error('No model call expected'); }};
            for (const tool of ['read', 'grep']) {{
                assert.equal(await repeatHint('task', tool, 'same output', 2, 'session'), '');
                assert.match(await repeatHint('task', tool, 'same output', 3, 'session'), /report the concrete blocker/);
            }}
            assert.match(await repeatHint('task', 'write', '', 4, 'session'), /do not git checkout/);
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

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
            "const many = ["
            "{ parts: [{ type: 'tool', tool: 'shell', state: { "
            "input: { command: 'pytest a.py' }, output: '===== 1 passed in 0.1s =====' } }] },"
            "{ parts: [{ type: 'tool', tool: 'shell', state: { "
            "input: { command: 'wc -l f.ts' }, output: '12 f.ts' } }] },"
            "{ parts: [{ type: 'tool', tool: 'shell', state: { "
            "input: { command: 'npm run typecheck' }, output: ('noise ').repeat(3000) + 'error TS2304' } }] }"
            "]; "
            "const capped = collectBashEvidence(many); "
            "if (capped.includes('1 passed')) throw new Error('kept-old-pytest'); "
            "if (capped.includes('12 f.ts')) throw new Error('kept-wc'); "
            "if (!capped.includes('error TS2304')) throw new Error('lost-typecheck'); "
            "if (capped.length > 4000) throw new Error('oversize ' + capped.length); "
            "const noop = collectBashEvidence(["
            "{ parts: [{ type: 'tool', tool: 'shell', state: { "
            "input: { command: 'wc -l x' }, output: '3 x' } }] }]); "
            "if (noop) throw new Error('wc-jev ' + noop); "
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
