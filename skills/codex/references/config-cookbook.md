# Codex CLI — config.toml & runtime cookbook

Curated from `github.com/openai/codex` via Context7 (May 2026). Every block carries the source path inside the repo. Use this as a quick lookup; conceptual coverage lives in `config.toml.md`, `permissions.md`, and `cli-flags.md`.

> Config locations:
> - `~/.codex/config.toml` — user config (defaults across all projects)
> - `.codex/config.toml` — repo-local override (committed alongside `AGENTS.md`)

## Sandbox modes (the three)

Source: `codex-rs/core/src/config/config_tests.rs`

```toml
# Read-only — agent can run commands but cannot write the filesystem.
# Network keys in [sandbox_workspace_write] are ignored under read-only.
sandbox_mode = "read-only"

# Workspace-write — writes confined to writable_roots, default network OFF.
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
writable_roots = ["/my/workspace"]
exclude_tmpdir_env_var = true   # drop $TMPDIR from writable set
exclude_slash_tmp = true         # drop /tmp from writable set
network_access = false           # default; set true to allow egress
```

```toml
# Danger-full-access — no sandbox. Network keys here are ignored
# (network is unrestricted anyway).
sandbox_mode = "danger-full-access"
```

### Workspace-write + network egress

Source: `codex-rs/skills/src/assets/samples/imagegen/references/codex-network.md`

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

Use this combo when the agent legitimately needs `curl`/`npm install`/etc. but you still want approval-on-request for risky operations.

## Approval policy values

```toml
approval_policy = "untrusted"   # ask for almost everything
approval_policy = "on-request"  # ask when the model requests escalation
approval_policy = "never"       # never ask (use with read-only or pre-blessed envs only)
```

Pair with `--ask-for-approval <value>` to override per-run.

## Launching the TUI

Source: `context7.com/openai/codex/llms.txt`

```bash
# Empty interactive session
codex

# Start with a prompt
codex "refactor the authentication module to use JWT"

# Model + working directory
codex -m gpt-5.1-codex -C /path/to/project "add unit tests for the parser"

# Workspace-write sandbox + auto-approval (full-auto loop)
codex --sandbox workspace-write --ask-for-approval never "run all tests and fix failures"

# Connect to remote app-server over WebSocket
codex --remote ws://127.0.0.1:4500 --remote-auth-token-env MY_TOKEN_ENV

# Enable a feature flag for this session only
codex --enable web_search_request "summarize the latest PRs"
```

## Sandbox subcommands (test command execution under sandbox)

Source: `codex-rs/README.md`

```bash
codex sandbox macos -- <command>    # test command under Apple Seatbelt
codex sandbox linux -- <command>    # test command under Landlock/seccomp
codex sandbox windows -- <command>  # test command under AppContainer
```

Use to validate that a command will succeed before letting the agent run it in a real session.

## App-server JSON-RPC — config and MCP management

Source: `context7.com/openai/codex/llms.txt`

Codex exposes a JSON-RPC surface over WebSocket (`codex --remote`). Common methods:

### Read effective config
```json
{ "method": "config/read", "id": 60 }
```
Response:
```json
{ "id": 60, "result": { "config": {
  "model": "gpt-5.1-codex",
  "approval_policy": "on-request"
}}}
```

### Write a single key
```json
{
  "method": "config/value/write",
  "id": 61,
  "params": { "keyPath": "model", "value": "gpt-5.1-codex" }
}
```

### Batch write + hot reload
```json
{
  "method": "config/batchWrite",
  "id": 62,
  "params": {
    "edits": [{
      "keyPath": "hooks.state",
      "value": { "/Users/me/.codex/config.toml:pre_tool_use:0:0": { "enabled": false } },
      "mergeStrategy": "upsert"
    }],
    "reloadUserConfig": true
  }
}
```

### List MCP server statuses
```json
{ "method": "mcpServerStatus/list", "id": 63, "params": { "detail": "full", "limit": 20 } }
```

### Reload MCP config from disk (no restart)
```json
{ "method": "config/mcpServer/reload", "id": 64 }
```

## Authoritative source map

| Topic | Source |
|---|---|
| Sandbox mode test fixtures | `github.com/openai/codex/blob/main/codex-rs/core/src/config/config_tests.rs` |
| Network-access example | `github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/imagegen/references/codex-network.md` |
| CLI flag reference | `context7.com/openai/codex/llms.txt` |
| Rust CLI changelog + sandbox subcommands | `github.com/openai/codex/blob/main/codex-rs/README.md` |

> Curated 2026-05-15 via Context7 (`/openai/codex`). Re-pull on each codex CLI release for new flags / JSON-RPC methods.
