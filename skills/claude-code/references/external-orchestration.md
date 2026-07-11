# External orchestration — running Claude Code from outside

> Claude Code does **not** ship an HTTP daemon like `opencode serve`. The three supported patterns: (a) headless `claude -p` per-invocation, (b) `claude agents` background sessions (current 2.1.140+), (c) Anthropic Agent SDK in a subprocess. For raw API calls without the CLI, use the `claude-api` skill.

> Verified 2026-05-16 against <https://code.claude.com/docs/en/headless> and the upstream CHANGELOG at `github.com/anthropics/claude-code` (current 2.1.142).

## Pattern A — Headless `claude -p` (per-invocation)

Already covered in detail in [interop.md](./interop.md). Quick recap:

```bash
claude --bare -p "Explain auth.py" --allowedTools "Read" --output-format json
```

- `--bare` (current default-bound in a future release): skips hooks, skills, MCP, CLAUDE.md auto-discovery — pure, reproducible runs. Recommended for CI.
- `--output-format {text|json|stream-json}` — JSONL stream with `--verbose --include-partial-messages` for live tokens.
- `--json-schema '{...}'` forces structured output into `.structured_output`.
- stdin cap is **10 MB** (since 2.1.128); above that, write to a file.
- Subscription users: starting **2026-06-15**, `claude -p` and SDK calls draw from a separate monthly Agent SDK credit pool.

Exit codes: `0` success, `1` blocked/error, `2` user cancelled.

## Pattern B — Background sessions (`claude agents`)

Added through 2.1.140–2.1.142. A long-running daemon process manages "agent sessions" — like tmux for Claude runs. Useful when you want to dispatch work, walk away, attach later.

### Spawning

```bash
# Background a session at this cwd, with permissions baked in
claude --bg --dangerously-skip-permissions -p "Run the migration suite and fix failures"

# Or dispatch via the claude agents subcommand (2.1.142 added the full flag set)
claude agents \
  --cwd /srv/myapp \
  --add-dir /srv/shared \
  --settings ~/myapp.settings.json \
  --mcp-config ~/myapp.mcp.json \
  --plugin-dir /opt/claude-plugins/my-plugin \
  --permission-mode acceptEdits \
  --model claude-sonnet-4-6 \
  --effort high \
  --dangerously-skip-permissions
```

Listed flags are upstream-verified from CHANGELOG 2.1.142.

### Listing & scoping

```bash
# All background sessions
claude agents

# Only those launched in a given directory (2.1.141)
claude agents --cwd /srv/myapp
```

### Attaching & abandoning

Inside an interactive `claude` session, `←` cycles through background sessions; pressing once again detaches and returns to TUI. Empty/idle sessions are auto-retired after **5 minutes** (CHANGELOG 2.1.142). To explicitly abandon, attach and `/exit`.

### Liveness & state

The daemon process is a long-running supervisor:

- Crash detection: if the binary upgrades (e.g. `brew upgrade`), 2.1.142 fixed the daemon-not-exiting-cleanly bug that crash-looped dispatched agents. Practical advice: after upgrading, run `claude agents` once to verify the supervisor is healthy.
- Permission mode is now preserved across `/bg` / `←←` dispatch (2.1.141).
- Background side-queries use `ANTHROPIC_SMALL_FAST_MODEL` if set (Bedrock/Vertex/Foundry/gateway environments — 2.1.141).

### Limits

- No HTTP API. Orchestration is **CLI-driven** (other processes shell out to `claude agents` or watch its output).
- Output goes to log files under `~/.claude/sessions/<id>/` (path may vary by OS). Treat as semi-stable; for programmatic consumption prefer the Pattern C subprocess approach with `--output-format stream-json`.
- "Research preview" status — exact subcommand surface may shift release-to-release. Re-verify against the CHANGELOG when targeting a specific version.

## Pattern C — Subprocess from your own server (timeout-independent)

The most robust embedding: spawn `claude -p` from your Node process, stream JSONL on stdout, never block your HTTP handler.

```ts
// claude-runner.ts — Node 24, no extra deps
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

export type ClaudeEvent =
  | { type: 'system'; subtype: string; [k: string]: unknown }
  | { type: 'message'; content: Array<{ type: string; text?: string }> }
  | { type: 'tool_use'; [k: string]: unknown }
  | { type: 'result'; result: string; session_id: string; total_cost_usd: number };

export async function* runClaude(prompt: string, opts: {
  cwd?: string;
  allowedTools?: string;
  maxTurns?: number;
  signal?: AbortSignal;
} = {}): AsyncGenerator<ClaudeEvent> {
  const args = [
    '--bare', '-p', prompt,
    '--output-format', 'stream-json',
    '--verbose', '--include-partial-messages',
  ];
  if (opts.allowedTools) args.push('--allowedTools', opts.allowedTools);
  if (opts.maxTurns) args.push('--max-turns', String(opts.maxTurns));

  const child = spawn('claude', args, { cwd: opts.cwd, stdio: ['ignore', 'pipe', 'pipe'] });
  opts.signal?.addEventListener('abort', () => child.kill('SIGINT'));

  const rl = createInterface({ input: child.stdout });
  for await (const line of rl) {
    if (!line.trim()) continue;
    try { yield JSON.parse(line); } catch { /* tolerate non-JSON noise */ }
  }
  const code: number = await new Promise((r) => child.on('exit', r));
  if (code !== 0 && code !== null) throw new Error(`claude exited ${code}`);
}

// Usage inside an HTTP handler — non-blocking from the client's perspective
// (the handler returns 202 immediately, work continues; status surfaced via WS/SSE/poll)
for await (const ev of runClaude('Review the diff', { allowedTools: 'Read,Bash(git diff *)' })) {
  if (ev.type === 'result') console.log('done:', ev.result);
}
```

