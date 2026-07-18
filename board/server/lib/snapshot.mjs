import { lstat, readdir, readFile } from 'node:fs/promises';
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

async function readControllerSummary(runPath) {
  const filePath = path.join(runPath, 'controller.json');
  let value;
  try {
    value = JSON.parse(await readFile(filePath, 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR' && !(error instanceof SyntaxError)) {
      warn(`could not read ${filePath}`, error);
    }
    return null;
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;

  const controllerPath = path.join(runPath, 'controller');
  const readInteger = async (name) => {
    try {
      const source = (await readFile(path.join(controllerPath, name), 'utf8')).trim();
      if (!/^-?\d+$/.test(source)) return { value: null, invalid: true };
      const parsed = Number(source);
      return Number.isInteger(parsed)
        ? { value: parsed, invalid: false }
        : { value: null, invalid: true };
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read controller ${name}`, error);
      return { value: null, invalid: false };
    }
  };
  const pidReceipt = await readInteger('lane-bg.pid');
  const exitReceipt = await readInteger('lane-bg.exit');
  const pid = pidReceipt.value;
  const exitCode = exitReceipt.value;
  let running = false;
  if (pid !== null && pid > 1 && exitCode === null) {
    try {
      const parts = (await readFile(`/proc/${pid}/stat`, 'utf8')).trim().split(/\s+/);
      if (parts.length >= 22 && parts[2] !== 'Z') {
        process.kill(pid, 0);
        running = true;
      }
    } catch {
      running = false;
    }
  }
  const text = (field) => typeof value[field] === 'string' ? value[field] : null;
  const counts = value.counts && typeof value.counts === 'object' && !Array.isArray(value.counts)
    ? Object.fromEntries(['total', 'accepted', 'blocked', 'running', 'pending']
      .filter((key) => Number.isInteger(value.counts[key]) && value.counts[key] >= 0)
      .map((key) => [key, value.counts[key]]))
    : null;
  let lastEvent = value.last_event === null
    || typeof value.last_event === 'string'
    || (value.last_event && typeof value.last_event === 'object' && !Array.isArray(value.last_event))
    ? value.last_event
    : null;
  let stage = text('stage');
  let nextAction = text('next_action');
  if (stage === 'accepted') {
    const tasks = value.tasks && typeof value.tasks === 'object' && !Array.isArray(value.tasks)
      ? Object.values(value.tasks)
      : [];
    const consistent = tasks.length > 0
      && tasks.every((task) => task && typeof task === 'object' && task.stage === 'accepted')
      && counts?.total === tasks.length
      && counts?.accepted === tasks.length
      && nextAction === 'complete';
    if (!consistent) {
      stage = 'failed';
      nextAction = 'operator_intervention';
      lastEvent = {
        type: 'transition',
        event: 'controller_failed',
        detail: 'accepted controller receipt is inconsistent with task stages or counts',
        inferred: true,
      };
    }
  }
  if (!['accepted', 'blocked', 'failed'].includes(stage)
    && (exitReceipt.invalid || pidReceipt.invalid || exitCode !== null || (pid !== null && !running))) {
    const detail = exitReceipt.invalid || pidReceipt.invalid
      ? 'controller process left an invalid pid or exit receipt'
      : exitCode !== null
        ? `controller process exited ${exitCode} without a terminal receipt`
        : 'controller process is dead without a terminal receipt';
    stage = 'failed';
    nextAction = 'operator_intervention';
    lastEvent = {
      type: 'transition',
      event: 'controller_failed',
      detail,
      inferred: true,
    };
  }
  const terminalStage = ['accepted', 'blocked', 'failed'].includes(stage) ? stage : null;
  const status = terminalStage
    ?? text('status')
    ?? (running ? 'running' : exitCode !== null ? (exitCode === 0 ? 'stopped' : 'failed') : 'unknown');
  return {
    status,
    stage,
    counts,
    last_event: lastEvent,
    next_action: nextAction,
    pid: Number.isInteger(value.pid) && value.pid > 0 ? value.pid : pid,
    updated_at: text('updated_at'),
  };
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
      status: promoteMergedTaskStatus(task.status, merged, task.schemaVersion),
    }));

    runs.push({
      slug: entry.name,
      lastActivity: await runLastActivity(runPath),
      merged,
      controller: await readControllerSummary(runPath),
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
      controller: run.controller,
      tasks: run.tasks.map(({ id, title, status, risk, lane, verify, runtime }) => ({
        id, title, status, risk, lane, verify, ...(runtime ? { runtime } : {}),
      })),
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
