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
  await mkdir(path.join(root, '.agents', 'runs', 'run-a', 'controller'), { recursive: true });
  await mkdir(path.join(root, '.agents', 'todos'), { recursive: true });
  await mkdir(path.join(root, '.agents', 'session-log'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-a', 'controller.json'), JSON.stringify({
    schema_version: 1,
    stage: 'providers',
    counts: { total: 3, accepted: 1, blocked: 0, running: 2, pending: 0 },
    last_event: { type: 'provider_started', task_id: '003' },
    next_action: 'wait',
    updated_at: '2026-07-18T06:00:00Z',
    ignored_secret: 'must not reach API',
  }));
  await writeFile(path.join(root, '.agents', 'runs', 'run-a', 'controller', 'lane-bg.pid'), `${process.pid}\n`);
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
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'controller.json'), activity, activity),
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'controller'), activity, activity),
    utimes(path.join(root, '.agents', 'runs', 'run-a', 'controller', 'lane-bg.pid'), activity, activity),
  ]);

  const snapshot = await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root });
  const summary = projectSummary(snapshot);
  const detail = projectDetail(snapshot);

  assert.deepEqual(summary.taskCounts, { pending: 0, running: 0, done: 1, blocked: 0, stalled: 0 });
  assert.equal(summary.todoOpenCount, 1);
  assert.deepEqual(summary.review, { date: '2026-07-13', passed: 1, failed: 0 });
  assert.deepEqual(detail.runs, [{
    slug: 'run-a', lastActivity: '2026-07-13T00:00:00.000Z', merged: { date: null, commit: null }, controller: {
      status: 'running',
      stage: 'providers',
      counts: { total: 3, accepted: 1, blocked: 0, running: 2, pending: 0 },
      last_event: { type: 'provider_started', task_id: '003' },
      next_action: 'wait',
      pid: process.pid,
      updated_at: '2026-07-18T06:00:00Z',
    }, tasks: [{
      id: '001', title: 'First task', status: 'done', risk: 'low', lane: 'codex', verify: 'tests',
    }],
  }]);
  assert.deepEqual(detail.progress, { now: ['Building server'], blocked: ['(none)'], next: ['Ship'] });
});

test('malformed controller receipt is ignored without hiding the run', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-controller-malformed-'));
  fixtures.push(root);
  const runPath = path.join(root, '.agents', 'runs', 'run-a');
  await mkdir(path.join(runPath, 'tasks'), { recursive: true });
  await writeFile(path.join(runPath, 'tasks', '001.yaml'), 'id: 001\ntitle: Visible task\n');
  await writeFile(path.join(runPath, 'controller.json'), '{not json');

  const detail = projectDetail(await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root }));

  assert.equal(detail.runs.length, 1);
  assert.equal(detail.runs[0].controller, null);
  assert.equal(detail.runs[0].tasks[0].id, '001');
});

test('inconsistent accepted controller receipt is shown fail closed', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-controller-inconsistent-'));
  fixtures.push(root);
  const runPath = path.join(root, '.agents', 'runs', 'run-a');
  await mkdir(path.join(runPath, 'tasks'), { recursive: true });
  await writeFile(path.join(runPath, 'tasks', '001.yaml'), 'id: 001\ntitle: Visible task\n');
  await writeFile(path.join(runPath, 'controller.json'), JSON.stringify({
    schema_version: 1,
    stage: 'accepted',
    counts: { total: 1, accepted: 1, blocked: 0, running: 0, pending: 0 },
    next_action: 'complete',
    status: 'running',
    tasks: { '001': { stage: 'running' } },
  }));

  const detail = projectDetail(await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root }));

  assert.equal(detail.runs[0].controller.stage, 'failed');
  assert.equal(detail.runs[0].controller.status, 'failed');
  assert.equal(detail.runs[0].controller.next_action, 'operator_intervention');
  assert.equal(detail.runs[0].controller.last_event.event, 'controller_failed');
});

test('dead nonterminal controller is shown as inferred failure', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-controller-dead-'));
  fixtures.push(root);
  const runPath = path.join(root, '.agents', 'runs', 'run-a');
  await mkdir(path.join(runPath, 'tasks'), { recursive: true });
  await mkdir(path.join(runPath, 'controller'), { recursive: true });
  await writeFile(path.join(runPath, 'tasks', '001.yaml'), 'id: 001\ntitle: Visible task\n');
  await writeFile(path.join(runPath, 'controller.json'), JSON.stringify({
    schema_version: 1,
    stage: 'running',
    counts: { total: 1, accepted: 0, blocked: 0, running: 1, pending: 0 },
    next_action: 'poll',
    tasks: { '001': { stage: 'running' } },
  }));
  await writeFile(path.join(runPath, 'controller', 'lane-bg.pid'), '99999999\n');
  await writeFile(path.join(runPath, 'controller', 'lane-bg.exit'), '1\n');

  const detail = projectDetail(await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root }));

  assert.equal(detail.runs[0].controller.stage, 'failed');
  assert.equal(detail.runs[0].controller.status, 'failed');
  assert.equal(detail.runs[0].controller.next_action, 'operator_intervention');
  assert.equal(detail.runs[0].controller.last_event.event, 'controller_failed');
  assert.match(detail.runs[0].controller.last_event.detail, /exited 1/);
});

