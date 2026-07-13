import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const TASK_STATUSES = new Set(['pending', 'running', 'done', 'blocked', 'stalled']);

function warn(message, error) {
  console.warn(`[lane-board] ${message}${error ? `: ${error.message}` : ''}`);
}

function scalar(value) {
  const trimmed = value.trim();
  if (!trimmed || trimmed === '|' || trimmed === '>') return null;

  const quote = trimmed[0];
  if (quote === '"' || quote === "'") {
    if (trimmed.length < 2 || trimmed.at(-1) !== quote) return null;
    return trimmed.slice(1, -1).replace(/\\"/g, '"').replace(/\\'/g, "'");
  }

  return trimmed.replace(/\s+#.*$/, '').trim() || null;
}

export function normalizeTaskStatus(status) {
  const normalized = String(status ?? '').trim().toLowerCase();
  return TASK_STATUSES.has(normalized) ? normalized : 'pending';
}

export function parseTaskYaml(source, { run = '', filePath = 'task YAML' } = {}) {
  if (typeof source !== 'string') {
    warn(`skipping malformed ${filePath}`);
    return null;
  }

  const fields = {};
  for (const line of source.split(/\r?\n/)) {
    const match = line.match(/^\s*(id|title|status|risk|lane|verify):\s*(.*?)\s*$/i);
    if (!match) continue;
    const value = scalar(match[2]);
    if (value === null) {
      warn(`skipping malformed scalar in ${filePath}`);
      return null;
    }
    fields[match[1].toLowerCase()] = value;
  }

  if (!fields.id || !fields.title) {
    warn(`skipping malformed ${filePath}: id and title are required`);
    return null;
  }

  return {
    id: fields.id,
    title: fields.title,
    status: normalizeTaskStatus(fields.status),
    risk: fields.risk ?? null,
    lane: fields.lane ?? null,
    verify: fields.verify ?? null,
    run,
  };
}

async function readDirectory(directory) {
  try {
    return await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${directory}`, error);
    return [];
  }
}

export async function readTasks(tasksDirectory, run) {
  const tasks = [];
  const entries = await readDirectory(tasksDirectory);

  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || !entry.name.endsWith('.yaml')) continue;
    const filePath = path.join(tasksDirectory, entry.name);
    try {
      const task = parseTaskYaml(await readFile(filePath, 'utf8'), { run, filePath });
      if (task) tasks.push(task);
    } catch (error) {
      warn(`could not read ${filePath}`, error);
    }
  }

  return tasks;
}

export function parseProgress(source) {
  const progress = { now: [], blocked: [], next: [] };
  if (typeof source !== 'string') return progress;

  const headings = new Map([
    ['## Now', 'now'],
    ['## Blocked', 'blocked'],
    ['## Next', 'next'],
  ]);
  let section = null;
  let currentBullet = null;

  for (const line of source.split(/\r?\n/)) {
    const heading = headings.get(line.trim());
    if (heading) {
      section = heading;
      currentBullet = null;
      continue;
    }
    if (/^##\s+/.test(line.trim())) {
      section = null;
      currentBullet = null;
      continue;
    }
    if (!section) continue;

    const bullet = line.match(/^-\s+(.+)\s*$/);
    if (bullet) {
      progress[section].push(bullet[1].trim());
      currentBullet = progress[section].length - 1;
      continue;
    }
    if (currentBullet !== null && /^\s+\S/.test(line)) {
      progress[section][currentBullet] = `${progress[section][currentBullet]} ${line.trim()}`;
    }
  }

  return progress;
}

export async function readProgress(projectPath) {
  const filePath = path.join(projectPath, 'PROGRESS.md');
  try {
    return parseProgress(await readFile(filePath, 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${filePath}`, error);
    return { now: [], blocked: [], next: [] };
  }
}

function markdownCells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
}

