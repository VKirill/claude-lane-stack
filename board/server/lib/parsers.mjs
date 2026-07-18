import { readdir, readFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
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

function safePathSegment(value) {
  return typeof value === 'string' && value !== '.' && value !== '..' && path.basename(value) === value;
}

export function normalizeTaskStatus(status) {
  const normalized = String(status ?? '').trim().toLowerCase();
  return TASK_STATUSES.has(normalized) ? normalized : 'pending';
}

export function promoteMergedTaskStatus(status, merged, schemaVersion = 1) {
  if (schemaVersion >= 2) return status;
  return status === 'pending' && merged?.commit ? 'done' : status;
}

function runtimeStatusToBoard(status) {
  const normalized = String(status ?? '').trim().toLowerCase();
  if (['accepted', 'done', 'failed', 'cancelled', 'verification_failed', 'blocked'].includes(normalized)) return 'blocked';
  if (normalized === 'stalled') return 'stalled';
  if (['starting', 'running', 'awaiting_verification', 'verifying', 'verified'].includes(normalized)) return 'running';
  return 'pending';
}

async function readJsonObject(filePath) {
  try {
    const value = JSON.parse(await readFile(filePath, 'utf8'));
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR' && !(error instanceof SyntaxError)) {
      warn(`could not read ${filePath}`, error);
    }
    return null;
  }
}

async function readInteger(filePath) {
  try {
    const source = (await readFile(filePath, 'utf8')).trim();
    if (!/^-?\d+$/.test(source)) return null;
    const value = Number(source);
    return Number.isInteger(value) ? value : null;
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read ${filePath}`, error);
    return null;
  }
}

async function fileAgeSeconds(filePath) {
  try {
    const info = await stat(filePath);
    return Math.max(0, Math.floor((Date.now() - info.mtimeMs) / 1000));
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not inspect ${filePath}`, error);
    return null;
  }
}

