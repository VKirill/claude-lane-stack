# Slash Commands + Custom Prompts

## Built-in slash commands

| Command | Purpose |
|---|---|
| `/model` | Switch model or reasoning level |
| `/permissions` | Adjust sandbox + approval policy (older alias `/approvals`) |
| `/status` | Show session settings |
| `/diff` | Show pending workspace diff |
| `/compact` | Compress conversation context |
| `/clear` | Clear context (older alias `/new`) |
| `/init` | Generate `AGENTS.md` |
| `/mcp` | List & manage MCP servers |
| `/memory` | Show / edit project memory |
| `/review` | Review current diff |
| `/goal` | Set / show high-level session goal |
| `/title` | Rename the session |
| `/statusline` | Configure status line |
| `/login` `/logout` | Auth |
| `/help` | List commands |

Exit interactive mode: `Ctrl+C` (some versions also accept `/quit`).

## Custom prompts

Drop a markdown file at:
- **Project**: `.codex/prompts/<name>.md`
- **User**: `~/.codex/prompts/<name>.md`

Invoke as `/<name> [args]`.

### Frontmatter

```yaml
---
description: "Conventional Commits PR description"
argument-hint: "<ticket-id>"
profile: review               # optional — run under this profile
---
```

| Field | Purpose |
|---|---|
| `description` | Shown in `/help` |
| `argument-hint` | TUI auto-complete hint |
| `profile` | Run this prompt with a specific profile's model/sandbox |

### Body

Placeholders:
- `$ARGUMENTS` — full arg string
- `$1`, `$2`, ... — positional
- `$CWD` — working directory

### Example: `.codex/prompts/pr-desc.md`

```markdown
---
description: "Generate Conventional Commits PR description from current diff"
argument-hint: "<ticket-id>"
profile: review
---
Generate a PR description for the current git diff.
Reference ticket: $ARGUMENTS

Sections required: Summary, Why, Test plan, Risk.

Run `git diff origin/main...HEAD` to see the diff.
```

Invoke: `/pr-desc PROJ-1234`.

## Comparison vs Claude Code, OpenCode

| Feature | Codex | Claude Code | OpenCode |
|---|---|---|---|
| Project prompts | `.codex/prompts/*.md` | `.claude/commands/*.md` | `.opencode/commands/*.md` |
| User prompts | `~/.codex/prompts/*.md` | `~/.claude/commands/*.md` | `~/.config/opencode/commands/*.md` |
| Bind to model/sandbox | via `profile` field | via `model` + `allowed-tools` | via `agent` field |
| Placeholders | `$ARGUMENTS`, `$1..N` | same | same |
| Namespacing | subdir → `/group:name` | subdir → `/group:name` | subdir → `/group:name` |

## Built-in command shifts (version history)

Some commands were renamed:

| Old | New |
|---|---|
| `/approvals` | `/permissions` |
| `/new` | `/clear` |

Older docs may still use the old names. Both forms typically work for backward compatibility, but `/permissions` and `/clear` are the canonical 2026 names.
