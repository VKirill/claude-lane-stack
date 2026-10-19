---
title: Project memory pack
type: component
created: 2026-07-11
updated: 2026-10-19
status: active
confidence: high
tags: [memory, project-state, retrieval]
sources:
  - bin/lane_memory.py
  - bin/lane_memory_hub.py
  - bin/project-memory-init
  - bin/resume-project
  - bin/pipeline_stages.py
  - hooks/session_ledger.py
  - bin/jev_slots.py
---
# Project memory pack

TL;DR: Project memory combines human-readable project state, session evidence, and structured facts; when the BB hub resolves the project, shared facts use hub RPC, while unavailable/offline hub paths use local Markdown and a derived lexical index (`bin/lane_memory.py:403-417`, `bin/lane_memory.py:634-680`).

## Purpose

Describe project state and structured memory inputs, retrieval, and cleanup paths (`bin/lane_memory.py:345-394`, `bin/lane_memory_hub.py:100-165`).

Project state, session evidence, and structured memory each have separate write and retrieval paths.

| File | Purpose | Who writes |
|------|---------|------------|
| `AGENTS.md` / `CLAUDE.md` | Hard rules + non-obvious gotchas | Human + onboard / rare agent edits |
| `.agents/PROGRESS.md` | Now / blocked / next / last verify | Agents after work; human anytime |
| `.agents/LESSONS.md` | Mistakes → do/don't | Agents after corrections |
| `docs/decisions.md` | ADR-light durable choices | Human or agent on big forks |
| `.agents/onboard.scenario.yaml` | minimal\|full + fast\|deep + score | `project-onboard` |
| `.agents/routing.profile.yaml` | which CLIs / lanes | `agents-doctor --apply` |
| `.agents/session-log/` | Auto handoff evidence (files/shell/git) | Hooks |
| `.agents/agent-notes/OPEN.md` | Open debt from code TODOs | Hooks + agents |
| `.agents/findings/` | Canonical typed review findings, including prior-programmer context | `night-review` |
| `.agents/night-review/checkpoint.json` | Last completely reviewed source boundary | `night-review` |
| `.agents/runs/<slug>/night-fix-state.json` | Resumable dispatch/verify/re-review state | `night-fix-runner` |
| `.agents/runs/<slug>/artifacts/<task>/review.json` | Identity-bound Codex re-review receipt | `night-review-engine` |
| `.agents/runs/<slug>/artifacts/<task>/attempts/<n>/runtime.json` | Sanitized Grok protocol/runtime receipt | `lane-session` |
| `.agents/runs/<slug>/artifacts/<task>/outcome.json` | CLI-agnostic result manifest (exit_status, failure_class, files_changed) for supervisors | `run-controller` |
| `.agents/night-fix-current.json` | Pointer to current/last repair state | `night-fix-runner` |
| `.agents/todos/` | Ideas backlog | Humans + PM agents |
| `.agents/qa/<slug>/` | Browser QA cases / REPORT / replay | `browser-qa` |
| `.agents/qa/context.md` | Non-secret browser setup | `browser-qa` |
| `.agents/runs/` | Immutable task specs + machine receipts + reports | Orchestrator + lanes |
| `.agents/runs/BOARD.md` | Generated multi-run board | `run-board` |
| `docs/` wiki (if any) | Architecture truth | Humans + wiki pipeline / docs-maintain |

**Solo:** orchestrator auto-merges worktrees to `main` (`wt-merge-main`). See `SOLO-ORCHESTRATION.md`.  
`run-finalize` applies declared PROGRESS/BOARD/OPEN updates after merge and
records them in `finalize.json`; it never guesses which checklist lines are stale.
**Language:** all of the above agent-written files are **English** (`LANGUAGE.md`).

## Init a repo

```bash
export PATH="$HOME/.agents/bin:$PATH"
project-memory-init /path/to/repo
: 'full passport (preferred first time):'
project-onboard /path/to/repo          # or /project-onboard in Claude
: 'force forensic:'
project-onboard /path/to/repo --deep
```