async function pidAlive(pid, expectedStart) {
  if (!Number.isInteger(pid) || pid <= 1) return false;
  try {
    const parts = (await readFile(`/proc/${pid}/stat`, 'utf8')).trim().split(/\s+/);
    if (parts.length < 22 || parts[2] === 'Z') return false;
    if (Number.isInteger(expectedStart) && Number(parts[21]) !== expectedStart) return false;
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function reportEvidence(filePath) {
  try {
    const match = (await readFile(filePath, 'utf8')).match(/^\s*STATUS\s*:\s*([A-Za-z_-]+)\b/im);
    return { exists: true, complete: match?.[1]?.toLowerCase() === 'complete' };
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read ${filePath}`, error);
    return { exists: false, complete: false };
  }
}

function stateLifecycle(status) {
  const normalized = typeof status === 'string' && status.trim() ? status.trim().toLowerCase() : 'not_started';
  if (normalized === 'accepted') {
    return {
      status: 'unknown',
      reason: 'acceptance_receipt_missing',
      next_action: 'inspect',
    };
  }
  const known = {
    awaiting_verification: ['provider_complete', 'verify'],
    blocked: ['blocked', 'inspect'],
    cancelled: ['cancel_requested', 'retry'],
    failed: ['provider_exit_nonzero', 'retry'],
    launching: ['provider_starting', 'wait'],
    not_started: ['not_started', 'start'],
    provider_incomplete: ['report_incomplete', 'retry'],
    running: ['provider_state_recorded', 'inspect'],
    stalled: ['heartbeat_stalled', 'cancel'],
    verified: ['verification_passed', 'accept'],
    verification_failed: ['verification_failed', 'retry'],
    verifying: ['verification_running', 'wait'],
  };
  const [reason, nextAction] = known[normalized] ?? ['unrecognized_state', 'inspect'];
  return { status: normalized, reason, next_action: nextAction };
}

function trustedVerification(verification, state, taskId, attempt) {
  return verification?.schema_version === 2
    && verification.task_id === taskId
    && verification.task_sha256 === state.task_sha256
    && verification.task_file === state.task_file
    && verification.project_cwd === state.project_cwd
    && verification.attempt === attempt;
}

async function readTaskRuntime(runPath, taskId, taskSha256) {
  if (!safePathSegment(taskId)) return null;
  const artifactPath = path.join(runPath, 'artifacts', taskId);
  const acceptance = await readJsonObject(path.join(artifactPath, 'acceptance.json'));
  const state = await readJsonObject(path.join(artifactPath, 'state.json'));
  const currentAttempt = state?.current_attempt ?? state?.attempt;
  const accepted = (
    acceptance?.schema_version === 2
    && acceptance?.task_id === taskId
    && acceptance?.task_sha256 === taskSha256
    && Number.isInteger(acceptance?.attempt)
    && acceptance.attempt > 0
    && acceptance.attempt === currentAttempt
    && acceptance?.provider_exit === 0
    && acceptance?.report === 'complete'
    && acceptance?.owns_check === 'passed'
    && acceptance?.verification === 'passed'
    && ['passed', 'not_required'].includes(acceptance?.review)
    && acceptance?.accepted === true
    && typeof acceptance?.accepted_at === 'string'
    && acceptance.accepted_at.length > 0
  );
  if (!state) return null;

  const attempt = Number.isInteger(currentAttempt) && currentAttempt > 0 && currentAttempt < 100
    ? currentAttempt
    : null;
  const attemptPath = attempt === null ? null : path.join(artifactPath, 'attempts', String(attempt).padStart(2, '0'));
  const control = attemptPath ? await readJsonObject(path.join(attemptPath, 'control.json')) : null;
  const pid = attemptPath ? await readInteger(path.join(attemptPath, 'lane-bg.pid')) : null;
  const exitCode = attemptPath ? await readInteger(path.join(attemptPath, 'lane-bg.exit')) : null;
  const running = await pidAlive(pid, control?.pid_start_time);
  const heartbeatAge = await fileAgeSeconds(path.join(artifactPath, 'heartbeat.json'));
  const report = await reportEvidence(path.join(artifactPath, 'report.md'));
  const verification = attemptPath ? await readJsonObject(path.join(attemptPath, 'verification.json')) : null;
  const verificationTrusted = trustedVerification(verification, state, taskId, attempt);

  let lifecycle;
  if (accepted) lifecycle = { status: 'accepted', reason: 'acceptance_valid', next_action: 'none' };
  else if (state.status === 'cancelled') lifecycle = stateLifecycle('cancelled');
  else if (state.status === 'blocked') lifecycle = stateLifecycle('blocked');
  else if (state.status === 'stalled' && running) lifecycle = stateLifecycle('stalled');
  else if (running) lifecycle = { status: 'running', reason: 'provider_running', next_action: 'wait' };
  else if (exitCode === 0 && !report.complete) {
    lifecycle = {
      status: 'provider_incomplete',
      reason: report.exists ? 'report_incomplete' : 'report_missing',
      next_action: 'retry',
    };
  } else if (exitCode === 0 && verificationTrusted && verification.status === 'passed') {
    lifecycle = { status: 'verified', reason: 'verification_passed', next_action: 'accept' };
  } else if (exitCode === 0 && verificationTrusted && verification.status === 'failed') {
    lifecycle = { status: 'verification_failed', reason: 'verification_failed', next_action: 'retry' };
  } else if (exitCode === 0 && verificationTrusted && verification.status === 'running') {
    lifecycle = { status: 'verifying', reason: 'verification_running', next_action: 'wait' };
  } else if (exitCode === 0) {
    lifecycle = { status: 'awaiting_verification', reason: 'provider_complete', next_action: 'verify' };
  } else if (exitCode !== null) {
    lifecycle = { status: 'failed', reason: 'provider_exit_nonzero', next_action: 'retry' };
  } else if (control) {
    lifecycle = { status: 'unknown', reason: 'provider_state_unknown', next_action: 'inspect' };
  } else lifecycle = stateLifecycle(state.status);

  const runtime = {
    status: lifecycle.status,
    attempt,
    pid,
    running,
    exit_code: exitCode,
    heartbeat_age_seconds: heartbeatAge,
    report_complete: report.complete,
    reason: lifecycle.reason,
    next_action: lifecycle.next_action,
  };
  return { status: accepted ? 'done' : runtimeStatusToBoard(runtime.status), runtime, acceptance, state };
}


export function parseTaskYaml(source, { run = '', filePath = 'task YAML' } = {}) {
  if (typeof source !== 'string') {
    warn(`skipping malformed ${filePath}`);
    return null;
  }

  const fields = {};
  for (const line of source.split(/\r?\n/)) {
    const match = line.match(/^\s*(schema_version|id|title|status|risk|lane|verify):\s*(.*?)\s*$/i);
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

  const task = {
    id: fields.id,
    title: fields.title,
    status: Number(fields.schema_version) === 2 ? 'pending' : normalizeTaskStatus(fields.status),
    risk: fields.risk ?? null,
    lane: fields.lane ?? null,
    verify: fields.verify ?? null,
    run,
  };
  if (Number(fields.schema_version) === 2) task.schemaVersion = 2;
  return task;
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
  const runPath = path.dirname(tasksDirectory);

  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || !entry.name.endsWith('.yaml')) continue;
    const filePath = path.join(tasksDirectory, entry.name);
    try {
      const source = await readFile(filePath, 'utf8');
      const task = parseTaskYaml(source, { run, filePath });
      if (task) {
        const taskSha256 = createHash('sha256').update(source).digest('hex');
        const runtime = await readTaskRuntime(runPath, task.id, taskSha256);
        if (runtime) {
          task.status = runtime.status;
          task.runtime = runtime.runtime;
        }
        tasks.push(task);
      }
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

export async function readTodoBody(projectPath, todoId) {
  if (!safePathSegment(todoId)) return null;

  const itemsDirectory = path.join(projectPath, '.agents', 'todos', 'items');
  const candidates = [
    path.join(itemsDirectory, `${todoId}.md`),
    path.join(itemsDirectory, todoId, 'README.md'),
  ];
  for (const filePath of candidates) {
    try {
      return await readFile(filePath, 'utf8');
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read ${filePath}`, error);
    }
  }
  return null;
}

