# Task YAML — where to write what

Read this **before** filling `tasks/*.yaml`. Template: `templates/run-contract/task-v2.yaml`.
Gate: `run-validate --phase pre-dispatch`.

YAML is a machine contract, not a briefing. `objective` is the TZ. Do not dump the TZ into `interfaces`.

## Files in the run

| File | What goes there |
|------|-----------------|
| `PLAN.md` | DAG, who owns what, L1 vs L2. Not the per-task TZ. |
| `SPEC.md` | Run-level Goal / Interfaces / Invariants / Out of scope / Done (English). Score ≥7 or ≥2 tasks. |
| `tasks/<id>.yaml` | One product outcome. Writer prompt = this YAML verbatim + packet. |

Do not copy writer-agent rules (`edit` vs `write`, `wc -l`, `git checkout`) into the task.

## Field map

| Field | Write | Do not write |
|-------|-------|----------------|
| `title` | One-line outcome | Process / “continue the attempt” |
| `objective` | The TZ: behavior + smallest change | Tool HOWTO, continuation, Gaps dump |
| `acceptance` | Observable checks the report can cite | “typecheck green” as the only criterion |
| `owns_paths` | Every path this outcome must edit | Caches, `.agents`, DESIGN.md unless tokens |
| `never_touch` | Secrets / unrelated | Duplicate of `out_of_scope` essays |
| `read_first` | Existing project-relative **files** | `section C4`, `lines 10-20 ONLY`, grep notes |
| `context_selectors` | `{path, start_line, end_line}` windows | omit if you need the whole file |
| `interfaces` | Signatures / type names, or `[]` | CONTINUATION, Gaps, module novels |
| `invariants` | Product constraints, or `[]` | HARD RULE / edit tool / `wc -l` / checkout |
| `out_of_scope` | Non-goals not already in `never_touch`, or `[]` | Writer recovery |
| `expected_outputs` | Artifact path this task creates | Restate `verification[]` |
| `verification` | Focused L1 commands, absolute `cwd` | Full-package `npm test` on multi-task |
| `verify` | `tests` / `smoke` / `none` matching L1 | A second suite (L1 reads `verification[]` only) |
| `depends_on` | Real compile/data ids | Chat-order |
| `lane` | adoc `main_write` | Hardcoded `kimi` |
| `impact_receipt` / `skills` | omit unless the file/skill is real | Invent |

## Good

```yaml
read_first:
  - apps/foo/src/persist-executor.ts
  - apps/foo/src/__tests__/persist-executor.test.ts
context_selectors:
  - path: apps/foo/src/persist-executor.ts
    start_line: 28
    end_line: 165
interfaces:
  - "buildGatesSummary({ statusFile, flags, workDir }): { summary, reasons }"
invariants:
  - "PUT never sends status published"
out_of_scope:
  - "admin badge UI"
expected_outputs:
  - apps/foo/src/persist/gates-summary.ts
objective: |
  When auto_publish is true and every gate on disk passed, POST the landing
  as published; otherwise keep draft and write reasons next to the receipt.
acceptance:
  - "all-pass fixture POSTs status published plus gates"
  - "fail fixture stays draft and writes gates-summary.json reasons"
```

## Bad (pre-dispatch rejects)

```yaml
read_first:
  - "explore-report.md section C4 (the map)"
  - "persist-executor.ts lines 28-165 ONLY"
interfaces:
  - "CONTINUATION: git status --short then finish Gaps from last attempt"
invariants:
  - "HARD RULE: edit tool only; wc -l; git checkout -- file and redo"
```

`run-validate` rejects those. Writer already has edit/write/checkout rules; repeating them in YAML caused the restore loop.
