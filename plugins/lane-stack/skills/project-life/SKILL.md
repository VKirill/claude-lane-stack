---
name: project-life
description: "Единый скилл ведения задач и жизни проекта: идеи/туду → планы/roadmap → раны → артефакты → прогресс/уроки. Use when user says туду, запиши, идея, backlog, потом, план, спланируй, планируем, пока план, не запускай, обсудим, roadmap, этапы, приоритеты, прогресс, урок, итоги — or todo, plan, planning, lesson, progress. Cold-start «где мы / handoff / продолж» is resume-project, not this skill. `$ARGUMENTS` exactly info prints the card."
argument-hint: "[info]"
---

# Project life — one skill for tasks & project memory

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / tools `lane_pilot_*` present) the PM does not write PROGRESS, ROADMAP or plan ticks after a run: Lane Pilot's project-life helper does it (PROGRESS ≤40 lines, one CHANGELOG line, commit `chore(progress)`). The PM keeps `.agents/todos/`, `.agents/plans/` and decision drafts. «делай» = `lane_pilot_dispatch_writer` (the whole plan at once, order through `depends_on`; no waves). A lesson = `lane_pilot_lesson` (rule, audience pm, writer or both — required; `always` only for a rule true of every writer task). Project facts that cannot be derived live in the hub memory (`lane_pilot_memory_context`, `lane-memory search|context`). `run-init`, `run-finalize`, `memory-scribe`, `resume-project` CLI and `~/.agents/bin/*` below are the terminal harness.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop. Do not create a todo or plan unless the user already asked for that in the same message.

Everything lives in files under `.agents/` (project) or `~/.agents/` (global).
**Durable files: English only.** Chat may be Russian — answer in RU, write EN
to disk. Never put secrets in any of these files.
**No orchestrator MCP.** No `todo_add` / task CLI for ideas.

## The lifecycle (one mental model)

```text
idea ──► todo ──► plan ──► run ──► merged work
        (backlog) (map)   (execution)   │
                                        ▼
              memory: PROGRESS · lessons→hub · decisions · session-log · artifacts
```

Skipping layers **upward** is fine (small fix: idea → run). Skipping the
memory update after work is not.

## Folder map

```text
<project>/.agents/
  todos/            # ideas backlog        → references/todos.md
    INDEX.md
    items/<YYYY-MM-DD-slug>/{README.md, AGENT.md, meta.yaml}
  plans/            # delivery map         → references/plans.md
    ROADMAP.md
    items/<YYYY-MM-DD-slug>/{PLAN.md, meta.yaml, artifacts/}
  runs/             # execution contracts  (skill lane-contract)
    <slug>/artifacts/<task>/...
  PROGRESS.md       # now / blocked / next → references/memory.md
  agent-notes/OPEN.md
  session-log/      # hooks own it — read only
  decisions/        # decision drafts; the docs pass publishes them to docs/decisions.md
<project>/.agents/plans/       # long-form strategy (NOT this layer)
<project>/docs/                # code documentation only, kept by the docs pass
```

Choose project root when cwd has `.git`/`package.json`/`CLAUDE.md`; use
`~/.agents/...` when user says «глобально» or cwd is home.

## When to apply what

