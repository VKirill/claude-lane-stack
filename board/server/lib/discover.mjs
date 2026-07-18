import { createHash } from 'node:crypto';
import { lstat, readdir } from 'node:fs/promises';
import path from 'node:path';

const PRUNED_DIRECTORY_NAMES = new Set(['.agents', '.git', 'node_modules', 'postgres_data']);

function warn(message, error) {
  console.warn(`[lane-board] ${message}${error ? `: ${error.message}` : ''}`);
}

async function isDirectory(target) {
  try {
    return (await lstat(target)).isDirectory();
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not inspect ${target}`, error);
    return false;
  }
}

async function readDirectories(directory) {
  try {
    return await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${directory}`, error);
    return [];
  }
}

export function projectId(projectPath) {
  return createHash('sha256').update(path.resolve(projectPath)).digest('hex').slice(0, 16);
}

/**
 * Find repository roots below the supplied search roots. A project must have a
 * real .git directory, intentionally excluding Git worktrees whose marker is
 * a .git file.
 */
export async function discoverProjects({ roots, maxDepth = 3 } = {}) {
  const projects = [];
  const seen = new Set();

  for (const root of roots ?? []) {
    const absoluteRoot = path.resolve(root);
    const queue = [{ directory: absoluteRoot, depth: 0 }];

    while (queue.length > 0) {
      const { directory, depth } = queue.shift();
      const gitDirectory = await isDirectory(path.join(directory, '.git'));
      const runsDirectory = await isDirectory(path.join(directory, '.agents', 'runs'));

      if (gitDirectory && runsDirectory && !seen.has(directory)) {
        seen.add(directory);
        projects.push({
          id: projectId(directory),
          name: path.basename(directory),
          path: directory,
        });
      }

      if (depth >= maxDepth) continue;

      for (const entry of await readDirectories(directory)) {
        if (!entry.isDirectory() || PRUNED_DIRECTORY_NAMES.has(entry.name)) continue;
        queue.push({ directory: path.join(directory, entry.name), depth: depth + 1 });
      }
    }
  }

  return projects.sort((left, right) => left.path.localeCompare(right.path));
}
