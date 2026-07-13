import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { discoverProjects } from './lib/discover.mjs';
import { readAllReviews, readTaskDetail, readTodoBody, readTodos } from './lib/parsers.mjs';
import { searchAcrossProjects } from './lib/search.mjs';
import { buildProjectSnapshot, buildProjectSummaries, projectDetail } from './lib/snapshot.mjs';
import { createProjectWatcher } from './lib/watch.mjs';

const moduleDirectory = path.dirname(fileURLToPath(import.meta.url));
const boardDirectory = path.resolve(moduleDirectory, '..');
const webDirectory = path.join(boardDirectory, 'web');
const staticRootPrefix = `${webDirectory}${path.sep}`;

function defaultRoots() {
  const home = os.homedir();
  return ['apps', 'sites', 'tools'].map((name) => path.join(home, name));
}

function warn(message, error) {
  console.warn(`[lane-board] ${message}${error ? `: ${error.message}` : ''}`);
}

function sendJson(response, statusCode, body, method = 'GET') {
  const payload = JSON.stringify(body);
  response.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
  });
  if (method !== 'HEAD') response.end(payload);
  else response.end();
}

function contentType(filePath) {
  switch (path.extname(filePath).toLowerCase()) {
    case '.html': return 'text/html; charset=utf-8';
    case '.js': return 'text/javascript; charset=utf-8';
    case '.css': return 'text/css; charset=utf-8';
    case '.json': return 'application/json; charset=utf-8';
    case '.svg': return 'image/svg+xml';
    case '.png': return 'image/png';
    case '.jpg':
    case '.jpeg': return 'image/jpeg';
    case '.ico': return 'image/x-icon';
    default: return 'application/octet-stream';
  }
}

async function staticFile(requestPath) {
  let decodedPath;
  try {
    decodedPath = decodeURIComponent(requestPath);
  } catch {
    return null;
  }
  const relativePath = decodedPath === '/' ? 'index.html' : decodedPath.replace(/^\/+/, '');
  const requestedPath = path.resolve(webDirectory, relativePath);
  if (requestedPath !== webDirectory && !requestedPath.startsWith(staticRootPrefix)) return null;

  const indexPath = path.join(webDirectory, 'index.html');
  for (const candidate of [requestedPath, indexPath]) {
    try {
      if ((await stat(candidate)).isFile()) return candidate;
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') warn(`could not inspect static file ${candidate}`, error);
    }
  }
  return null;
}

async function serveStatic(request, response, requestPath) {
  const filePath = await staticFile(requestPath);
  if (!filePath) {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end(request.method === 'HEAD' ? '' : 'not found');
    return;
  }
  try {
    const body = await readFile(filePath);
    response.writeHead(200, {
      'content-type': contentType(filePath),
      'content-length': body.length,
    });
    response.end(request.method === 'HEAD' ? '' : body);
  } catch (error) {
    warn(`could not read static file ${filePath}`, error);
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end(request.method === 'HEAD' ? '' : 'not found');
  }
}

function sseHeaders(response) {
  response.writeHead(200, {
    'content-type': 'text/event-stream; charset=utf-8',
    'cache-control': 'no-cache',
    connection: 'keep-alive',
  });
  response.flushHeaders?.();
}

