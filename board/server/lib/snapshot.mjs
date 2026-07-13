import { lstat, readdir } from 'node:fs/promises';
import path from 'node:path';
import {
  readLatestReview,
  readProgress,
  readTasks,
  readTodos,
} from './parsers.mjs';

export const EMPTY_TASK_COUNTS = Object.freeze({
  pending: 0,
  running: 0,
  done: 0,
  blocked: 0,
  stalled: 0,
});

function warn(message, error) {
  console.warn(`[lane-board] ${message}${error ? `: ${error.message}` : ''}`);
}

async function directories(directory) {
  try {
    return (await readdir(directory, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .sort((left, right) => left.name.localeCompare(right.name));
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${directory}`, error);
    return [];
  }
}

async function exists(target) {
  try {
    await lstat(target);
    return true;
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not inspect ${target}`, error);
    return false;
  }
}

export async function readRuns(projectPath) {
  const runsDirectory = path.join(projectPath, '.agents', 'runs');
  const runs = [];
  for (const entry of await directories(runsDirectory)) {
    const runPath = path.join(runsDirectory, entry.name);
    const tasksDirectory = path.join(runPath, 'tasks');
    const hasTasksDirectory = await exists(tasksDirectory);
    const merged = await exists(path.join(runPath, 'MERGE.md'));
    if (!hasTasksDirectory && !merged) continue;

    runs.push({
      slug: entry.name,
      merged,
      tasks: hasTasksDirectory ? await readTasks(tasksDirectory, entry.name) : [],
    });
  }
  return runs;
}

export async function buildProjectSnapshot(project) {
  const [progress, runs, todos, review] = await Promise.all([
    readProgress(project.path),
    readRuns(project.path),
    readTodos(project.path),
    readLatestReview(project.path),
  ]);
  return { project, progress, runs, todos, review };
}

export function projectSummary(snapshot) {
  const taskCounts = { ...EMPTY_TASK_COUNTS };
  for (const run of snapshot.runs) {
    for (const task of run.tasks) taskCounts[task.status] += 1;
  }
  const review = snapshot.review
    ? {
      date: snapshot.review.date,
      passed: snapshot.review.verdicts.filter((verdict) => verdict.verdict === 'passed').length,
      failed: snapshot.review.verdicts.filter((verdict) => verdict.verdict === 'failed').length,
    }
    : null;

  return {
    id: snapshot.project.id,
    name: snapshot.project.name,
    path: snapshot.project.path,
    taskCounts,
    progressNow: snapshot.progress.now,
    progressBlocked: snapshot.progress.blocked,
    todoOpenCount: snapshot.todos.filter((todo) => todo.status.toLowerCase() === 'open').length,
    review,
  };
}

export function projectDetail(snapshot) {
  return {
    project: {
      id: snapshot.project.id,
      name: snapshot.project.name,
      path: snapshot.project.path,
    },
    progress: snapshot.progress,
    runs: snapshot.runs.map((run) => ({
      slug: run.slug,
      merged: run.merged,
      tasks: run.tasks.map(({ id, title, status, risk, lane, verify }) => ({ id, title, status, risk, lane, verify })),
    })),
    todos: snapshot.todos,
    review: snapshot.review,
  };
}

export async function buildProjectSummaries(projects) {
  const snapshots = await Promise.all(projects.map(async (project) => {
    try {
      return await buildProjectSnapshot(project);
    } catch (error) {
      warn(`could not build snapshot for ${project.path}`, error);
      return { project, progress: { now: [], blocked: [], next: [] }, runs: [], todos: [], review: null };
    }
  }));
  return snapshots.map(projectSummary);
}
