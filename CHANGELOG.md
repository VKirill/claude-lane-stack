# Changelog

## Unreleased

### Changed
- **Event-driven Grok control plane:** added a source-read-only
  `lane-supervisor` and typed `lane-ctl` actions for detached start, compact
  status/events/tail, recorded-argv retry, cancel, and independent verify.
- **Bounded parallel pools:** Grok writer sessions now default to five slots and
  support 1–10; verification uses a separate semaphore (default two, max ten).
- **Deterministic prompts:** `lane-ctl` composes the canonical Grok writer
  contract with raw task YAML and records control/prompt artifacts per attempt.
- **Lifecycle correctness:** `lane-exec` emits atomic JSONL lifecycle events,
  preserves child exit codes, and writes final status before closing its log.
- **Host-surviving detach:** `lane-bg` uses a transient user-systemd service by
  default and retains an explicit nohup fallback for hermetic tests/older hosts.
- **Attempt-bound acceptance:** verification now requires provider exit 0, uses
  the command snapshot captured at start, enforces per-command timeouts, rejects
  symlink escapes, and cannot survive into a retry. Retry is capped at one and
  revalidates a duplicate-free argv schema.
- **Portable session locks:** a read-only `XDG_RUNTIME_DIR` falls back to a
  private per-user lock directory under `/tmp`.
- **Grok is the only write programmer.** Removed write-lane CLI integrations and
  docs for the retired fast-write path. `agents-doctor` / profiles / implementer
  routing use Grok only; Codex remains review and write fallback.
- **Progressive MODE defaults:** grok/codex implementers use smart MODE when
  omitted (≥2 task YAML → `start`, single → `full`). PM skill forbids N×
  `MODE=full` on multi-task runs; dispatch must pass `RUN_DIR` + explicit MODE.
  Hard rule on multi-full join-wait in `dev-orchestrator` + `orchestrator-lanes`.


## 1.3.1 — 2026-07-16

Hardening progressive accept: anti-join guard + detached heartbeats.

### Added
- **`lane-mode-check`**: refuses `MODE=full` when a run has ≥2 task cards (exit 2 / `refused_full_on_multi_task`). Implementers call it in preflight. Override: `LANE_ALLOW_FULL=1`.
- **`lane-exec` auto-heartbeat**: with `--heartbeat path`, writes `heartbeat.json` on real activity (stdout/CPU, throttled) so `lane-stall-check` works after `MODE=start`.
- **`tests/test_progressive_accept.sh`**: fixtures for mode-check, progressive poll accept-while-sibling-runs, and heartbeat write.

### Changed
- grok/codex implementers + orchestrator-lanes / dev-orchestrator / LANE-EXEC docs document the hard guard and detached heartbeat.

## 1.3.0 — 2026-07-16

Progressive accept: no more join-wait on multi-task waves.

### Added
- **`lane-poll`**: multi-artifact poll for a run (`finish_ready` = CLI done, no report yet). PM uses it to accept tasks as they complete.
- **Implementer MODE** (`start` | `finish` | `full`) on grok/codex implementers: multi-task fire-and-return start, then finish for report; `full` remains for micro/single-task.

