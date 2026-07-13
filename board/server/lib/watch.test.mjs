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
