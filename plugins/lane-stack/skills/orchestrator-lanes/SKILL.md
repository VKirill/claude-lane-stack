---
name: orchestrator-lanes
description: Claude Code `dev-orchestrator` only. File-based multi-lane PM playbook (score, DAG, run-controller, L0/L1/L2, ship). Use when this session IS that agent. SKIP: Grok, Codex, Kimi, Qwen, AGY, Cursor writer CLIs and any default coding agent — do not load, do not wt-create.
---

# Orchestrator lanes — solo operator

Load: **karpathy-guidelines**, **lane-contract**, **project-memory**, **resume-project**.

Docs: `FILE-CONTRACT.md`, `ROUTING.md`, `SOLO-ORCHESTRATION.md`,
`PLATFORM-CAPABILITIES.md` (Claude Code + Codex features we use),
`docs/decisions/ADR-codex-effort.md` under the lane-stack / `~/.agents/docs/`.

You are the **only** person who merges to `main`. Human never merges.

---

## Phase 0 — Score (announce once)

+2 multi-problem · +2 UI/state/auth/pay · +2 backend/API · +2 multi-surface · +2 needs verify · +3 prod/billing/security

| Score | Path |
|------:|------|
| 0–2 | Micro: 1 short contract, **commit main** |
| 3–6 | Express: 1 task, dispatch, verify, **commit/merge main** |
| 7–8 | Brief: 2–4 tasks, **filled** PLAN + SPEC; workspace per `adoc` profile |
| 9–10 | Full: rich SPEC + DAG; workspace per `adoc` profile |
| 11+ | Split feature; ask user |

**Writer source of truth = `adoc` / `agents-doctor`** → `.agents/routing.profile.yaml`
(`lanes.main_write`, `writer.model`, `writer.reasoning_effort`, **`workspace.mode`**).

- Every task YAML **must** set `lane: <main_write>` exactly (e.g. `lane: codex`).
- Never hardcode `lane: kimi` unless adoc says so. `run-validate` rejects mismatch.
- `run-controller` defaults `--provider` / model / effort from the same profile.
- Selectable writers: kimi / qwen / grok / agy / **codex**. Codex Sol remains recovery + night review / onboard / docs.
- **Workspace** (adoc tab **Work**): `in_place` | `worktree` | `auto` — see Phase 2.

---

## Task decomposition (MUST — non-negotiable)

Bad multi-task runs almost always start here. Apply **before** `run-init` / before filling YAML.

### One outcome per task

| Rule | Do | Don't |
|------|----|--------|
| Single product outcome | One shippable behavior per task id | Bundle “rewrite feature A” + “delete subsystem B” in one task |
| Unlock vs feature | Minimal **decouple** task if B must compile without A’s modules | Make a large feature rewrite block a pure deletion DAG edge |
| Risk class | Keep similar risk/blast in one task | Mix low UI polish with high auth/schema in one YAML |
| Owns completeness | Every file the objective **must** touch is in `owns_paths` (companions included) | Rely on OFF-SPEC edits (“I had to touch intent_qa”) |
| depends_on | Only real compile/data edges | “002 waits on 001 because the chat summary listed them in order” |

### Patterns

```text
# Good — unlock then delete then optional feature
001-decouple  owns: callers that import doomed modules
002-delete    depends_on: [001]   owns: modules + routes to remove
003-ui        depends_on: []      parallel if disjoint owns
004-feature   depends_on: [] or [001]  new behavior (e.g. SERP v4) — separate outcome

# Bad — combos that stall ships
001 = full SERP rewrite + remove all structure imports  → 002 waits on unrelated SERP work
001 owns missing companion files the prompt forces the writer to edit
```

### Size budgets (soft, then hard)

| Signal | Action |
|--------|--------|
| `owns_paths` ≥ 12 entries **or** objective > ~80 lines | Prefer split |
| Two independent user-visible outcomes | Prefer two tasks or two runs |
| Delete fan-out + new algorithm | **Always** split (delete DAG ≠ greenfield feature) |

### Parallelism

- Parallel only with **disjoint** `owns_paths` (and disjoint runtime side effects when possible).
- Shared worktree is fine; do not put package caches in owns (see owns noise recovery).

---

## Phase 1 — Files

**Not** `docs/plans/` for coding execution. Strategy stays in `docs/plans/`; promote to a run when implementing.

