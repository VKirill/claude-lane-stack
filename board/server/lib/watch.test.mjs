import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createProjectWatcher } from './watch.mjs';

const fixtures = [];

after(async () => {
  await Promise.all(fixtures.map((directory) => rm(directory, { recursive: true, force: true })));
});

test('emits a project refresh when a source file signal changes', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-'));
  fixtures.push(root);
  await mkdir(path.join(root, '.agents', 'runs'), { recursive: true });
  await writeFile(path.join(root, 'PROGRESS.md'), '## Now\n- First\n');

  const project = { id: 'fixture-project', name: 'fixture', path: root };
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => [project] });
  watcher.subscribe((projectId) => refreshed.push(projectId));

  await watcher.poll();
  await writeFile(path.join(root, 'PROGRESS.md'), '## Now\n- A changed, longer item\n');
  await watcher.poll();

  assert.deepEqual(refreshed, ['fixture-project']);
  watcher.stop();
});

test('emits a project refresh when a task state receipt changes', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-state-'));
  fixtures.push(root);
  const artifact = path.join(root, '.agents', 'runs', 'demo', 'artifacts', '001');
  await mkdir(artifact, { recursive: true });
  await writeFile(path.join(artifact, 'state.json'), '{"status":"running"}\n');

  const project = { id: 'fixture-project', name: 'fixture', path: root };
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => [project] });
  watcher.subscribe((projectId) => refreshed.push(projectId));

  await watcher.poll();
  await writeFile(path.join(artifact, 'state.json'), '{"status":"awaiting_verification","attempt":1}\n');
  await watcher.poll();

  assert.deepEqual(refreshed, ['fixture-project']);
  watcher.stop();
});

test('emits a project refresh when a night-review failure receipt changes', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-review-failure-'));
  fixtures.push(root);
  const sessionLog = path.join(root, '.agents', 'session-log');
  await mkdir(sessionLog, { recursive: true });
  const receipt = path.join(sessionLog, 'REVIEW-2026-07-28.failures.json');
  await writeFile(receipt, '{"failures":["first failure"]}\n');

  const project = { id: 'fixture-project', name: 'fixture', path: root };
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => [project] });
  watcher.subscribe((projectId) => refreshed.push(projectId));

  await watcher.poll();
  await writeFile(receipt, '{"failures":["a changed, longer failure"]}\n');
  await watcher.poll();

  assert.deepEqual(refreshed, ['fixture-project']);
  watcher.stop();
});

test('emits refreshes when a project is added or removed after the initial poll', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-project-list-'));
  fixtures.push(root);
  const project = { id: 'fixture-project', name: 'fixture', path: root };
  let projects = [];
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => projects });
  watcher.subscribe((projectId) => refreshed.push(projectId));

  await watcher.poll();
  projects = [project];
  await watcher.poll();
  projects = [];
  await watcher.poll();

  assert.deepEqual(refreshed, ['fixture-project', 'fixture-project']);
  watcher.stop();
});

test('emits a project refresh when attempt runtime metadata changes', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-attempt-runtime-'));
  fixtures.push(root);
  const attempt = path.join(root, '.agents', 'runs', 'demo', 'artifacts', '001', 'attempts', '01');
  await mkdir(attempt, { recursive: true });
  const runtime = path.join(attempt, 'runtime.json');
  await writeFile(runtime, '{"provider":"claude"}\n');
  const project = { id: 'fixture-project', name: 'fixture', path: root };
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => [project] });
  watcher.subscribe((projectId) => refreshed.push(projectId));

  await watcher.poll();
  await writeFile(runtime, '{"provider":"codex","model":"gpt-5.6-sol"}\n');
  await watcher.poll();

  assert.deepEqual(refreshed, ['fixture-project']);
  watcher.stop();
});

test('emits refreshes for controller, heartbeat, report, and current-attempt evidence', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-watch-runtime-'));
  fixtures.push(root);
  const run = path.join(root, '.agents', 'runs', 'demo');
  const artifact = path.join(run, 'artifacts', '001');
  const attempt = path.join(artifact, 'attempts', '01');
  await mkdir(attempt, { recursive: true });
  await writeFile(path.join(run, 'controller.json'), '{"stage":"running"}\n');
  await writeFile(path.join(artifact, 'heartbeat.json'), '{"status":"running"}\n');
  await writeFile(path.join(artifact, 'report.md'), 'STATUS: partial\n');
  await writeFile(path.join(attempt, 'lane-bg.exit'), '0\n');

  const project = { id: 'fixture-project', name: 'fixture', path: root };
  const refreshed = [];
  const watcher = createProjectWatcher({ getProjects: async () => [project] });
  watcher.subscribe((projectId) => refreshed.push(projectId));
  await watcher.poll();

  await writeFile(path.join(run, 'controller.json'), '{"stage":"accepted","counts":{"total":1}}\n');
  await watcher.poll();
  await writeFile(path.join(artifact, 'heartbeat.json'), '{"status":"running","note":"activity"}\n');
  await watcher.poll();
  await writeFile(path.join(artifact, 'report.md'), 'STATUS: complete\nmore evidence\n');
  await watcher.poll();
  await writeFile(path.join(attempt, 'lane-bg.exit'), '65\n');
  await watcher.poll();

  assert.deepEqual(refreshed, Array(4).fill('fixture-project'));
  watcher.stop();
});
