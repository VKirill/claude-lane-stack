# Recommended defaults — codex

Canonical operational defaults for OpenAI Codex CLI 0.130.x. **Other files in this skill cite this table — do not redefine inline.**

> Citation rule: every recommendation includes a default + a tune-up/tune-down condition.

## Sandbox + approval combos (the two-knob decision)

| Use case | `sandbox_mode` | `approval_policy` | Notes |
|---|---|---|---|
| Unfamiliar repo, audit | `read-only` | `untrusted` | Default for first session in any new codebase |
| Productive coding in trusted workspace | `workspace-write` | `on-request` | This is what `--full-auto` aliases to |
| CI / batch | `workspace-write` | `never` | Required — no human to answer prompts |
| Devcontainer / VM only | `danger-full-access` | `never` | Never on host machine |

`--full-auto` shorthand = `-s workspace-write -a on-request`. Treat as the daily-driver default for trusted workspaces.

## Profile defaults (recommended scaffolding)

```toml
# ~/.codex/config.toml or project .codex/config.toml

[profiles.review]
model = "gpt-5.5"
model_reasoning_effort = "low"
sandbox_mode = "read-only"
approval_policy = "untrusted"

[profiles.build]
model = "gpt-5-codex"
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[profiles.refactor]
model = "gpt-5-codex"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[profiles.ci]
model = "gpt-5-codex"
sandbox_mode = "workspace-write"
approval_policy = "never"
```

Invoke: `codex -p review`, `codex -p build`, `codex exec -p ci ...`.

## Model selection rules

| Model | Use when |
|---|---|
| `gpt-5.5` | Interactive chat-like UI; ~1000 tok/s; fast iteration; "review" profile |
| `gpt-5-codex` | Serious agentic work; multi-step refactors; longer reasoning |

| `model_reasoning_effort` | When |
|---|---|
| `low` | Quick edits, formatting, doc rewrites |
| `medium` | Default for `build` profile |
| `high` | Hard refactors, debugging, design decisions |

## Config precedence

CLI flag > project `.codex/config.toml` > user `~/.codex/config.toml` > built-in defaults.

| Knob | Recommended location |
|---|---|
| Model + reasoning effort | Project (matches codebase complexity) |
| Sandbox + approval | Project (matches trust boundary) |
| MCP servers | User (cross-project) for general tools; project for project-specific |
| Profiles | User (reusable across repos) |

## MCP server defaults

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }
```

| Rule | Why |
|---|---|
| Always use `${ENV_VAR}` interpolation | No secrets inline in config.toml |
| Prefer `codex mcp add` over hand-editing | Validates schema, prevents typos |
| Pin version where supported | Server upgrades break tool signatures silently |

## Headless / CI defaults

```bash
codex exec "review the diff" \
  -p ci \
  --json
```

| Knob | CI default |
|---|---|
| `--json` | Always — parseable output |
| `-p ci` (or `-a never -s workspace-write`) | Required — no interactive prompts in CI |
| `OPENAI_API_KEY` | From secret store; never inline |

## Hard rules

- NEVER `--dangerously-bypass-approvals-and-sandbox` on host — Docker/VM only.
- NEVER commit `.codex/auth.json` or `.codex/tokens.json` — gitignore the directory.
- NEVER use `approval_policy = "on-request"` in CI — no human to respond.

## Citation rule

Other files MUST NOT redefine these values inline. Use:

> Defaults: see [recommended-defaults.md](recommended-defaults.md).

## Last verified

2026-05-15 against Codex CLI 0.130.x official docs (`github.com/openai/codex`).
