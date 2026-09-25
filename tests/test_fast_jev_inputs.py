from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _bun(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bun", "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=30,
    )


class FastJevInputsTest(unittest.TestCase):
    def test_upstream_fits_large_text_without_clipping_session_text(self) -> None:
        out = _bun(r"""
            import assert from 'node:assert/strict';
            import { compactSession } from './plugins/lane-stack/hooks/fast-jev.ts';
            import { estimateTokens } from './plugins/lane-stack/fast-jev/src/state.ts';
            const longText = 'подробная история решения задачи '.repeat(3000);
            assert(estimateTokens(longText) > 65000);
            for (const role of ['assistant', 'user']) {
                const input = { path: 'old.log', payload: 'input evidence '.repeat(4000) };
                const output = 'obsolete log output '.repeat(12000);
                const messages = [
                    { role: 'user', text: 'Initial task constraint', toolUses: [] },
                    { role, text: longText, toolUses: [] },
                    { role: 'assistant', text: '', toolUses: [{tool_use_id: 'u1', tool: 'Read', input}] },
                    { role: 'user', text: '', toolUses: [], toolResults: [{tool_use_id: 'u1', text: output}] },
                    ...Array.from({length: 6}, () => ({role: 'assistant', text: 'Recent context', toolUses: []})),
                ];
                const before = JSON.stringify(messages);
                let requests = 0;
                const {result} = await compactSession(messages,
                    {apiKey: 'fixture', model: 'jev-test', compactAtPercent: 60, minReductionRatio: .25},
                    async (_, init) => {
                        requests++;
                        const body = JSON.parse(init.body);
                        assert(estimateTokens(JSON.stringify(body.state)) <= 25000);
                        assert(estimateTokens(init.body) <= 30000);
                        assert(!JSON.stringify(body.state).includes(output));
                        const call = body.state.history.flatMap(e => e.tool_calls ?? []).find(c => c.id === 't1');
                        assert(call.result.includes('omitted'));
                        assert(call.input.length <= 1000);
                        return {ok: true, status: 200, text: JSON.stringify({answers: {
                            call_t1: {noul: 1}, result_t1: {noul: 0},
                        }})};
                    });
                assert.equal(requests, 1);
                assert.equal(result.stats.stateStage, 'texts abridged');
                assert.equal(result.stats.resultsDropped, 1);
                assert(result.messages.includes(messages[1]), 'long original message keeps its handle');
                assert.equal(result.messages[1].text, longText);
                assert.equal(result.messages[2].toolUses[0].input, input);
                assert.equal(JSON.stringify(messages), before, 'source transcript must not mutate');
            }
            console.log('long-text upstream regression: ok');
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_kept_and_pinned_evidence_stays_verbatim(self) -> None:
        out = _bun(r"""
            import assert from 'node:assert/strict';
            import { compact } from './plugins/lane-stack/fast-jev/src/compact.ts';
            const huge = 'full evidence '.repeat(40000);
            const messages = [
                {role: 'user', text: 'Task', toolUses: []},
                {role: 'assistant', text: '', toolUses: [{tool_use_id: 'old', tool: 'Read', input: {huge}}]},
                {role: 'user', text: '', toolUses: [], toolResults: [{tool_use_id: 'old', text: huge}]},
                ...Array.from({length: 6}, () => ({role: 'assistant', text: 'tail', toolUses: []})),
                {role: 'assistant', text: '', toolUses: [{tool_use_id: 'recent', tool: 'Read', input: {huge}}]},
                {role: 'user', text: '', toolUses: [], toolResults: [{tool_use_id: 'recent', text: huge}]},
            ];
            const result = await compact(messages, {ask: async (_, questions) => {
                assert.deepEqual(Object.keys(questions), ['call_t1', 'result_t1']);
                return {answers: {call_t1: {noul: 1}, result_t1: {noul: 1}}};
            }});
            assert.equal(result.decisions[1].reason, 'pinned');
            assert.deepEqual(result.messages, messages);
            assert(result.messages.every((m, i) => m === messages[i]));
            console.log('kept/pinned evidence: ok');
        """)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_later_batch_failure_restores_original_event(self) -> None:
        out = _bun(r"""
            import assert from 'node:assert/strict';
            import { register } from './plugins/lane-stack/hooks/fast-jev.ts';
            import { collectToolCalls, fitState } from './plugins/lane-stack/fast-jev/src/state.ts';
            import { resolveOptions } from './plugins/lane-stack/fast-jev/src/compact.ts';
            const messages = [{role: 'user', text: 'Task', toolUses: []}];
            for (let i = 0; i < 12; i++) {
                messages.push({role: 'assistant', text: '', toolUses: [{tool_use_id: `u${i}`, tool: 'Read', input: {path: 'x'}}]});
                messages.push({role: 'user', text: '', toolUses: [], toolResults: [{tool_use_id: `u${i}`, text: 'result '.repeat(1000)}]});
            }
            for (let i = 0; i < 6; i++) messages.push({role: 'assistant', text: 'tail', toolUses: []});
            const state = fitState(messages, collectToolCalls(messages, 6), resolveOptions());
            let handler;
            register((name, fn) => {if (name === 'session.compact') handler = fn}, {maxRequestTokens: state.tokens + 350});
            const before = JSON.stringify(messages);
            const event = {messages};
            let requests = 0, fallback;
            await handler({
                env: {get: async () => 'fixture'}, settings: {read: async () => ({})},
                ui: {log() {}, toast() {}},
                http: {fetch: async (_, init) => {
                    if (++requests === 2) throw Error('later batch failed');
                    return {ok: true, status: 200, text: JSON.stringify({answers:
                        Object.fromEntries(Object.keys(JSON.parse(init.body).questions).map(k => [k, {noul: 0}]))
                    })};
                }},
            }, event, value => {fallback = value; return value});
            assert(requests >= 2);
            assert.equal(fallback, event);
            assert.equal(JSON.stringify(messages), before);
            console.log('later-batch fail-open: ok');
        """)
        self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
