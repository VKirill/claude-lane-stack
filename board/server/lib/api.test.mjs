import assert from 'node:assert/strict';
import { request } from 'node:http';
import { after, test } from 'node:test';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createLaneBoardServer } from '../server.mjs';
import { projectId } from './discover.mjs';

const fixtures = [];

after(async () => {
  await Promise.all(fixtures.map((directory) => rm(directory, { recursive: true, force: true })));
});

function getJson(url) {
  return new Promise((resolve, reject) => {
    const client = request(url, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => { body += chunk; });
      response.on('end', () => resolve({ status: response.statusCode, body: JSON.parse(body) }));
    });
    client.once('error', reject);
    client.end();
  });
}

async function startFixtureServer(root) {
  const { server, watcher } = createLaneBoardServer({ roots: [root], discoveryDepth: 1 });
  await watcher.start();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      server.off('error', reject);
      resolve();
    });
  });
  const address = server.address();
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    async close() {
      watcher.stop();
      await new Promise((resolve) => server.close(resolve));
    },
  };
}

test('serves todo bodies, task detail reports, and review history', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'lane-board-api-'));
  fixtures.push(root);
  const projectPath = path.join(root, 'fixture');
  const runPath = path.join(projectPath, '.agents', 'runs', 'run-a');
  await mkdir(path.join(projectPath, '.git'), { recursive: true });
  await mkdir(path.join(runPath, 'tasks'), { recursive: true });
  await mkdir(path.join(runPath, 'artifacts', '008c'), { recursive: true });
  await mkdir(path.join(projectPath, '.agents', 'todos', 'items', 'todo-dir'), { recursive: true });
  await mkdir(path.join(projectPath, '.agents', 'session-log'), { recursive: true });
  await writeFile(path.join(runPath, 'tasks', '008-proxy-status-passthrough.yaml'), [
    'id: "008"',
    'title: Proxy status passthrough',
    'status: RUNNING',
    'model: gpt-5.6-terra',
    'objective: >',
    '  Keep the proxy state visible.',
    '  Preserve useful status details.',
    'done_when:',
    '  - node --test board/server/lib/*.test.mjs',
    'owns_paths:',
    '  - board/server/**',
    'verify: tests',
  ].join('\n'));
  await writeFile(path.join(runPath, 'artifacts', '008c', 'report.md'), Array.from({ length: 61 }, (_, index) => `line ${index + 1}`).join('\n'));
  await writeFile(path.join(projectPath, '.agents', 'todos', 'INDEX.md'), [
    '| status | priority | id | title |',
    '|---|---|---|---|',
    '| open | high | todo-dir | Directory todo |',
  ].join('\n'));
  await writeFile(path.join(projectPath, '.agents', 'todos', 'items', 'todo-dir', 'README.md'), '# Full todo body\n\nKeep this markdown.\n');
  await writeFile(path.join(projectPath, '.agents', 'session-log', 'REVIEW-2026-07-12.md'), 'run/run-a — VERDICT: passed\n');
  await writeFile(path.join(projectPath, '.agents', 'session-log', 'REVIEW-2026-07-13.md'), 'run/run-a — VERDICT: failed\n');

  const fixture = await startFixtureServer(root);
  const id = projectId(projectPath);
  try {
    const todo = await getJson(`${fixture.baseUrl}/api/projects/${id}/todos/todo-dir`);
    assert.equal(todo.status, 200);
    assert.deepEqual(todo.body.meta, { status: 'open', priority: 'high', id: 'todo-dir', title: 'Directory todo' });
    assert.equal(todo.body.body, '# Full todo body\n\nKeep this markdown.\n');

    const missingTodo = await getJson(`${fixture.baseUrl}/api/projects/${id}/todos/missing`);
    assert.deepEqual(missingTodo, { status: 404, body: { error: 'not found' } });

    const task = await getJson(`${fixture.baseUrl}/api/projects/${id}/tasks/run-a/008`);
    assert.equal(task.status, 200);
    assert.equal(task.body.status, 'running');
    assert.equal(task.body.objective, 'Keep the proxy state visible.\nPreserve useful status details.');
    assert.deepEqual(task.body.done_when, ['node --test board/server/lib/*.test.mjs']);
    assert.equal(task.body.verify, 'tests');
    assert.equal(task.body.report.split('\n').length, 60);
    assert.equal(task.body.report.startsWith('line 1\n'), true);

    const reviews = await getJson(`${fixture.baseUrl}/api/projects/${id}/reviews`);
    assert.equal(reviews.status, 200);
    assert.deepEqual(reviews.body.reviews.map((review) => review.date), ['2026-07-13', '2026-07-12']);
  } finally {
    await fixture.close();
  }
});
