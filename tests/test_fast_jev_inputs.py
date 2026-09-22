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
    def test_large_complete_state_reaches_transport_and_errors_fail_open(self) -> None:
        out = _bun(
            f"""
            import assert from 'node:assert/strict';
            import {{ compactSession }} from './plugins/lane-stack/hooks/fast-jev.ts';
            import {{ register }} from './plugins/lane-stack/hooks/fast-jev.ts';

            const longEvidence = ('full tool output marker\\n' + 'evidence '.repeat(40000));
            const messages = Array.from({{ length: 10 }}, (_, i) => ({{
                role: i % 2 ? 'assistant' : 'user',
                text: i === 0 ? 'first task' : (i === 4 ? longEvidence : ''),
                toolUses: [],
            }}));
            messages[1].toolUses.push({{
                tool_use_id: 'u1',
                tool: 'read',
                input: {{ path: 'full-input-marker', payload: longEvidence }},
            }});
            messages[2].toolResults = [{{ tool_use_id: 'u1', text: longEvidence }}];

            let requestBody;
            const compacted = await compactSession(
                messages,
                {{ apiKey: 'fixture', model: 'jev-test', compactAtPercent: 60, minReductionRatio: 0.25 }},
                async (_url, init) => {{
                    requestBody = JSON.parse(init.body);
                    return {{ status: 200, ok: true, text: JSON.stringify({{ answers: {{
                        call_t1: {{ type: 'noul', noul: 1 }},
                        result_t1: {{ type: 'noul', noul: 0 }},
                    }} }}) }};
                }},
            );
            const encoded = JSON.stringify(requestBody.state);
            assert.ok(encoded.length > 30000, 'default path must send beyond former request cap');
            assert.ok(encoded.includes('full-input-marker'));
            assert.ok(requestBody.state.history.some((entry) => entry.text === longEvidence));
            const call = requestBody.state.history
                .flatMap((entry) => entry.tool_calls ?? [])
                .find((entry) => entry.id === 't1');
            assert.ok(call.input.includes('full-input-marker'));
            assert.ok(call.input.length > longEvidence.length);
            assert.equal(call.result, longEvidence);
            assert.equal(compacted.result.stats.resultsDropped, 1);

            let compactHandler;
            register((name, handler) => {{
                if (name === 'session.compact') compactHandler = handler;
            }}, {{}});
            let fallback;
            const ui = {{ log() {{}}, toast() {{}} }};
            await compactHandler(
                {{
                    env: {{ get: async () => 'fixture' }},
                    settings: {{ read: async () => ({{}}) }},
                    http: {{ fetch: async () => {{ throw new Error('transport unavailable'); }} }},
                    ui,
                }},
                {{ messages }},
                (event) => {{ fallback = event; return event; }},
            );
            assert.ok(fallback, 'transport errors must use the built-in fallback');
            assert.deepEqual(fallback.messages, messages);
            console.log('fast-jev complete-input regression: ok');
            """
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("complete-input regression: ok", out.stdout)


if __name__ == "__main__":
    unittest.main()
