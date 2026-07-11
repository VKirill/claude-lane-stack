---
name: codex
description: "OpenAI Codex CLI — OpenAI's official Rust-based agentic terminal coding tool (NOT the deprecated 2021 Codex completion model). Use when: openai codex, codex CLI, @openai/codex npm, codex exec, codex app-server, AGENTS.md, .codex/config.toml, sandbox_mode read-only/workspace-write/danger-full-access, approval_policy untrusted/on-request/on-failure/never, /permissions, /mcp, codex --full-auto, gpt-5-codex, codex profiles, ChatGPT subscription auth. SKIP: Claude Code CLI (→claude-code), OpenCode CLI (→opencode), OpenAI SDK programmatic (→openai-sdk), GitHub Copilot CLI (different tool), deprecated code-davinci-002 model (discontinued)."
stacks:
  - codex
  - cli-agents
tags:
  - codex
  - openai
  - cli
  - agent
  - rust
  - mcp
  - sandbox
  - approval-policy
packages:
  - "@openai/codex"
manifests:
  - .codex/config.toml
  - AGENTS.md
source: vechkasov-global-skills
risk: medium-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (June 2026)

**Primary pins:**
- OpenAI Codex CLI: `0.130.x (`@openai/codex`, Rust-based sandbox)`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-06-11

<!-- versions:end -->

## Usage

Loaded automatically when the description matches the active task. Read only the section relevant to the current question.

## Use this skill when

- Installing or updating `codex` (`npm i -g @openai/codex`, `brew install --cask codex`, GitHub Releases binary)
- Authoring `.codex/config.toml` (project) or `~/.codex/config.toml` (user)
- Writing or editing `AGENTS.md` (same file used by OpenCode)
- Setting `sandbox_mode` (`read-only` / `workspace-write` / `danger-full-access`) and `approval_policy` (`untrusted` / `on-request` / `on-failure` / `never`)
- Picking a model (`gpt-5-codex`, `gpt-5.5`) and `model_reasoning_effort`
- Using profiles (`-p, --profile`) for per-project model/sandbox bundles
- Configuring MCP servers in `[mcp_servers.*]` blocks
- Running headless: `codex exec "..."`, JSON output, CI integration
- Using `codex app-server` (v0.130+) for app-server / IPC integration
- Writing custom prompts/commands in `.codex/prompts/<name>.md`
- Disambiguating from the **deprecated** 2021 Codex completion model (`code-davinci-002`) — it's discontinued
- Migrating between Codex CLI, Claude Code, and OpenCode

## Do not use this skill when

