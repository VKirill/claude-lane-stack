import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {
  parseMerge,
  parseProgress,
  parseReview,
  parseTaskDetail,
  readAllReviews,
  readLatestReview,
  readTasks,
  readTodos,
} from './parsers.mjs';

const fixtures = [];

async function fixtureDirectory(prefix) {
  const directory = await mkdtemp(path.join(os.tmpdir(), prefix));
  fixtures.push(directory);
  return directory;
}

after(async () => {
  await Promise.all(fixtures.map((directory) => rm(directory, { recursive: true, force: true })));
});

test('reads flat task YAML and skips malformed task files', async () => {
  const root = await fixtureDirectory('lane-board-tasks-');
  const tasksDirectory = path.join(root, 'tasks');
  await mkdir(tasksDirectory, { recursive: true });
  await writeFile(path.join(tasksDirectory, '001.yaml'), [
    'id: "001"',
    'title: Lane Board API',
    'status: running',
    'risk: medium',
    'lane: codex',
    'verify: node --test',
    'objective: |',
    '  A block scalar that is intentionally ignored.',
  ].join('\n'));
  await writeFile(path.join(tasksDirectory, 'bad.yaml'), 'not valid task data\n');

  const tasks = await readTasks(tasksDirectory, 'lane-board');

  assert.deepEqual(tasks, [{
    id: '001',
    title: 'Lane Board API',
    status: 'running',
    risk: 'medium',
    lane: 'codex',
    verify: 'node --test',
    run: 'lane-board',
  }]);
});

test('parses progress headings and joins wrapped bullet text', () => {
  const progress = parseProgress([
    '# Progress',
    '## Now',
    '- First item wraps',
    '  onto this continuation.',
    '- Second item',
    '## Blocked',
    '- Waiting on review',
    '## Next',
    '- Ship it',
    '## Other',
    '- Must not be captured',
  ].join('\n'));

  assert.deepEqual(progress, {
    now: ['First item wraps onto this continuation.', 'Second item'],
    blocked: ['Waiting on review'],
    next: ['Ship it'],
  });
});

test('parses todo table UTF-8 rows and falls back to todo item names', async () => {
  const indexedProject = await fixtureDirectory('lane-board-todos-index-');
  const indexDirectory = path.join(indexedProject, '.agents', 'todos');
  await mkdir(indexDirectory, { recursive: true });
  await writeFile(path.join(indexDirectory, 'INDEX.md'), [
    '| status | priority | id | title |',
    '|--------|----------|----|-------|',
    '| open | high | task-1 | Проверить отчёт |',
    '| done | low | task-2 | Finished |',
  ].join('\n'));

  assert.deepEqual(await readTodos(indexedProject), [
    { status: 'open', priority: 'high', id: 'task-1', title: 'Проверить отчёт' },
    { status: 'done', priority: 'low', id: 'task-2', title: 'Finished' },
  ]);

  const fallbackProject = await fixtureDirectory('lane-board-todos-fallback-');
  const itemsDirectory = path.join(fallbackProject, '.agents', 'todos', 'items');
  await mkdir(path.join(itemsDirectory, 'directory-item'), { recursive: true });
  await writeFile(path.join(itemsDirectory, 'file-item.md'), '# File item\n');
  await writeFile(path.join(itemsDirectory, 'directory-item', 'README.md'), '# Directory item\n');

  assert.deepEqual(await readTodos(fallbackProject), [
    { status: 'open', priority: null, id: 'directory-item', title: 'directory-item' },
    { status: 'open', priority: null, id: 'file-item', title: 'file-item.md' },
  ]);
});

