# Memory — PROGRESS, LESSONS, decisions, history, artifacts

| File | Max size | Update when |
|------|----------|-------------|
| `.agents/PROGRESS.md` | ~40 lines | End of meaningful work / session |
| `.agents/LESSONS.md` | grow slowly | After user correction or failed approach |
| `docs/decisions.md` | rare | Expensive irreversible choice |
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

## LESSONS.md entry

```markdown
### YYYY-MM-DD — short title
- **Symptom:** …
- **Wrong approach:** …
- **Do:** …
- **Don't:** …
- **Evidence:** path or test name
```

Only after a real correction or landmine — not per session.

## docs/decisions.md (ADR-light)

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
4. LESSONS/ADR only if genuinely earned.
5. OPEN checkboxes updated if debt changed.
6. Nothing important exists only in chat.