function isSeparatorRow(cells) {
  return cells.length === 4 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

export function parseTodosIndex(source) {
  if (typeof source !== 'string') return null;
  const lines = source.split(/\r?\n/);
  const expectedHeader = ['status', 'priority', 'id', 'title'];
  const headerIndex = lines.findIndex((line) => {
    if (!line.trim().startsWith('|')) return false;
    const cells = markdownCells(line).map((cell) => cell.toLowerCase());
    return cells.length === expectedHeader.length && cells.every((cell, index) => cell === expectedHeader[index]);
  });

  if (headerIndex === -1) return null;
  const todos = [];
  for (let index = headerIndex + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) break;
    if (!line.trim().startsWith('|')) break;
    const cells = markdownCells(line);
    if (isSeparatorRow(cells)) continue;
    if (cells.length !== 4) {
      warn(`skipping malformed todo row: ${line.trim()}`);
      continue;
    }
    const [status, priority, id, title] = cells;
    if (!id) {
      warn(`skipping todo row without id: ${line.trim()}`);
      continue;
    }
    todos.push({ status, priority: priority || null, id, title });
  }

  return todos;
}

async function fallbackTodos(itemsDirectory) {
  const todos = [];
  for (const entry of await readDirectory(itemsDirectory)) {
    if (entry.isDirectory()) {
      todos.push({ status: 'open', priority: null, id: entry.name, title: entry.name });
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      todos.push({
        status: 'open',
        priority: null,
        id: path.basename(entry.name, '.md'),
        title: entry.name,
      });
    }
  }
  return todos.sort((left, right) => left.id.localeCompare(right.id));
}

export async function readTodos(projectPath) {
  const todosDirectory = path.join(projectPath, '.agents', 'todos');
  const indexPath = path.join(todosDirectory, 'INDEX.md');
  try {
    const todos = parseTodosIndex(await readFile(indexPath, 'utf8'));
    if (todos !== null) return todos;
    warn(`could not parse ${indexPath}; falling back to todo items`);
  } catch (error) {
    if (error.code !== 'ENOENT') warn(`could not read ${indexPath}; falling back to todo items`, error);
  }
  return fallbackTodos(path.join(todosDirectory, 'items'));
}

export function parseReview(source, date) {
  const review = { date, verdicts: [], findings: [], fixPlan: [] };
  if (typeof source !== 'string') return review;

  let inFixPlan = false;
  for (const line of source.split(/\r?\n/)) {
    const heading = line.trim();
    if (/^##\s+/.test(heading)) {
      inFixPlan = heading.toLowerCase() === '## morning fix plan';
      continue;
    }

    const actualVerdict = line.match(/^\s*(.+?)\s+—\s+VERDICT:\s*(passed|failed)\b/i);
    const alternateVerdict = line.match(/^\s*VERDICT\s+(.+?):\s*(passed|failed)\b/i);
    const verdict = actualVerdict ?? alternateVerdict;
    if (verdict) {
      review.verdicts.push({ scope: verdict[1].trim(), verdict: verdict[2].toLowerCase() });
    }

    const finding = line.match(/^\s*(P[01]):\s*(.+?)\s*$/i);
    if (finding) {
      const remainder = finding[2].trim();
      const dashIndex = remainder.indexOf('—');
      review.findings.push({
        level: finding[1].toUpperCase(),
        text: (dashIndex === -1 ? remainder : remainder.slice(dashIndex + 1)).trim(),
      });
    }

    const fixPlanItem = inFixPlan ? line.match(/^\s*-\s*\[ \]\s+(.+)\s*$/) : null;
    if (fixPlanItem) review.fixPlan.push(fixPlanItem[1].trim());
  }

  return review;
}

export async function readLatestReview(projectPath) {
  const directory = path.join(projectPath, '.agents', 'session-log');
  const entries = await readDirectory(directory);
  const reviewFiles = entries
    .filter((entry) => entry.isFile())
    .map((entry) => ({ entry, match: entry.name.match(/^REVIEW-(\d{4}-\d{2}-\d{2})\.md$/) }))
    .filter(({ match }) => match)
    .sort((left, right) => right.match[1].localeCompare(left.match[1]));

  for (const { entry, match } of reviewFiles) {
    const filePath = path.join(directory, entry.name);
    try {
      return parseReview(await readFile(filePath, 'utf8'), match[1]);
    } catch (error) {
      warn(`could not read ${filePath}`, error);
    }
  }
  return null;
}
