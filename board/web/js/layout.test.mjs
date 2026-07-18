import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

test('task cards may shrink inside their board column', async () => {
  const css = await readFile(new URL('../css/views.css', import.meta.url), 'utf8');
  const rule = css.match(/\.task-card\s*\{([^}]*)\}/);

  assert.ok(rule, 'expected a .task-card rule');
  assert.match(rule[1], /\bmin-width\s*:\s*0\s*;/);
});
