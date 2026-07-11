# Agent hooks / guards — multi-CLI (2026-07)

Deterministic guards that catch agents mid-flight. Shared logic lives in
`~/.agents/hooks/`; each CLI wires its own config format.

## Shared scripts (`~/.agents/hooks/`)

| Script | When | What |
|--------|------|------|
| `guard_shell.py` | PreToolUse (shell) | `--no-verify`, force-push, DROP/TRUNCATE, DELETE without WHERE, reckless `rm -rf` |
| `guard_code_quality.py` | PostToolUse (edit) | `any`, Prisma `$queryRawUnsafe`, `@ts-ignore`, eval, hardcoded secrets |
| `lib_payload.py` | — | Normalize stdin JSON for Claude / Codex / Grok / AGY |

Set `AGENT_HOOK_CLIENT=claude|codex|grok|agy` so deny payload matches the host.

Escape hatch for code quality: `// guardian: allow <reason>` on the same line.

---

## Claude Code (already rich)

Config: `~/.claude/settings.json` → `hooks`

- PM guard: `guard-orchestrator-no-direct-edits.sh` (allows `.agents/todos|runs`)
- Shell: lockfile, dangerous-bash, secrets, git-no-verify
- Post edit: `guardian-code.sh` (local sibling of `guard_code_quality.py`)
- Trace: `orchestrator-trace.sh`

---

## Codex CLI

| Piece | Path |
|-------|------|
| Feature flag | `~/.codex/config.toml` → `[features] hooks = true` |
| Global hooks | `~/.codex/hooks.json` |
| Project hooks | `<repo>/.codex/hooks.json` |
| Shared scripts | `AGENT_HOOK_CLIENT=codex ~/.agents/hooks/guard_*.py` |

**Status:** global hooks wired; `selfystudio/.codex/hooks.json` cleaned of **repowise** (was still calling `repowise-augment`).

Legacy scripts still in `~/.codex/hooks/` (`block-dangerous-shell.py`, handoff-*) — optional; new wiring uses shared Python.

**Trust:** first time may need hook trust (`--dangerously-bypass-hook-trust` only for automation). Restart Codex after editing hooks.json.

Matcher notes: Codex PreToolUse often matches **Bash/shell**; file edits via `apply_patch`.

---

## Grok CLI

| Piece | Path |
|-------|------|
| Global hooks | `~/.grok/hooks/*.json` (always trusted) |
| Project hooks | `<repo>/.grok/hooks/*.json` (needs `/hooks-trust`) |
| Claude compat | Also reads `~/.claude/settings.json` hooks by default |
| Docs | `~/.grok/docs/user-guide/10-hooks.md` |

**Installed:** `~/.grok/hooks/agent-guards.json`

Deny format: `{"decision":"deny","reason":"..."}` exit 2.  
Fail-open on crash/timeout — hooks must return explicit deny.

Matchers map Claude names → Grok (`Bash`→`run_terminal_command`, `Edit`→`search_replace`).

Check UI: `/hooks` after restart.

---

## Antigravity (AGY)

| Piece | Path |
|-------|------|
| Global | `~/.gemini/antigravity-cli/hooks.json` |
| Project / plugin | `hooks.json` in customization root / plugin |
| Docs | antigravity-cli builtin `docs/hooks.md` |

**Installed:**

- `agent-guard-shell` → PreToolUse `run_command`
- `agent-guard-code` → PostToolUse `replace_file_content|…|write_to_file`
- Broken `code-guidelines-gate` (missing validate-tool-call.cjs) → **disabled**

Deny format: `{"decision":"deny","reason":"..."}`  
PostToolUse: `{}` (+ stderr for quality notes).

Tool names: `run_command`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`.

Restart `agy` session after editing hooks.json.

---

## What each CLI can / cannot block

| Capability | Claude | Codex | Grok | AGY |
|------------|--------|-------|------|-----|
| Block dangerous shell | ✅ | ✅ | ✅ | ✅ |
| Block force-push / no-verify | ✅ | ✅ | ✅ | ✅ |
| Post-edit `any` / Prisma unsafe | ✅ (block feedback) | ✅ | soft (message) | soft (stderr) |
| PM no production Write | ✅ orchestrator guard | ❌ (not PM host) | ❌ | ❌ (lane writer) |
| Fail-open on hook crash | yes | yes | yes | yes |

---

## Adding a new shared guard

1. Add `~/.agents/hooks/guard_foo.py` using `lib_payload`.
2. Wire into:
   - Claude: `settings.json` Pre/PostToolUse
   - Codex: `~/.codex/hooks.json`
   - Grok: `~/.grok/hooks/*.json`
   - AGY: `~/.gemini/antigravity-cli/hooks.json`
3. Keep scripts **fast** (<2–5s). Fail-open except explicit deny.
4. Document here.

---

## Community patterns (2026)

- PreToolUse = hard policy; PostToolUse = quality / format ([hooks guides](https://prg.sh/notes/Claude-Code-Hooks))
- Explicit `deny` JSON — never rely on crash to block
- AgentGuard / security scanners as optional Pre+Post layer
- Prefer shared scripts + thin per-CLI wrappers (what we did)

---

## Session ledger (handoff log) — NOT a changelog from safety guards

**Safety guards** (force-push, `any`, …) do **not** write history.

**Session ledger** hooks write project under-the-hood notes after work:

| Path | Purpose |
|------|---------|
| `.agents/session-log/INDEX.md` | Newest-first index for night audits |
| `.agents/session-log/YYYY-MM-DD/*.md` | One **session ledger** / **agent handoff log** per flush |
| `.agents/agent-notes/OPEN.md` | TODO/FIXME debt found in touched files |

Community names (X / blogs 2026):

- **agent handoff log** — decisions, files, next steps
- **session ledger / coding journal** — chronological agent work
- **ADR / decision log** — big architecture choices (promote manually to `docs/decisions.md`)
- **agent notes** — open debt / simplify later

### How it works

1. **PostToolUse** → `session_ledger.py record` (files + shell samples in `/tmp/...`)
2. **Stop / SessionEnd** → `session_ledger.py flush` → writes markdown + INDEX
3. Evidence-based: tools + `git status/diff` — **no invented prose “why”** (that needs model summary or run `report.md`)

### Wired on

| CLI | Config |
|-----|--------|
| Claude | `settings.json` PostToolUse + Stop + SessionEnd |
| Codex | `~/.codex/hooks.json` (+ selfystudio project) |
| Grok | `~/.grok/hooks/agent-guards.json` |
| AGY | `~/.gemini/antigravity-cli/hooks.json` |

### Night audit recipe

```bash
# recent sessions
head -30 .agents/session-log/INDEX.md
# open debt
cat .agents/agent-notes/OPEN.md
# for each session: verify tests cover touched paths, close OPEN items
```

### Run reports (lanes)

File-based lanes still write ` .agents/runs/<slug>/artifacts/*/report.md ` with human/agent **why**.
Session ledger is the automatic cross-CLI layer; run reports are richer for intentional tasks.

## Project memory pack

See [PROJECT-MEMORY.md](./PROJECT-MEMORY.md). Init: `~/.agents/bin/project-memory-init .`  
Night: `~/.agents/bin/night-audit .`  
Skill: `project-memory`.