test('parses real review verdict format, findings, plans, and empty review input', async () => {
  const review = parseReview([
    '# Night review',
    '## Verdicts',
    'run/lane-board — VERDICT: passed',
    'commits — VERDICT: failed',
    '## P0/P1 findings',
    'P0: board/server/server.mjs:42 — fix an important bug',
    'P1: board/server/lib/watch.mjs:8 — tighten polling',
    '## Morning fix plan',
    '- [ ] Fix the important bug',
    '- [ ] Add a regression test',
  ].join('\n'), '2026-07-13');

  assert.deepEqual(review, {
    date: '2026-07-13',
    verdicts: [
      { scope: 'run/lane-board', verdict: 'passed' },
      { scope: 'commits', verdict: 'failed' },
    ],
    findings: [
      { level: 'P0', text: 'fix an important bug' },
      { level: 'P1', text: 'tighten polling' },
    ],
    fixPlan: ['Fix the important bug', 'Add a regression test'],
  });
  assert.deepEqual(parseReview('# A review without expected records\n', '2026-07-13'), {
    date: '2026-07-13', verdicts: [], findings: [], fixPlan: [],
  });
  assert.deepEqual(parseReview('VERDICT run/alternate: failed\n', '2026-07-13').verdicts, [
    { scope: 'run/alternate', verdict: 'failed' },
  ]);

  const projectWithoutReview = await fixtureDirectory('lane-board-no-review-');
  await mkdir(path.join(projectWithoutReview, '.agents', 'session-log'), { recursive: true });
  assert.equal(await readLatestReview(projectWithoutReview), null);
});

test('reads every review newest first and skips an empty malformed review', async () => {
  const project = await fixtureDirectory('lane-board-all-reviews-');
  const reviewsDirectory = path.join(project, '.agents', 'session-log');
  await mkdir(reviewsDirectory, { recursive: true });
  await writeFile(path.join(reviewsDirectory, 'REVIEW-2026-07-10.md'), 'run/old — VERDICT: passed\n');
  await writeFile(path.join(reviewsDirectory, 'REVIEW-2026-07-12.md'), '');
  await writeFile(path.join(reviewsDirectory, 'REVIEW-2026-07-13.md'), 'run/new — VERDICT: failed\n');

  const reviews = await readAllReviews(project);

  assert.deepEqual(reviews.map((review) => review.date), ['2026-07-13', '2026-07-10']);
  assert.deepEqual(reviews[0].verdicts, [{ scope: 'run/new', verdict: 'failed' }]);
});

test('parses merge receipts with merge commits preferred over feature commits', () => {
  assert.deepEqual(parseMerge([
    '# MERGE — receipt-email-ux',
    '- feat commit: a1290b354',
    '- merge commit on main: a8562efa1',
    '- when: 2026-07-12 ~10:35 UTC',
  ].join('\n')), { date: '2026-07-12', commit: 'a8562efa1' });
  assert.deepEqual(parseMerge('hotfix closed (no source change, dist rebuild only)\n'), { date: null, commit: null });
});

test('parses a task detail scalar mix, block objectives, and only the done_when list', () => {
  const detail = parseTaskDetail([
    'id: "008"',
    'title: Proxy status passthrough',
    'status: BLOCKED',
    'risk: medium',
    'model: gpt-5.6-terra',
    'objective: |',
    '  Keep the first line.',
    '    Keep this nested indentation.',
    'done_when:',
    '  - "node --test board/server/lib/*.test.mjs"',
    '  - curl -s /healthz',
    'owns_paths:',
    '  - board/server/**',
    'verify: tests',
  ].join('\n'));

  assert.deepEqual(detail, {
    id: '008',
    title: 'Proxy status passthrough',
    status: 'blocked',
    risk: 'medium',
    model: 'gpt-5.6-terra',
    objective: 'Keep the first line.\n  Keep this nested indentation.',
    done_when: ['node --test board/server/lib/*.test.mjs', 'curl -s /healthz'],
    verify: 'tests',
  });

  assert.deepEqual(parseTaskDetail([
    'id: 009',
    'objective: >',
    '  Folded syntax remains readable.',
    '  The endpoint keeps line breaks.',
    'done_when:',
    '  - done',
  ].join('\n')), {
    id: '009',
    objective: 'Folded syntax remains readable.\nThe endpoint keeps line breaks.',
    done_when: ['done'],
  });
});
