import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, utimes, writeFile } from 'node:fs/promises';
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
  readTaskDetail,
  promoteMergedTaskStatus,
} from './parsers.mjs';

const fixtures = [];

async function fixtureDirectory(prefix) {
  const directory = await mkdtemp(path.join(os.tmpdir(), prefix));
  fixtures.push(directory);
  return directory;
}

async function writeTrustedProviderReport({ artifactDirectory, taskId, taskSource, attempt = 1 }) {
  const attemptDirectory = path.join(artifactDirectory, 'attempts', String(attempt).padStart(2, '0'));
  const taskSha256 = createHash('sha256').update(taskSource).digest('hex');
  const promptSha256 = createHash('sha256').update(`prompt:${taskId}:${attempt}`).digest('hex');
  const report = [
    'STATUS: complete',
    `TASK_ID: ${taskId}`,
    `PROMPT_SHA256: ${promptSha256}`,
    '',
  ].join('\n');
  const reportSha256 = createHash('sha256').update(report).digest('hex');
  await mkdir(attemptDirectory, { recursive: true });
  await writeFile(path.join(attemptDirectory, 'control.json'), JSON.stringify({
    schema_version: 2,
    task_id: taskId,
    task_sha256: taskSha256,
    attempt,
    prompt_sha256: promptSha256,
  }));
  await writeFile(path.join(attemptDirectory, 'runtime.json'), JSON.stringify({
    schema_version: 1,
    provider: 'grok',
    model: 'grok-4.5',
    task_id: taskId,
    attempt,
    provider_exit_code: 0,
    exit_code: 0,
    protocol_valid: true,
    stop_reason: 'EndTurn',
    sandbox: 'bubblewrap-workspace',
    provider_sandbox: 'off',
    permission_mode: 'bypassPermissions',
    control_plane_read_only: true,
    prompt_sha256: promptSha256,
    report_sha256: reportSha256,
  }));
  await writeFile(path.join(artifactDirectory, 'report.md'), report);
  return { attemptDirectory, reportSha256, taskSha256 };
}

async function writeTrustedVerification({ attemptDirectory, taskId, taskSha256, taskFile, projectCwd, attempt = 1 }) {
  await writeFile(path.join(attemptDirectory, 'verification.json'), JSON.stringify({
    schema_version: 2,
    task_id: taskId,
    task_sha256: taskSha256,
    task_file: taskFile,
    project_cwd: projectCwd,
    attempt,
    status: 'passed',
  }));
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

test('v2 task status comes from state and acceptance receipts, not mutable YAML', async () => {
  const root = await fixtureDirectory('lane-board-v2-state-');
  const runPath = path.join(root, 'contract-v2');
  const tasksDirectory = path.join(runPath, 'tasks');
  const artifactDirectory = path.join(runPath, 'artifacts', '001');
  await mkdir(tasksDirectory, { recursive: true });
  await mkdir(artifactDirectory, { recursive: true });
  const taskSource = [
    'schema_version: 2',
    'id: "001"',
    'title: Immutable task',
    'status: done',
    'risk: low',
    'lane: grok',
    'verify: tests',
  ].join('\n');
  const taskFile = path.join(tasksDirectory, '001.yaml');
  const projectCwd = root;
  await writeFile(taskFile, taskSource);
  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: createHash('sha256').update(taskSource).digest('hex'),
    task_file: taskFile,
    project_cwd: projectCwd,
    status: 'awaiting_verification',
    current_attempt: 1,
  }));

  let tasks = await readTasks(tasksDirectory, 'contract-v2');
  assert.equal(tasks[0].status, 'running');
  assert.equal(tasks[0].schemaVersion, 2);

  const trusted = await writeTrustedProviderReport({
    artifactDirectory,
    taskId: '001',
    taskSource,
  });
  await writeFile(path.join(trusted.attemptDirectory, 'lane-bg.exit'), '0\n');
  await writeTrustedVerification({
    attemptDirectory: trusted.attemptDirectory,
    taskId: '001',
    taskSha256: trusted.taskSha256,
    taskFile,
    projectCwd,
  });
  await writeFile(path.join(artifactDirectory, 'acceptance.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: createHash('sha256').update(taskSource).digest('hex'),
    attempt: 1,
    provider_exit: 0,
    report: 'complete',
    report_sha256: trusted.reportSha256,
    owns_check: 'passed',
    verification: 'passed',
    review: 'not_required',
    accepted: true,
    accepted_at: '2026-07-18T00:00:00Z',
  }));
  tasks = await readTasks(tasksDirectory, 'contract-v2');
  assert.equal(tasks[0].status, 'done');

  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: trusted.taskSha256,
    task_file: taskFile,
    project_cwd: projectCwd,
    status: 'running',
    current_attempt: 2,
  }));
  tasks = await readTasks(tasksDirectory, 'contract-v2');
  assert.equal(tasks[0].status, 'running');

  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: trusted.taskSha256,
    task_file: taskFile,
    project_cwd: projectCwd,
    status: 'awaiting_verification',
    current_attempt: 1,
  }));

  await writeFile(path.join(artifactDirectory, 'acceptance.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: '0'.repeat(64),
    attempt: 1,
    provider_exit: 0,
    report: 'complete',
    owns_check: 'passed',
    verification: 'passed',
    review: 'not_required',
    accepted: true,
    accepted_at: '2026-07-18T00:00:00Z',
  }));
  tasks = await readTasks(tasksDirectory, 'contract-v2');
  assert.equal(tasks[0].status, 'running');

  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: trusted.taskSha256,
    task_file: taskFile,
    project_cwd: projectCwd,
    status: 'accepted',
    current_attempt: 2,
  }));
  tasks = await readTasks(tasksDirectory, 'contract-v2');
  assert.equal(tasks[0].status, 'pending');
  assert.deepEqual(
    [tasks[0].runtime.status, tasks[0].runtime.reason, tasks[0].runtime.next_action],
    ['unknown', 'acceptance_receipt_missing', 'inspect'],
  );
});

