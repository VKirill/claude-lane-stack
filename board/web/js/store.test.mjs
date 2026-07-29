import assert from 'node:assert/strict';
import test from 'node:test';
import { invalidate, loadProject } from './store.js';

test('an invalidated in-flight project response cannot overwrite fresh cache', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = () => new Promise((resolve) => requests.push(resolve));
  try {
    const stale = loadProject('fixture', 'recent', true);
    invalidate();
    const fresh = loadProject('fixture', 'recent', true);
    requests[1]({ ok: true, status: 200, json: async () => ({ version: 'fresh' }) });
    assert.deepEqual(await fresh, { version: 'fresh' });
    requests[0]({ ok: true, status: 200, json: async () => ({ version: 'stale' }) });
    await stale;
    assert.deepEqual(await loadProject('fixture', 'recent'), { version: 'fresh' });
  } finally {
    invalidate();
    globalThis.fetch = originalFetch;
  }
});