### Changed
- **Progressive accept is mandatory for ≥2 write tasks**: never wait for the slowest concurrent lane before accepting finished ones; free slots and pipeline the next ready task (still ≤3 concurrent). See `skills/orchestrator-lanes/SKILL.md`, `agents/claude/dev-orchestrator.md`, `docs/LANE-EXEC.md`, `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `docs/FILE-CONTRACT.md`.

## 1.2.0 — 2026-07-13

Nightly-only review, micro path, Lane Board dashboard, warm sessions.

### Added
- **Diff-scoped review SPEC**: `BASE_REF` is required and the supervisor constructs `SPEC` from the task's changed paths, so reviewers inspect only the scoped diff and direct dependencies, never repo-wide context. See `agents/claude/codex-reviewer.md`, `agents/codex/reviewer.md`.
- **Nightly medium-tier review**: Medium changes merge after report + `check-owns-paths` + verify; review runs off the critical path in the nightly `night-review` batch, findings become morning fix tasks, and strong review remains synchronous pre-merge. See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `skills/orchestrator-lanes/SKILL.md`.
- **Tiered review policy**: `none` for micro/low, `codex-reviewer` (`gpt-5.6-sol` + `medium`) for `risk: medium`, and `codex-reviewer` (`gpt-5.6-sol` + `high`, escalating to `xhigh` for critical paths) for high-risk/ship; micro commits now include `[micro:<slug>]`. See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `skills/orchestrator-lanes/SKILL.md`.
- **Micro path tier** (score 0–2): skips PLAN/worktree/board/heartbeat/reviewer for trivial ≤2-file changes; adds `verify` field (`none`|`smoke`|`tests`) to the task YAML contract. See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `docs/FILE-CONTRACT.md`.
- **Run-scoped warm Grok sessions**: `lane-session` resumes native conversations across related tasks, preserves up to three parallel slots, rotates after seven successful tasks by default (hard max ten), and invalidates failed/stale sessions.
- preflight smoke is cached by CLI version and agent-definition hash instead of spending a model call before every task.
- **Push-on-merge and meaningful commits**: PM pushes `main` right after merge when a remote exists; commit messages must be meaningful with conventional type(scope) and explanation in body. See `agents/claude/dev-orchestrator.md`, `skills/orchestrator-lanes/SKILL.md`, `docs/SOLO-ORCHESTRATION.md`.
- **Lane Board** (`board/`): from-scratch read-only dashboard — zero-dependency Node stdlib server + vanilla JS dark UI; projects overview with needs-attention strip, kanban with status-based scope=recent, todos view with full idea bodies, runs timeline, night-review history, Cmd+K search, SSE live refresh; `bin/lane-board` launcher.
- **Nightly review automation**: `bin/night-review` (per-repo batch review of the day's merged work -> REVIEW-<date>.md with per-run verdicts + Morning fix plan) and `bin/night-review-all` (auto-discovers lane-stack repos, reviews only those active in the last 24h; cron example included); `resume-project` surfaces the newest REVIEW report at session start.

### Changed
- **Pre-merge review gate removed by default**: solo, no-user-facing context — all review now runs in the nightly `night-review` batch (`none`/`nightly` tiers only); synchronous pre-merge review becomes opt-in per project via `gate: pre-merge` in PROGRESS.md Pointers or a task YAML. See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `skills/orchestrator-lanes/SKILL.md`, `agents/claude/dev-orchestrator.md`, `agents/claude/codex-reviewer.md`.

### Fixed
- Provider output is streamed through `lane-exec` for correct idle detection; interrupted lanes terminate the complete provider process group before releasing a session slot.

## 1.1.0 — 2026-07-11

Deep onboard, dual scenarios, activity-aware lanes, and Claude Bash background survival.

### Docs
- Full refresh of README (EN/RU) + v1.1.0 blocks on all locale READMEs; BEGINNER EN/RU + locale notes; ROUTING/LANE-EXEC/ONBOARD/COMPARISON/PROJECT-MEMORY/FILE-CONTRACT/llms.txt/install.sh aligned to current product.

## 1.1.0 details

### Changed
- **Language policy**: all agent-written files English; chat with human Russian (`docs/LANGUAGE.md`).

### Fixed
- **Lane background under Claude Bash**: long `lane-exec`/`grok`/`codex` must use **`lane-bg`** + poll **`lane-wait --once`**. Foreground Bash is killed ~2 minutes by the host (not lane-exec idle/max). Implementers + dev-orchestrator + LANE-EXEC updated.
- **lane-exec**: activity-aware timeouts (idle resets on stdout/CPU; absolute max). Replaces hard `timeout 570` in implementers so thinking agents are not killed mid-run.

### Added
- **Onboard depth** `fast` | `deep` (default: full→deep, minimal→fast):
  - Forensic deep checklist in Codex `onboard.md` (entrypoints, flows, wiki↔code, verify, ship, secrets)
  - Auto `deep-scan.md` evidence pack under `.agents/runs/_onboard/artifacts/001/`
  - Flags: `--deep` / `--fast`, `ONBOARD_DEPTH=`, `/project-onboard deep`
  - Nested deploy detect (maxdepth 3 compose/Dockerfile) for maturity score
  - Deep uses **gpt-5.6-sol** high; fast uses terra high
- **Dual onboard scenarios** (`minimal` vs `full`):
  - Auto maturity score in `project-onboard` → `.agents/onboard.scenario.yaml`
  - Override: `--minimal` / `--full` or `ONBOARD_SCENARIO=`
  - Full seeds: GOTCHAS, GLOSSARY, TESTING, deployment, nested `apps/*/CLAUDE.md`, optional SECURITY
  - Skip seed when case-insensitive sibling exists (`gotchas.md` vs `GOTCHAS.md`)
  - Docs: `docs/ONBOARD-SCENARIOS.md`; Codex `onboard.md` + `docs-maintain` scenario-aware
  - Templates: `GOTCHAS.md`, `GLOSSARY.md`, `TESTING.md`, `deployment.md`

- **GPT-5.6 routing** (Sol / Terra / Luna): no GPT-5.5. See `docs/ROUTING.md`, `profiles/claude-codex.yaml`.
  - Write default: **terra** (+ xhigh medium); high-risk: **sol** xhigh
  - Review/ship: **sol** xhigh
  - Onboard / docs-maintain: **terra** high
  - Luna: trivia only, not default lanes
- **Onboard** seeds `docs/ARCHITECTURE.md` + README anamnesis pattern; Codex fills from evidence.
- **docs-maintainer**: `docs-maintain-project`, `docs-maintain-all`, skill + `codex-docs-maintainer` agent.
- Templates: `ARCHITECTURE.md`, `README.anamnesis.md`.

### Fixed
- : ban `call_mcp_tool` / `inheritMcp` on lane agents; grok-implementer preflight.

## 0.1.0
- Initial public package (file contracts, solo merge, beginner guides).
