---
name: lane-contract
description: File-based task contracts under .agents/runs/ with owns_paths, verification tiers L0/L1/L2, and solo merge rules. Use when authoring or reviewing task YAML / the task-v2 contract (Lane Pilot `plan`), owns_paths, acceptance, or verification commands; `$ARGUMENTS` exactly info prints the card.
argument-hint: "[info]"
---

# Lane contract (files only)

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / tools `lane_pilot_*` present) the contract is the task-v2 JSON in the `plan` of `lane_pilot_dispatch_writer`, and its schema is strict: exactly `schema_version`, `id`, `title`, `risk`, `lane`, `project_cwd`, `read_first`, `interfaces`, `invariants`, `out_of_scope`, `expected_outputs`, `owns_paths`, `never_touch`, `depends_on`, `objective`, `acceptance`, `verify`, `verification[{command, cwd, timeout_sec?}]` (`timeout_sec` up to 7200). Any other field (`context_selectors`, `impact_*`, `skills`) makes Lane Pilot reject the whole contract: put line windows in `objective` or `interfaces` as `path:start-end`. The writer RUNS `verification` and Lane Pilot re-runs it at acceptance, so every task needs real verification commands. Lane Pilot owns run state; `run-init`, `run-validate --phase`, `lane-ctl`, `run-supervisor`, the L0 rule «writer does not run tests» and `lane = adoc main_write` below are the terminal Lane Stack harness.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop. Do not write task YAML.

Canonical: `FILE-CONTRACT.md`, `SOLO-ORCHESTRATION.md`,
`docs/decisions/ADR-codex-effort.md`, skill **orchestrator-lanes** (`references/decomposition.md`).

---

## Orchestrator must

1. `run-init` → fill PLAN/SPEC/tasks → `run-validate --phase pre-dispatch` before dispatch.  
2. Set **`owns_paths`**, **`never_touch`**, behavioral **`acceptance`**.  
3. **`read_first`**: existing project-relative files only. Line windows go in **`context_selectors`**. **`interfaces`**: signatures/types, or `[]`. Product **`invariants`** / **`out_of_scope`**; never writer recovery. **`expected_outputs`**: artifact path, not “tests green”.  
4. One `run-supervisor` per run; `lane-supervisor` only for typed one-shots.  
5. Parallel only with **disjoint** owns_paths.  
6. Controller: owns → L1 verify → accept **progressively**.  
7. Task YAML immutable after first start.  
8. Pre-merge validate → merge main (PM only).  
9. Writers via durable controller (kimi/…); Codex write = recovery only.  
10. Separate provider vs verification pools.  
11. **Decompose** per orchestrator-lanes `references/decomposition.md` (one outcome per task; unlock ≠ feature).  
12. **SPEC.md** is real content when score ≥ 7 or ≥ 2 tasks (not the template stub).  

---

## Authoring checklist (before pre-dispatch)

### Decomposition

- [ ] Each task id has **one** product outcome  
- [ ] `depends_on` is a real compile/data edge, not narrative order  
- [ ] Large delete vs new algorithm are **separate** tasks  
- [ ] Parallel tasks have disjoint owns  

### Owns completeness

- [ ] Every path the objective **requires** editing is listed (including companion modules the prompt forces — e.g. quality gates that still reference a removed field)  
- [ ] Package caches, `node_modules`, `.npm-cache`, build caches are **never** in owns  
- [ ] `never_touch` covers secrets, prisma (if frozen), unrelated products  

### Verification (L1)

- [ ] Commands are path-scoped unit/typecheck for **this** task  
- [ ] No bare monorepo `npm run build` / root `npm test` on multi-task runs (that is L2)  
- [ ] **`timeout_sec` — omit.** Runtime defaults to 900s. Do not invent or bike-shed timeouts in plans  
- [ ] **Every script path in `verification[].command` exists on disk under `verification[].cwd` before pre-dispatch**  
- [ ] If `project_cwd` is a **worktree**: do **not** assume main-repo `.agents/runs/...` is visible — write/copy `check.py` into the worktree path **or** put tests under product `tests/` in owns; absolute paths to main are rejected  
- [ ] Prefer product tests (`tests/test_*.py`) over `.agents/**/check.py` when possible  
- [ ] PM **may** Write only basename `check.py` under `.agents/runs/<slug>/[artifacts/<id>/]` (guard allowlist); not other `.py`, not `state.json`/reports  


### Acceptance

- [ ] Observable behavior, not “all packages green”  
- [ ] Matches objective; greps/sweeps named when deletion tasks  

---

## Lane must (writer)