## Skills

- `lane-memory` — opt-in SMA fact corpus (`.agents/memory/`, adoc `stages.memory`)
- `project-life` — todos, delivery plans, PROGRESS/LESSONS/ADR after a task/session
- `project-onboard` — dual scenario + depth passport
- `resume-project` — cold start (`resume-project .`)
- `lane-contract` / `orchestrator-lanes` — runs + solo merge + lane-bg

## Cold start / night audit

```bash
~/.agents/bin/resume-project /path/to/repo
~/.agents/bin/night-audit /path/to/repo
: '.agents/session-log/AUDIT-YYYY-MM-DD.md'
~/.agents/bin/night-shift /path/to/repo
: 'typed findings + optional isolated Grok repair run'
```

Review observations must not remain only in a transcript. A concrete or
systemic defect is stored once under `.agents/findings/` and linked from its
daily report, OPEN projection, TODO, generated fix task, and closure receipt.
This makes the next reviewer start from prior evidence instead of rediscovering
the same failure.

## Community names

session ledger · agent handoff log · coding journal · ADR · agent notes · progress file · lessons log

## Structured memory lifecycle

The memory layer prefers one project memory on the BB hub when the hub and project are available; it falls back to local project records when the hub is off or out of reach (`bin/lane_memory.py:403-417`). The local corpus accepts memory types, truth modes, statuses, sensitivity levels, audiences, and relationship types from explicit enumerations (`bin/lane_memory.py:15-45`). A local record is usable only after its status, validity window, trust, and audience checks pass (`bin/lane_memory.py:345-367`).

| Status | Retrieval behavior | Transition or cleanup |
|---|---|---|
| `draft` | Not included as a live record; draft files must live under `drafts/` (`bin/lane_memory.py:31-34`, `bin/lane_memory.py:957-959`). |
| `active` | Candidate for retrieval subject to trust, date, sensitivity, and audience filters (`bin/lane_memory.py:345-394`). |
| `superseded`, `revoked`, `expired`, `archived` | Terminal statuses excluded from live retrieval (`bin/lane_memory.py:31-34`, `bin/lane_memory.py:385-394`). |

| Transition | From | To | Function and condition |
|---|---|---|---|
| Replacement | active | superseded | A new record names `supersedes`; the old file receives `superseded_by` (`bin/lane_memory.py:1267-1284`). |
| Explicit forget | stored | expired / archived | `forget` writes the requested status and rebuilds derived files (`bin/lane_memory.py:1331-1355`). |
| Explicit erase | stored | removed | `forget --mode erase --yes` unlinks the Markdown file and checks remaining traces (`bin/lane_memory.py:1331-1345`). |

Hub searches return hub records when the RPC succeeds; when it does not, local search uses the project's Markdown corpus and generated SQLite index (`bin/lane_memory.py:634-680`). The local index stores tokenized record ID, claim, retrieval hint/areas, and memory type (`bin/lane_memory.py:370-382`, `bin/lane_memory.py:468-498`). When the local corpus hash differs, the next search rebuilds the index; a failed rebuild reports the index as unavailable (`bin/lane_memory.py:461-510`). Memory data fields and cleanup behavior are documented in [the data model](data-model.md).

## Night finding triage

Night Jev triage considers only actionable findings in `open`, `needs_human`, or `in_progress`. A Jev error dismisses none; findings scoring below the dismissal cutoff are marked non-actionable and `dismissed` (`bin/jev_slots.py:12-59`).

## How it works

1. `project-memory-init` seeds project memory files, and `project-onboard` writes the project passport (`bin/project-memory-init:1-45`, `bin/project-onboard:40-55`).
2. Session hooks record tool and Git evidence into the session ledger (`hooks/session_ledger.py:1-40`).
3. When enabled, `lane-memory` validates source records, filters them by status/trust/audience, and searches the generated local index (`bin/lane_memory.py:345-394`, `bin/lane_memory.py:468-510`).
4. The configured memory stage can maintain or inject memory during a run; it is disabled in the default stage map (`bin/pipeline_stages.py:264-279`).

