import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { buildProjectSnapshot, projectDetail, projectSummary } from './snapshot.mjs';

const fixtures = [];

after(async () => {
  await Promise.all(fixtures.map((directory) => rm(directory, { recursive: true, force: true })));
});

test('builds the fixed list and detail API shapes from a project tree', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-snapshot-'));
  fixtures.push(root);
  await mkdir(path.join(root, '.agents', 'runs', 'run-a', 'tasks'), { recursive: true });
  await mkdir(path.join(root, '.agents', 'todos'), { recursive: true });
  await mkdir(path.join(root, '.agents', 'session-log'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-a', 'tasks', '001.yaml'), [
    'id: 001', 'title: First task', 'status: done', 'risk: low', 'lane: codex', 'verify: tests',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'runs', 'run-a', 'MERGE.md'), 'merged\n');
  await writeFile(path.join(root, 'PROGRESS.md'), '## Now\n- Building server\n## Blocked\n- (none)\n## Next\n- Ship\n');
  await writeFile(path.join(root, '.agents', 'todos', 'INDEX.md'), [
    '| status | priority | id | title |', '|---|---|---|---|', '| OPEN | high | todo-1 | Check output |',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'session-log', 'REVIEW-2026-07-13.md'), 'run/run-a — VERDICT: passed\n');

  const snapshot = await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root });
  const summary = projectSummary(snapshot);
  const detail = projectDetail(snapshot);

  assert.deepEqual(summary.taskCounts, { pending: 0, running: 0, done: 1, blocked: 0, stalled: 0 });
  assert.equal(summary.todoOpenCount, 1);
  assert.deepEqual(summary.review, { date: '2026-07-13', passed: 1, failed: 0 });
  assert.deepEqual(detail.runs, [{
    slug: 'run-a', merged: true, tasks: [{
      id: '001', title: 'First task', status: 'done', risk: 'low', lane: 'codex', verify: 'tests',
    }],
  }]);
  assert.deepEqual(detail.progress, { now: ['Building server'], blocked: ['(none)'], next: ['Ship'] });
});