| User says (≈) | Do | Reference |
|---------------|----|-----------|
| «занеси в туду / запиши / потом / не теряй» | Create/update todo item + INDEX | `references/todos.md` |
| chat about a todo, no «запиши» | Do not invent a todo; ask if they want it filed | — |
| «покажи туду / что в бэклоге» | Read INDEX + open items, answer in RU | — |
| «закрой / сделано / не надо» | status done/dropped + INDEX | `references/todos.md` |
| «планируем / пока план / не запускай / обсудим / спланируй / разбей на этапы» | **Planning session** — draft in `.agents/plans/`, no run | `references/plans.md` |
| «архитектор / новое приложение / новый сервис / спроектируем продукт» | Load **app-architect**. Same plan folder, living `artifacts/`. No run | skill `app-architect` |
| «что дальше по проекту» (already in session) | PROGRESS → ROADMAP → todos INDEX counts | — |
| «делай / реализуй / в работу / запускай ран» | Exit planning. Lane Pilot: `lane_pilot_dispatch_writer`. Terminal: spawn a run (`lane-contract`). Link it from the plan | — |
| run закончился зелёным | Terminal: tick plan task → refresh ROADMAP → rewrite PROGRESS. Lane Pilot: its helper does this | `references/memory.md` |
| поправили тебя / наступил на грабли | One lesson. Lane Pilot: `lane_pilot_lesson` with audience. Terminal: `lane-memory lesson "<rule>" --for pm\|writer\|both` (hub, not a file) | `references/memory.md` |
| зафиксировано крупное необратимое решение | draft in .agents/decisions/<date>-<slug>.md (the docs pass publishes it to docs/decisions.md) | `references/memory.md` |
| «итоги / конец сессии» | PROGRESS current, ideas filed as todos, no orphan runs | `references/memory.md` |
| «что делали / почему так / покажи отчёт» | Read session-log INDEX, run artifacts, findings — don't write them | — |
| «где мы / handoff / продолж» (cold start) | Skill `resume-project` (terminal: `~/.agents/bin/resume-project .`), not this file | — |

## Planning session

Stay here until the user says «делай / реализуй / в работу / запускай ран».

Triggers: «планируем», «пока план», «не запускай», «обсудим», «спланируй»,
«разбей на этапы», «только карта», «пока не в ран».

1. Create or open `.agents/plans/items/<YYYY-MM-DD-slug>/` (`status: draft`).
2. Each decision → edit `PLAN.md` + dated **History**. Chat is not the store.
3. Screenshots / notes → optional `items/<slug>/artifacts/`; link from PLAN **Links**.
4. Ask the next scoped question. Do not invent a run or score a conveyor.

Forbidden until «делай»:
- `run-init`, `run-controller`, `run-supervisor`, writers
- Claude Code **Plan mode** and any write under `~/.claude/plans/`
- owns_paths / task YAML in this `PLAN.md`

If the host is already in Claude Plan mode: tell the user to switch to
**default** and keep writing under `.agents/plans/`. Do not copy the
harness file as the canon (you may quote it once into `PLAN.md`).

UI / visual initiative: Links must include `docs/DESIGN.md`. If it is
missing, spawn **design-lead** (skill `project-design`) or draft DESIGN.md
here — do not `run-init` a UI lane without it.

Exit: «делай» → Lane Pilot: `lane_pilot_dispatch_writer`; terminal: `lane-contract` / orchestrator-lanes Phase 0. Set plan
`status: active`, link the run in the task table + `meta.yaml.runs`.

## Decision guide (where does X go?)

| X | Goes to |
|---|---------|
| "we should someday…" | **todo** |
| "we will, in this order…" | **`.agents/plans/`** (delivery map) |
| long-form strategy / COCOON | **`.agents/plans/`** (not a coding queue) |
| "change code now" | **run** (never directly from todo/plan). Run has its own `PLAN.md` — execution DAG, not the map |
| "current state of reality" | **PROGRESS** (≤40 lines, rewrite not append) |
| "we got burned by…" | **lesson** → `lane_pilot_lesson` (Lane Pilot) / `lane-memory lesson` (terminal) |
| "we chose A over B forever" | **draft in `.agents/decisions/`** → published to `docs/decisions.md` |
| leftover debt / simplify later | **`.agents/agent-notes/OPEN.md`** |
| planning-session notes / screenshots | **`.agents/plans/items/<slug>/artifacts/`** (until a run exists) |
| reports, screenshots, receipts after a run | **run artifacts** (immutable, stay in the run) |
| "why is this code here" | session-log / findings (read only) |

