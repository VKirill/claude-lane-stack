# Changelog

## 1.5.2 — 2026-07-18

### Fixed
- **Lane Board cards stay inside their columns:** task cards can shrink around
  long runtime details without covering neighbouring lanes at desktop or
  tablet widths.
- **The dashboard mirrors fail-closed acceptance:** task details validate the
  current attempt, runtime identity, terminal protocol, sandbox contract, and
  prompt/report digests before presenting a provider report as complete.
- **Project discovery skips non-project data trees:** recursive scanning prunes
  `.agents`, `.git`, `node_modules`, and `postgres_data`, eliminating repeated
  permission errors and needless CPU/memory use on broad application roots.
- **Board assets refresh predictably:** static JavaScript and CSS use
  `Cache-Control: no-cache`, so a normal reload picks up a new release.

## 1.5.1 — 2026-07-18

### Fixed
- **Headless Grok no longer cancels on shell approval:** writer lanes use the
  unattended `bypassPermissions` mode required by Grok Build instead of
  interactive `acceptEdits`, which cancelled non-auto-approved terminal calls.
- **The control plane is kernel-enforced read-only to Grok:** an outer
  Bubblewrap mount protects repository `.agents` while owned source paths stay
  writable inside the same outer workspace boundary. Grok's native sandbox is
  disabled inside it so terminal tools are not blocked by nested isolation.
- **Host pathname endpoints are isolated from writer lanes:** `/run`, `/tmp`,
  and `/var/tmp` are private mounts, active pathname Unix sockets exposed by a
  writable bind are masked, and the provider receives an allowlisted
  environment rather than SSH, D-Bus, Docker, or unrelated host variables.
- **Reports cross a validated transport:** Grok returns one final envelope bound
  to task ID and prompt digest; `lane-session` rejects missing, duplicate,
  malformed, stale, cancelled, oversized, or symlink-targeted reports and
  atomically materializes canonical `report.md` only after `EndTurn`.
- **Acceptance is bound to the current attempt:** status, verify, and accept
  require the current `runtime.json` prompt/report digests; retry archives the
  old root report and acceptance receipts record `report_sha256`.
- **Grok routing now probes Bubblewrap:** `agents-doctor` disables writer lanes
  when the binary exists but cannot create the required sandbox.

## 1.5.0 — 2026-07-18

### Added
- **Durable daytime run controller:** `run-controller start/watch/status` owns
  schema-v2 DAG dispatch, separate bounded provider/verification pools,
  progressive ownership/verification/acceptance, one retry, atomic
  `controller.json`, duplicate locking, crash receipts, and host-surviving
  `lane-bg` process lifetime.
- **One visible supervisor per run:** the source-read-only `run-supervisor`
  starts or resumes the controller and stays visible through bounded watches
  until the run is accepted or blocked. `lane-supervisor` remains available for
  explicit one-lane diagnostics and recovery.
- **Exact Lane Board observability:** run/task APIs and drawers expose raw
  lifecycle stage, attempt, PID/liveness, provider exit, heartbeat age, report
  completeness, reason, next action, and the run controller summary without
  changing the existing board-column grouping.

### Changed
- **Day and night are separate loops:** daytime has no LLM review; exact
  ownership and registered verification drive acceptance and shipping. The
  existing Codex Sol xhigh review → Grok fix → re-review pipeline remains the
  independent night shift.
- **Grok completion is fail-closed:** only `EndTurn` is successful.
  `Cancelled`, `Error`, and unknown terminal reasons now produce a sanitized
  protocol failure and non-zero wrapper exit.
- **A report is mandatory before verify:** provider exit zero without root
  `report.md` and `STATUS: complete` is `provider_incomplete → retry`, never
  `awaiting_verification`.
- **Parallel ownership no longer self-conflicts:** daytime shared worktrees use
  a receipt-recorded union of all pre-dispatch-validated, disjoint task
  `owns_paths`; direct and night single-task checks remain task-strict.
