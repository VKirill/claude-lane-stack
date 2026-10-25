---
title: Agent hooks / guards — multi-CLI
type: component
created: 2026-07-11
updated: 2026-10-25
status: active
confidence: high
tags: [hooks, guards, cli]
sources:
  - hooks/guard_shell.py
  - hooks/guard_code_quality.py
  - hooks/lane_statusline_session.py
  - bin/lane_statusline_lib.py
  - hooks/session_ledger.py
  - hooks/pm_stop_sentinel.py
  - plugins/lane-stack/hooks/jev-router.ts
  - plugins/lane-stack/hooks/jev-route-core.ts
  - profiles/cursor/lane-writer/scripts/before_read.py
  - profiles/opencode/opencode-lane/index.ts
  - plugins/lane-stack/winnow/sidecar/src/winnow/serve.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/extract.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/policy.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/mcp_server.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/chunk.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/labels.py
  - plugins/lane-stack/winnow/sidecar/src/winnow/cli.py
  - profiles/opencode/opencode-lane/v1.ts
---
# Agent hooks / guards — multi-CLI

TL;DR: Shared host hooks enforce shell and lifecycle policy; provider-specific adapters translate each CLI event into the same guarded behavior, while Winnow filters supported tool output and fails open on unavailable judgment (`hooks/guard_shell.py:1-40`, `plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:92-120`).

## Purpose

Document the hook entry points, shared guards, and adapter-specific failure behavior across supported CLIs (`plugins/lane-stack/hooks/jev-router.ts:105-129`, `profiles/cursor/lane-writer/scripts/before_read.py:25-37`).

Deterministic guards that catch agents mid-flight. Shared logic lives in
`~/.agents/hooks/`; each CLI wires its own config format.

## Shared scripts (`~/.agents/hooks/`)

| Script | When | What |
|--------|------|------|
| `guard_shell.py` | PreToolUse (shell + PM edits) | PM read/verify/control-plane allowlist; delegates package, source, process/service/container, and DB mutations; also blocks controller bypass, `--no-verify`, force-push, destructive SQL, and reckless `rm -rf` |
| `guard_code_quality.py` | PostToolUse (edit) | JavaScript/TypeScript `any`, Prisma unsafe raw SQL, TypeScript suppression comments, dynamic evaluation, likely hardcoded credentials; skips `.agents` and `node_modules` (`hooks/guard_code_quality.py:21-23`, `hooks/guard_code_quality.py:34-69`) |
| `lib_payload.py` | — | Normalize stdin JSON for Claude / Codex / Grok |
| `pm_stop_sentinel.py` | Stop + PostToolUse `Agent\|Task` (`asyncRewake`) | PM: do not idle while `run-supervisor` is live or a recent controller is terminal/orphan; wake idle PM when stage becomes accepted/blocked/failed |

Set `AGENT_HOOK_CLIENT=claude|codex|grok` so deny payload matches the host.

Escape hatch for code quality: `// guardian: allow <reason>` on the same line.

---

## Claude Code (already rich)

Config: `~/.claude/settings.json` → `hooks`

- PM guard: shared `guard_shell.py` on `Bash|Edit|Write|MultiEdit|NotebookEdit`; installation
  merges this matcher without replacing user hooks.
- Shell: shared `guard_shell.py`, lockfile, dangerous-bash, secrets, git-no-verify
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

Restart Codex after editing its hooks configuration.

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

## What each CLI can / cannot block

| Capability | Claude | Codex | Grok |
|------------|--------|-------|------|
| Block dangerous shell | ✅ | ✅ | ✅ |
| Block force-push / no-verify | ✅ | ✅ | ✅ |
| Post-edit `any` / Prisma unsafe | ✅ (block feedback) | ✅ | soft (message) |
| PM no production Write | ✅ orchestrator guard | ❌ (not PM host) | ❌ |
| Fail-open on hook crash | yes | yes | yes |

---

## Adding a new shared guard