```bash
run-init "$(pwd)" <slug> --score <score>
# Fill PLAN.md, SPEC.md (required content when score≥7 or ≥2 tasks), tasks/*.yaml
plan-critique --run-dir "$(pwd)/.agents/runs/<slug>"   # stages.plan_critique (adoc)
# MUST read artifacts/critique.json → decision + pm_action (see below)
run-validate --run-dir "$(pwd)/.agents/runs/<slug>" --phase pre-dispatch
run-board "$(pwd)"
```

**Plan critique** (configure in `adoc` → **Stages**):

1. **Structural** checks always run when `enabled`.
2. When `provider` is `qwen` / `codex` / `kimi` / `grok` / `agy` (not `structural`),
   `plan-critique` **invokes that model** one-shot and merges findings.
3. Writes `artifacts/critique.json` + `critique.md` with a PM **`decision`**:

| `decision` | PM must |
|------------|---------|
| `ship` | Proceed to pre-dispatch → controller |
| `revise` | Prefer fix PLAN/SPEC/tasks, re-run `plan-critique`; residual risk only with explicit reason (advisory) or `--ack --note` (gate) |
| `revise_required` | **Stop.** Edit contracts under `.agents/runs/<slug>/`, re-run `plan-critique` until `ship` (or gate-ack). **Do not** start writers |

**MUST after every `plan-critique` / pre-dispatch validate:**

```bash
# Read decision (do not skip)
python3 -c "import json; d=json.load(open('.agents/runs/<slug>/artifacts/critique.json')); print(d['decision'], d.get('pm_action','')); print(d.get('summary')); [print(f['severity'], f['title'], f.get('detail','')[:120]) for f in d.get('findings') or []]"
```

- If `decision=revise_required`: apply findings (fix_plan / fix_spec / fix_task / split_task), re-run `plan-critique`, re-read decision. Loop ≤3 times then escalate to human with critique.md.
- If `decision=revise`: fix cheap wins, re-critique, or state residual risk in chat before dispatch.
- If `decision=ship`: continue.
- `run-validate --phase pre-dispatch` **auto-runs** plan-critique when the artifact is missing.
- `mode: advisory` warns; `mode: gate` blocks until `status: pass|ack` and not `revise_required`.

### PLAN.md

DAG table, goals, out-of-scope, verification plan (L1 vs L2), risk notes.

### SPEC.md (professional, not a stub)

Required when **score ≥ 7** or **≥ 2 tasks**. Must include, in English:

1. **Goal** — one paragraph  
2. **Interfaces** — stable exports/routes/types the writer must honor  
3. **Invariants** — what must not break  
4. **Out of scope** — explicit non-goals  
5. **Definition of done** — observable, testable  

Reject template-only text (“Record interfaces, invariants…”). `run-validate` enforces this.

### Task YAML

Immutable after first start. Required fields per **lane-contract**.  
`verification[]` = **L1 focused** only (see below).

Repeated correction rule: if you retype the same path/command fix twice in a project, persist it in CLAUDE.md / LESSONS.md first, then regenerate the plan.

---

## Phase 2 — Isolation (workspace from adoc)

This skill is **Claude Code `dev-orchestrator` only**. Codex / Grok / Kimi / Qwen / AGY
must **not** load it and must **not** `wt-create` / `git worktree add`.

Read `.agents/routing.profile.yaml` → `workspace.mode` (default **auto** if missing).
**`in_place` wins over score, risk, and multi-write.** Never override adoc In-place.

| `workspace.mode` | Action |
|------------------|--------|
| **in_place** | `project_cwd` = repo; **no** `wt-create`; PM **commits main** |
| **worktree** | always `wt-create` → `project_cwd` = `.worktrees/<slug>`; PM `wt-merge-main` |
| **auto** | worktree when `score ≥ worktree_min_score` (default 4) **or** (`worktree_on_multi_write` and ≥2 write tasks); else in-place |

Also: high-risk write → prefer worktree even under auto; avoid parallel writers on overlapping blast radius.

---

## Phase 3 — Dispatch (durable, bounded)

```text
run-controller start → one run-supervisor watches
provider slots (default 5) release ready DAG tasks
complete → owns → L1 verify → accept (progressive)
retry once; eligible 2nd failure → Codex Sol high fallback (not xhigh by default)
task blocked → siblings continue; dependents of blocked upstream cascade-blocked
```

**Never** one Claude subagent per writer. Writers = durable processes (kimi/…).  
**Never** PM `run-controller start|watch|status` — only `Agent(run-supervisor)`.  
**Never** PM nohup/async ad-hoc monitors.

