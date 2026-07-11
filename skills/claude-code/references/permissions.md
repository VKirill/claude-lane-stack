# Permissions, Plan Mode, Sandbox

## Permission modes

Set with `--permission-mode <mode>`, `/permissions`, or `settings.json` (`permissions.defaultMode`).

| Mode | Behaviour |
|---|---|
| `plan` | Read-only. Claude drafts a plan; no Edit/Write/Bash side effects. |
| `default` | Prompt before each tool that's not in `permissions.allow`. |
| `acceptEdits` | Auto-allow Edit/Write; still prompt for Bash/WebFetch. |
| `bypassPermissions` | No prompts at all. Sandbox/devcontainer only. |

## Allow/deny matchers

```json
{
  "permissions": {
    "defaultMode": "default",
    "allow": [
      "Read",
      "Grep",
      "Edit(src/**)",
      "Bash(npm test:*)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "WebFetch(domain:docs.anthropic.com)"
    ],
    "deny": [
      "Edit(.env*)",
      "Edit(**/secrets/**)",
      "Bash(rm -rf:*)",
      "Bash(sudo:*)",
      "Bash(curl * | bash)",
      "WebFetch(domain:*)"
    ]
  }
}
```

Matcher syntax:
- `Tool` — match all uses of the tool
- `Tool(pattern)` — match when input matches pattern
- `Bash(cmd:*)` — Bash with command starting `cmd ` (glob-style)
- `Edit(glob)` — Edit with file path matching glob (`**` for recursive)
- `WebFetch(domain:host)` — WebFetch limited to `host`

Deny wins over allow. Place broad denies (`Bash(rm -rf:*)`) in user-global settings so they apply everywhere.

## Plan mode workflow

```bash
claude --permission-mode plan
```

Or `/plan` inside an active session.

1. Claude reads the codebase, drafts a multi-step plan
2. User reviews; can ask follow-ups
3. Exit plan mode (`/plan off`) to execute
4. Each step now subject to normal permission prompts

Use cases:
- Unfamiliar repo: read first, then act
- Large refactor: see the full plan before touching anything
- Code review: read-only by definition

## Sandbox (network)

Claude Code 2.x includes an outbound-network sandbox. Configure in `settings.json`:

```json
{
  "sandbox": {
    "network": {
      "deniedDomains": ["*"],
      "allowedDomains": ["docs.anthropic.com", "registry.npmjs.org", "github.com", "api.github.com"]
    }
  }
}
```

Default-deny is recommended for production projects. Add allowed hosts as needed.

## `/fewer-permission-prompts`

Scans recent transcripts for repeated allow-now responses on read-only patterns and proposes additions to `permissions.allow`. Run periodically to keep prompts down without weakening guards.

## Settings split — what belongs where

| Setting | File |
|---|---|
| API key, OAuth state | `~/.claude/settings.json` (or `auth.json`) |
| Default model | user or project |
| Permission allow/deny (broad) | user (e.g. `Bash(rm -rf:*)` deny) |
| Permission allow/deny (project-specific) | project shared `.claude/settings.json` |
| Personal experiments / secret env | `.claude/settings.local.json` (gitignored) |
| Hooks (team policy) | project shared |
| Hooks (personal notifications) | user |
| MCP servers (team) | project shared |
| MCP servers (personal) | user |

## Anti-patterns

- `bypassPermissions` on host machine — disables all guards
- Putting secrets in committed `.claude/settings.json` — use `${ENV_VAR}` interpolation + local override
- Permissive `WebFetch(domain:*)` — sandbox bypass; pin to specific hosts
- Forgetting `--permission-mode plan` for code review tasks — wastes tokens executing
