import { lstat, readdir } from 'node:fs/promises';
import path from 'node:path';
import {
  readMerge,
  readLatestReview,
  readProgress,
  readTasks,
  readTodos,
  promoteMergedTaskStatus,
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

async function entries(directory) {
  try {
    return await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${directory}`, error);
    return null;
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

/** Return the newest mtime in a run tree, or null when the root is unreadable. */
export async function runLastActivity(runPath) {
  const rootEntries = await entries(runPath);
  if (rootEntries === null) return null;

  let newest = null;
  async function visit(target, knownEntries) {
    let info;
    try {
      info = await lstat(target);
    } catch (error) {
      if (error.code !== 'ENOENT') warn(`could not inspect ${target}`, error);
      return;
    }
    if (Number.isFinite(info.mtimeMs)) newest = newest === null ? info.mtimeMs : Math.max(newest, info.mtimeMs);
    if (!info.isDirectory()) return;

    const childEntries = knownEntries ?? await entries(target);
    if (childEntries === null) return;
    for (const entry of childEntries) await visit(path.join(target, entry.name));
  }

  await visit(runPath, rootEntries);
  return newest === null ? null : new Date(newest).toISOString();
}

function activityMs(run) {
  const timestamp = Date.parse(run?.lastActivity ?? '');
  return Number.isFinite(timestamp) ? timestamp : -Infinity;
}

const ACTIVE_TASK_STATUSES = new Set(['pending', 'running', 'blocked', 'stalled']);

/** A run is active while at least one of its tasks is not yet done. */
function isActiveRun(run) {
  return (run?.tasks ?? []).some((task) => ACTIVE_TASK_STATUSES.has(task.status));
}

const DONE_RUN_LIMIT = 3;

/** Recent = every active run, plus the most recently modified fully-done runs. */
export function selectRecentRuns(runsWithActivity) {
  const sorted = (Array.isArray(runsWithActivity) ? runsWithActivity : [])
    .map((run, index) => ({ run, index, activity: activityMs(run), active: isActiveRun(run) }))
    .sort((left, right) => right.activity - left.activity || left.index - right.index);
  let doneKept = 0;
  return sorted
    .filter((entry) => {
      if (entry.active) return true;
      if (doneKept >= DONE_RUN_LIMIT) return false;
      doneKept += 1;
      return true;
    })
    .map(({ run }) => run);
}

export async function readRuns(projectPath) {
  const runsDirectory = path.join(projectPath, '.agents', 'runs');
  const runs = [];
  for (const entry of await directories(runsDirectory)) {
    const runPath = path.join(runsDirectory, entry.name);
    const tasksDirectory = path.join(runPath, 'tasks');
    const hasTasksDirectory = await exists(tasksDirectory);
    const merged = await readMerge(runPath);
    if (!hasTasksDirectory && !merged) continue;

    const tasks = hasTasksDirectory ? await readTasks(tasksDirectory, entry.name) : [];
    const promotedTasks = tasks.map((task) => ({
      ...task,
      status: promoteMergedTaskStatus(task.status, merged),
    }));

    runs.push({
      slug: entry.name,
      lastActivity: await runLastActivity(runPath),
      merged,
      tasks: promotedTasks,
    });
  }
  return runs;
}

export async function buildProjectSnapshot(project, { scope = 'all' } = {}) {
  const [progress, runs, todos, review] = await Promise.all([
    readProgress(project.path),
    readRuns(project.path),
    readTodos(project.path),
    readLatestReview(project.path),
  ]);
  return { project, progress, runs: scope === 'recent' ? selectRecentRuns(runs) : runs, todos, review };
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
      lastActivity: run.lastActivity,
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
