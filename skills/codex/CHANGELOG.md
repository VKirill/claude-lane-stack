# codex skill — CHANGELOG

## [2.1.0] — 2026-05-16

### Added
- `references/interop.md` — appended an **"Embedding pattern — long-running orchestration via `app-server`"** section (~90 lines, non-disruptive — appended at the end, leaves all prior content intact):
  - Why `codex app-server` over `codex exec` for embedding (persistent JSON-RPC server vs one-shot)
  - Transport table: stdio (`codex app-server --stdio`) vs WebSocket (`codex --remote ws://… --remote-auth-token-env`)
  - Concise JSON-RPC method table (`config/read`, `config/value/write`, `config/batchWrite`, `config/mcpServer/reload`, `mcpServerStatus/list`) with reference back to `config-cookbook.md` for full request/response shapes — no duplication
  - Paste-runnable Node 24 + TS stdio JSON-RPC client (~30 lines)
  - Liveness (`config/read` ping pattern) + abort (JSON-RPC abort method + SIGINT escalation)
  - Cross-reference to capability matrix in `claude-code/references/external-orchestration.md` (no duplication)
- Added "See also" links to `opencode/references/server-mode.md` and `claude-code/references/external-orchestration.md`.

### Rationale
- Closes the "CLI-as-long-running-daemon" pattern triad. With `opencode serve` (HTTP) and `claude-code/external-orchestration.md` (subprocess + background sessions) now documented, the Codex JSON-RPC story sits cleanly alongside both, with a clear use-when picker.

### Source
- `codex/references/config-cookbook.md` (already in this skill — pulled from Context7 `/openai/codex`)
- `context7.com/openai/codex/llms.txt` — `codex --remote ws://` flag confirmation

## [2.0.0] — 2026-05-16

### Added (v3 retrofit)
- `references/recommended-defaults.md` — canonical sandbox+approval combos per use-case, profile scaffolding (review/build/refactor/ci), model selection rules (gpt-5-codex vs gpt-5.5), config precedence, MCP secrets via `${ENV_VAR}`
- `references/troubleshooting.md` — symptom-indexed: app-server connection refused, sandbox false-blocks, CI approval hangs, model not found, MCP handshake stalls, update fails, deprecated-model ambiguity
- `references/wrong-vs-right.md` — 4 side-by-side pairs: DFA vs workspace-write, CI approval `never` vs `on-request`, profile-per-task vs stacked flags, secrets inline vs env interpolation

### Changed
- `references/eval-cases.md` migrated to v3: user-voice phrasing (RU/EN mixed, incomplete welcome), `Expected behavior` column citing target sub-files, `How to verify` section. 10/10/5 structure preserved.
- SKILL.md trimmed to 242 lines (was 252): condensed Subagents and Headless/Migration sections; API Reference table extended with the three new references.

## [1.1.0] — 2026-05-15

### Added
- `references/config-cookbook.md` — curated `config.toml` fixtures (all three sandbox modes, workspace-write + network combo), `codex` TUI launch flags, `codex sandbox macos/linux/windows` subcommands, app-server JSON-RPC methods (`config/read`, `config/value/write`, `config/batchWrite`, `mcpServerStatus/list`, `config/mcpServer/reload`). Every snippet linked to `github.com/openai/codex` source path.
- Wired the new file into SKILL.md API Reference table.

### Source
- Pulled via Context7 (`/openai/codex`) — `codex-rs/core/src/config/config_tests.rs`, `codex-rs/skills/.../codex-network.md`, `codex-rs/README.md`, `llms.txt`.

## [1.0.0] — 2026-05-15

### Added
- Initial skill generation
- SKILL.md with Pattern 2 layout
- 11 reference files: install, CLI flags, config.toml, commands, subagents (profile pattern), MCP, permissions, interop, migration, eval-cases
- Templates: `.codex/config.toml`, `AGENTS.md`, custom prompt, MCP server entry
- Examples: quickstart session, GitHub Actions PR review (read-only sandbox)
- Cross-links to `claude-code` and `opencode` skills

### Verified versions (May 2026)
- OpenAI Codex CLI 0.130.x (Rust 94.9%; `@openai/codex` npm wrapper)
- Models: gpt-5-codex, gpt-5.5
- `codex app-server` IPC server (added in 0.130.0, April 2026)

### Naming disambiguation
- This skill is **explicitly NOT** about the deprecated 2021-2023 Codex completion model (`code-davinci-002`)
- This skill is **explicitly NOT** about GitHub Copilot CLI (different vendor, different binary)
- This skill IS about `github.com/openai/codex` — OpenAI's official agentic terminal CLI

### Scope decisions
- Excludes raw OpenAI SDK usage (delegates to `openai-sdk` cascade marker)
- Excludes custom MCP server development (`mcp-builder` cascade marker)
- Excludes general agent benchmarking (`agent-evaluation`)
- Codex's subagent story is weaker than Claude Code's; documented via `subagents.md` as "profiles + external exec" pattern