test('task list and detail expose the same exact read-only lifecycle evidence', async () => {
  const project = await fixtureDirectory('lane-board-runtime-evidence-');
  const run = 'runtime-run';
  const runPath = path.join(project, '.agents', 'runs', run);
  const tasksDirectory = path.join(runPath, 'tasks');
  const artifactDirectory = path.join(runPath, 'artifacts', '001');
  const attemptDirectory = path.join(artifactDirectory, 'attempts', '02');
  await mkdir(tasksDirectory, { recursive: true });
  await mkdir(attemptDirectory, { recursive: true });
  const taskSource = [
    'schema_version: 2',
    'id: "001"',
    'title: Observable provider',
    'lane: grok',
    'verify: tests',
  ].join('\n');
  const taskFile = path.join(tasksDirectory, '001.yaml');
  const projectCwd = project;
  await writeFile(taskFile, taskSource);
  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: createHash('sha256').update(taskSource).digest('hex'),
    status: 'running',
    current_attempt: 2,
  }));
  await writeFile(path.join(attemptDirectory, 'control.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    attempt: 2,
  }));
  await writeFile(path.join(attemptDirectory, 'lane-bg.pid'), `${process.pid}\n`);
  const heartbeatPath = path.join(artifactDirectory, 'heartbeat.json');
  await writeFile(heartbeatPath, JSON.stringify({ status: 'running' }));
  const heartbeatTime = new Date(Date.now() - 4_000);
  await utimes(heartbeatPath, heartbeatTime, heartbeatTime);

  const [listed] = await readTasks(tasksDirectory, run);
  const detail = await readTaskDetail(project, run, '001');

  assert.equal(listed.status, 'running');
  assert.deepEqual(detail.runtime, listed.runtime);
  assert.deepEqual({ ...listed.runtime, heartbeat_age_seconds: null }, {
    status: 'running',
    attempt: 2,
    pid: process.pid,
    running: true,
    exit_code: null,
    heartbeat_age_seconds: null,
    report_complete: false,
    report_trusted: false,
    report_reason: 'runtime_missing',
    report_sha256: null,
    recorded_report_sha256: null,
    provider: null,
    model: null,
    provider_exit_code: null,
    runtime_exit_code: null,
    protocol_valid: null,
    protocol_error: null,
    stop_reason: null,
    sandbox: null,
    provider_sandbox: null,
    permission_mode: null,
    control_plane_read_only: null,
    prompt_sha256: null,
    reason: 'provider_running',
    next_action: 'wait',
  });
  assert.ok(listed.runtime.heartbeat_age_seconds >= 3);
  assert.ok(listed.runtime.heartbeat_age_seconds < 30);
});