1. Add `~/.agents/hooks/guard_foo.py` using `lib_payload`.
2. Wire into:
   - Claude: `settings.json` Pre/PostToolUse
   - Codex: `~/.codex/hooks.json`
   - Grok: `~/.grok/hooks/*.json`
3. Keep scripts **fast** (<2–5s). PreToolUse payload errors fail closed;
   nonblocking PostToolUse quality checks fail open.
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

### Night audit recipe

```bash
: 'recent sessions'
head -30 .agents/session-log/INDEX.md
: 'open debt'
cat .agents/agent-notes/OPEN.md
: 'for each session: verify tests cover touched paths, close OPEN items'
```

### Run reports (lanes)

File-based lanes still write ` .agents/runs/<slug>/artifacts/*/report.md ` with human/agent **why**.
Session ledger is the automatic cross-CLI layer; run reports are richer for intentional tasks.

## Project memory pack

See [PROJECT-MEMORY.md](./PROJECT-MEMORY.md). Init: `~/.agents/bin/project-memory-init .` 
Night: `~/.agents/bin/night-audit .` 
Skill: `project-life`.

## Cursor read gate

The Cursor `before_read.py` hook reads one JSON payload from stdin, imports `decide_read`, and writes its permission response. A malformed result or exception returns `{"permission":"allow"}` (`profiles/cursor/lane-writer/scripts/before_read.py:25-37`). This hook therefore fails open on its own import or parsing failures.

## Lane status-line session routing

`lane_statusline_session.py` stores the `agent_type` for recognized lane-agent sessions so the status-line command can select the lane HUD. It extracts a session ID from session fields or transcript paths, including nested `data`; SessionEnd removes that session's marker. A non-lane agent also removes a known stale marker. A lane agent with no session ID writes a timestamped `last_lane_agent.json` fallback (`hooks/lane_statusline_session.py:56-67`, `hooks/lane_statusline_session.py:70-117`).

Malformed JSON, non-object payloads, and marker filesystem errors exit without blocking the host session (`hooks/lane_statusline_session.py:70-77`, `hooks/lane_statusline_session.py:84-101`, `hooks/lane_statusline_session.py:104-116`).

## Code quality post-edit guard

`guard_code_quality.py` reads the hook payload, resolves its file path, and exits when the file is missing, is under `.agents` or `node_modules`, or has no detected findings. For JavaScript and TypeScript extensions it scans for `any`, Prisma unsafe raw SQL, TypeScript suppression comments, and dynamic evaluation; it scans all supported files for credential-like hardcoded string assignments. A `guardian: allow` marker suppresses a matching line. Findings are formatted and passed to the client-specific post-block emitter (`hooks/guard_code_quality.py:11-28`, `hooks/guard_code_quality.py:34-69`, `hooks/guard_code_quality.py:71-78`).

If payload parsing or scanning raises, the outer handler exits successfully without blocking (`hooks/guard_code_quality.py:80-84`).

## Jev agent-spawn routing

The `jev-router` plugin defaults `LANE_JEV_EFFORT` to enabled; values `0`, `off`, `false`, and `no` disable routing. It routes a non-fork agent spawn only when at least one lane marker is non-empty. The router strips a raw task YAML preamble before classification, falls back to the default route on missing credentials, timeout, or request/parse errors, caches the result by spawned agent ID, then applies the cached effort to that agent’s turn steps (`plugins/lane-stack/hooks/jev-route-core.ts:57-60`, `plugins/lane-stack/hooks/jev-router.ts:16-20`, `plugins/lane-stack/hooks/jev-router.ts:61-88`, `plugins/lane-stack/hooks/jev-router.ts:93-129`).

## OpenCode lane plugin

`OpenCodeLanePlugin` starts telemetry and the Winnow sidecar in every session, and gates writer guard, notes, sticky task context, and effort routing on lane markers (`profiles/opencode/opencode-lane/v1.ts:208-234`). Lane chat messages update per-session prompt state and add a skill hint; failures are logged and contained (`profiles/opencode/opencode-lane/v1.ts:244-262`).

