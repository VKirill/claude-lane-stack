---
name: lane-contract
description: File-based task contracts under .agents/runs/ with owns_paths, verification tiers L0/L1/L2, and solo merge rules. Use when authoring or reviewing task YAML, owns_paths, acceptance, or verification commands.
---

# Lane contract (files only)

Canonical: `FILE-CONTRACT.md`, `SOLO-ORCHESTRATION.md`,
`docs/decisions/ADR-codex-effort.md`, skill **orchestrator-lanes** (decomposition).

---

## Orchestrator must

1. `run-init` → fill PLAN/SPEC/tasks → `run-validate --phase pre-dispatch` before dispatch.  
2. Set **`owns_paths`**, **`never_touch`**, behavioral **`acceptance`**.  
3. Paste real interfaces into `interfaces`; declare `read_first`, `invariants`, `out_of_scope`, `expected_outputs`.  
4. One `run-supervisor` per run; `lane-supervisor` only for typed one-shots.  
5. Parallel only with **disjoint** owns_paths.  
6. Controller: owns → L1 verify → accept **progressively**.  
7. Task YAML immutable after first start.  
8. Pre-merge validate → merge main (PM only).  
9. Writers via durable controller (kimi/…); Codex write = recovery only.  
10. Separate provider vs verification pools.  
11. **Decompose** per orchestrator-lanes (one outcome per task; unlock ≠ feature).  
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
- [ ] Timeouts realistic (unit 60–300s; avoid 1800s full suites per task)  
- [ ] **Every script path in `verification[].command` exists on disk under `verification[].cwd` before pre-dispatch**  
- [ ] If `project_cwd` is a **worktree**: do **not** assume main-repo `.agents/runs/...` is visible — copy pre-authored `check.py` into the worktree path **or** put tests under product `tests/` in owns; absolute paths to main are rejected  
- [ ] Prefer product tests (`tests/test_*.py`) over `.agents/**/check.py` when possible  

### Acceptance

- [ ] Observable behavior, not “all packages green”  
- [ ] Matches objective; greps/sweeps named when deletion tasks  

---

## Lane must (writer)

1. Read TASK_FILE completely.  
2. Work only in `PROJECT_CWD`.  
3. Edit **only** `owns_paths`. Honor `never_touch`.  
4. Do not write `.agents`.  
5. **L0 focused** checks only; report in English.  
6. No git merge/push main.  
7. Outside-owns build break → report Gaps, do not “fix the world”.  
8. No monorepo full suite as Worker checks on multi-task runs.  

---

## Required schema-v2 task fields

`schema_version`, `id`, `title`, `risk`, `lane`, `project_cwd`, `read_first`,
`interfaces`, `invariants`, `out_of_scope`, `expected_outputs`, `owns_paths`,
`never_touch`, `depends_on`, `objective`, `acceptance`, `verify`, structured
`verification` (`command`, absolute `cwd`, `timeout_sec`).

No mutable `status` / free-form verify strings on new runs.

---

## Verification tiers

| Tier | Who | What |
|------|-----|------|
| **L0** | Writer | Focused tests while coding |
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