test('finished provider lifecycle distinguishes incomplete report and verification phases', async () => {
  const project = await fixtureDirectory('lane-board-runtime-phases-');
  const runPath = path.join(project, '.agents', 'runs', 'phases');
  const tasksDirectory = path.join(runPath, 'tasks');
  await mkdir(tasksDirectory, { recursive: true });

  async function writePhase(id, { report = null, verification = null, stateStatus = 'running' } = {}) {
    const source = ['schema_version: 2', `id: "${id}"`, `title: Phase ${id}`].join('\n');
    const artifact = path.join(runPath, 'artifacts', id);
    const attempt = path.join(artifact, 'attempts', '01');
    await mkdir(attempt, { recursive: true });
    await writeFile(path.join(tasksDirectory, `${id}.yaml`), source);
    await writeFile(path.join(artifact, 'state.json'), JSON.stringify({
      schema_version: 2,
      task_id: id,
      task_sha256: createHash('sha256').update(source).digest('hex'),
      task_file: path.join(tasksDirectory, `${id}.yaml`),
      project_cwd: project,
      status: stateStatus,
      current_attempt: 1,
    }));
    let trusted = null;
    if (report !== null) {
      trusted = await writeTrustedProviderReport({
        artifactDirectory: artifact,
        taskId: id,
        taskSource: source,
      });
    } else {
      await writeFile(path.join(attempt, 'control.json'), JSON.stringify({ attempt: 1 }));
    }
    await writeFile(path.join(attempt, 'lane-bg.pid'), '999999999\n');
    await writeFile(path.join(attempt, 'lane-bg.exit'), '0\n');
    if (verification !== null) {
      await writeFile(path.join(attempt, 'verification.json'), JSON.stringify({
        schema_version: 2,
        task_id: id,
        task_sha256: createHash('sha256').update(source).digest('hex'),
        task_file: path.join(tasksDirectory, `${id}.yaml`),
        project_cwd: project,
        attempt: 1,
        status: verification,
      }));
    }
  }

  await writePhase('001');
  await writePhase('002', { report: 'STATUS: complete\n' });
  await writePhase('003', { report: 'STATUS: complete\n', verification: 'running' });
  await writePhase('004', { stateStatus: 'blocked' });

  const tasks = await readTasks(tasksDirectory, 'phases');
  const runtimeById = Object.fromEntries(tasks.map((task) => [task.id, task.runtime]));
  assert.deepEqual(
    Object.fromEntries(Object.entries(runtimeById).map(([id, runtime]) => [id, [runtime.status, runtime.reason, runtime.next_action]])),
    {
      '001': ['provider_incomplete', 'runtime_missing', 'retry'],
      '002': ['awaiting_verification', 'provider_complete', 'verify'],
      '003': ['verifying', 'verification_running', 'wait'],
      '004': ['blocked', 'blocked', 'inspect'],
    },
  );
  assert.equal(runtimeById['001'].exit_code, 0);
  assert.equal(runtimeById['002'].report_complete, true);
  assert.equal(runtimeById['002'].report_trusted, true);
});

