# Migration — Codex ↔ Claude Code ↔ OpenCode

## File mapping

| Concept | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Project memory | `AGENTS.md` | `CLAUDE.md` | `AGENTS.md` |
| User memory | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` |
| Project settings | `.codex/config.toml` | `.claude/settings.json` | `opencode.json` |
| User settings | `~/.codex/config.toml` | `~/.claude/settings.json` | `~/.config/opencode/opencode.json` |
| Auth | `~/.codex/auth.json` | `~/.claude/auth.json` | `~/.local/share/opencode/auth.json` |
| Custom prompts | `.codex/prompts/*.md` | `.claude/commands/*.md` | `.opencode/commands/*.md` |
| Subagents | profiles + external `codex exec` | `.claude/agents/*.md` | `opencode.json: agent.*` or `.opencode/agents/*.md` |
| Hooks | none native (use wrappers) | `settings.json: hooks` | none native (use wrappers) |
| MCP servers | `[mcp_servers.*]` in TOML | `mcpServers` in JSON | `mcp` in JSON |
| Skills | none | `.claude/skills/<name>/SKILL.md` | community plugin |

## Headless command mapping

| Goal | Codex | Claude Code | OpenCode |
|---|---|---|---|
| One-shot | `codex exec "..."` | `claude -p "..."` | `opencode run "..."` |
| JSON output | `--json` | `--output-format json` | `--json` (JSONL) |
| Read-only | `-s read-only -a untrusted` | `--permission-mode plan` | `--agent plan` |
| Full auto | `--full-auto` | `--permission-mode bypassPermissions` | `--auto` |
| DFA | `--dangerously-bypass-approvals-and-sandbox` | `--dangerously-skip-permissions` | `--auto` + container |
| Pick model | `-m gpt-5-codex` | `--model claude-sonnet-4-6` | `--model anthropic/claude-sonnet-4-6` |
| Resume | `--resume` | `-c` | `-c` |

## Slash command mapping

| Action | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Clear | `/clear` (or older `/new`) | `/clear` | `/new` |
| Compact | `/compact` | `/compact` | `/compact` |
| Init | `/init` | `/init` | `/init` |
| Permissions | `/permissions` (or older `/approvals`) | `/permissions` | `/permissions` |
| MCP | `/mcp` | `/mcp` | `/mcp` |
| Model | `/model` | `/config` model field | `/models` |
| Status | `/status` | (n/a) | (in TUI footer) |
| Diff | `/diff` | (use Bash git diff) | (use Bash git diff) |

## Memory file portability

`AGENTS.md` is **the** standard for Codex and OpenCode. To use one file across all three:

```bash
# In project root
ln -s AGENTS.md CLAUDE.md
```

## Permission model translation

| Need | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Read-only baseline | `-s read-only -a untrusted` | `--permission-mode plan` | `--agent plan` |
| Block .env edits | (use sandbox + OS perms) | `permissions.deny: ["Edit(.env*)"]` | wrapper script |
| Block destructive bash | sandbox boundary | `permissions.deny: ["Bash(rm -rf:*)"]` | `tools.bash: false` |
| Network deny | (OS / container layer) | `sandbox.network.deniedDomains` | container layer |
| Productive auto | `--full-auto` | `acceptEdits` mode | (default with prompt) |

Codex's filesystem sandbox is Rust-enforced — strongest of the three. Claude Code's permission matchers are the most expressive. OpenCode keeps the model simple and pushes isolation to the container.

## Hook → wrapper translation

Codex has no native hooks. Wrap `codex exec` for equivalent behaviour:

```bash
#!/usr/bin/env bash
# codex-with-format.sh
codex exec "$@" --json > /tmp/cx.json
# Parse tool_use events for edited files (Codex prints structured tool calls in JSON)
jq -r '.tool_calls[]? | select(.tool=="Edit" or .tool=="Write") | .input.file_path' /tmp/cx.json \
  | sort -u | xargs -r -n1 prettier --write
jq -r '.result' /tmp/cx.json
```

## When to pick which CLI

| Need | Best pick |
|---|---|
| OpenAI ChatGPT subscription billing | Codex |
| Anthropic Claude subscription billing | Claude Code |
| Multi-provider BYOK | OpenCode |
| Strongest filesystem sandbox out of the box | Codex |
| Deep hook system + per-tool permission matchers | Claude Code |
| Skills system | Claude Code |
| Open-source, self-host | OpenCode |
| Rust-only runtime, no Node at runtime | Codex |

## Dual-CLI shop

Many teams in 2026 use **two** of the three:
- Claude Code for daily work (skills, hooks, depth)
- Codex CLI for OpenAI-tied review pipelines (sandbox guarantees)

Or:
- OpenCode for provider flexibility
- Claude Code for skills-driven workflows

Pick CLIs per task, not as religion.