| Lane | Who |
|------|-----|
| kimi / qwen / agy / grok / codex | process writer via controller (`adoc` `main_write`) |
| codex Sol fallback | one Sol **high** after two eligible writer availability failures |
| `emergency-writer` | manual emergency after terminal block |
| `night-reviewer` | nightly (sol **high**; xhigh only escalate) |

**Claude agent names are roles, not brands.** Daytime coder = process from adoc.
Roster: `agents/claude/README.md`.

---

## Verification tiers (L0 / L1 / L2)

| Tier | Owner | Scope | When |
|------|-------|-------|------|
| **L0** | Writer | Unit/spec under owns; optional package typecheck | During implement |
| **L1** | Controller | Task `verification[]` — **focused** paths/suites only | After report → accept |
| **L2** | PM pre-merge / CI | **One** full or affected suite for the whole run | After all accepted |

### L1 rules (PM when authoring YAML)

- Prefer: `npm run test:unit -- path/to/spec --silent`, single-package typecheck, path-scoped vitest/jest.  
- **Do not** put bare monorepo `npm run build` / root `npm test` on every task when the run has ≥2 tasks — that is L2.  
- Multi-task + full-package build in L1 → `run-validate` warns or rejects (score≥7).  
- Acceptance = **behavior**, not “entire monorepo green”.

### L1 paths under worktree (MUST — temples-admin class bugs)

`verification[].cwd` is almost always **`project_cwd`** (the worktree). Relative
script args resolve **there**, not in the main checkout.

| Wrong | Right |
|-------|--------|
| `cwd: worktree` + `python3 .agents/runs/X/artifacts/001/check.py` when check exists only on **main** | **Before** `run-controller start`: copy check into worktree at that relative path (recovery lane / PM shell allowed paths), **or** |
| Absolute path to main `.agents/...` | Forbidden (escapes worktree) |
| “Writer will create check.py under `.agents`” | Forbidden — writers must not author `.agents`; pre-author checks |

**Canonical patterns:**

1. **Product test under owns** (best): `tests/test_foo.py` +  
   `python3 -m unittest discover -s tests -p test_foo.py` with `cwd: project_cwd`.  
2. **Worktree-local pre-authored check**:  
   `worktree/.agents/runs/<slug>/artifacts/<id>/check.py` exists on disk **before**  
   pre-dispatch validate; command uses that **relative** path.  
   PM **may** `Write` only basename `check.py` under  
   `.agents/runs/<slug>/[artifacts/<id>/]check.py` (or under `.worktrees/...` same
   shape) — not `helper.py`, not `state.json` / reports.  
3. **in_place** (`adoc` Work → In-place): one tree — main `.agents/runs/...` paths work.

`run-validate --phase pre-dispatch` **rejects** missing script files under
verification cwd. Fix paths **before** first lane start (YAML is sha-pinned).

### L2

After all accepted: `run-validate --phase pre-merge`, then **one** build/test pass, then merge.

---

## Phase 4 — Accept (progressive)

When A verifies while B runs: **accept A now**. Done only with `acceptance.json`.  
No daytime LLM review; medium/high → nightly tier.

---

## Phase 5 — Stall & owns recovery

```bash
lane-stall-check "$(pwd)" --minutes 5
```

### Owns blocked — diagnose before “rewrite the task”

1. Read `artifacts/<id>/owns-check.json` (`violations`, `foreign_ignored`, `baseline_used`).  
2. If violations are **only** package caches (`.npm-cache`, `node_modules`, `.pnpm-store`, …) → gate bug/noise: **do not** add caches to `owns_paths`. Re-run owns/verify after stack ignore fix / clean cache.  
3. If violations are **product files** outside owns → contract bug: add missing companion to owns (replacement task) or revert OFF-SPEC.  
4. If upstream blocked only for noise → after fix, siblings/dependents can proceed (partial-block controller).  
5. **Never** recommend “add `.npm-cache` to owns_paths”.

---

## Phase 6 — Ship

All accepted → pre-merge validate → L2 once → `wt-merge-main` or commit main → push if remote.

---

## Phase 7 — Context budget

After ~6 tasks or heavy transcripts: handoff to PROGRESS; fresh orchestrator session if needed.

---

## Recovery ladder (typed only)

1. Same-provider retry (controller / `lane-ctl retry` via **lane-supervisor**)  
2. Codex Sol **high** fallback if `fallback_eligible`  
3. `lane-supervisor` one-shot (status / retry / accept / verify — **one** typed action)  
4. `emergency-writer` after **terminal** block only (ADR-codex-effort)  
5. Replacement task if YAML wrong after start  
6. Human only for business / irreversible  