- **Dispatch validation stays fresh:** the controller reruns strict
  `pre-dispatch` validation at startup and before every dependency-release wave.

## 1.4.0 — 2026-07-18

### Changed
- **Typed autonomous night shift:** `night-shift` now runs bounded Codex Sol
  xhigh review chunks, validates JSON-schema output, persists deduplicated
  `.agents/findings/`, and compiles actionable findings into immutable v2 Grok
  tasks in an isolated worktree. `night-shift-all --jobs 1..10` coordinates
  active repositories.
- **Bounded repair and closure:** `night-fix-runner` resumes from machine
  receipts, retries Grok at most once, rejects unsafe generated verification,
  runs ownership + independent verification, requires a fresh Codex re-review,
  and records standardized finding closure links. Night merge/push is opt-in
  through `.agents/night-shift.yaml`.
- **Dedicated Codex reviewer profile:** installer adds
  `~/.codex/night-review.config.toml` with `gpt-5.6-sol`, `xhigh`, read-only
  sandbox, and approval policy `never`; unattended invocations ignore unrelated
  base user config and MCP startup.
- **Structured Grok runtime:** `lane-session` uses streaming JSON,
  `--no-subagents`, workspace sandbox rules, bounded logs, protocol fail-closed,
  and an attempt-local sanitized `runtime.json` while preserving warm-session
  reuse and the 1–10 slot pool.
- **Live E2E hardening:** automated Grok and Codex lanes mark their hook
  processes as orchestration work, preventing global session-ledger hooks from
  mutating reviewed worktrees. Codex receives an API-compatible projection of
  the result schema while the engine retains full local JSON Schema validation.
- **Role-specific skills:** every Claude control/review/fallback subagent now
  declares a narrow skill allowlist; the dev-orchestrator list is duplicate-free.
- **Verification is fail-closed:** legacy and v2 `smoke/tests` tasks with an
  empty recorded command list can no longer receive a passed receipt.
- **V2 verification is shell-free:** `lane-ctl` validates the executable,
  arguments, package subcommand, and worktree boundary before provider launch,
  snapshots the project allowlist into the attempt control receipt, and later
  executes the parsed argv directly instead of invoking `/bin/bash -c`.
- **Deterministic bin install:** `install.sh` copies only regular executable
  files, so local `__pycache__` directories cannot trigger the fallback copy,
  leak runtime caches into `~/.agents/bin`, or drift installed permissions.
- **Night-shift release hardening:** stale empty legacy receipts are untrusted,
  recurring fixed findings reopen, reviewer input is treated as untrusted data,
  and generated verification rejects shell expansion, globbing, package
  fetch/install, and worktree escapes.
- **Versioned run contracts:** `run-init` now generates schema-v2 `run.yaml`,
  PLAN/SPEC/STATUS views, and a complete task template; `run-validate` gates
  dispatch and merge with schema, DAG, path-ownership, and receipt checks.
- **Immutable task lifecycle:** task YAML is hashed at first start; runtime
  state moved to `state.json`, retries preserve `attempts/NN`, and completion
  is represented only by `acceptance.json`.
- **Machine delivery receipts:** ownership, verification, acceptance, merge,
  local install, and deterministic finalization now have JSON receipts while
  Markdown files remain concise human views.
- **Generated status views:** heartbeat no longer appends to STATUS.md;
  `run-board` rebuilds v2 STATUS/BOARD from state and acceptance, with legacy
  run fallback in CLI and Lane Board APIs.
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
- **Pre-merge review gate removed by default**: solo, no-user-facing context — all review now runs in the nightly `night-review` batch (`none`/`nightly` tiers only); synchronous pre-merge review becomes opt-in per run via `gate: pre-merge` in `run.yaml` (or a project default in PROGRESS.md Pointers before `run-init`). See `docs/ROUTING.md`, `docs/SOLO-ORCHESTRATION.md`, `skills/orchestrator-lanes/SKILL.md`, `agents/claude/dev-orchestrator.md`, `agents/claude/codex-reviewer.md`.

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
