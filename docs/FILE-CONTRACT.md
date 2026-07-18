# File-based agent contracts (no orchestrator MCP)

Replace Postgres/task MCP with **files in the project**. Agents never call task/orchestrator MCP — they only `Read` paths.

**Language:** all contract files (**PLAN, SPEC, STATUS, task YAML, report.md, review.md, MERGE.md**) are **English only**. Chat with the human may be Russian. See [LANGUAGE.md](LANGUAGE.md).

**Solo operator mode (default):** one human, one orchestrator. Workers may use worktrees; **only the orchestrator merges to `main`**. The human never merges.

## Docs vs runs (do not confuse)

| Path | Use |
|------|-----|
| `.agents/runs/<slug>/` | **Execution** for the orchestrator: PLAN, task YAML, reports, MERGE |
| `.agents/findings/<fingerprint>.json` | Canonical nightly review finding and closure state |
| `.agents/night-review/checkpoint.json` | Last fully persisted review boundary; never advances on partial failure |
| `.agents/runs/<slug>/night-fix-state.json` | Resumable repair-run control state |
| `.agents/night-fix-current.json` | Pointer to the current/last repair state |
| `.agents/todos/` | Ideas / backlog until promoted |
| `docs/plans/<topic>/` | Durable **strategy / SEO / product** docs (e.g. `COCOON.md`) for humans + long-form research |
| `docs/` | Architecture, decisions, wiki |

A COCOON or product strategy **correctly** lives under `docs/plans/`. 
When the user says implement → **promote** into `.agents/runs/<slug>/` with `owns_paths` tasks. Do not treat `docs/plans` alone as a coding run.

## Layout (per feature run)

```text
.agents/runs/
  BOARD.md # live board (all runs) — regenerate via run-board
  <slug>/
    run.yaml # schema v2: repo/base/score/pools/gate/finalize actions
    PLAN.md # concise DAG and ownership boundaries
    SPEC.md # interfaces, invariants, behavioral acceptance
    STATUS.md # generated view; never an append-only log
    merge.json # machine merge/push/install receipt
    MERGE.md # human view of merge.json
    finalize.json # deterministic PROGRESS/BOARD/OPEN actions
    worktree.json # { branch, path, base } if isolated
    sessions.json # Grok warm-session pool + rotation history
    events.jsonl # append-only lifecycle events for registered lanes
    controller.json # schema v1: atomic run-level lifecycle summary and next action
    controller/
      lane-bg.pid # durable controller supervisor PID
      lane-bg.exit # terminal controller exit
      lane-bg.supervisor.log # compact transition log
    tasks/
      001-short-title.yaml # immutable after first start
    artifacts/
      001/
        state.json # sole lifecycle state for current attempt
        report.md
        owns-check.json
        acceptance.json # sole technical done receipt
        review.json # codex when required
        heartbeat.json # last touch from lane
        attempts/
          01/
            control.json # immutable argv + task hash + attempt metadata
            prompt.md # canonical writer contract + raw immutable task YAML
            provider.out
            runtime.json # sanitized Grok protocol/model/usage receipt
            verification.json # independent command evidence for attempt 01
            lane-bg.pid
            lane-bg.exit
            lane-bg.supervisor.log
            lane-exec.log
          02/ # retry; attempt 01 is never overwritten
```

Normal daytime runs start through `run-controller`, itself detached with
`lane-bg`. It releases the task DAG through typed `lane-ctl` actions and writes
`controller.json`; one source-read-only `run-supervisor` watches bounded state
changes only for operator visibility. Provider lanes remain detached and no
Claude model is the lifecycle decision loop. See [LANE-EXEC.md](LANE-EXEC.md).
The receipt follows `schemas/run-controller-v1.schema.json`; consumers must
fail closed on unknown run/task stages instead of inferring success.