## Linking discipline (what makes it ONE system)

Every hop leaves a back-link so any file leads to the full trail:

- todo `meta.yaml.related_runs` ↔ plan `meta.yaml.source_todos`
- plan task row `run:` link ↔ run notes its plan id
- artifacts stay under `.agents/runs/<slug>/artifacts/` — link load-bearing
  ones from PLAN.md **Links** and PROGRESS, never copy them around
- Lessons and ADRs name their evidence (run, test, artifact)

## Rituals

**Session start:** read `.agents/PROGRESS.md` (project rules reach you through CORE and the brief) →
ROADMAP + todos INDEX **counts only**. Don't dump session-log into context.
Cold start / unknown repo: skill `resume-project` (terminal CLI: `~/.agents/bin/resume-project .`), then this skill
for writes. Lane writers under a task contract do **not** write `.agents/`
(the PM does) — this skill's write rules are for the PM / interactive agent.

**After a green run (terminal; in Lane Pilot its helper does this):** tick plan task → refresh ROADMAP → rewrite PROGRESS
(Now/Blocked/Next/Last verify) → a lesson only if corrected → ADR only if a
durable fork was locked. After a **wave** of tasks, refresh PROGRESS once,
not per micro-edit. Schema-v2: declare `progress_now` / `close_next` /
`close_open` in run.yaml; `run-finalize` applies them — never guess stale
checklist lines.

**Session end:** PROGRESS current; new ideas from chat filed as todos;
session-log untouched (hooks own it).

**Delegate the bookkeeping (Claude):** when a ritual touches more than one
file (PROGRESS + plan row + ROADMAP/INDEX, or filing todos), dispatch the
`memory-scribe` subagent (Haiku) with 3–5 bullets of what happened — it
formats and files per `references/`. Write **lessons and ADRs yourself** (judgment
calls). Single quick append — just do it. Other CLIs: write directly.

**Init a repo:** `~/.agents/bin/project-memory-init <repo>`; full passport:
`/project-onboard`. If only root `PROGRESS.md` / `LESSONS.md` exist, init
and session-ledger migrate them into `.agents/`.

**Night audit:** `~/.agents/bin/night-audit .` or read `AUDIT-*.md`. Close
OPEN items or spawn todos/runs.

## Writing formats

Exact file templates live in this skill's `references/` (`todos.md`,
`plans.md`, `memory.md`). Stable paths: `~/.agents/skills/project-life/references/`
(any CLI agent) or `~/.claude/plugins/marketplaces/claude-lane-stack/skills/project-life/references/`
(Claude plugin). Read the matching file **before creating or restructuring**
any of these; skip it for trivial appends you already know the shape of.

## Ambiguity protocol

A vague ask («сделай красиво», unclear scope, two plausible readings) is
**not** a license to guess. Order of preference:

1. Look it up yourself — code, PROGRESS, plans, todos, session-log.
2. Still ambiguous → ask the user a **structured question with 2–4 options**
   (Claude: AskUserQuestion), not an open-ended one.
3. Never silently pick an interpretation for destructive or scope-changing
   work. For trivial reversible work: pick the obvious reading, say so.

## Keeping the layers right

- Everything that matters is a file: todos, plans and results never live only in chat.
- The project plan is `.agents/plans/`, not Claude Plan mode or `~/.claude/plans/`; it is a delivery map, not a run queue, so it holds no task YAML or owns_paths (that is `lane-contract`) and no run starts during a planning session.
- One layer per file: todo, plan and PROGRESS stay separate. PROGRESS is rewritten, not appended to; plans and todos link the runs that shipped them.
- `docs/` holds only the code documentation; plans, research and reports go to `.agents/`.
- Production code changes go through a run (a writer dispatch), never straight from a todo or plan; ideas are files, not an orchestrator MCP `todo_add`.
- Durable files are English and contain no secrets.
