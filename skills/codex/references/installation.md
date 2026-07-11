# Installation, Auth, Model Selection

## Install paths

### npm

```bash
npm i -g @openai/codex
```

The npm package is a thin wrapper that fetches the platform-specific Rust binary.

### Homebrew (macOS — includes the desktop app)

```bash
brew install --cask codex
```

Installs both the GUI app and the `codex` CLI.

### Direct binary download

From `https://github.com/openai/codex/releases/latest`:

| Platform | File |
|---|---|
| macOS arm64 | `codex-aarch64-apple-darwin.tar.gz` |
| macOS x64 | `codex-x86_64-apple-darwin.tar.gz` |
| Linux x64 (musl) | `codex-x86_64-unknown-linux-musl.tar.gz` |
| Linux arm64 (musl) | `codex-aarch64-unknown-linux-musl.tar.gz` |

```bash
tar -xzf codex-*.tar.gz
sudo mv codex /usr/local/bin/
```

### Verify

```bash
codex --version
# codex-cli 0.130.x
```

### Update

```bash
codex update
```

## Authentication

### ChatGPT subscription (recommended for individuals)

```bash
codex login
```

Opens a browser, signs in via chatgpt.com, stores token in `~/.codex/auth.json`. Uses your ChatGPT plan quota (Plus / Pro / Enterprise).

### API key (for CI, programmatic)

```bash
export OPENAI_API_KEY="sk-..."
```

Or persist in `~/.codex/config.toml`:

```toml
# Note: prefer env interpolation over literal keys
[providers.openai]
api_key = "${OPENAI_API_KEY}"
```

API key takes precedence over OAuth when both are present.

### Logout

```bash
codex logout
```

## Models

| Model | Use case | Speed |
|---|---|---|
| `gpt-5-codex` | Default agentic CLI work | Standard |
| `gpt-5.5` | Heavier reasoning, hard refactors | Slower |
| `gpt-5.5` | Interactive / chat-like, >1000 tok/s | Instant |

Set via:

```toml
# ~/.codex/config.toml
model = "gpt-5-codex"
model_reasoning_effort = "medium"   # low | medium | high
```

Or per-invocation:

```bash
codex -m gpt-5.5
```

## Devcontainer

A minimal Codex devcontainer:

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl ca-certificates
RUN curl -fsSL https://github.com/openai/codex/releases/latest/download/codex-x86_64-unknown-linux-musl.tar.gz | tar -xz -C /usr/local/bin/
WORKDIR /workspace
```

Mount `~/.codex/` for auth persistence.

## Config locations

```
~/.codex/config.toml      # user defaults
~/.codex/auth.json        # auth tokens (gitignore)
~/.codex/AGENTS.md        # user memory
~/.codex/prompts/*.md     # user-wide custom prompts
<project>/.codex/config.toml   # project (committed except auth)
<project>/AGENTS.md            # project memory
<project>/.codex/prompts/*.md  # project prompts
```

Project config wins over user config; CLI flags win over both. One-off overrides via `-c key=value`.

## Surfaces — they share config

OpenAI ships Codex in three surfaces:
- **CLI** (`codex` binary)
- **VS Code extension** ("Codex for VS Code")
- **macOS desktop app** (Codex.app)

All three read `~/.codex/config.toml`, but the **interactive UI** for changing settings differs. The CLI uses flags + slash commands; the extension has a settings panel; the app has a preferences window. Config edits may require a surface restart to take effect.