Grok write lanes run through `lane-session`. Sessions are scoped to this
run, role, worktree, and model. One slot accepts one task at a time; concurrent
tasks spill into a pool of five slots by default, configurable from 1–10. A slot rotates after seven
successful tasks (configurable up to a hard maximum of ten), after a provider
failure, or when cwd/model changes. Review lanes never reuse writer sessions.
Only `EndTurn` is a successful Grok terminal reason. `Cancelled`, `Error`, an
unknown terminal reason, or a missing/invalid final report envelope is a
retryable protocol failure and cannot enter verification. The provider cannot
write `.agents`: Bubblewrap mounts the control plane read-only for Grok.
Instead, Grok returns one report envelope bound to `TASK_ID` and the assembled
prompt SHA-256; trusted `lane-session` validates it and atomically writes root
`report.md`. A valid `STATUS: partial|timeout|unavailable` report remains
provider-incomplete and retryable. The current attempt's `runtime.json` binds
that file by SHA-256; status, verification, and acceptance fail closed after a
manual or stale-report substitution. Retry moves the old root report into its
attempt directory before the next provider starts.
Provider stderr/error text is never persisted raw. A bounded in-memory matcher
stores only a typed failure class and digest. The controller records a
non-blocking retry deadline (30 seconds by default), replays Grok once, and may
start one ephemeral Codex `gpt-5.6-sol` + `high` attempt only after a second
failure explicitly marked `fallback_eligible`. Codex receives the same
immutable prompt and read-only `.agents` boundary, then produces the same bound
report and runtime receipt. Unknown, task, ownership, verification, and
cancellation failures never trigger an automatic provider switch.

Night review is also file-based. Codex Sol xhigh emits schema-constrained chunk
results; the engine validates and deduplicates them into
`.agents/findings/<fingerprint>.json`. Each finding preserves source SHA, source
task/attempt when known, severity, evidence, ownership scope, verification,
status, and first/last-seen timestamps. `REVIEW-YYYY-MM-DD.md`, OPEN, and TODOs
are projections of those canonical files, not independent truth. An actionable
finding may link to a generated v2 repair task and can become `fixed` only after
independent verification plus a matching fresh re-review receipt.

`artifacts/<task>/review.json` follows
`schemas/task-review-receipt-v2.schema.json`. It binds the result to the exact
task SHA, current attempt, canonical worktree, immutable base commit, tracked
binary diff digest, and a framed digest of all Git-visible untracked files.
`lane-ctl accept` recomputes those digests; any edit after review fails closed.
Generated repair tasks also retain the source finding fingerprint and control
digest, so a closed, changed, or missing finding cannot be dispatched from a
stale task file.

`<slug>` = kebab-case feature, e.g. `fix-subscription-panel-flicker`.

Create this layout with `run-init <repo> <slug> ...`. Validate it before any
provider starts with `run-validate --phase pre-dispatch` and before merge with
`run-validate --phase pre-merge`. The durable controller repeats
`pre-dispatch` validation at startup and before each dependency-release wave.

## Task YAML v2

```yaml
schema_version: 2
id: "001"
title: "Gate loading on initial load only"
risk: low # low | medium | high
lane: grok # -coder | -frontend | grok | codex-review
verify: smoke # none | smoke | tests — see table below
project_cwd: "/absolute/path/to/repo-or-worktree"
read_first:
  - AGENTS.md
interfaces:
  - "SubscriptionPanel(props: SubscriptionPanelProps)"
invariants:
  - "Cached data remains visible during refresh"
out_of_scope:
  - "API response shape"
expected_outputs:
  - "Loading placeholder is limited to the initial request"
owns_paths:
  - apps/cabinet/src/components/SubscriptionPanel.vue
  - apps/cabinet/src/components/subscription-panel.test.ts
never_touch:
  - apps/cabinet/src/server/**
  - prisma/**
  - .env*
objective: |
  One paragraph: what and why.
acceptance:
  - "Loading text only when pending and no data"
depends_on: []
verification:
  - command: "npm -w apps/cabinet run test -- subscription-panel"
    cwd: "/absolute/path/to/repo-or-worktree"
    timeout_sec: 600
```

The raw task bytes are hashed at first start. `lane-ctl` rejects retry, verify,
or accept if those bytes later change. Existing schema-v1 runs remain readable,
but all newly generated runs use v2.

### `verify` levels

| Level | Meaning |
|-------|---------|
| none | No tests/build evidence needed (visual or trivial change) |
| smoke | Build passes / page renders / command runs once |
| tests | Real test run evidence required in report |

