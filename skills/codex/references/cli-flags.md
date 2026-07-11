# CLI Flags Reference

## Modes

| Form | Purpose |
|---|---|
| `codex` | Interactive TUI |
| `codex exec "<prompt>"` | One-shot headless |
| `codex app-server` | Headless app-server with IPC (v0.130+) |
| `codex serve` | HTTP server mode (programmatic) |

## Model & profile

| Flag | Notes |
|---|---|
| `-m, --model <id>` | Override model (`gpt-5-codex`, `gpt-5.5`) |
| `-p, --profile <name>` | Use a profile from `config.toml` |
| `-c, --config key=value` | One-off override (e.g. `-c model_reasoning_effort=high`) |

## Filesystem / cwd

| Flag | Notes |
|---|---|
| `-C, --cd <path>` | Set working directory |
| `--add-dir <path>` | Add a writable directory outside the primary workspace |

## Sandbox & approval

| Flag | Values |
|---|---|
| `-s, --sandbox` | `read-only`, `workspace-write`, `danger-full-access` |
| `-a, --ask-for-approval` | `untrusted`, `on-request`, `never` (`on-failure` deprecated) |
| `--full-auto` | Shorthand for `-a on-request -s workspace-write` |
| `--dangerously-bypass-approvals-and-sandbox` | DFA mode — sandbox/VM only |

## Other run options

| Flag | Notes |
|---|---|
| `--search` | Enable live web search tool |
| `-i, --image <path>` | Attach image(s) to prompt context (repeatable) |
| `--json` | JSON output for `exec` |
| `--resume` | Resume last session |
| `--max-turns N` | Cap reasoning loops |

## Subcommands

| Subcommand | Purpose |
|---|---|
| `login` / `logout` | Auth |
| `mcp add` / `mcp list` / `mcp remove` | Manage MCP servers |
| `update` | Self-update |
| `exec <prompt>` | Headless |
| `app-server` | App-server / IPC |
| `serve` | HTTP API server |
| `completion {bash\|zsh\|fish\|powershell}` | Shell completion |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Tool denied / blocked |
| `2` | User cancelled |
| `3` | Auth error |

## Examples

```bash
# Safe initial review of unknown repo
codex -s read-only -a untrusted

# Productive default
codex --full-auto

# Profile invocation
codex -p ci-review

# Headless with JSON output
codex exec "Summarize CHANGELOG.md" -s read-only -a never --json

# One-off model + reasoning override
codex -m gpt-5.5 -c model_reasoning_effort=high

# DFA inside Docker
docker run --rm -it codex-devcontainer codex --dangerously-bypass-approvals-and-sandbox
```

## Compare with the others

| Goal | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Headless | `codex exec` | `claude -p` | `opencode run` |
| JSON | `--json` | `--output-format json` | `--json` (JSONL) |
| Read-only | `-s read-only -a untrusted` | `--permission-mode plan` | `--agent plan` |
| Full auto | `--full-auto` | `--permission-mode bypassPermissions` | `--auto` |
