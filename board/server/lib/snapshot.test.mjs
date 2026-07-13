import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, utimes, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { buildProjectSnapshot, projectDetail, projectSummary, selectRecentRuns } from './snapshot.mjs';

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
  const activity = new Date('2026-07-13T00:00:00.000Z');
  await Promise.all([
    utimes(path.join(root, '.agents', 'runs', 'run-a'), activity, activity),
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'tasks'), activity, activity),
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'tasks', '001.yaml'), activity, activity),
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'MERGE.md'), activity, activity),
  ]);

  const snapshot = await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root });
  const summary = projectSummary(snapshot);
  const detail = projectDetail(snapshot);

  assert.deepEqual(summary.taskCounts, { pending: 0, running: 0, done: 1, blocked: 0, stalled: 0 });
  assert.equal(summary.todoOpenCount, 1);
  assert.deepEqual(summary.review, { date: '2026-07-13', passed: 1, failed: 0 });
  assert.deepEqual(detail.runs, [{
    slug: 'run-a', lastActivity: '2026-07-13T00:00:00.000Z', merged: { date: null, commit: null }, tasks: [{
      id: '001', title: 'First task', status: 'done', risk: 'low', lane: 'codex', verify: 'tests',
    }],
  }]);
  assert.deepEqual(detail.progress, { now: ['Building server'], blocked: ['(none)'], next: ['Ship'] });
});

test('recent keeps every run with an unfinished task plus only the three newest fully-done runs', () => {
  const now = new Date('2026-07-13T12:00:00.000Z');
  const daysAgo = (days) => new Date(now.getTime() - (days * 24 * 60 * 60 * 1000)).toISOString();
  const done = { status: 'done' };

  const recent = selectRecentRuns([
    { slug: 'active-old', lastActivity: daysAgo(400), tasks: [done, { status: 'blocked' }] },
    { slug: 'active-new', lastActivity: daysAgo(1), tasks: [{ status: 'pending' }] },
    { slug: 'done-2', lastActivity: daysAgo(2), tasks: [done] },
    { slug: 'done-3', lastActivity: daysAgo(3), tasks: [done] },
    { slug: 'done-4', lastActivity: daysAgo(4), tasks: [done] },
    { slug: 'done-5', lastActivity: daysAgo(5), tasks: [done] },
    { slug: 'done-6', lastActivity: daysAgo(6), tasks: [done] },
  ]).map((run) => run.slug);

  assert.deepEqual(recent, ['active-new', 'done-2', 'done-3', 'done-4', 'active-old']);
});

test('recent run count is active-run count plus min(3, fully-done run count)', () => {
  const activeTask = { status: 'running' };
  const doneTask = { status: 'done' };
  const makeRuns = (activeCount, doneCount) => [
    ...Array.from({ length: activeCount }, (_, index) => (
      { slug: `active-${index}`, lastActivity: null, tasks: [activeTask] }
    )),
    ...Array.from({ length: doneCount }, (_, index) => (
      { slug: `done-${index}`, lastActivity: null, tasks: [doneTask] }
    )),
  ];

  for (const [activeCount, doneCount] of [[0, 0], [2, 1], [0, 5], [3, 5], [1, 2]]) {
    assert.equal(selectRecentRuns(makeRuns(activeCount, doneCount)).length, activeCount + Math.min(3, doneCount));
  }
});

test('a run with no tasks at all counts as fully done, not active', () => {
  assert.equal(selectRecentRuns([{ slug: 'empty', lastActivity: null, tasks: [] }]).length, 1);
  assert.equal(selectRecentRuns([
    { slug: 'e1', lastActivity: null, tasks: [] },
    { slug: 'e2', lastActivity: null, tasks: [] },
    { slug: 'e3', lastActivity: null, tasks: [] },
    { slug: 'e4', lastActivity: null, tasks: [] },
  ]).length, 3);
});
