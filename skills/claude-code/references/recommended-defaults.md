# Recommended defaults — claude-code

Canonical operational defaults for Claude Code 2.1.x in production projects. **Other files in this skill cite this table — do not redefine inline.**

> Citation rule: every recommendation includes a default + a tune-up/tune-down condition. Cargo-culting defaults across all projects is worse than no defaults.

## settings.json hierarchy & precedence

Order (most → least specific):

1. `.claude/settings.local.json` (project, user-private, **gitignored**)
2. `.claude/settings.json` (project, committed)
3. `~/.claude/settings.json` (user-global)
4. Anthropic defaults (built-in)

More specific overrides less specific. **Never commit `.claude/settings.local.json`** — secrets and per-user overrides live there.

## Permission mode

| Mode | When |
|---|---|
| `plan` | Unfamiliar repo; large refactors; security audits — read-only first |
| `default` | Daily driver — prompt per tool |
| `acceptEdits` | Trusted repo + scoped session; pair with strict `permissions.deny` |
| `bypassPermissions` | **Never outside sandboxed devcontainer/VM** |

## permissions.allow / permissions.deny defaults

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(sudo:*)",
      "Edit(.env*)",
      "Edit(**/secrets/**)",
      "Edit(**/.git/**)",
      "Write(.env*)"
    ],
    "allow": [
      "Bash(npm test:*)",
      "Bash(npm run lint:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Read(**)"
    ]
  }
}
```

| Knob | Default | Tune-up when | Tune-down when |
|---|---|---|---|
| Deny matchers | block destructive bash + secrets edits | repo has billing/auth code → add domain-specific denies | very controlled sandbox → minimal |
| Allow read-only | broad `Read(**)`, `git status/diff/log` | CI/scoped tasks | secret-bearing repos — narrow `Read` |

## Sandbox network

Default-deny outbound, explicit allowlist for trusted domains.

```json
{
  "sandbox": {
    "network": {
      "deniedDomains": ["*"],
      "allowedDomains": [
        "api.anthropic.com",
        "registry.npmjs.org",
        "github.com",
        "raw.githubusercontent.com"
      ]
    }
  }
}
```

Tune up `allowedDomains` only for documented project needs (private registries, internal APIs). Never wildcard-allow.

## Hook event policy

| Event | Recommendation |
|---|---|
| `PreToolUse` | Use sparingly — blocks every tool call; can become CI bottleneck. Best for hard safety gates (block `rm -rf`). |
| `PostToolUse` | Default home for formatters/linters after `Edit`/`Write`. Keep idempotent. |
| `UserPromptSubmit` | Use for prompt rewriting / template injection. Don't block — annotate. |
| `SessionStart` | Load project state, warm caches, print git status |
| `Stop` | Notifications, logs — never destructive |
| `PreCompact` | Snapshot working state before context compaction |
| `SubagentStart` | Audit only — log spawn metadata |

**Hook idempotency rule:** same input → same output, no side effects beyond the documented one. A formatter hook that modifies the file is fine; one that bumps a build counter is not.

## MCP server defaults

```json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/oraios/serena", "serena-mcp-server"],
      "timeout": 30000
    }
  }
}
```

| Knob | Default | Notes |
|---|---|---|
| `timeout` | 30000 ms | Most MCP handshakes complete <1s; 30s catches network hangs |
| Pin version | YES where the server supports it | Server upgrades break tool signatures silently |
| Allowlist scope | minimum required | Treat MCP output as untrusted context |

## CLAUDE.md conventions

- Keep under 500 lines — gets injected on every session start
- Section order: stack/ports → conventions → gotchas → ops
- Cite `PROJECT.md` for source of truth on stack; don't duplicate
- No secrets ever — even comments

## Headless / CI mode

```bash
claude -p "review PR #123" \
  --output-format json \
  --permission-mode plan \
  --disallowed-tools "Bash,Edit,Write"
```

| Knob | Default in CI |
|---|---|
| `--output-format` | `json` — parseable exit |
| `--permission-mode` | `plan` for read-only; `acceptEdits` only with disallowed-tools narrowed |
| `ANTHROPIC_API_KEY` | from secret store; never inline |
| Exit codes | `0`=ok, `1`=blocked, `2`=cancelled |

## Citation rule

Other files MUST NOT redefine these values inline. Use:

> Defaults: see [recommended-defaults.md](recommended-defaults.md).

## Last verified

2026-05-15 against Claude Code 2.1.x official docs.
