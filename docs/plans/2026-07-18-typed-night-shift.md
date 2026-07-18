# Typed night shift for Claude + Grok + Codex

## Goal

Replace the fragile free-form nightly batch with a fail-closed, resumable flow:

1. Codex `gpt-5.6-sol` + `xhigh` reviews bounded diff chunks read-only.
2. Structured findings are validated, deduplicated, and persisted.
3. Actionable findings become immutable schema-v2 Grok tasks.
4. Grok remains the only normal code writer.
5. Independent verification and a fresh Codex re-review close each finding.

## Non-goals

- Forking or vendoring the Grok Build runtime.
- Giving Codex normal product-code write access.
- Replacing the existing run-scoped warm-session pool with ACP in this stage.
- Automatically deploying high-risk changes without the configured merge gate.

## Known root causes

- Legacy `lane-ctl verify` records `passed` when a smoke/tests task has zero
  verification commands; schema-v2 already rejects this, legacy does not.
- `night-review` is one strict-mode shell script: a missing task lookup returns
  non-zero from `emit_task_context` and aborts the full project review silently.
- One unbounded prompt is used for all selected commits, so large repositories
  can exceed the provider input limit.
- The reviewer returns free-form lines parsed with `grep`; only a daily aggregate
  TODO is created, and prior unresolved findings are not a first-class queue.
- The real nightly command uses `high` despite the requested Sol `xhigh` policy.
- Grok writer output is plain text and scope restrictions are primarily checked
  after the write, not captured as a structured runtime receipt.

## Workstreams

### A. Verification fail-closed

Write scope:

- `bin/lane-ctl`
- `tests/test_lane_ctl.py`

Steps:

1. Add a regression test proving a legacy `verify: smoke|tests` task with an
   empty recorded command snapshot fails and writes no passed receipt.
2. Make the common verification parser enforce non-empty commands for every
   schema version when `verify` is `smoke` or `tests`.
3. Preserve `verify: none` compatibility and explicit legacy string commands.
4. Verify failed attempts cannot be accepted.

### B. Structured nightly findings and fix task compiler

Write scope:

- `bin/night-review`
- `bin/night-review-all`
- new `bin/night-review-engine`
- new `schemas/night-review-result-v1.schema.json`
- new `schemas/finding-v1.schema.json`
- new `tests/test_night_review.py`

Steps:

1. Keep `night-review` as a compatibility wrapper around a tested Python engine.
2. Select unreviewed commits/runs from a durable checkpoint and include unresolved
   findings from previous nights.
3. Build bounded per-run/per-commit chunks with deterministic byte limits; record
   skipped/oversized chunks as failures rather than advancing the checkpoint.
4. Invoke `codex exec -p night-review --ephemeral --output-schema ...` once per
   chunk and validate every result locally.
5. Persist canonical findings under `.agents/findings/<fingerprint>.json` with
   source SHA/task/attempt, severity, evidence, scope, verification, status,
   first_seen, and last_seen.
6. Render `REVIEW-YYYY-MM-DD.md`, `.agents/agent-notes/OPEN.md` projection entries,
   and one idempotent TODO per actionable finding.
7. Compile actionable findings into one schema-v2 run under
   `.agents/runs/night-fixes-YYYY-MM-DD/`; every task has non-empty structured
   verification commands, disjoint ownership, and a source finding id.
8. Never mark a finding fixed until a matching acceptance/re-review receipt exists.

### C. Grok runtime receipts and pre-write guardrails

Write scope:

- `bin/lane-session`
- `tests/test_lane_session.py`
- `agents/grok/writer.md`

Steps:

1. Keep run-scoped warm session IDs and process-group cleanup unchanged.
2. Switch the provider transport to `streaming-json` and parse session/usage/tool
   events without hiding stdout activity from `lane-exec`.
3. Add `--no-subagents`, an explicit workspace sandbox, and deterministic rules
   that bind writes to the registered task contract.
4. Persist a sanitized runtime receipt containing model, session id, effort,
   usage/cost when exposed, exit status, and Grok version.
5. Fail closed on malformed structured output while preserving a bounded plain-log
   diagnostic artifact.

### D. Codex profile, Claude routing, docs, installation

Parent write scope:

