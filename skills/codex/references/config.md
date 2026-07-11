# `config.toml` — Schema, Profiles, Layering

## Top-level keys

```toml
# ~/.codex/config.toml or <project>/.codex/config.toml

model = "gpt-5-codex"
model_reasoning_effort = "medium"     # low | medium | high
approval_policy = "on-request"        # untrusted | on-request | never
sandbox_mode = "workspace-write"      # read-only | workspace-write | danger-full-access
web_search = "cached"                 # cached | live | disabled

# Profiles
[profiles.review]
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "untrusted"
model_reasoning_effort = "low"

[profiles.build]
model = "gpt-5-codex"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

# MCP servers
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }

[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/me/projects"]
```

## Precedence

```
1. CLI flag                          (highest)
2. `-c key=value` one-off override
3. <project>/.codex/config.toml
4. ~/.codex/config.toml
5. Built-in defaults                  (lowest)
```

## Profiles

A profile = named bundle of settings. Activated with `-p <name>`:

```bash
codex -p review
codex exec "..." -p ci-review
```

Field inheritance: when a profile is active, fields it doesn't set fall through to top-level config.

### Suggested profile catalog

```toml
[profiles.review]
# Read-only, fast model — for code review work
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "untrusted"
model_reasoning_effort = "low"

[profiles.build]
# Productive default for normal coding work
model = "gpt-5-codex"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
model_reasoning_effort = "medium"

[profiles.refactor]
# Heavy lift; gpt-5.5 with high reasoning
model = "gpt-5.5"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
model_reasoning_effort = "high"

[profiles.ci-review]
# Headless in CI — never prompts
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "never"
```

## Env interpolation

```toml
[mcp_servers.postgres]
command = "node"
args = ["./tools/pg-mcp.js"]
env = { DATABASE_URL = "${DATABASE_URL}" }
```

## Comments

TOML supports `#` line comments. Use them liberally for non-obvious settings.

## Validation

```bash
codex doctor       # validates config, auth, MCP handshake
codex -c model=gpt-5.5 --version   # dry-check an override
```

## Surface notes

The macOS app and VS Code extension read the **same** `config.toml`, but they don't always hot-reload after edits. Restart the surface after config changes.
