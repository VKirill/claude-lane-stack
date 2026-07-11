# Migration: Claude Code ↔ OpenCode ↔ Codex

The three CLI agents converged on similar primitives but with different formats. This document maps them so you can port configs and prompts between them.

## File mapping

| Concept | Claude Code | OpenCode | OpenAI Codex |
|---|---|---|---|
| Project memory | `CLAUDE.md` | `AGENTS.md` | `AGENTS.md` |
| User memory | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `~/.codex/AGENTS.md` |
| Project settings | `.claude/settings.json` | `opencode.json` (or `.opencode/opencode.json`) | `.codex/config.toml` |
| User settings | `~/.claude/settings.json` | `~/.config/opencode/opencode.json` | `~/.codex/config.toml` |
| Custom commands | `.claude/commands/*.md` | `.opencode/commands/*.md` | `.codex/prompts/*.md` |
| Subagents | `.claude/agents/*.md` | `opencode.json: agent.*` or `.opencode/agents/*.md` | Profiles in `config.toml` |
| Hooks | `settings.json: hooks` | (none native — use shell wrappers) | (none native — use shell wrappers) |
| MCP servers | `settings.json: mcpServers` | `opencode.json: mcp` | `config.toml: mcp_servers` |
| Skills | `.claude/skills/<name>/SKILL.md` | `.opencode/skills/` (community plugin) | (none) |
| Auth | `auth.json` (managed by `claude login`) | `~/.local/share/opencode/auth.json` | `~/.codex/auth.json` |

## Headless command mapping

| Goal | Claude Code | OpenCode | OpenAI Codex |
|---|---|---|---|
| One-shot prompt | `claude -p "..."` | `opencode run "..."` | `codex exec "..."` |
| JSON output | `--output-format json` | `--json` | `--json` |
| Read-only / plan | `--permission-mode plan` | `--agent plan` | `-s read-only -a untrusted` |
| Full auto | `--permission-mode bypassPermissions` | `--agent build --auto` | `--full-auto` |
| Pick model | `--model claude-sonnet-4-6` | `--model anthropic/claude-sonnet-4-6` | `-m gpt-5-codex` |

## Slash command mapping

| Action | Claude Code | OpenCode | OpenAI Codex |
|---|---|---|---|
| New session | `/clear` | `/new` | `/clear` (or `/new`) |
| Compact | `/compact` | `/compact` | `/compact` |
| Init project | `/init` | `/init` | `/init` |
| Permissions | `/permissions` | `/permissions` | `/permissions` |
| MCP | `/mcp` | `/mcp` | `/mcp` |
| Plan vs build | (mode flag) | `/agent plan` or `/agent build` | (sandbox flag) |
| Resume last | `claude -c` | `opencode run -c` | `codex --resume` |

## Memory / context file

All three look for a project-root file at session start:

```text
CLAUDE.md   → Claude Code
AGENTS.md   → OpenCode AND OpenAI Codex
```

For maximum portability, write a single `AGENTS.md` and symlink `ln -s AGENTS.md CLAUDE.md` (or vice versa). Content style is identical.

## Permission model — conceptual

| Concept | Claude Code | OpenCode | OpenAI Codex |
|---|---|---|---|
| Read-only sandbox | `plan` mode | `plan` agent | `-s read-only` |
| Auto-edit, prompt on Bash | `acceptEdits` | (default) | `-s workspace-write -a on-request` |
| Full auto | `bypassPermissions` | `--auto` | `--full-auto` |
| Bypass everything | `--dangerously-skip-permissions` | (n/a — provider-level) | `--dangerously-bypass-approvals-and-sandbox` |

## Hook → wrapper translation

Claude Code is the only one of the three with native hooks. To get equivalent behaviour with OpenCode or Codex, wrap the CLI in a shell script:

```bash
#!/usr/bin/env bash
# wrapper.sh — runs OpenCode/Codex and post-formats edited files
opencode run "$@" --json > /tmp/run.json
jq -r '.events[]? | select(.type=="tool_use" and (.tool=="Edit" or .tool=="Write")) | .input.file_path' /tmp/run.json \
  | xargs -r -n1 biome format --write
```

## MCP — the same servers work everywhere

MCP is a standard. The server binary is identical across the three CLIs; only the config format differs.

| Tool | Claude Code | OpenCode | Codex |
|---|---|---|---|
| filesystem | `mcpServers.filesystem.command` | `mcp.filesystem.command` | `[mcp_servers.filesystem] command=` |
| github | `mcpServers.github` | `mcp.github` | `[mcp_servers.github]` |

Pin one canonical MCP server list in your `AGENTS.md` and reference it from all three configs.

## When to use which CLI

| Need | Best pick |
|---|---|
| Best agent quality + skills/hooks ecosystem | Claude Code |
| Multi-provider BYOK (Claude, GPT, Gemini, Ollama) | OpenCode |
| OpenAI-tied workflow, ChatGPT subscription | OpenAI Codex |
| Rust-only sandbox guarantees | OpenAI Codex |
| Open-source code, self-host | OpenCode |
| Native binary, no Node at runtime | Claude Code (2.x) or Codex |