export function createLaneBoardServer({ roots = defaultRoots(), discoveryDepth = 3 } = {}) {
  const findProjects = () => discoverProjects({ roots, maxDepth: discoveryDepth });
  const watcher = createProjectWatcher({ getProjects: findProjects });

  const server = createServer(async (request, response) => {
    const method = request.method ?? 'GET';
    let requestUrl;
    try {
      requestUrl = new URL(request.url ?? '/', 'http://lane-board.local');
    } catch {
      sendJson(response, 404, { error: 'not found' }, method);
      return;
    }
    const pathname = requestUrl.pathname;

    if ((method === 'GET' || method === 'HEAD') && pathname === '/healthz') {
      sendJson(response, 200, { ok: true }, method);
      return;
    }

    if ((method === 'GET' || method === 'HEAD') && pathname === '/api/projects') {
      sendJson(response, 200, { projects: await buildProjectSummaries(await findProjects()) }, method);
      return;
    }

    if ((method === 'GET' || method === 'HEAD') && pathname === '/api/search') {
      const projects = await findProjects();
      const snapshots = await Promise.all(projects.map((project) => buildProjectSnapshot(project)));
      sendJson(response, 200, { results: searchAcrossProjects(snapshots, requestUrl.searchParams.get('q')) }, method);
      return;
    }

    const todoMatch = pathname.match(/^\/api\/projects\/([^/]+)\/todos\/([^/]+)$/);
    if ((method === 'GET' || method === 'HEAD') && todoMatch) {
      const projects = await findProjects();
      const project = projects.find((candidate) => candidate.id === todoMatch[1]);
      if (!project) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      const body = await readTodoBody(project.path, todoMatch[2]);
      if (body === null) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      const meta = (await readTodos(project.path)).find((todo) => todo.id === todoMatch[2]) ?? { id: todoMatch[2] };
      sendJson(response, 200, { meta, body }, method);
      return;
    }

    const taskMatch = pathname.match(/^\/api\/projects\/([^/]+)\/tasks\/([^/]+)\/([^/]+)$/);
    if ((method === 'GET' || method === 'HEAD') && taskMatch) {
      const projects = await findProjects();
      const project = projects.find((candidate) => candidate.id === taskMatch[1]);
      if (!project) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      const detail = await readTaskDetail(project.path, taskMatch[2], taskMatch[3]);
      if (detail === null) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      sendJson(response, 200, detail, method);
      return;
    }

    const reviewsMatch = pathname.match(/^\/api\/projects\/([^/]+)\/reviews$/);
    if ((method === 'GET' || method === 'HEAD') && reviewsMatch) {
      const projects = await findProjects();
      const project = projects.find((candidate) => candidate.id === reviewsMatch[1]);
      if (!project) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      sendJson(response, 200, { reviews: await readAllReviews(project.path) }, method);
      return;
    }

    const projectMatch = pathname.match(/^\/api\/projects\/([^/]+)$/);
    if ((method === 'GET' || method === 'HEAD') && projectMatch) {
      const projects = await findProjects();
      const project = projects.find((candidate) => candidate.id === projectMatch[1]);
      if (!project) {
        sendJson(response, 404, { error: 'not found' }, method);
        return;
      }
      const scope = requestUrl.searchParams.get('scope') === 'all' ? 'all' : 'recent';
      sendJson(response, 200, projectDetail(await buildProjectSnapshot(project, { scope })), method);
      return;
    }

    if (method === 'GET' && pathname === '/api/events') {
      sseHeaders(response);
      response.write(': connected\n\n');
      const unsubscribe = watcher.subscribe((projectId) => {
        if (!response.writableEnded) response.write(`event: refresh\ndata: ${JSON.stringify({ projectId })}\n\n`);
      });
      const heartbeat = setInterval(() => {
        if (!response.writableEnded) response.write(': heartbeat\n\n');
      }, 25_000);
      heartbeat.unref?.();
      const close = () => {
        clearInterval(heartbeat);
        unsubscribe();
      };
      request.once('close', close);
      return;
    }

    if (pathname.startsWith('/api/')) {
      sendJson(response, 404, { error: 'not found' }, method);
      return;
    }

    if (method === 'GET' || method === 'HEAD') {
      await serveStatic(request, response, pathname);
      return;
    }

    response.writeHead(405, { allow: 'GET, HEAD' });
    response.end();
  });

  return { server, watcher };
}

export async function startLaneBoardServer({
  host = process.env.HOST || '127.0.0.1',
  port = Number.parseInt(process.env.PORT || '4311', 10),
  ...options
} = {}) {
  const { server, watcher } = createLaneBoardServer(options);
  await watcher.start();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(Number.isInteger(port) && port > 0 ? port : 4311, host, () => {
      server.off('error', reject);
      resolve();
    });
  });
  return { server, watcher };
}

async function closeServer(server, watcher) {
  watcher.stop();
  await new Promise((resolve) => {
    server.close(() => resolve());
    server.closeAllConnections?.();
  });
}

async function main() {
  const { server, watcher } = await startLaneBoardServer();
  const address = server.address();
  const displayAddress = typeof address === 'object' && address ? `${address.address}:${address.port}` : 'unknown';
  console.log(`[lane-board] listening on ${displayAddress}`);

  let closing = false;
  const shutdown = async (signal) => {
    if (closing) return;
    closing = true;
    try {
      await closeServer(server, watcher);
      process.exit(0);
    } catch (error) {
      warn(`failed to stop after ${signal}`, error);
      process.exit(1);
    }
  };
  process.once('SIGINT', () => { void shutdown('SIGINT'); });
  process.once('SIGTERM', () => { void shutdown('SIGTERM'); });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    warn('failed to start', error);
    process.exit(1);
  });
}