For both legacy and v2 tasks, `smoke` and `tests` require at least one recorded
command. An empty command snapshot fails closed and cannot produce an
acceptance receipt. Only `verify: none` permits an empty list.

Schema-v2 commands are parsed and executed as argv vectors without a shell.
Shell composition, redirection, substitution, unsafe path arguments, direct
network/package tools, and mutating package-manager subcommands are rejected
before the provider starts. Optional project verifier basenames come from
`.agents/night-shift.yaml`; the accepted list is frozen in the attempt's
`control.json`. Schema-v1 execution remains unchanged for compatibility.

### Ownership rules

1. Write lane may only edit paths under `owns_paths` (or `files` if `owns_paths` omitted). 
2. `never_touch` always wins — even if listed in owns. 
3. Parallel tasks **must** have disjoint `owns_paths` (no path prefix overlap). 
4. After a lane finishes, the daytime controller runs `check-owns-paths
   --run-scope`: shared-worktree changes must stay inside the union of all
   validated disjoint task ownership. Direct/single-task checks remain strict
   to that task. Any edit outside the selected scope → task **blocked**, not done.
5. Build errors in files **not** in owns_paths → ignore / wait; do not “helpfully” fix.

## Acceptance receipt

`artifacts/<id>/acceptance.json` is the only technical definition of done:

```json
{
  "schema_version": 2,
  "task_id": "001",
  "task_sha256": "<64 hex>",
  "attempt": 2,
  "provider_exit": 0,
  "provider": "grok",
  "model": "grok-4.5",
  "report": "complete",
  "owns_check": "passed",
  "verification": "passed",
  "review": "not_required",
  "accepted": true,
  "accepted_at": "2026-07-18T01:30:00+00:00"
}
```

STATUS.md, BOARD.md, resume-project, and the merge gate derive completion from
this receipt. A provider exit, a green worker claim, or a `status: done` line in
legacy YAML is not sufficient for schema v2.

## Lifecycle (orchestrator — solo)

1. `run-init` creates run.yaml, PLAN, SPEC, generated STATUS, and a strict task
   template; replace placeholders, split tasks, then pass pre-dispatch validation.
2. If score ≥ 4 **or** ≥2 write tasks → `wt-create` worktree; all tasks share that `project_cwd`. 
3. If single low-risk task → may use main working tree (still PM commits). 
4. Dispatch one source-read-only `run-supervisor`. It starts or resumes the
   durable `run-controller`; provider slots default to 5 (range 1–10) and
   parallel ownership remains disjoint.
5. The controller reacts to task receipts and persists `controller.json`.
   `lane-supervisor` status/tail remains a bounded manual diagnostic.
6. After provider exit 0 plus a complete report, run the registered structured `verification` snapshot under
   the independent verify pool (default 2, range 1–10). Each command has a
   bounded timeout and evidence is valid only for that provider attempt.
7. Run `check-owns-paths --run-scope` to write `owns-check.json`, then
   `lane-ctl accept`. The receipt records `scope: run` and the exact task IDs
   whose ownership formed the union.
   The receipt is valid only for the immutable task hash and current attempt.
   Accept each task **as soon as** `acceptance.json.accepted` is true — do not
   batch-wait for the slowest task.
8. No daytime LLM review. Explicit historical review gates stop for an operator
   decision; the standard Codex review/fix/re-review loop runs at night.
9. When all current-attempt receipts are accepted, PM freezes the source branch
   and pre-merge validation passes. `wt-merge-main` merges locally, writes
   merge.json/MERGE.md, invokes `run-finalize`, pushes only after finalize
   succeeds, and removes the worktree only after a successful ship.
10. Human is never asked to merge.

## Why files beat task MCP

| File contract | Task MCP |
|---------------|----------|
| Visible in git, reviewable | Hidden in Postgres |
| Agents `Read` path — zero MCP tax | Every worker hits MCP |
| Works offline | Needs DB |
| Easy handoff | Opaque |

## Naming

- Task ids: `001`, `002` (sort = plan order). 
- Never put secrets in YAML.
