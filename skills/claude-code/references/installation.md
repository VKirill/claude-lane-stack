# Installation, Auth, Model Selection

## Install paths

### Native installer (recommended)

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Installs a single platform-specific binary to `~/.local/bin/claude` (or `$XDG_BIN_DIR`). No Node runtime required at execution time.

### npm

```bash
npm install -g @anthropic-ai/claude-code
```

Since the 2026 native-binary migration, the npm package is a thin shim that pulls the right platform binary as an optional dependency (`@anthropic-ai/claude-code-darwin-arm64`, `@anthropic-ai/claude-code-linux-x64`, etc.). Node 24+ recommended for `npm install`, but **not required** at runtime.

### Homebrew (macOS)

```bash
brew install anthropics/tap/claude-code
```

### Verify

```bash
claude --version
claude doctor   # diagnoses install, PATH, auth, MCP issues
```

### Self-update

```bash
claude update
```

The CLI checks for updates on launch and prompts when a new release is available.

## Authentication

### OAuth (subscription billing)

```bash
claude login
```

Opens a browser, signs in via claude.ai, stores OAuth token in `~/.config/claude/auth.json` (XDG) or `~/.claude/auth.json` (legacy). Subscription quota and rate limits apply.

### API key (API billing)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or persist in `~/.claude/settings.json`:

```json
{ "env": { "ANTHROPIC_API_KEY": "sk-ant-..." } }
```

API key has priority over OAuth when both are present. For CI/CD always use API key via secret env var.

### Logout

```bash
claude logout
```

Removes stored credentials.

## Model selection

Three production models in the Claude 4 family:

| Model ID | Use case | Cost |
|---|---|---|
| `claude-opus-4-7-20260315` | Hardest reasoning, refactors, long planning | Highest |
| `claude-sonnet-4-6-20260201` | Default daily-driver, best speed/quality ratio | Mid |
| `claude-haiku-4-5-20260115` | Fast classification, headless review, bulk runs | Lowest |

Set the default via:

```json
{ "model": "claude-sonnet-4-6-20260201" }
```

Or per-invocation: `claude --model claude-opus-4-7`.

## Devcontainer

Anthropic ships a reference devcontainer at `https://github.com/anthropics/claude-code/tree/main/.devcontainer`. Copy `.devcontainer/devcontainer.json` + `Dockerfile` into your repo; mounts `~/.claude/` so auth persists across rebuilds.

## Settings hierarchy

```
~/.claude/settings.json          # user-global (auth, default model, global hooks)
<project>/.claude/settings.json  # project (team-shared, committed to git)
<project>/.claude/settings.local.json  # user-local override (gitignored, secrets ok)
```

Resolution order: project local → project shared → user global. More-specific wins. Use `claude config` to dump effective config.
