# Task decomposition

Bad multi-task runs almost always start here, so apply this before filling task YAML: in the terminal harness before `run-init`, in Lane Pilot before building the `plan` of `lane_pilot_dispatch_writer`.

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