- Task is Claude Code CLI (settings.json, hooks, .claude/skills) — use `claude-code`
- Task is OpenCode CLI (multi-provider, opencode.json) — use `opencode`
- Task is the OpenAI Assistants/Responses API or SDK calls from code — use `openai-sdk`
- Task is GitHub Copilot CLI (Microsoft's tool, different binary) — clarify with the user; this is a NAMING COLLISION
- Task is the deprecated `code-davinci-002` Codex completion model from 2021–2023 — refuse and redirect to this skill (modern Codex agent) or `openai-sdk`
- Task is general agent benchmarking — use `agent-evaluation`

## Purpose

The OpenAI Codex CLI (`@openai/codex`, `github.com/openai/codex`) is OpenAI's **official agentic terminal tool**, written predominantly in Rust (94.9% as of mid-2026). It's the OpenAI counterpart to Anthropic's Claude Code: heavy investment, fast release cadence (700+ releases since launch), Apache-2.0 license, 75K+ GitHub stars. It powers a coding agent backed by `gpt-5-codex` and related OpenAI models.

**Critical naming clarification**: "Codex" in 2026 means this agentic CLI tool. The original 2021-era Codex completion model (`code-davinci-002`, sunset 2023) is **discontinued** — do not write code targeting it. The modern Codex is fundamentally different: it's an agent CLI that uses current GPT-5 models under the hood.

This skill covers: install/auth, `config.toml` schema, sandbox + approval policy model (Codex's strongest area — Rust-enforced filesystem and network boundaries), MCP server configuration, headless `codex exec`, custom prompts, `codex app-server` for IPC, and migration to/from Claude Code and OpenCode.

## Capabilities

### Installation, auth, models

Three install paths: `npm i -g @openai/codex` (wraps the platform binary), `brew install --cask codex` (macOS app + CLI), or `codex-aarch64-apple-darwin.tar.gz`/`codex-x86_64-unknown-linux-musl.tar.gz` from GitHub Releases. Auth: `codex login` (ChatGPT subscription OAuth) or `OPENAI_API_KEY` env. Subscription path uses your ChatGPT quota; API path bills per token. Default model `gpt-5-codex`; `gpt-5.5` for near-instant interactive use.

> Full reference: [references/installation.md](references/installation.md)

### CLI flags

Interactive: `codex`. Headless: `codex exec "<prompt>"`. Key flags:
`-m, --model`, `-s, --sandbox {read-only|workspace-write|danger-full-access}`, `-a, --ask-for-approval {untrusted|on-request|on-failure|never}`, `--full-auto` (= `-a on-request -s workspace-write`), `--dangerously-bypass-approvals-and-sandbox` (DFA mode), `-p, --profile <name>`, `-C, --cd <path>`, `-c, --config key=value` (one-off override), `--add-dir`, `-i, --image`, `--search`, `--json`. Subcommands: `login`, `logout`, `mcp add|list|remove`, `update`, `exec`, `app-server`.

> Full reference: [references/cli-flags.md](references/cli-flags.md)

### Configuration (`config.toml`)

TOML format. Precedence: CLI flag > project `.codex/config.toml` > user `~/.codex/config.toml` > built-in defaults. Top-level keys: `model`, `model_reasoning_effort`, `approval_policy`, `sandbox_mode`, `web_search`, `profiles`, `mcp_servers`. Profile blocks (`[profiles.<name>]`) bundle settings for `-p <name>`.

> Full reference: [references/config.md](references/config.md)

### Sandbox + approval (Rust-enforced)

The headline feature. Three sandbox levels:
- `read-only`: no writes, no shell side effects
- `workspace-write`: writes only within `cwd` and `--add-dir`
- `danger-full-access`: no filesystem boundary (DFA)

Four approval policies:
- `untrusted`: prompt for every tool call
- `on-request`: prompt only when the model asks for elevation
- `on-failure`: prompt only on command-failure / sandboxed error retry
- `never`: no prompts (CI mode)

`--full-auto` = `-a on-request -s workspace-write` (the recommended productive default).
`/permissions` switches live in interactive mode.

> Full reference: [references/permissions.md](references/permissions.md)

### Slash commands

Interactive: `/model`, `/permissions` (older alias `/approvals`), `/status`, `/diff`, `/compact`, `/clear` (older alias `/new`), `/init`, `/mcp`, `/memory`, `/review`, `/help`, `/login`, `/logout`, `/goal`, `/title`, `/statusline`. Custom prompts: `.codex/prompts/<name>.md` (project) or `~/.codex/prompts/<name>.md` (user). Invoke `/<name> [args]`.

> Full reference: [references/commands.md](references/commands.md)

### Profiles

Per-project bundles of model + sandbox + approval. Defined in `config.toml`:

```toml
[profiles.review]
model = "gpt-5.5"
sandbox_mode = "read-only"
approval_policy = "untrusted"
model_reasoning_effort = "low"
```

Invoke with `codex -p review`. Useful for separating "fast read-only review" from "full-auto build" without editing config each time.

> Full reference: [references/config.md](references/config.md)

### Subagents (via profiles)

Codex has no first-class named subagents. Closest equivalent: **profiles** + spawning `codex exec -p review ...` from a session. See [references/subagents.md](references/subagents.md).

### MCP servers

Configure in `config.toml` under `[mcp_servers.<name>]`:

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }
```

`codex mcp add` is the recommended way to write these blocks safely. Same server binaries as Claude Code / OpenCode.

> Full reference: [references/mcp.md](references/mcp.md)

### Headless, app-server, migration

`codex exec "<prompt>"` is one-shot mode (add `--json` for structured output). `codex app-server` (v0.130+) starts a headless IPC server for pipeline embedding. `AGENTS.md` is shared with OpenCode; slash command set differs from Claude Code. See [references/interop.md](references/interop.md) and [references/migration.md](references/migration.md).

## Behavioral Traits

- Starts in `read-only` + `untrusted` for unfamiliar repos; loosens once trust is established
- Uses `--full-auto` for productive sessions in a trusted workspace
- NEVER uses `--dangerously-bypass-approvals-and-sandbox` outside Docker/VM
- Prefers profiles (`-p review`, `-p build`) over inline flags for repeated workflows
- Picks `gpt-5.5` (1000 tok/s) for chat-like interactive UI, `gpt-5-codex` for serious agentic work
- Adds `model_reasoning_effort = "high"` for hard refactors, `"low"` for quick edits
- Wraps `codex exec` in shell scripts to replicate Claude Code hooks (Codex has no native hooks)
- Disambiguates the modern Codex CLI from the deprecated 2021 model whenever a user says "Codex" ambiguously
- Verifies which surface (CLI vs VS Code extension vs macOS app) the user is on — they share config but expose settings differently
- Stores secrets as `${ENV_VAR}` interpolation in `config.toml`, never inline

## Important Constraints

- NEVER recommend the deprecated `code-davinci-002` Codex completion model — it's discontinued; today's Codex is an agent CLI
- NEVER use `--dangerously-bypass-approvals-and-sandbox` on a host machine — Docker/VM only
- NEVER commit `.codex/auth.json` — it contains tokens; gitignore the `.codex/` directory or specific auth files
- NEVER conflate OpenAI Codex CLI with GitHub Copilot CLI — different products, different vendors (despite OpenAI being upstream to both)
- NEVER hand-edit `mcp_servers` blocks for sensitive servers without `codex mcp add` validation
- ALWAYS pin a profile per CI workflow (`codex exec -p ci-review ...`) instead of stacking flags
- ALWAYS start unfamiliar repos in `-s read-only -a untrusted` mode
- ALWAYS check `codex --version` after `codex update` — features depend on version (e.g., `app-server` requires 0.130+)

## Related Skills

**90%-filter applied.** ✓ = active; rest are cascade markers.

### Cousin CLI agents
- ✓ `claude-code` — Anthropic's official CLI
- ✓ `opencode` — Multi-provider open-source CLI
- `gemini-cli` — Google's CLI agent (cascade marker)
- `cursor-cli` — Cursor's headless agent (cascade marker)
- `aider` — Python CLI pair-programmer (cascade marker)

### SDK
- `openai-sdk` — calling OpenAI API directly from code (cascade marker)

### Runtime / language
- ✓ `nodejs` — Node 24 for npm install path
- ✓ `typescript` — TS 5.9 (target codebases)
- ✓ `linux-sysadmin` — Docker sandbox, devcontainer

### CI/CD
- `github-actions` — primary CI target (cascade marker)

### Git
- ✓ `git` — heavy git integration (cascade marker)

### MCP
- `mcp-builder` — building custom MCP servers (cascade marker)

## API Reference

### Reference files (Pattern 2)

| Topic | File |
|---|---|
| Index + decision map | [references/REFERENCE.md](references/REFERENCE.md) |
| Install, auth, model picker, devcontainer | [references/installation.md](references/installation.md) |
| Full CLI flag reference | [references/cli-flags.md](references/cli-flags.md) |
| `config.toml` schema, profiles, layering | [references/config.md](references/config.md) |
| Slash commands + custom `.codex/prompts/*.md` | [references/commands.md](references/commands.md) |
| Profiles-as-subagents pattern | [references/subagents.md](references/subagents.md) |
| MCP server config, transports, debugging | [references/mcp.md](references/mcp.md) |
| Sandbox modes, approval policies, DFA | [references/permissions.md](references/permissions.md) |
| Headless `codex exec`, `app-server`, GitHub Actions | [references/interop.md](references/interop.md) |
| Migration Codex ↔ Claude Code ↔ OpenCode | [references/migration.md](references/migration.md) |
| Config & JSON-RPC cookbook — `config.toml` fixtures, sandbox combos, app-server JSON-RPC methods (curated from `github.com/openai/codex` via Context7) | [references/config-cookbook.md](references/config-cookbook.md) |
| Recommended defaults (sandbox/approval combos, profile scaffolding, model selection, MCP secrets) | [references/recommended-defaults.md](references/recommended-defaults.md) |
| Troubleshooting (app-server, sandbox false-blocks, CI approval hangs, model not found, MCP stalls) | [references/troubleshooting.md](references/troubleshooting.md) |
| Wrong vs right code pairs (DFA, CI approval, profile-per-task, secrets interpolation) | [references/wrong-vs-right.md](references/wrong-vs-right.md) |
| Eval cases (10 pos / 10 neg / 5 edge) | [references/eval-cases.md](references/eval-cases.md) |

### Templates

| Template | File |
|---|---|
| Project `.codex/config.toml` with profiles + MCP | [templates/config.toml.template](templates/config.toml.template) |
| `AGENTS.md` for project memory | [templates/AGENTS.md.template](templates/AGENTS.md.template) |
| Custom prompt under `.codex/prompts/` | [templates/prompt.md.template](templates/prompt.md.template) |
| MCP server entry | [templates/mcp-server.toml.template](templates/mcp-server.toml.template) |

### Examples

| Scenario | File |
|---|---|
| Full session: install → ChatGPT login → first edit (full-auto) | [examples/quickstart-session.md](examples/quickstart-session.md) |
| GitHub Actions: headless PR review with sandbox=read-only | [examples/github-actions-pr-review.md](examples/github-actions-pr-review.md) |

<!-- changelog-watch:start -->
### Свежее из чейнджлога (проверено: 2026-06-11)
- rust-v0.139.0: Code mode умеет вызывать standalone web search напрямую, включая вложенные JavaScript tool calls, и получает plaintext-результаты.
- rust-v0.139.0: схемы tool/connector input сохраняют `oneOf` и `allOf`, а большие схемы компактируются с большей shallow-структурой; можно надежнее использовать богатые MCP-инструменты.
- rust-v0.139.0: `codex doctor` добавляет в локальный отчет editor/pager environment details, но в JSON-output raw values редактируются.
- rust-v0.139.0: `codex plugin marketplace list --json` теперь включает marketplace source, а plugin lists могут отдать cached remote catalog до фонового refresh.
- rust-v0.139.0: `codex resume --last "..."` и `codex fork --last "..."` трактуют хвостовой аргумент как initial prompt, а не как session ID.
- rust-v0.139.0: `/new`, `/clear` и `/fork` больше не сбрасывают cloud-managed requirements и feature flags при TUI config reload.
- rust-v0.139.0: sandbox execution стабильнее сохраняет approved escalation decisions и строже соблюдает configured proxy-only networking.
- rust-v0.138.0: `/app` передает текущий CLI thread в Codex Desktop на macOS и native Windows; Windows workspace launch может сразу открываться в Desktop.
- rust-v0.138.0: local image attachments и standalone image generations показывают model saved file paths; follow-up edits и file references стали надежнее.
- rust-v0.138.0: reasoning effort selection поддерживает fallback shortcuts для терминалов без `Alt`, а model-defined effort levels идут в порядке, объявленном моделью.
- rust-v0.138.0: app-server integrations могут читать account token usage; auth поддерживает v2 personal access tokens в CLI и app-server flows.
- rust-v0.138.0: plugin automation получила structured output: add/remove и marketplace commands поддерживают `--json`; plugin detail показывает default prompts, remote MCP servers и unavailable app templates.

⚠️ Устарело в теле скилла:
- В Version Requirements указан pin `0.130.x`, но свежий стабильный changelog уже описывает `rust-v0.139.0`; alpha-линейка `rust-v0.140.0-alpha.*` тоже опубликована.
<!-- changelog-watch:end -->
