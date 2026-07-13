import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { discoverProjects, projectId } from './discover.mjs';

const fixtures = [];

async function fixtureDirectory() {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'lane-board-discover-'));
  fixtures.push(directory);
  return directory;
}

async function projectAt(directory, { worktree = false } = {}) {
  await mkdir(path.join(directory, '.agents', 'runs'), { recursive: true });
  if (worktree) await writeFile(path.join(directory, '.git'), 'gitdir: /elsewhere\n');
  else await mkdir(path.join(directory, '.git'));
}

after(async () => {
  await Promise.all(fixtures.map((directory) => rm(directory, { recursive: true, force: true })));
});

test('discovers real repositories but excludes worktree .git files', async () => {
  const home = await fixtureDirectory();
  const apps = path.join(home, 'apps');
  const foo = path.join(apps, 'foo');
  const worktree = path.join(foo, '.worktrees', 'bar');
  await projectAt(foo);
  await projectAt(worktree, { worktree: true });

  const projects = await discoverProjects({ roots: [apps], maxDepth: 3 });

  assert.deepEqual(projects, [{ id: projectId(foo), name: 'foo', path: foo }]);
});

test('does not discover qualifying directories deeper than the configured limit', async () => {
  const home = await fixtureDirectory();
  const apps = path.join(home, 'apps');
  const allowed = path.join(apps, 'one', 'two', 'three');
  const tooDeep = path.join(apps, 'one', 'two', 'three', 'four');
  await projectAt(allowed);
  await projectAt(tooDeep);

  const projects = await discoverProjects({ roots: [apps], maxDepth: 3 });

  assert.deepEqual(projects.map((project) => project.path), [allowed]);
});