test('tampered provider report is fail-closed and exposed as untrusted', async () => {
  const project = await fixtureDirectory('lane-board-runtime-tamper-');
  const run = 'tampered-run';
  const runPath = path.join(project, '.agents', 'runs', run);
  const tasksDirectory = path.join(runPath, 'tasks');
  const artifactDirectory = path.join(runPath, 'artifacts', '001');
  await mkdir(tasksDirectory, { recursive: true });
  const taskSource = ['schema_version: 2', 'id: "001"', 'title: Tampered report'].join('\n');
  await writeFile(path.join(tasksDirectory, '001.yaml'), taskSource);
  const trusted = await writeTrustedProviderReport({ artifactDirectory, taskId: '001', taskSource });
  await writeFile(path.join(trusted.attemptDirectory, 'lane-bg.exit'), '0\n');
  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: trusted.taskSha256,
    status: 'awaiting_verification',
    current_attempt: 1,
  }));
  await writeFile(path.join(artifactDirectory, 'report.md'), [
    'STATUS: complete',
    'TASK_ID: 001',
    `PROMPT_SHA256: ${createHash('sha256').update('tampered').digest('hex')}`,
    '',
  ].join('\n'));

  const [listed] = await readTasks(tasksDirectory, run);
  const detail = await readTaskDetail(project, run, '001');

  assert.deepEqual(detail.runtime, listed.runtime);
  assert.equal(listed.status, 'pending');
  assert.equal(listed.runtime.status, 'provider_incomplete');
  assert.equal(listed.runtime.report_complete, false);
  assert.equal(listed.runtime.report_trusted, false);
  assert.equal(listed.runtime.report_reason, 'report_digest_mismatch');
});

test('accepted v2 task has identical done status in list and detail views', async () => {
  const project = await fixtureDirectory('lane-board-v2-parity-');
  const run = 'accepted-run';
  const runPath = path.join(project, '.agents', 'runs', run);
  const tasksDirectory = path.join(runPath, 'tasks');
  const artifactDirectory = path.join(runPath, 'artifacts', '001');
  await mkdir(tasksDirectory, { recursive: true });
  await mkdir(artifactDirectory, { recursive: true });
  const taskSource = [
    'schema_version: 2',
    'id: "001"',
    'title: Accepted task',
    'risk: low',
    'lane: grok',
    'verify: tests',
  ].join('\n');
  const taskFile = path.join(tasksDirectory, '001.yaml');
  const projectCwd = project;
  await writeFile(taskFile, taskSource);
  await writeFile(path.join(artifactDirectory, 'state.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: createHash('sha256').update(taskSource).digest('hex'),
    task_file: taskFile,
    project_cwd: projectCwd,
    status: 'awaiting_verification',
    current_attempt: 1,
  }));
  const trusted = await writeTrustedProviderReport({
    artifactDirectory,
    taskId: '001',
    taskSource,
  });
  await writeFile(path.join(trusted.attemptDirectory, 'lane-bg.exit'), '0\n');
  await writeTrustedVerification({
    attemptDirectory: trusted.attemptDirectory,
    taskId: '001',
    taskSha256: trusted.taskSha256,
    taskFile,
    projectCwd,
  });
  await writeFile(path.join(artifactDirectory, 'acceptance.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: createHash('sha256').update(taskSource).digest('hex'),
    attempt: 1,
    provider_exit: 0,
    report: 'complete',
    report_sha256: trusted.reportSha256,
    owns_check: 'passed',
    verification: 'passed',
    review: 'not_required',
    accepted: true,
    accepted_at: '2026-07-18T00:00:00Z',
  }));

  const [listed] = await readTasks(tasksDirectory, run);
  const detail = await readTaskDetail(project, run, '001');

  assert.equal(listed.status, 'done');
  assert.equal(detail.status, listed.status);

  await rm(path.join(trusted.attemptDirectory, 'verification.json'));
  const [missingVerification] = await readTasks(tasksDirectory, run);
  assert.equal(missingVerification.status, 'running');
  assert.equal(missingVerification.runtime.status, 'awaiting_verification');

  await writeTrustedVerification({
    attemptDirectory: trusted.attemptDirectory,
    taskId: '001',
    taskSha256: trusted.taskSha256,
    taskFile,
    projectCwd,
  });
  await writeFile(path.join(artifactDirectory, 'acceptance.json'), JSON.stringify({
    schema_version: 2,
    task_id: '001',
    task_sha256: trusted.taskSha256,
    attempt: 1,
    provider_exit: 0,
    report: 'complete',
    report_sha256: trusted.reportSha256,
    owns_check: 'passed',
    verification: 'passed',
    review: 'passed',
    accepted: true,
    accepted_at: '2026-07-18T00:00:00Z',
  }));
  const review = {
    schema_version: 2,
    receipt_type: 'task_re_review',
    task_id: '001',
    task_sha256: trusted.taskSha256,
    attempt: 1,
    project_cwd: projectCwd,
    base_ref: 'a'.repeat(40),
    reviewed_diff_sha256: 'b'.repeat(64),
    reviewed_tree_sha256: 'c'.repeat(64),
    verdict: 'passed',
    findings: [],
    reviewed_at: '2026-07-18T00:00:00Z',
  };
  await writeFile(path.join(artifactDirectory, 'review.json'), JSON.stringify(review));
  const [reviewed] = await readTasks(tasksDirectory, run);
  assert.equal(reviewed.status, 'done');

  await writeFile(path.join(artifactDirectory, 'review.json'), JSON.stringify({
    ...review,
    reviewed_diff_sha256: 'tampered',
  }));
  const [tamperedReview] = await readTasks(tasksDirectory, run);
  assert.equal(tamperedReview.status, 'running');
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

