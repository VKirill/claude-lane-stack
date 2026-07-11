# claude-code skill — CHANGELOG

## [2.2.0] — 2026-05-16

### Added
- `references/external-orchestration.md` — running Claude Code from outside (~250 lines). Documents three patterns:
  - **Pattern A**: headless `claude -p` (recap; full details remain in `interop.md`) — `--bare`, `--output-format stream-json`, exit codes, 10 MB stdin cap (2.1.128), upcoming June 2026 Agent SDK credit pool split for subscription users.
  - **Pattern B**: `claude agents` background sessions (verified against CHANGELOG 2.1.140–2.1.142): spawning via `--bg` and `claude agents` subcommand with full flag set (`--add-dir`, `--settings`, `--mcp-config`, `--plugin-dir`, `--permission-mode`, `--model`, `--effort`, `--dangerously-skip-permissions`), `--cwd` scoping (2.1.141), idle 5-min auto-retire (2.1.142), upgrade-crash-loop fix (2.1.142), `ANTHROPIC_SMALL_FAST_MODEL` fallback (2.1.141).
  - **Pattern C**: Node 24 subprocess streaming wrapper using `child_process.spawn` + `readline`, JSONL events, `AbortSignal` → `SIGINT` → 5s grace → escalation.
- Capability matrix comparing Claude Code vs `opencode serve` vs `codex app-server` (HTTP API, streaming, async submit, liveness, abort, auth, multi-client, best-for).
- BullMQ-integration pattern (HTTP handler returns 202; worker spawns Claude).
- systemd unit for a `claude --bg` worker.
- Three wrong-vs-right pairs: sync block in HTTP handler vs queue, full-buffer stdout vs readline streaming, `SIGKILL` vs `SIGINT` + grace.
- Wired the new file into SKILL.md API Reference table.

### Source
- <https://code.claude.com/docs/en/headless> — headless mode, `--bare`, output formats, stream-json schema (verified 2026-05-16; primary URL `docs.claude.com/en/docs/claude-code/headless` 301s here)
- <https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md> — 2.1.140 / 2.1.141 / 2.1.142 entries for `claude agents` flags, daemon lifecycle, background dispatch

### Notable upstream finding (flag in lieu of correction)
- The Claude Code CHANGELOG explicitly uses the word "daemon" for the supervisor process that manages `claude agents` background sessions (2.1.142 entry: "Fixed daemon not exiting cleanly after the binary is upgraded… causing dispatched agents to crash-loop"). This contradicts the common framing that "Claude Code is just a CLI" — there **is** a daemon, but it has no HTTP/IPC surface for external callers and is undocumented as a stability boundary. The new file frames it accurately: there's a daemon, but it's CLI-controlled only.

## [2.1.0] — 2026-05-16

### Changed (re-verified against upstream CHANGELOG @ github.com/anthropics/claude-code, current 2.1.142)
- **Slash commands** — **Wave 3b classification was wrong**. The previous CHANGELOG/SKILL.md split moved `/ultrareview`, `/proactive`, `/recap`, `/focus`, `/rewind` into a "Community / plugin commands" section as "NOT shipped by Anthropic". The official CHANGELOG shows the opposite: these (with the exception of `/proactive` and `/recap` — still community) are upstream built-ins:
  - `/focus`, `/tui` — added in **2.1.110**
  - `/ultrareview <PR#>`, `/less-permission-prompts` — added in **2.1.111**
  - `/team-onboarding` — added in **2.1.101**
  - `/goal`, `/scroll-speed` — added in **2.1.139**
  - `/rewind` — already upstream (was already listed)
  Moved back to the Built-in section. Each command now annotated with its introduction version. Routing intent unchanged.
- The "community / plugin commands you may see" callout removed; the Wave 3b community-fork hypothesis (that these came from `superpowers` / `ultrareview` plugin marketplaces) was based on stale documentation. Anthropic upstream now ships them all.
- Source attribution added inline: `(verified via CHANGELOG @ github.com/anthropics/claude-code, current 2.1.142)`.

### Not changed
- `/proactive` and `/recap` remain unclassified (no CHANGELOG entry found upstream as of 2.1.142); kept out of the Built-in enumeration.
- Hook event count "~25" stays — confirmed close to CHANGELOG-implied count (PreCompact added in 2.1.105, etc.).
- Version pin `2.1.x` covers current 2.1.142 (no pin change needed).

### Source
- <https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md> (current 2.1.142, retrieved 2026-05-16)

## [2.0.0] — 2026-05-16

### Added (v3 retrofit)
- `references/recommended-defaults.md` — canonical settings.json precedence, permission modes, sandbox/network defaults, hook event policy, MCP server defaults, CLAUDE.md conventions, headless/CI defaults
- `references/troubleshooting.md` — symptom-indexed: hooks not firing, MCP handshake fail, skill not activating, settings precedence, permission denied unexpectedly, `claude update` fail
- `references/wrong-vs-right.md` — 5 side-by-side pairs: hook blocking vs annotating, settings.local.json precedence, sandbox allowlist, permission matcher `:*`, CLAUDE.md size

### Changed
- `references/eval-cases.md` migrated to v3 format: user-voice phrasing (RU/EN mixed, typos welcome), `Expected behavior` column, `How to verify` section. 10/10/5 structure preserved.
- API Reference table in SKILL.md updated with the three new references.

## [1.0.0] — 2026-05-15

### Added
- Initial skill generation
- SKILL.md with Pattern 2 layout, 200+ lines
- 10 reference files covering install, CLI flags, slash commands, subagents, MCP, hooks, permissions, interop, migration, eval-cases
- Templates: settings.json, CLAUDE.md, custom command, subagent, MCP server entry
- Examples: quickstart session walkthrough, GitHub Actions PR review pipeline
- Cross-links to `opencode` and `codex` skills via migration.md

### Verified versions (May 2026)
- `@anthropic-ai/claude-code` 2.1.x (native per-platform binary)
- Node 24 LTS optional for npm install path
- 27 hook lifecycle events, sandbox.network.deniedDomains feature

### Scope decisions
- Excludes SKILL.md authoring (delegates to `skill-evaluation`)
- Excludes raw Anthropic SDK usage (delegates to `anthropic-sdk` cascade marker)
- Excludes custom MCP server development (delegates to `mcp-builder` cascade marker)