test('invalid controller process receipt is shown as inferred failure', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-controller-invalid-process-'));
  fixtures.push(root);
  const runPath = path.join(root, '.agents', 'runs', 'run-a');
  await mkdir(path.join(runPath, 'tasks'), { recursive: true });
  await mkdir(path.join(runPath, 'controller'), { recursive: true });
  await writeFile(path.join(runPath, 'tasks', '001.yaml'), 'id: 001\ntitle: Visible task\n');
  await writeFile(path.join(runPath, 'controller.json'), JSON.stringify({
    schema_version: 1,
    stage: 'running',
    counts: { total: 1, accepted: 0, blocked: 0, running: 1, pending: 0 },
    next_action: 'poll',
    tasks: { '001': { stage: 'running' } },
  }));
  await writeFile(path.join(runPath, 'controller', 'lane-bg.pid'), 'not-a-pid\n');

  const detail = projectDetail(await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root }));

  assert.equal(detail.runs[0].controller.stage, 'failed');
  assert.equal(detail.runs[0].controller.status, 'failed');
  assert.match(detail.runs[0].controller.last_event.detail, /invalid pid or exit/);
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

test('promotes task status to done in merged runs', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-snapshot-merged-'));
  fixtures.push(root);

  // Set up three runs:
  // 1. run-merged: has MERGE.md (merged) + task without status field -> should end up 'done'
  //                 + task with explicit status: blocked -> stays 'blocked'
  await mkdir(path.join(root, '.agents', 'runs', 'run-merged', 'tasks'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-merged', 'tasks', '001.yaml'), [
    'id: 001', 'title: Task without status',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'runs', 'run-merged', 'tasks', '002.yaml'), [
    'id: 002', 'title: Task blocked', 'status: blocked',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'runs', 'run-merged', 'MERGE.md'), [
    '# MERGE — run-merged',
    '- merge commit on main: a8562efa1',
    '- when: 2026-07-12 ~10:35 UTC',
  ].join('\n'));

  // 2. run-unmerged: no MERGE.md (unmerged) + task without status field -> stays 'pending'
  await mkdir(path.join(root, '.agents', 'runs', 'run-unmerged', 'tasks'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-unmerged', 'tasks', '003.yaml'), [
    'id: 003', 'title: Task without status unmerged',
  ].join('\n'));

  // 3. run-invalid-merge: MERGE.md has no valid commit (e.g. "merged\n") -> stays 'pending'
  await mkdir(path.join(root, '.agents', 'runs', 'run-invalid-merge', 'tasks'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-invalid-merge', 'tasks', '004.yaml'), [
    'id: 004', 'title: Task without status invalid merge',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'runs', 'run-invalid-merge', 'MERGE.md'), 'merged\n');

  const snapshot = await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root });
  const detail = projectDetail(snapshot);

  const runMerged = detail.runs.find((r) => r.slug === 'run-merged');
  assert.equal(runMerged.tasks.find((t) => t.id === '001').status, 'done');
  assert.equal(runMerged.tasks.find((t) => t.id === '002').status, 'blocked');

  const runUnmerged = detail.runs.find((r) => r.slug === 'run-unmerged');
  assert.equal(runUnmerged.tasks.find((t) => t.id === '003').status, 'pending');

  const runInvalidMerge = detail.runs.find((r) => r.slug === 'run-invalid-merge');
  assert.equal(runInvalidMerge.tasks.find((t) => t.id === '004').status, 'pending');

  // 4. Contract v2 never derives done from merge alone; acceptance.json is authoritative.
  await mkdir(path.join(root, '.agents', 'runs', 'run-v2', 'tasks'), { recursive: true });
  await writeFile(path.join(root, '.agents', 'runs', 'run-v2', 'tasks', '005.yaml'), [
    'schema_version: 2', 'id: 005', 'title: V2 task without acceptance',
  ].join('\n'));
  await writeFile(path.join(root, '.agents', 'runs', 'run-v2', 'merge.json'), JSON.stringify({
    schema_version: 2,
    completed_at: '2026-07-18T01:30:00+00:00',
    merge_commit: 'abcdef1234567890',
  }));

  const refreshed = projectDetail(await buildProjectSnapshot({ id: 'project-id', name: 'fixture', path: root }));
  const runV2 = refreshed.runs.find((r) => r.slug === 'run-v2');
  assert.equal(runV2.tasks.find((t) => t.id === '005').status, 'pending');
});