1. Read the complete raw task YAML supplied in the prompt; open TASK_FILE if absent or uncertain.
2. Work only in `PROJECT_CWD`.  
3. Edit **only** `owns_paths`. Honor `never_touch`.  
4. Do not write `.agents`.  
5. Do **not** run tests/typecheck/`verification[]`; L1 is `lane-ctl verify`. Report in English.  
6. No git merge/push main.  
7. Outside-owns build break → report Gaps, do not “fix the world”.  
8. Do not run monorepo suites or Worker checks.  

---

## Required schema-v2 task fields

Identity (must match adoc / run): `schema_version`, `id`, `title`, `risk`, `lane`, `project_cwd`.

| Field | What the machine uses | Fill | Leave empty / omit |
|-------|----------------------|------|-------------------|
| `objective` | Writer TZ (prompt) | One product outcome, behavior | never |
| `acceptance` | Report + PM | Observable behavior | never |
| `owns_paths` | Owns gate | Every path the outcome must edit | never |
| `never_touch` | Owns gate | Secrets / unrelated | `.env*` minimum |
| `read_first` | Packet files | Existing files, no notes | `[]` if none |
| `context_selectors` (terminal only) | Packet line windows | `{path, start_line, end_line}` | omit (do not put windows in `read_first`) |
| `verification` | L1 `lane-ctl verify` | Focused commands | `[]` only with `verify: none` |
| `verify` | Schema only | `tests` / `smoke` / `none` matching L1 | do not invent a second suite |
| `depends_on` | DAG | Real compile/data ids | `[]` |
| `interfaces` | Prompt + path scrape | Signatures / type names | `[]` |
| `invariants` | Prompt | Product constraints | `[]` |
| `out_of_scope` | Prompt | Non-goals not already in `never_touch` | `[]` |
| `expected_outputs` | Schema + prompt | Artifact path this task creates | one path, not “typecheck green” |
| `impact_receipt` / `impact_targets` (terminal only) | Packet | Only if you captured a receipt | omit |
| `skills` (terminal only) | Claude prompt inject | `impeccable-ui` on UI tasks | omit (OpenCode ignores) |

`run-validate --phase pre-dispatch` rejects: `git checkout`/`restore` in the YAML; `read_first` prose (`section C4`, `lines 10-20`); missing `read_first` files; CONTINUATION / Gaps / HARD RULE / `wc -l` / edit-tool recovery in `interfaces` or `invariants`.

No mutable `status` / free-form verify strings on new runs.

### Prepared execution context

`lane-ctl` supplies hashes and path pointers from `read_first` and `context_selectors`.
Paths named in `interfaces`/`objective` (`file.ts:12-40`) become `interface_refs`.
Keep related tests in `read_first` as **paths**.
The original task remains immutable. OpenCode already loads `lane-writer`; the
user prompt is YAML + packet, not a second copy of the writer contract.

Writers reuse unchanged supplied code. Omit `impact_receipt` unless the file exists
on disk.

---

## Verification tiers

| Tier | Who | What |
|------|-----|------|
| **L0** | Writer | Code + test files; do not execute runners |
| **L1** | `lane-ctl verify` | Task `verification[]` only |
| **L2** | PM / CI | One full or affected suite per run |

### Worktree + pre-authored checkers

`verification.cwd` must equal the task worktree/`project_cwd`. Relative scripts
resolve **inside that tree**. Main checkout `.agents/runs/<slug>/artifacts/001/check.py`
is **not** the same file as  
`worktree/.agents/runs/<slug>/artifacts/001/check.py`.

Before `run-validate --phase pre-dispatch` / controller start:

1. Pre-author the checker (recovery/PM — not the writer).  
2. Place it **under the worktree** at the path the command uses.  
3. Or use **in_place** workspace so one `.agents` tree is enough.

`run-validate` fails closed if the script file is missing.

### `verify` levels

| Level | Meaning |
|-------|---------|
| none | Trivial / visual |
| smoke | Single cheap command |
| tests | Focused automated tests (not monorepo green) |

---

## Owns / dirt / caches

| Class | Policy |
|-------|--------|
| Pre-existing dirt outside owns | Foreign ignored (baseline / no-baseline policy) |
| New product files outside owns | **Fail** (writer leak or missing owns entry) |
| `.npm-cache`, `node_modules`, pnpm/yarn/turbo caches | **Ignored** by gate — never put in owns |
| `never_touch` hits (new) | **Fail** |

If owns fails with only cache paths: treat as control-plane noise, not “expand owns”.

---

## SPEC.md contract (run level)

When required (score ≥ 7 or ≥ 2 tasks), SPEC must state goal, interfaces,
invariants, out of scope, definition of done — in English, not the run-init stub.
`run-validate --phase pre-dispatch` rejects stubs.