export function parseMerge(source) {
  const result = { date: null, commit: null };
  if (typeof source !== 'string') return result;

  result.date = source.match(/\b\d{4}-\d{2}-\d{2}\b/)?.[0] ?? null;
  const normalized = source.replace(/\*\*/g, '');
  const mergeCommit = normalized.match(/\bmerge\s+commit(?:\s+on\s+main)?\b(?:\s*:\s*|\s+)(`?[a-f0-9]{7,40}`?)/i);
  const genericCommit = normalized.match(/\b(?:feat(?:ure)?\s+)?commit\b(?:\s*:\s*|\s+)(`?[a-f0-9]{7,40}`?)/i);
  result.commit = (mergeCommit ?? genericCommit)?.[1]?.replace(/`/g, '') ?? null;
  return result;
}

export async function readMerge(runPath) {
  const receipt = await readJsonObject(path.join(runPath, 'merge.json'));
  if (receipt) {
    const completedAt = typeof receipt.completed_at === 'string' ? receipt.completed_at : '';
    const commit = typeof receipt.merge_commit === 'string' ? receipt.merge_commit : null;
    return { date: completedAt.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? null, commit };
  }
  const filePath = path.join(runPath, 'MERGE.md');
  try {
    return parseMerge(await readFile(filePath, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return null;
    warn(`could not read ${filePath}`, error);
    return { date: null, commit: null };
  }
}

function stripCommonIndentation(lines) {
  const indents = lines
    .filter((line) => /\S/.test(line))
    .map((line) => line.match(/^\s*/)[0].length);
  const indentation = indents.length > 0 ? Math.min(...indents) : 0;
  return lines.map((line) => line.slice(Math.min(indentation, line.length))).join('\n').trimEnd();
}

/** Parse the richer task-detail subset without changing the task-list parser. */
export function parseTaskDetail(source) {
  const detail = { objective: '', done_when: [] };
  if (typeof source !== 'string') return detail;

  let block = null;
  const finishBlock = () => {
    if (!block) return;
    if (block.kind === 'objective') detail.objective = stripCommonIndentation(block.lines);
    block = null;
  };

  for (const line of source.split(/\r?\n/)) {
    const field = line.match(/^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$/);
    if (field) {
      finishBlock();
      const key = field[1];
      const value = field[2];
      if (value === '|' || value === '>') {
        block = { kind: key === 'objective' ? 'objective' : 'skip', lines: [] };
        continue;
      }
      if (!value && key === 'done_when') {
        block = { kind: 'done_when', lines: [] };
        continue;
      }
      const parsed = scalar(value);
      if (parsed !== null) detail[key] = key === 'status' ? normalizeTaskStatus(parsed) : parsed;
      continue;
    }

    if (!block) continue;
    if (block.kind === 'done_when') {
      const item = line.match(/^\s*-\s+(.+?)\s*$/);
      if (item) {
        const value = scalar(item[1]);
        if (value !== null) detail.done_when.push(value);
      }
      continue;
    }
    if (block.kind === 'objective') block.lines.push(line);
  }
  finishBlock();
  return detail;
}

async function readTaskSource(tasksDirectory, taskId) {
  const exactPath = path.join(tasksDirectory, `${taskId}.yaml`);
  try {
    return await readFile(exactPath, 'utf8');
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read ${exactPath}`, error);
  }

  const entries = await readDirectory(tasksDirectory);
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || !entry.name.startsWith(taskId) || !entry.name.endsWith('.yaml')) continue;
    const filePath = path.join(tasksDirectory, entry.name);
    try {
      return await readFile(filePath, 'utf8');
    } catch (error) {
      warn(`could not read ${filePath}`, error);
    }
  }
  return null;
}

