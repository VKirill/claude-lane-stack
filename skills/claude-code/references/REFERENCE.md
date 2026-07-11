# claude-code — Reference Index

Decision map: pick the file that matches the task at hand.

| If you want to... | Open |
|---|---|
| Install or update the CLI, auth via OAuth or API key | [installation.md](installation.md) |
| Look up a CLI flag (`-p`, `--output-format`, `--permission-mode`) | [cli-flags.md](cli-flags.md) |
| Use or author a slash command (`/init`, `/review`, custom `.claude/commands/*`) | [slash-commands.md](slash-commands.md) |
| Define a subagent in `.claude/agents/<name>.md` | [subagents.md](subagents.md) |
| Wire an MCP server (filesystem, github, postgres, custom stdio/HTTP) | [mcp.md](mcp.md) |
| Add a lifecycle hook (PreToolUse, PostToolUse, Stop, etc.) | [hooks.md](hooks.md) |
| Configure permissions, plan mode, sandbox network rules | [permissions.md](permissions.md) |
| Run Claude Code headlessly in CI or as a script | [interop.md](interop.md) |
| Move config between Claude Code, OpenCode, and Codex | [migration.md](migration.md) |
| Verify routing works (positive/negative eval prompts) | [eval-cases.md](eval-cases.md) |

## Quick patterns

**Headless one-shot with JSON output:**
```bash
claude -p "Summarize CHANGELOG.md" --output-format json
```

**Plan-only review of unfamiliar repo:**
```bash
claude --permission-mode plan
```

**Add an MCP server interactively:**
```bash
claude mcp add
```

**Configure prompts to run automatically on save:**
```json
// .claude/settings.json
{ "hooks": { "PostToolUse": [{ "matcher": "Edit|Write", "hooks": [{ "type": "command", "command": "npx prettier --write $FILE_PATH" }] }] } }
```

**Block dangerous Bash patterns:**
```json
{ "permissions": { "deny": ["Bash(rm -rf:*)", "Edit(.env*)", "Edit(**/secrets/**)"] } }
```
