# Memory — PROGRESS, lessons, decisions, history, artifacts

| File | Max size | Update when |
|------|----------|-------------|
| `.agents/PROGRESS.md` | ~40 lines | End of meaningful work / session |
| lessons → hub rules | — | After a user correction or a failed approach: Lane Pilot: `lane_pilot_lesson` (rule + audience); terminal: `lane-memory lesson "<rule>" --for pm\|writer\|both` (not a file) |
| `.agents/decisions/<date>-<slug>.md` | rare | Expensive irreversible choice — a draft; the docs pass publishes it to `docs/decisions.md` |
| `.agents/agent-notes/OPEN.md` | grow | Debt / simplify later |
| `.agents/session-log/*` | auto | Hooks own it — never hand-author |
| `.agents/runs/*/artifacts/` | per run | Written during runs — immutable after |

## PROGRESS.md (rewrite, don't append)

```markdown
## Now
- <one sentence current reality>

## Blocked
- <or "none">

## Next
- [ ] <next concrete step>

## Last verify
- command: <what you ran>
- result: green|red
- when: YYYY-MM-DD
```

Leave `<!-- auto:session-ledger -->` … `<!-- /auto:session-ledger -->` blocks
alone — hooks own them.

After a wave of tasks, refresh PROGRESS **once**, not per micro-edit.

Schema-v2 runs: declare exact `progress_now`, `close_next`, and `close_open`
in `run.yaml`. Post-merge `run-finalize` applies them and records
hashes/actions in `finalize.json`. Never guess stale checklist items.

## Lessons → rules on the hub

A lesson is one imperative rule, sent to the project's memory on the BB hub (Lane Pilot), from whatever machine
the session runs on. Inside a Lane Pilot PM chat call the tool `lane_pilot_lesson` (rule, audience `pm`, `writer` or `both` — required, `always` only for a rule true of every writer task). In a terminal:

```bash
~/.agents/bin/lane-memory lesson "Run npm ci in writer worktrees, never npm install" --for writer \
  --evidence "owner corrected 2026-10-03; run lprun_… task gc-…" --scope apps/marketing
```

The hub keeps lessons bounded: a lesson close to a live rule counts as its repeat, a new one goes on trial
(at most 12 rules in force, unused ones retire), at most 30 wait. `--for pm`, `writer` or `both` says who follows it —
a `pm` rule never reaches a writer; `--always` marks a rule for every writer task. Writers get only the rules their
task needs.
Do not append to `.agents/LESSONS.md`: it grew without bound (≈150 entries in one project) and every writer
read all of it. Only after a real correction or landmine — not per session. Without a connection the lesson
waits in `.cls/memory-outbox/` and goes out with the next call (`lane-memory flush`).

## Decision drafts (`.agents/decisions/<date>-<slug>.md`, ADR-light)

Write one file per decision. Do not edit `docs/decisions.md`: the nightly docs pass (Lane Pilot or docs-maintain) turns each draft into an ADR there, with citations to the code, and names the draft.

```markdown
## ADR-NNN: Title
- **Date:** YYYY-MM-DD
- **Status:** accepted
- **Context:** …
- **Decision:** …
- **Consequences:** …
- **Alternatives considered:** …
```

Only durable irreversible forks. No ADRs for typo fixes.

## agent-notes/OPEN.md

Promote durable OPEN notes or close checkboxes after a green run. Night
audit (`~/.agents/bin/night-audit .`) closes OPEN items or spawns
todos/runs.

## Facts that cannot be derived

Durable non-code facts live in the hub memory, not in files: skill `lane-memory` (`lane-memory search|context`; in Lane Pilot also `lane_pilot_memory_context`). Not a second PROGRESS.

## History & artifacts (read-only layers)

- `.agents/session-log/` — auto handoff evidence (files/shell/git), written by
  hooks. To answer "what did we do": open its INDEX, not the bulk.
- `.agents/runs/<slug>/artifacts/<task>/` — reports, receipts, screenshots
  produced during runs. Immutable; link from PLAN.md/PROGRESS, never copy out.
- `.agents/findings/` — typed review findings (night-review). Read for prior
  evidence before re-diagnosing.

## Session-end checklist

1. PROGRESS rewritten (Now/Blocked/Next/Last verify).
2. New ideas from chat → todo items, not lost.
3. Plan task rows / ROADMAP reflect finished runs.
4. A lesson (`lane-memory lesson`) or ADR only if genuinely earned.
5. OPEN checkboxes updated if debt changed.
6. Nothing important exists only in chat.
