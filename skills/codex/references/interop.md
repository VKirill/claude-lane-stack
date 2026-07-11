# Interop — Headless, `app-server`, CI/CD

## Headless one-shot

```bash
codex exec "<prompt>" --json
```

Output is JSON (with `--json`) or plain text otherwise. JSON shape:

```json
{
  "session_id": "...",
  "result": "...final assistant text...",
  "usage": { "input_tokens": ..., "output_tokens": ... },
  "exit_code": 0
}
```

## `codex app-server` (v0.130+)

```bash
codex app-server
```

Starts a headless **app-server** that other processes can drive via IPC (Unix socket / stdio). Designed for embedding Codex into larger pipelines:
- A custom UI that uses Codex as backend
- An IDE plugin that wraps Codex
- A test harness that spawns many Codex sessions

```bash
# Example: pipe commands in
echo '{"cmd":"prompt","text":"summarize the diff"}' | codex app-server --stdio
```

## GitHub Actions

### Hand-rolled headless workflow

```yaml
name: Codex PR Review
on: pull_request
jobs:
  review:
    runs-on: ubuntu-latest
    permissions: { pull-requests: write, contents: read }
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - name: Install Codex
        run: npm i -g @openai/codex@0.130.0

      - name: Compute diff
        run: |
          git fetch origin ${{ github.event.pull_request.base.ref }}
          git diff origin/${{ github.event.pull_request.base.ref }}...HEAD > /tmp/diff.patch

      - name: Review with Codex
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          codex exec "Review the diff in /tmp/diff.patch. Reply 'OK' or list concerns." \
            -p ci-review \
            --json \
            > /tmp/run.json
          jq -r '.result' /tmp/run.json > /tmp/review.md

      - name: Comment PR
        env: { GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
        run: gh pr comment ${{ github.event.pull_request.number }} --body-file /tmp/review.md
```

`-p ci-review` uses the profile:

```toml
[profiles.ci-review]
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "never"
```

## Cost control

- `gpt-5.5` is the cheapest interactive model (~1000 tokens/s); ideal for CI bulk reviews
- `--max-turns` caps loops
- Web search policy: set `web_search = "disabled"` for CI to avoid surprise costs

## Comparison

| Concern | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Headless | `codex exec` | `claude -p` | `opencode run` |
| JSON output | `--json` | `--output-format json` | `--json` (JSONL) |
| App-server / IPC | `codex app-server` | (custom MCP server) | `opencode serve` (HTTP) |
| Self-update in CI | `codex update` or pin npm | `claude update` | `opencode upgrade` |

## Pinning version in CI

Always pin in CI:

```bash
npm i -g @openai/codex@0.130.0
```

Floating to `@latest` invites surprise breakage when a release changes flag names.

## Embedding pattern — long-running orchestration via `app-server`

> Use when an external process (editor plugin, queue worker, custom UI) needs to drive Codex without owning a long-lived TCP connection or blocking on `codex exec`. JSON-RPC over stdio or WebSocket lets the caller submit work, abort, and observe state without per-request HTTP timeouts.

### Why `codex app-server` (not `exec`) for embedding

- `codex exec` is a one-shot run; the process lives only for that turn. Wrap it in a queue + subprocess pattern if you just need fire-and-forget.
- `codex app-server` is a **persistent JSON-RPC server**: one process, many turns, observable state, cancellable. The right surface for IDEs, agent supervisors, and pipelines where setup cost matters.
- Unlike `opencode serve` (HTTP) and unlike a hypothetical Claude Code daemon (which doesn't exist — see `claude-code/references/external-orchestration.md`), Codex' app-server is **IPC-first**: no HTTP server, no Basic auth, no SSE. Trust boundary is the transport (filesystem perms for stdio, token for WS).

### Transport options

| Transport | Start command | Best for |
|---|---|---|
| stdio | `codex app-server --stdio` | Single embedding parent (editor extension, supervisor) — POSIX pipes |
| WebSocket | `codex app-server` (default port flag varies by release) | Network-attached clients; pair with `codex --remote ws://… --remote-auth-token-env MY_TOKEN_ENV` |

For WebSocket auth, the client side uses `--remote-auth-token-env` to read a bearer token from env. Never embed the token in the URL.

### JSON-RPC method reference

The authoritative cookbook with request/response shapes lives in [`config-cookbook.md`](./config-cookbook.md) (App-server JSON-RPC section). Concise lookup:

| Method | Purpose |
|---|---|
| `config/read` | Effective config snapshot |
| `config/value/write` | Write a single key path |
| `config/batchWrite` | Batch edit + optional `reloadUserConfig` hot-reload |
| `config/mcpServer/reload` | Reload MCP config from disk |
| `mcpServerStatus/list` | List MCP server states (`detail`, `limit` params) |

The set of model-execution methods (prompt submission, turn control, abort, completion notifications) follows the same JSON-RPC shape; consult the `/openai/codex` upstream `llms.txt` via Context7 for the current full catalog as it grows release-to-release.

### Long-running embedding pattern (Node 24)

```ts
// codex-rpc.ts — stdio JSON-RPC client around `codex app-server`
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

const child = spawn('codex', ['app-server', '--stdio'], { stdio: ['pipe', 'pipe', 'inherit'] });
const rl = createInterface({ input: child.stdout });

let nextId = 1;
const pending = new Map<number, (v: unknown) => void>();
const notifications: unknown[] = [];

(async () => {
  for await (const line of rl) {
    if (!line.trim()) continue;
    const msg = JSON.parse(line);
    if (typeof msg.id === 'number' && pending.has(msg.id)) {
      pending.get(msg.id)!(msg);
      pending.delete(msg.id);
    } else {
      notifications.push(msg); // turn deltas, status events
    }
  }
})();

function rpc(method: string, params?: unknown): Promise<unknown> {
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, id, params }) + '\n');
  });
}

// Use it
const cfg = await rpc('config/read');
console.log(cfg);

// Submit work; abort if the parent process is cancelled
process.on('SIGTERM', () => {
  rpc('abort', {}).finally(() => child.kill('SIGINT'));
});
```

The parent's HTTP request returns immediately after enqueuing work; the JSON-RPC client surfaces turn deltas via `notifications` (push them into a queue / WebSocket / SSE for the end user). The HTTP handler **never** waits for the model run — same timeout-avoidance principle as `opencode serve` Pattern 1, just over JSON-RPC instead of HTTP.

### Liveness & abort

- Liveness: send `config/read` (cheap, always-available); if it returns within ~500 ms the server is healthy. For stdio, also check `child.exitCode === null`.
- Abort: send the abort JSON-RPC method, then `SIGINT` the subprocess if it doesn't acknowledge within 5s. Avoid `SIGKILL` — leaves provider sessions dangling.

### When to use which

For the full capability matrix (HTTP, streaming, async submit, liveness, abort, auth, best-for) across Codex, Claude Code, and OpenCode, see the table in [`claude-code/references/external-orchestration.md`](../../claude-code/references/external-orchestration.md#comparison-vs-opencode-serve--codex-app-server) — not duplicated here.

## See also

- `opencode/references/server-mode.md` — HTTP-first equivalent (full `/doc` OpenAPI surface)
- `claude-code/references/external-orchestration.md` — subprocess + `claude agents` background sessions pattern
- `codex/references/config-cookbook.md` — full JSON-RPC request/response shapes
- `linux-sysadmin` — systemd unit for a long-lived `codex app-server` worker
