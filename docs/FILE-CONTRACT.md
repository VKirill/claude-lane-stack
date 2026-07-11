# File-based agent contracts (no orchestrator MCP)

Replace Postgres/task MCP with **files in the project**. Agents never call task/orchestrator MCP — they only `Read` paths.

**Language:** all contract files (**PLAN, SPEC, STATUS, task YAML, report.md, review.md, MERGE.md**) are **English only**. Chat with the human may be Russian. See [LANGUAGE.md](LANGUAGE.md).

**Solo operator mode (default):** one human, one orchestrator. Workers may use worktrees; **only the orchestrator merges to `main`**. The human never merges.

## Docs vs runs (do not confuse)

| Path | Use |
|------|-----|
| `.agents/runs/<slug>/` | **Execution** for the orchestrator: PLAN, task YAML, reports, MERGE |
| `.agents/todos/` | Ideas / backlog until promoted |
| `docs/plans/<topic>/` | Durable **strategy / SEO / product** docs (e.g. `COCOON.md`) for humans + long-form research |
| `docs/` | Architecture, decisions, wiki |

A COCOON or product strategy **correctly** lives under `docs/plans/`.  
When the user says implement → **promote** into `.agents/runs/<slug>/` with `owns_paths` tasks. Do not treat `docs/plans` alone as a coding run.

## Layout (per feature run)

```text
.agents/runs/
  BOARD.md                # live board (all runs) — regenerate via run-board
  <slug>/
    PLAN.md               # brief + score + routing
    SPEC.md               # optional full path
    STATUS.md             # this run board
    MERGE.md              # set by PM after auto-merge to main
    worktree.json         # { branch, path, base } if isolated
    tasks/
      001-short-title.yaml
    artifacts/
      001/
        report.md
        review.md         # codex when required
        verified.txt
        heartbeat.json    # last touch from lane
        lane-bg.pid       # detached supervisor (lane-bg)
        lane-bg.exit      # set when lane finishes
        lane-bg.supervisor.log
        lane-exec.log     # activity-aware wrapper
```

Long CLI lanes **must** start with `lane-bg` and poll via `lane-wait --once` — Claude kills foreground Bash ~2 minutes. See [LANE-EXEC.md](LANE-EXEC.md).

`<slug>` = kebab-case feature, e.g. `fix-subscription-panel-flicker`.

## Task YAML

```yaml
id: "001"
title: "Gate loading on initial load only"
risk: low                    # low | medium | high
lane: agy-frontend           # agy-coder | agy-frontend | grok | codex-review
status: pending              # pending | running | review | done | blocked | stalled
project_cwd: "/absolute/path/to/repo-or-worktree"
# Ownership — required for write lanes
owns_paths:
  - apps/cabinet/src/components/SubscriptionPanel.vue
  - apps/cabinet/src/components/subscription-panel.test.ts
never_touch:
  - apps/cabinet/src/server/**
  - prisma/**
  - .env*
files:                       # alias / union with owns_paths (legacy)
  - apps/cabinet/.../SubscriptionPanel.vue
objective: |
  One paragraph: what and why.
interfaces: |
  Signatures / snippets (paste code, not only paths).
constraints: |
  - Do not touch X
  - Reuse Y
  - Karpathy: surgical, minimum code
verification:                # commands that must appear with exit 0 evidence
  - "npm -w apps/cabinet run test -- subscription-panel"
done_when:                   # hard done gate (same as verification or stricter)
  - "npm -w apps/cabinet run test -- subscription-panel"
acceptance:
  - "Loading text only when pending and no data"
depends_on: []
heartbeat_sec: 120           # stall if no heartbeat longer than this (default 300)
high_risk_paths: false       # true → dual review (codex required even if risk medium)
```

### Ownership rules

1. Write lane may only edit paths under `owns_paths` (or `files` if `owns_paths` omitted).  
2. `never_touch` always wins — even if listed in owns.  
3. Parallel tasks **must** have disjoint `owns_paths` (no path prefix overlap).  
4. After lane finishes, PM runs `check-owns-paths` — edits outside owns → task **blocked**, not done.  
5. Build errors in files **not** in owns_paths → ignore / wait; do not “helpfully” fix.

## Lifecycle (orchestrator — solo)

1. Create run dir + PLAN + tasks with **disjoint** `owns_paths`.  
2. If score ≥ 4 **or** ≥2 write tasks → `wt-create` worktree; all tasks share that `project_cwd`.  
3. If single low-risk task → may use main working tree (still PM commits).  
4. Dispatch ≤3 parallel write lanes only when owns_paths disjoint.  
5. Lanes heartbeat via `lane-heartbeat`; PM may run `lane-stall-check`.  
6. Accept strong `report.md` + `check-owns-paths` clean + `done_when` evidence.  
7. `risk: high` or `high_risk_paths` or ship → Codex `review.md` must pass.  
8. When **all** tasks done → PM **auto-merges to main** (`wt-merge-main` or commit on main) → write `MERGE.md` → update `BOARD.md` + `PROGRESS.md`.  
9. Human is never asked to merge.

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