- new `profiles/codex/night-review.config.toml`
- `agents/claude/codex-reviewer.md`
- `agents/claude/dev-orchestrator.md`
- `skills/orchestrator-lanes/SKILL.md`
- `docs/FILE-CONTRACT.md`
- `docs/LANE-EXEC.md`
- `docs/PROJECT-MEMORY.md`
- `docs/ROUTING.md`
- `docs/SOLO-ORCHESTRATION.md`
- `install.sh`
- focused installer/contract tests as required

Steps:

1. Install a dedicated Codex profile using Sol xhigh, read-only sandbox, never
   approval, pragmatic reviewer instructions, and no product edits.
2. Define the night supervisor as control-plane only: select, dispatch, observe,
   verify, re-review, accept, and escalate; never write product code.
3. Document finding/task/review receipts and the bounded repair loop.
4. Install runtime files into `~/.agents`; install Claude agent definitions into
   `~/.claude` without changing existing running processes.

### E. Resumable night repair runner

Parent write scope:

- new `bin/night-shift`
- new `bin/night-fix-runner`
- new `bin/night-shift-all`
- `bin/run-init` only if required to adopt an isolated worktree safely
- focused runner tests

Steps:

1. Keep review/compilation separate from execution: `night-review` persists a
   complete finding set first; `night-fix-runner` consumes only validated tasks.
2. Create a dedicated `agent/night-fixes-YYYY-MM-DD` worktree and bind every
   generated task `project_cwd` and verification cwd to that exact path.
3. Persist runner state after every transition so interruption resumes at
   dispatch, provider exit, verify, re-review, or accept without replaying a
   completed side effect.
4. Use deterministic polling of `lane-ctl` receipts; never use a model as the
   liveness loop. Retry a failed provider attempt at most once.
5. Reject generated verification commands containing shell composition,
   redirection, substitutions, or an unapproved executable. Mark the finding
   `needs_human` instead of executing it.
6. Prepare and verify fixes automatically. Merge/push only when a project-level
   night-shift policy explicitly enables it; otherwise leave the accepted
   worktree and receipts ready for the morning PM.

## Night repair policy

- Normal writer: Grok only.
- Reviewer/spec compiler: Codex Sol xhigh, read-only.
- Control plane: deterministic scripts plus Claude supervisor decisions.
- Repair attempts: maximum two per finding.
- Low/medium: may proceed through the existing merge policy after verify + re-review.
- High/critical: fix may be prepared and verified, but configured pre-merge gate
  remains mandatory; no automatic deployment broadening.
- Automatic merge/push is opt-in per project; installing the stack never enables
  publication implicitly.
- No Grok or Codex subagent trees inside provider lanes; concurrency belongs to
  the lane pool.

## Acceptance checks

- Empty legacy smoke/tests verification fails in the original reproduction.
- Existing non-empty legacy and schema-v2 verification remains green.
- Missing task context cannot abort a whole nightly project review.
- Oversized input is split or recorded as a failed chunk; checkpoint is unchanged.
- Invalid model output cannot create findings or tasks.
- Empty, shell-composed, or unapproved generated verification commands cannot be
  dispatched or executed.
- Re-running the same night is idempotent: no duplicate findings/tasks/TODOs.
- Unresolved previous findings are included even with no new commits.
- Every generated fix task passes `run-validate --phase pre-dispatch`.
- Codex invocation is Sol xhigh + read-only via the dedicated profile.
- Grok runtime preserves warm-session reuse, parallel slot isolation, streamed
  activity, and process-group cleanup.
- Interrupted night repair resumes from receipts without repeating an accepted
  task, and a dirty main checkout leaves the fix worktree recoverable.
- Full Python/Node/shell test suites and `git diff --check` pass.
- GitNexus `detect_changes` is reviewed before any commit.
- Claude Companion code review findings are triaged and accepted fixes reverified.

## Rollback

- Keep the old CLI names and install locations.
- `night-review --dry-run` remains non-mutating.
- Nightly checkpoints advance only after all selected chunks persist valid results.
- Runtime installation is copy-based; repository files remain the source of truth.
- No commit, push, merge, service restart, or mutation of running lanes is part of
  this implementation unless separately requested.
