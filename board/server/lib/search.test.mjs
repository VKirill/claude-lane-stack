import assert from 'node:assert/strict';
import { test } from 'node:test';
import { searchAcrossProjects } from './search.mjs';

const snapshots = [{
  project: { id: 'alpha', name: 'Alpha' },
  runs: [{
    slug: 'run-1',
    tasks: [
      { id: '001-photo', title: 'Prepare assets', status: 'running' },
      { id: '002', title: 'Photo import', status: 'pending' },
    ],
  }],
  todos: [{ id: 'todo-photo', title: 'Ship checklist', status: 'open' }],
}];

test('searches task and todo ids and titles case-insensitively', () => {
  assert.deepEqual(searchAcrossProjects(snapshots, 'PHOTO').map((result) => result.id), [
    '001-photo', '002', 'todo-photo',
  ]);
  assert.deepEqual(searchAcrossProjects(snapshots, 'check').map((result) => result.id), ['todo-photo']);
  assert.deepEqual(searchAcrossProjects(snapshots, '').map((result) => result.id), []);
});

test('caps search results across every project combined', () => {
  const manyTasks = Array.from({ length: 55 }, (_, index) => ({
    id: `task-${index}`,
    title: `Photo task ${index}`,
    status: 'pending',
  }));
  const results = searchAcrossProjects([{
    project: { id: 'many', name: 'Many' },
    runs: [{ slug: 'run-many', tasks: manyTasks }],
    todos: [{ id: 'todo-photo', title: 'Photo todo', status: 'open' }],
  }], 'photo');

  assert.equal(results.length, 50);
  assert.equal(results.at(-1).id, 'task-49');
});