Silence protocol: idle ≠ done — read `controller.json` / `events.jsonl`; re-dispatch one `run-supervisor` if `running`/`degraded`.

### Mode XOR — TEAM vs WRITE

| Mode | For | Not for |
|------|-----|---------|
| **TEAM** | Research/audit teammates | Same-goal product write via `run-supervisor` |
| **WRITE** | `run-supervisor` + durable writer | Same-goal research team spawn |

Close TEAM before WRITE (and vice versa) on one human goal. Announce «режим: TEAM|WRITE».

### Claude Agent / teams close — Claude Code 2.1.22x

| State | Meaning |
|-------|---------|
| **working** | Still running a turn |
| **done** | One-shot Agent finished with a final result |
| **idle** | Parked for resume — **normal after** `DONE`/`FAILED`/`WAIT`; not a failure |

| Mode | Rule |
|------|------|
| **Agent team teammate** | Each turn ends with `DONE <path>` / `FAILED <reason>` / `WAIT <why>` (TeammateIdle hook). Report under `.agents/team/…`. Idle = read last message + file. Next ask = `SendMessage`. No nag «you went idle» |
| **Stack one-shot** (`run-supervisor`, …) | One job → `DONE`/`FAILED` + evidence → end as **done**. Next action = new `Agent(...)`, not SendMessage-resume after DONE |

Also:

1. **Deploy / long jobs** — Bash + log (or `lane-bg`), not a teammate that only tails deploy.
2. **Disk is truth** for conveyor — `acceptance.json` / controller stage; idle chips are not stage.
3. **`TaskStop`** — hung **working** Agents or intentional abort; not the happy path after `DONE`.
4. **Lane product work** — only `run-supervisor` / `lane-supervisor` (teams ≠ writers).

### `SendMessage` / `ListAgents`

Claude Code ≥ **2.1.224** (Remote Control **start-by-name** in **2.1.225**).

| Where | What |
|-------|------|
| Lead ↔ teammate | Normal team dialogue (questions, clarifications, final ask) |
| `run-supervisor` → PM | Mid-run stage lines via **`SendMessage`** (tool name exact) |
| PM → operator Remote Control (optional) | On terminal `blocked`/`failed` or ship: `ListAgents` → `SendMessage` to `name [ref]` |
| Not for | Writer start/accept/verify, replacing `controller.json`, secrets in peer text, accusing idle teammates of failure |

Control plane stays file-based. Peer messages are short status + paths only.

### Forbidden bypasses (control-plane integrity)

While a run has `controller.json` stage in `running` / `degraded` / `dispatching`
**or** a live `run-controller` process:

| Forbidden for PM | Do instead |
|------------------|------------|
| Run task `verification[]` yourself in Bash and call it accept | Let controller L1 run; or `lane-supervisor` typed `verify`/`accept` |
| Hand-write `acceptance.json` / `report.md` / forge receipts | `lane-ctl accept` only after owns+verify evidence |
| `emergency-writer` to “just finish” a still-runnable lane | Only after terminal `blocked`/`failed` with no retry left |
| Parallel Claude coder subagents for the same task | One durable writer via controller |
| Restart controller mid-flight without reading `runtime.json` | Diagnose protocol/owns first; fix stack or retry typed |

**Done** for a task = `artifacts/<id>/acceptance.json` from the control plane — not
“tests green in chat”. Product may be correct and still not shipped until accept.

Protocol failures (`protocol_error` in `runtime.json`, e.g. report envelope): treat
as **provider protocol**, not “rewrite product”. Prefer retry after stack fix;
do not re-implement the feature as Claude.

---

## Hard rules (MUST)

1. No production Edit/Write — only `.agents/**`, `docs/plans/**`, PROGRESS/LESSONS, and dotenv (`.env`, `.env.*`) for secrets (keep keys out of writer prompts).  
2. No task MCP queue.  
3. Parallel = disjoint owns only.  
4. You merge main when green; workers never push/merge main.  
5. Provider pool ≤10; verification pool separate.  
6. Done = report + owns + L1 verify + `acceptance.json`.  
7. English for all run/docs files; Russian OK in chat with human.  
8. Progressive accept; partial block; L0/L1/L2.  
9. **Decompose** before dispatch; **SPEC** real when score≥7 or ≥2 tasks.  
10. Never Claude-subagent-per-writer; never PM nohup; never cache-in-owns.  
11. **Never bypass the controller** for L1 verify/accept while the run is live — see Recovery.  