test('reads machine merge receipt before the legacy markdown view', async () => {
  const runPath = await fixtureDirectory('lane-board-merge-json-');
  await writeFile(path.join(runPath, 'merge.json'), JSON.stringify({
    schema_version: 2,
    completed_at: '2026-07-18T01:30:00+00:00',
    merge_commit: 'abcdef1234567890',
  }));
  await writeFile(path.join(runPath, 'MERGE.md'), [
    '# legacy view',
    '- merge commit on main: 1111111',
    '- when: 2026-07-17',
  ].join('\n'));

  const { readMerge } = await import('./parsers.mjs');
  assert.deepEqual(await readMerge(runPath), {
    date: '2026-07-18',
    commit: 'abcdef1234567890',
  });
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

test('readTaskDetail promotes pending task to done if run is merged', async () => {
  const project = await fixtureDirectory('lane-board-task-detail-merged-');
  
  // 1. Task without explicit status: field -> detail.status is undefined (not introduced)
  const runMergedPath = path.join(project, '.agents', 'runs', 'run-merged');
  await mkdir(path.join(runMergedPath, 'tasks'), { recursive: true });
  await writeFile(path.join(runMergedPath, 'tasks', '001.yaml'), [
    'id: "001"',
    'title: Merged task no status',
  ].join('\n'));
  await writeFile(path.join(runMergedPath, 'MERGE.md'), [
    '# MERGE — run-merged',
    '- merge commit on main: a8562efa1',
    '- when: 2026-07-12 ~10:35 UTC',
  ].join('\n'));

  const detail1 = await readTaskDetail(project, 'run-merged', '001');
  assert.equal(detail1.status, undefined);

  // 2. Task with status: pending -> promoted to done
  await writeFile(path.join(runMergedPath, 'tasks', '002.yaml'), [
    'id: "002"',
    'title: Merged task pending',
    'status: pending',
  ].join('\n'));
  
  const detail2 = await readTaskDetail(project, 'run-merged', '002');
  assert.equal(detail2.status, 'done');

  // 3. Unmerged run (no MERGE.md) -> task with status: pending -> stays pending
  const runUnmergedPath = path.join(project, '.agents', 'runs', 'run-unmerged');
  await mkdir(path.join(runUnmergedPath, 'tasks'), { recursive: true });
  await writeFile(path.join(runUnmergedPath, 'tasks', '003.yaml'), [
    'id: "003"',
    'title: Unmerged task pending',
    'status: pending',
  ].join('\n'));

  const detail3 = await readTaskDetail(project, 'run-unmerged', '003');
  assert.equal(detail3.status, 'pending');

  // 4. Merged run + task with explicit status: blocked -> stays blocked
  await writeFile(path.join(runMergedPath, 'tasks', '004.yaml'), [
    'id: "004"',
    'title: Merged task blocked',
    'status: blocked',
  ].join('\n'));

  const detail4 = await readTaskDetail(project, 'run-merged', '004');
  assert.equal(detail4.status, 'blocked');
});