async function readTaskReport(runPath, taskId) {
  const artifactsDirectory = path.join(runPath, 'artifacts');
  const entries = await readDirectory(artifactsDirectory);
  const exact = entries.find((entry) => entry.isDirectory() && entry.name === taskId);
  const artifact = exact ?? entries
    .filter((entry) => entry.isDirectory() && entry.name.startsWith(taskId))
    .sort((left, right) => right.name.localeCompare(left.name))[0];
  if (!artifact) return null;

  const filePath = path.join(artifactsDirectory, artifact.name, 'report.md');
  try {
    return (await readFile(filePath, 'utf8')).split(/\r?\n/).slice(0, 60).join('\n');
  } catch (error) {
    if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not read ${filePath}`, error);
    return null;
  }
}

export async function readTaskDetail(projectPath, run, taskId) {
  if (!safePathSegment(run) || !safePathSegment(taskId)) return null;
  const runPath = path.join(projectPath, '.agents', 'runs', run);
  const source = await readTaskSource(path.join(runPath, 'tasks'), taskId);
  if (source === null) return null;
  const detail = parseTaskDetail(source);
  const taskSha256 = createHash('sha256').update(source).digest('hex');
  const runtime = await readTaskRuntime(runPath, taskId, taskSha256);
  if (runtime) {
    detail.status = runtime.status;
    detail.runtime = runtime.runtime;
  } else if (detail.status !== undefined) {
    const merged = await readMerge(runPath);
    detail.status = promoteMergedTaskStatus(detail.status, merged);
  }
  return { ...detail, report: await readTaskReport(runPath, taskId) };
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

export async function readAllReviews(projectPath) {
  const directory = path.join(projectPath, '.agents', 'session-log');
  const entries = await readDirectory(directory);
  const reviewFiles = entries
    .filter((entry) => entry.isFile())
    .map((entry) => ({ entry, match: entry.name.match(/^REVIEW-(\d{4}-\d{2}-\d{2})\.md$/) }))
    .filter(({ match }) => match)
    .sort((left, right) => right.match[1].localeCompare(left.match[1]));
  const reviews = [];

  for (const { entry, match } of reviewFiles) {
    const filePath = path.join(directory, entry.name);
    try {
      const source = await readFile(filePath, 'utf8');
      if (!source.trim()) {
        warn(`skipping empty review ${filePath}`);
        continue;
      }
      reviews.push(parseReview(source, match[1]));
    } catch (error) {
      warn(`could not read ${filePath}`, error);
    }
  }
  return reviews;
}