| Mode | Input | Behavior | Output |
|---|---|---|---|
| Project passport | Project path | Creates or refreshes onboarding state | Project-local passport files (`bin/project-onboard:40-55`). |
| Session evidence | Hook tool/Git observations | Records evidence and flushes session notes | `.agents/session-log/` and agent notes (`hooks/session_ledger.py:1-40`). |
| Structured memory | Hub RPC when available; local Markdown record otherwise | Searches hub first, then local records and index; sensitive local records stay machine-local (`bin/lane_memory.py:634-680`, `bin/lane_memory.py:1227-1267`). |
| Queued hub write | Method and payload in `.cls/memory-outbox/` | Flushes files in sorted order and stops at first failure to preserve order (`bin/lane_memory_hub.py:125-154`). |

**Failure behavior:** a failed hub call returns no result and writes are queued locally; queued flush stops at the first failed send (`bin/lane_memory_hub.py:65-88`, `bin/lane_memory_hub.py:137-165`). Invalid local records are excluded from deliverable records; a stale index rebuild failure returns an unavailable index result (`bin/lane_memory.py:385-394`, `bin/lane_memory.py:501-510`). Sensitive records bypass shared hub writes and are stored in local memory, outside the owner lexical index (`bin/lane_memory.py:1227-1235`, `bin/lane_memory.py:427-430`).

## Business rules

- Record `status`, `memory_type`, and `truth_mode` must use the closed vocabularies (`bin/lane_memory.py:28-45`, `bin/lane_memory.py:1197-1201`).
- A status of `draft` is valid only in a `drafts/` directory (`bin/lane_memory.py:957-959`).
- Records with `sensitive` or `encrypted-required` sensitivity do not enter the owner lexical index (`bin/lane_memory.py:427-430`).
- Hub write payloads cap concepts at 24 and source text at 300 characters; hub lessons cap rule text at 600, evidence at 1,000 characters, and scope at 8 items (`bin/lane_memory_hub.py:168-178`, `bin/lane_memory.py:1450-1457`).

## Public commands

| Command | Use |
|---|---|
| `project-memory-init PATH` | Initialize memory files in a project (`bin/project-memory-init:1-45`). |
| `project-onboard PATH` | Create a project passport (`bin/project-onboard:40-55`). |
| `resume-project PATH` | Read current project state (`bin/resume-project:1-55`). |
| `lane-memory` | Manage structured memory; configured in the optional memory stage (`bin/lane_memory.py:1-45`, `bin/pipeline_stages.py:264-279`). |

## Gotchas

- The SQLite memory index is disposable derived data; Markdown records remain the source (`bin/lane_memory.py:468-510`).
- Expire and archive change status but preserve the record file; erase requires explicit confirmation (`bin/lane_memory.py:1331-1355`).
- When hub mode is available, shared records are not stored in the local corpus; local writes are used for sensitive records or when hub mode is off/unavailable (`bin/lane_memory.py:412-417`, `bin/lane_memory.py:1227-1267`).

<!-- lane-pilot:backlinks -->
## Referenced by

- [docs/BEGINNER.de.md](BEGINNER.de.md)
- [docs/BEGINNER.es.md](BEGINNER.es.md)
- [docs/BEGINNER.fr.md](BEGINNER.fr.md)
- [docs/BEGINNER.ja.md](BEGINNER.ja.md)
- [docs/BEGINNER.ko.md](BEGINNER.ko.md)
- [docs/BEGINNER.md](BEGINNER.md)
- [docs/BEGINNER.pt-BR.md](BEGINNER.pt-BR.md)
- [docs/BEGINNER.zh-CN.md](BEGINNER.zh-CN.md)
- [Agent hooks / guards — multi-CLI](HOOKS.md)