## Winnow response filtering

`handle_with_meta` increments request counters, skips unworthy post-tool events, obtains the judge runtime, and dispatches post-tool or user-prompt handlers. If runtime startup fails, it sends one notice and leaves tool results untouched; event exceptions are logged without breaking the tool call (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:92-120`).

The response extractor rewrites Bash `stdout`, Read file content, Grep content, or a string response. Other response shapes return `None` and remain unchanged (`plugins/lane-stack/winnow/sidecar/src/winnow/extract.py:30-82`). `decide` keeps blocks with missing probabilities and uncertain scores; it prunes only scores below `drop`, unless the error score reaches `keep` or the proposed pruning ratio is below `min_prune_ratio` (`plugins/lane-stack/winnow/sidecar/src/winnow/policy.py:23-59`).

`winnow_recall` uses the stub’s key to load cached output, optionally returns an inclusive line range, and reports a missing key when the cache entry is absent (`plugins/lane-stack/winnow/sidecar/src/winnow/mcp_server.py:21-37`).

Winnow replay can draw a seeded, blind hand-labeling sample from a judged file. It bins labeled blocks by probability (`low` [0, 0.2), `mid` [0.2, 0.5), `high` [0.5, 1.01)), defaults to 50/25/25 blocks per bin, skips blocks without a probability or usable weak label, and skips samples whose case or block cannot be resolved (`plugins/lane-stack/winnow/sidecar/src/winnow/labels.py:26`, `plugins/lane-stack/winnow/sidecar/src/winnow/labels.py:37-91`, `plugins/lane-stack/winnow/sidecar/src/winnow/cli.py:353-360`). The command writes JSONL and a Markdown sheet that hides the judge probability and weak label; a person can label interactively or import numbered answers, then compare agreement or score against hand labels (`plugins/lane-stack/winnow/sidecar/src/winnow/labels.py:94-121`, `plugins/lane-stack/winnow/sidecar/src/winnow/cli.py:189-219`, `plugins/lane-stack/winnow/sidecar/src/winnow/cli.py:348-375`).

## Before-read extraction limits

Winnow splits extracted text into numbered blocks. It closes a block at `block_lines` or at a blank line after at least half that size, and increases block size to stay within `max_blocks` (`plugins/lane-stack/winnow/sidecar/src/winnow/chunk.py:22-57`).

## Orchestrator guard (PM allowlist)

Policy lives in `hooks/guard_shell.py` and is installed into
`~/.claude/settings.json` PreToolUse via `merge_claude_settings.py` on
`install.sh`. It must stay aligned with SOLO / `dev-orchestrator`:

**PM shell allow**
- Read/inspect: `cat`, `jq`, `rg`, `git status/diff/log`, docker **logs/ps/inspect**, …
- Control plane: `run-init`, `run-validate`, `run-board`, `run-finalize`,
  `resume-project`, `wt-create`, `wt-merge-main`, `lane-stall-check`, `agents-doctor`
- Delivery: `git add/commit/merge/push` (no `--force` without lease, no `--no-verify`)
- Verification (L2): `npm|pnpm|yarn test|run typecheck|lint|build|check|verify`,
  `pytest`, `cargo test`, …

**PM shell deny**
- `run-controller start|watch|status` (must be `Agent(run-supervisor)`)
- `lane-ctl` lifecycle (start/accept/verify/…) — use `lane-supervisor`
- Background / nohup / redirections (`&`, `>`, heredoc writes)
- Package install/deploy, docker mutate, DB writes, process control, source sed -i

**PM edit allow**
- `PROGRESS.md`, `LESSONS.md`
- `.agents/**` text/json/yaml **except** machine receipts:
  `controller.json`, `controller/`, `artifacts/`, `events.jsonl`, `sessions.json`
- `docs/plans/**`
- `/tmp/*` short notes (md/yaml/json/txt)

**Silence protocol:** read receipts with `cat`/`jq` on `controller.json` /
`events.jsonl` (allowed). Do not invent nohup watchers (denied).

Mid-session policy flips without install are a defect class
(`orchestrator-guard-midsession-tightening`); pin by not rewriting
`settings.json` mid-run and always passing `agent_type` on tool payloads.

## How it works

1. The host CLI emits a hook event and payload.
2. The adapter normalizes that payload and calls shared policy or provider-specific logic (`hooks/guard_shell.py:1-40`, `profiles/cursor/lane-writer/scripts/before_read.py:25-37`).
3. A guard returns an allow/deny response or raises a provider-recognized error; observer hooks append session or telemetry data (`hooks/session_ledger.py:1-40`, `profiles/opencode/opencode-lane/v1.ts:293-309`).

| Hook mode | Input | Output | Failure behavior |
|---|---|---|---|
| Shell guard | Tool command and session context | Allow or deny response | Guard policy is evaluated before shell execution (`hooks/guard_shell.py:1-40`). |
| Cursor before-read | JSON hook payload from stdin | `permission: allow|deny` | Malformed output or exception returns allow (`profiles/cursor/lane-writer/scripts/before_read.py:25-37`). |
| Jev agent route | Non-fork lane-agent prompt | Model and effort route | Missing route or classification error uses the default route (`plugins/lane-stack/hooks/jev-router.ts:61-88`). |
| Winnow post-tool | Tool name, input, and result | Rewritten output or pass-through | Unsupported output or unavailable judge leaves original output intact (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:101-120`, `plugins/lane-stack/winnow/sidecar/src/winnow/extract.py:30-82`). |

## Business rules

- A non-fork spawn is routed only when routing is enabled and at least one lane marker is non-empty (`plugins/lane-stack/hooks/jev-route-core.ts:57-60`, `plugins/lane-stack/hooks/jev-router.ts:93-113`).
- Winnow keeps missing-probability and uncertain blocks; it prunes only low-probability blocks when the overall savings pass the configured threshold (`plugins/lane-stack/winnow/sidecar/src/winnow/policy.py:29-59`).
- Winnow recall line bounds are inclusive and use the line numbering printed in the stub (`plugins/lane-stack/winnow/sidecar/src/winnow/mcp_server.py:22-37`).

## Public commands

| Command / tool | Purpose |
|---|---|
| `winnow_recall(key, start?, end?)` | Restore all or a line range from cached output (`plugins/lane-stack/winnow/sidecar/src/winnow/mcp_server.py:21-37`). |
| `winnow doctor` | Diagnose a missing Winnow judge runtime (`plugins/lane-stack/winnow/sidecar/src/winnow/serve.py:103-110`). |

## Gotchas

- Cursor’s before-read adapter explicitly allows on exceptions, so adapter failure does not deny a read (`profiles/cursor/lane-writer/scripts/before_read.py:25-37`).
- Winnow chunk IDs are zero-based indexes formatted with a `b` prefix; line starts are one-based (`plugins/lane-stack/winnow/sidecar/src/winnow/chunk.py:9-19`, `plugins/lane-stack/winnow/sidecar/src/winnow/chunk.py:43-57`).

<!-- lane-pilot:backlinks -->
## Referenced by

- [docs/BEGINNER.de.md](BEGINNER.de.md)
- [docs/BEGINNER.es.md](BEGINNER.es.md)
- [docs/BEGINNER.fr.md](BEGINNER.fr.md)
- [docs/BEGINNER.ja.md](BEGINNER.ja.md)
- [docs/BEGINNER.ko.md](BEGINNER.ko.md)
- [docs/BEGINNER.md](BEGINNER.md)
- [docs/BEGINNER.pt-BR.md](BEGINNER.pt-BR.md)
- [Beginner guide](BEGINNER.ru.md)
- [docs/BEGINNER.zh-CN.md](BEGINNER.zh-CN.md)
- [Claude Lane Stack architecture](architecture.md)
- [Claude Lane Stack overview](overview.md)
