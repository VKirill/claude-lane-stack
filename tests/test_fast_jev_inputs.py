from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _bun(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bun", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class FastJevInputsTest(unittest.TestCase):
    def test_complete_calls_are_batched_with_safe_limits(self) -> None:
        out = _bun(
            f"""
            import assert from 'node:assert/strict';
            import {{ compactSession }} from './plugins/lane-stack/hooks/fast-jev.ts';
            import {{ estimateTokens }} from './plugins/lane-stack/fast-jev/src/state.ts';
            import {{ resolveOptions }} from './plugins/lane-stack/fast-jev/src/compact.ts';

            const messages = [{{ role: 'user', text: 'first task', toolUses: [] }}];
            const payloads = [];
            for (let i = 1; i <= 10; i++) {{
                const payload = `full-input-marker-${{i}} ` + 'evidence '.repeat(2500);
                const result = `full-result-marker-${{i}} ` + 'result '.repeat(2500);
                payloads.push({{ payload, result }});
                messages.push({{
                    role: 'assistant', text: '', toolUses: [{{
                        tool_use_id: `u${{i}}`, tool: 'read', input: {{ path: `path-${{i}}`, payload }},
                    }}],
                }});
                messages.push({{ role: 'user', text: '', toolResults: [{{ tool_use_id: `u${{i}}`, text: result }}], toolUses: [] }});
            }}
            for (let i = 0; i < 8; i++) messages.push({{ role: 'assistant', text: 'tail context', toolUses: [] }});

            const limits = resolveOptions({{ maxStateTokens: Infinity, maxRequestTokens: Infinity }});
            assert.equal(limits.maxStateTokens, 25000);
            assert.equal(limits.maxRequestTokens, 30000);
            const requestBodies = [];
            const compacted = await compactSession(
                messages,
                {{ apiKey: 'fixture', model: 'jev-test', compactAtPercent: 60, minReductionRatio: 0.25, maxStateTokens: Infinity, maxRequestTokens: Infinity }},
                async (_url, init) => {{
                    const body = JSON.parse(init.body);
                    requestBodies.push(body);
                    const answers = Object.fromEntries(Object.keys(body.questions).map((key) => [key, {{ type: 'noul', noul: 1 }}]));
                    return {{ status: 200, ok: true, text: JSON.stringify({{ answers }}) }};
                }},
            );
            assert.ok(requestBodies.length > 1, 'large history must use bounded requests');
            const seenIds = [];
            for (const body of requestBodies) {{
                assert.ok(estimateTokens(JSON.stringify(body.state)) + estimateTokens(JSON.stringify(body.questions)) + 20 <= 30000);
                for (const call of body.state.history.flatMap((entry) => entry.tool_calls ?? [])) {{
                    seenIds.push(call.id);
                    const index = Number(call.id.slice(1)) - 1;
                    assert.equal(call.input, JSON.stringify({{ path: `path-${{index + 1}}`, payload: payloads[index].payload }}));
                    assert.equal(call.result, payloads[index].result);
                }}
            }}
            assert.deepEqual(seenIds.map((id) => Number(id.slice(1))).sort((a, b) => a - b), Array.from({{ length: 10 }}, (_, i) => i + 1));
            assert.equal(compacted.result.stats.resultsDropped, 0);
            console.log('fast-jev bounded complete-input regression: ok');
            """
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("bounded complete-input regression: ok", out.stdout)

    def test_oversized_call_is_untouched_and_unscored(self) -> None:
        out = _bun(
            f"""
            import assert from 'node:assert/strict';
            import {{ compact }} from './plugins/lane-stack/fast-jev/src/compact.ts';

            const huge = 'oversized-evidence '.repeat(40000);
            const messages = [
                {{ role: 'user', text: 'first task', toolUses: [] }},
                {{ role: 'assistant', text: '', toolUses: [{{ tool_use_id: 'u1', tool: 'read', input: {{ huge }} }}] }},
                {{ role: 'user', text: '', toolResults: [{{ tool_use_id: 'u1', text: huge }}], toolUses: [] }},
                ...Array.from({{ length: 6 }}, () => ({{ role: 'assistant', text: 'tail', toolUses: [] }})),
            ];
            let requests = 0;
            const result = await compact(messages, {{
                async ask() {{ requests++; throw new Error('oversized calls must not be sent'); }}
            }}, {{ maxStateTokens: 25000, maxRequestTokens: 30000 }});
            assert.equal(requests, 0);
            assert.deepEqual(result.messages, messages);
            assert.equal(result.stats.requests, 0);
            assert.equal(result.decisions[0].action, 'keep');
            console.log('fast-jev oversized call: ok');
            """
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("oversized call: ok", out.stdout)

    def test_pinned_call_is_untouched_without_a_request(self) -> None:
        out = _bun(
            f"""
            import assert from 'node:assert/strict';
            import {{ compact }} from './plugins/lane-stack/fast-jev/src/compact.ts';

            const messages = [
                {{ role: 'user', text: 'first task', toolUses: [{{ tool_use_id: 'u1', tool: 'read', input: {{ path: 'pinned' }} }}] }},
                {{ role: 'user', text: '', toolResults: [{{ tool_use_id: 'u1', text: 'pinned result' }}], toolUses: [] }},
                ...Array.from({{ length: 6 }}, () => ({{ role: 'assistant', text: 'tail', toolUses: [] }})),
            ];
            let requests = 0;
            const result = await compact(messages, {{ async ask() {{ requests++; throw new Error('pinned calls are not scored'); }} }});
            assert.equal(requests, 0);
            assert.deepEqual(result.messages, messages);
            assert.equal(result.decisions[0].reason, 'pinned');
            console.log('fast-jev pinned call: ok');
            """
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("pinned call: ok", out.stdout)

    def test_transport_errors_fail_open_to_original_event(self) -> None:
        out = _bun(
            f"""
            import assert from 'node:assert/strict';
            import {{ register }} from './plugins/lane-stack/hooks/fast-jev.ts';

            const messages = [
                {{ role: 'user', text: 'first task', toolUses: [] }},
                {{ role: 'assistant', text: '', toolUses: [{{ tool_use_id: 'u1', tool: 'read', input: {{ path: 'x' }} }}] }},
                {{ role: 'user', text: '', toolResults: [{{ tool_use_id: 'u1', text: 'result' }}], toolUses: [] }},
                ...Array.from({{ length: 6 }}, () => ({{ role: 'assistant', text: 'tail', toolUses: [] }})),
            ];
            let compactHandler;
            register((name, handler) => {{ if (name === 'session.compact') compactHandler = handler; }}, {{}});
            let fallback;
            const ui = {{ log() {{}}, toast() {{}} }};
            await compactHandler(
                {{ env: {{ get: async () => 'fixture' }}, settings: {{ read: async () => ({{}}) }}, http: {{ fetch: async () => {{ throw new Error('transport unavailable'); }} }}, ui }},
                {{ messages }},
                (event) => {{ fallback = event; return event; }},
            );
            assert.ok(fallback);
            assert.deepEqual(fallback.messages, messages);
            console.log('fast-jev transport fallback: ok');
            """
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("transport fallback: ok", out.stdout)


if __name__ == "__main__":
    unittest.main()
