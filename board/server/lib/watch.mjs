import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';

function warn(message, error) {
  console.warn(`[lane-board] ${message}${error ? `: ${error.message}` : ''}`);
}

async function readDirectory(directory) {
  try {
    return await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${directory}`, error);
    return [];
  }
}

async function addStat(parts, target) {
  try {
    const info = await stat(target);
    parts.push(`${target}:${info.mtimeMs}:${info.size}`);
    return info;
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not inspect ${target}`, error);
    return null;
  }
}

/** Return a stable lightweight fingerprint of every source feeding a project. */
export async function projectSignal(project) {
  const parts = [];
  const projectPath = project.path;
  await addStat(parts, path.join(projectPath, 'PROGRESS.md'));

  const agentsPath = path.join(projectPath, '.agents');
  const runsPath = path.join(agentsPath, 'runs');
  await addStat(parts, runsPath);
  for (const run of await readDirectory(runsPath)) {
    if (!run.isDirectory()) continue;
    const runPath = path.join(runsPath, run.name);
    await addStat(parts, path.join(runPath, 'controller.json'));
    await addStat(parts, path.join(runPath, 'controller', 'lane-bg.pid'));
    await addStat(parts, path.join(runPath, 'controller', 'lane-bg.exit'));
    await addStat(parts, path.join(runPath, 'MERGE.md'));
    await addStat(parts, path.join(runPath, 'merge.json'));
    const tasksPath = path.join(runPath, 'tasks');
    await addStat(parts, tasksPath);
    for (const task of await readDirectory(tasksPath)) {
      if (task.isFile() && task.name.endsWith('.yaml')) await addStat(parts, path.join(tasksPath, task.name));
    }
    const artifactsPath = path.join(runPath, 'artifacts');
    await addStat(parts, artifactsPath);
    for (const artifact of await readDirectory(artifactsPath)) {
      if (!artifact.isDirectory()) continue;
      const artifactPath = path.join(artifactsPath, artifact.name);
      await addStat(parts, path.join(artifactPath, 'state.json'));
      await addStat(parts, path.join(artifactPath, 'acceptance.json'));
      await addStat(parts, path.join(artifactPath, 'heartbeat.json'));
      await addStat(parts, path.join(artifactPath, 'report.md'));
      await addStat(parts, path.join(artifactPath, 'review.json'));
      const attemptsPath = path.join(artifactPath, 'attempts');
      await addStat(parts, attemptsPath);
      for (const attempt of await readDirectory(attemptsPath)) {
        if (!attempt.isDirectory()) continue;
        const attemptPath = path.join(attemptsPath, attempt.name);
        await addStat(parts, path.join(attemptPath, 'control.json'));
        await addStat(parts, path.join(attemptPath, 'lane-bg.pid'));
        await addStat(parts, path.join(attemptPath, 'lane-bg.exit'));
        await addStat(parts, path.join(attemptPath, 'verification.json'));
      }
    }
  }

  const todosPath = path.join(agentsPath, 'todos');
  await addStat(parts, path.join(todosPath, 'INDEX.md'));
  const itemsPath = path.join(todosPath, 'items');
  await addStat(parts, itemsPath);
  for (const item of await readDirectory(itemsPath)) {
    const itemPath = path.join(itemsPath, item.name);
    if (item.isFile() && item.name.endsWith('.md')) await addStat(parts, itemPath);
    if (item.isDirectory()) await addStat(parts, path.join(itemPath, 'README.md'));
  }

  const sessionLogPath = path.join(agentsPath, 'session-log');
  await addStat(parts, sessionLogPath);
  for (const entry of await readDirectory(sessionLogPath)) {
    if (entry.isFile() && /^REVIEW-\d{4}-\d{2}-\d{2}\.md$/.test(entry.name)) {
      await addStat(parts, path.join(sessionLogPath, entry.name));
    }
  }
  return parts.sort().join('|');
}

/**
 * A polling watcher deliberately has no HTTP knowledge. Consumers receive a
 * project id and decide how to notify their own subscribers.
 */
export function createProjectWatcher({ getProjects, intervalMs = 5000 } = {}) {
  if (typeof getProjects !== 'function') throw new TypeError('getProjects must be a function');

  const listeners = new Set();
  const signals = new Map();
  let timer = null;
  let polling = false;

  async function poll() {
    if (polling) return;
    polling = true;
    try {
      const projects = await getProjects();
      const knownIds = new Set();
      for (const project of projects) {
        knownIds.add(project.id);
        const nextSignal = await projectSignal(project);
        const previousSignal = signals.get(project.id);
        signals.set(project.id, nextSignal);
        if (previousSignal !== undefined && previousSignal !== nextSignal) {
          for (const listener of listeners) {
            try {
              listener(project.id);
            } catch (error) {
              warn(`watch subscriber failed for ${project.id}`, error);
            }
          }
        }
      }
      for (const id of signals.keys()) {
        if (!knownIds.has(id)) signals.delete(id);
      }
    } catch (error) {
      warn('project polling failed', error);
    } finally {
      polling = false;
    }
  }

  return {
    async start() {
      if (timer) return;
      await poll();
      timer = setInterval(() => { void poll(); }, intervalMs);
      timer.unref?.();
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
      listeners.clear();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    poll,
  };
}
