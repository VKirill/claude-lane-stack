# Slash Commands

## Built-in (selected, frequently used)

| Command | Purpose |
|---|---|
| `/init` | Scan repo and generate a `CLAUDE.md` |
| `/clear` | Clear conversation history, keep settings |
| `/compact` | Compress conversation to free context |
| `/recap` | Print a structured summary of the session so far |
| `/review` | Review current diff or named PR |
| `/security-review` | Security-focused diff review |
| `/ultrareview <PR#>` | Heavy multi-pass review using Opus |
| `/loop [interval] [cmd]` | Run a prompt/command on a recurring interval; omit interval → self-paced |
| `/proactive` | Toggle proactive mode (Claude asks/acts without further prompts) |
| `/undo` | Roll back the last edit |
| `/rewind` | Roll back to a specific checkpoint |
| `/focus` | Narrow Claude's attention to a single file or sub-tree |
| `/skills` | List loaded skills and their match status |
| `/agents` | Manage subagents (list, edit, run) |
| `/hooks` | Interactive hook editor |
| `/mcp` | Manage MCP servers (list, add, restart) |
| `/permissions` | Adjust permission mode and allow/deny rules |
| `/fewer-permission-prompts` | Auto-allow common read-only patterns based on transcript history |
| `/config` | Settings menu |
| `/theme` | Switch terminal theme |
| `/login` `/logout` | Auth |
| `/bug` | File an issue with context attached |
| `/help` | Full command list |

## Custom slash commands

Drop a markdown file at:
- **Project**: `.claude/commands/<name>.md`
- **User**: `~/.claude/commands/<name>.md`

Invoked as `/name [args]`. Body is treated as a prompt template; placeholders:

| Placeholder | Expands to |
|---|---|
| `$ARGUMENTS` | Everything after `/name ` |
| `$1`, `$2`, ... | Positional args (whitespace split) |
| `$FILE_PATH` | Current file (when invoked from a file context) |

### Frontmatter

```yaml
---
description: "Quick PR description for the current diff"
allowed-tools: "Bash(git diff:*), Read"
argument-hint: "<optional ticket id>"
model: claude-sonnet-4-6
---
```

| Field | Purpose |
|---|---|
| `description` | Shown in `/help` listing |
| `allowed-tools` | Restricts the tool set for this command (matchers as in settings.json) |
| `argument-hint` | Auto-complete hint in TUI |
| `model` | Override default model just for this command |

### Example: `.claude/commands/pr-desc.md`

```markdown
---
description: "Generate a PR description from the current diff"
allowed-tools: "Bash(git diff:*), Bash(git log:*), Read"
argument-hint: "<ticket-id>"
---
Generate a Conventional-Commits PR description for the current git diff.
Reference ticket: $ARGUMENTS

Sections: Summary, Why, Test plan, Risk.
```

Invoke: `/pr-desc PROJ-1234`.

## Namespacing

Commands inside `.claude/commands/<group>/<name>.md` become `/group:name`. Useful for plugin-distributed commands (`/superpowers:writing-plans`).
