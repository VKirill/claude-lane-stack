# CLI Flags Reference

## Modes

| Flag | Effect |
|---|---|
| (none) | Interactive TUI |
| `-p, --print <prompt>` | Headless: one-shot, prints answer, exits |
| `-c, --continue` | Resume the most recent session in this directory |
| `-r, --resume <id>` | Resume a specific session by id |

## I/O

| Flag | Values | Notes |
|---|---|---|
| `--output-format` | `text` (default), `json`, `stream-json` | `json` returns `{"result":..., "usage":..., "session_id":...}` |
| `--input-format` | `text`, `stream-json` | For piping multi-turn input |
| `-q, --quiet` | — | Suppress progress chatter; useful for scripts |

## Permission control

| Flag | Values |
|---|---|
| `--permission-mode` | `default`, `plan`, `acceptEdits`, `bypassPermissions` |
| `--allowed-tools` | Comma list, e.g. `Edit,Bash(npm test:*),WebFetch` |
| `--disallowed-tools` | Comma list |
| `--dangerously-skip-permissions` | Same as `--permission-mode bypassPermissions` (sandbox only) |

## Filesystem

| Flag | Notes |
|---|---|
| `--add-dir <path>` | Make additional directory writable (repeatable) |
| `-C, --cd <path>` | Run as if launched from `<path>` |

## Model

| Flag | Example |
|---|---|
| `--model` | `--model claude-opus-4-7` |
| `--max-turns` | Cap agent turns (default unlimited) |

## MCP

| Flag | Notes |
|---|---|
| `--mcp-config <file>` | Load extra MCP server definitions from JSON file |
| `--strict-mcp-config` | Treat MCP config errors as fatal (CI mode) |

## Other

| Flag | Notes |
|---|---|
| `--version` | Print CLI version |
| `--debug` | Verbose diagnostics |
| `--no-color` | Disable ANSI colour |
| `doctor` | Subcommand: validate install, PATH, MCP servers |
| `mcp` | Subcommand group: `add`, `remove`, `list` |
| `update` | Subcommand: self-update |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Tool call denied / abort |
| `2` | User cancelled (Ctrl-C) |
| `3` | Auth / config error |
| `>3` | Internal error |

## Headless example for CI

```bash
claude -p "Review the diff in this PR for security issues. Reply 'OK' or list concerns." \
  --output-format json \
  --permission-mode plan \
  --max-turns 6 \
  --model claude-sonnet-4-6 \
  > review.json
```

Parse `.result` from `review.json` to post back to the PR.