Pair with a queue (BullMQ) so the HTTP request doesn't wait on the subprocess at all — see Wrong-vs-right #1 below.

## Comparison vs `opencode serve` / `codex app-server`

| Capability | Claude Code | OpenCode `serve` | Codex `app-server` |
|---|---|---|---|
| HTTP API | ❌ (subprocess only) | ✅ `:4096` + live OpenAPI at `/doc` | ❌ (JSON-RPC over stdio / WebSocket) |
| Streaming | `--output-format stream-json` JSONL on stdout | SSE `/event`, `/global/event` | JSON-RPC notifications |
| Async submit | `claude --bg` / `claude agents` (daemon-managed) OR spawn detached | `POST /session/:id/prompt_async` (returns 204) | JSON-RPC method, response is awaited via notification |
| Liveness | `claude agents` listing; `kill -0 $PID` for spawned | `GET /global/health` | JSON-RPC ping / connection state |
| Abort | `SIGINT` to subprocess; `/exit` inside attached session | `POST /session/:id/abort` | JSON-RPC abort method |
| Auth | OS user + `ANTHROPIC_API_KEY` env | HTTP Basic (`OPENCODE_SERVER_PASSWORD`) | Filesystem perms (socket) or `--remote-auth-token-env` (WS) |
| Multi-client | One daemon, but no concurrent external clients via HTTP | Many HTTP clients concurrently | One IPC peer at a time per server |
| Best for | Per-task CI runs; background dispatched work | Web backends, browser clients, multi-process orchestration | Editor/IDE plugins, single-process embedding |

Bottom line: when the requirement is "external HTTP caller that survives long-running model work without holding a connection," **OpenCode `serve` is the only one of the three with a first-class HTTP daemon**. Claude Code and Codex require subprocess management.

## Production patterns

### Queue long invocations (recommended)

Don't run `claude -p` in the request thread. Push the job to BullMQ; the worker spawns Claude:

```ts
// queue producer (in HTTP handler) — returns immediately
await reviewQueue.add('pr-review', { prNumber, prompt });
return reply.code(202).send({ jobId: job.id });

// worker — bounded concurrency, retries, observability
new Worker('pr-review', async (job) => {
  let final = '';
  for await (const ev of runClaude(job.data.prompt, { maxTurns: 6 })) {
    if (ev.type === 'result') final = ev.result;
  }
  return final;
}, { concurrency: 2 });
```

See the `bullmq` skill for full setup.

### Liveness probes for `claude agents`

```bash
# Returns one line per session; empty exit = no sessions
claude agents --cwd "$PWD" || exit 1
```

For supervised processes spawned directly:

```bash
kill -0 "$PID" 2>/dev/null || echo "claude subprocess died"
```

### systemd for a long-lived `claude agents` worker

```ini
# /etc/systemd/system/claude-bg.service
[Unit]
Description=Claude Code background dispatcher
After=network-online.target

[Service]
Type=simple
User=claude
WorkingDirectory=/srv/myapp
EnvironmentFile=/etc/claude/env   # ANTHROPIC_API_KEY=...
ExecStart=/usr/local/bin/claude --bg --dangerously-skip-permissions -p "watch for work and process"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

> `--dangerously-skip-permissions` here is appropriate **only** inside a hardened container/VM. Don't run this on a developer laptop.

## Wrong-vs-right

### 1. Don't block your HTTP handler on `claude -p`

```ts
// ❌ Caller times out; node event loop tied up for 5 minutes
app.post('/review', async (req, reply) => {
  const out = execSync(`claude -p "${req.body.prompt}" --output-format json`);
  reply.send(JSON.parse(out.toString()));
});

// ✅ Enqueue; respond 202; worker spawns Claude; client polls or SSEs.
app.post('/review', async (req, reply) => {
  const job = await reviewQueue.add('pr-review', { prompt: req.body.prompt });
  reply.code(202).send({ jobId: job.id });
});
```

### 2. Don't buffer all of stdout

```ts
// ❌ Buffers gigabytes for a long session, OOMs on big repos
const { stdout } = await execFile('claude', ['-p', prompt, '--output-format', 'stream-json']);
const events = stdout.split('\n').filter(Boolean).map(JSON.parse);

// ✅ Stream line-by-line with readline.
for await (const ev of runClaude(prompt)) { /* ... */ }
```

### 3. Don't `SIGKILL` mid-run

```ts
// ❌ Leaves auth tokens / tmp files dangling; no graceful flush
child.kill('SIGKILL');

// ✅ SIGINT, wait up to 5s, then escalate.
child.kill('SIGINT');
const killer = setTimeout(() => child.kill('SIGKILL'), 5000);
await new Promise((r) => child.on('exit', r));
clearTimeout(killer);
```

## See also

- `opencode/references/server-mode.md` — the HTTP-first equivalent
- `codex/references/interop.md` — `codex app-server` JSON-RPC embedding
- `bullmq` — queue + worker pattern for offloading long runs
- `nodejs` — `child_process` patterns, `AbortController`, streams
- `linux-sysadmin` — systemd unit + reverse proxy patterns
