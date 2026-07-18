---
name: project-memory
description: >
  Living project memory files: PROGRESS.md, LESSONS.md, docs/decisions.md,
  session-log, agent-notes. Use when finishing a task/session, writing handoff,
  night audit, onboarding a cold project, or user says progress/lessons/ADR/handoff.
---

# Project memory

**Canon:** `/home/ubuntu/.agents/docs/PROJECT-MEMORY.md`  
**Templates:** `~/.agents/templates/`  
**Init:** `~/.agents/bin/project-memory-init <repo>`

## Files (project root unless noted)

| File | Max size | Update when |
|------|----------|-------------|
| `PROGRESS.md` | ~40 lines | End of meaningful work / session |
| `LESSONS.md` | grow slowly | After user correction or failed approach |
| `docs/decisions.md` | rare | Expensive irreversible choice |
| `.agents/session-log/*` | auto | Hooks (do not hand-author bulk) |
| `.agents/agent-notes/OPEN.md` | grow | Debt / simplify later |

## Session start (all agents)

1. Read `AGENTS.md` / `CLAUDE.md` (project).  
2. Read `PROGRESS.md` if present (one pass).  
3. Skim last 5 lines of `LESSONS.md` titles if present.  
4. Optional: `.agents/todos/INDEX.md` counts only.  
5. Do **not** dump full session-log into context — open INDEX only if resuming unknown work.

## After a task (lane or implementer)

When `report.md` is green / complete:

1. **PROGRESS.md** — rewrite Now / Next / Last verify (keep Auto section intact).  
2. If user corrected you or you hit a landmine → **LESSONS.md** one entry.  
3. If architectural fork locked → **docs/decisions.md** ADR-light entry.  
4. Promote durable OPEN notes or close checkboxes in `agent-notes/OPEN.md`.  
5. Do **not** invent ADRs for typo fixes.

### PROGRESS update recipe

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

Leave `<!-- auto:session-ledger -->` … `<!-- /auto:session-ledger -->` alone (hooks own it).

### LESSONS entry recipe

```markdown
### YYYY-MM-DD — short title
- **Symptom:** …
- **Wrong approach:** …
- **Do:** …
- **Don't:** …
- **Evidence:** path or test name
```

### ADR recipe (only if durable)

```markdown
## ADR-NNN: Title
- **Date:** YYYY-MM-DD
- **Status:** accepted
- **Context:** …
- **Decision:** …
- **Consequences:** …
- **Alternatives considered:** …
```

## PM / orchestrator

- Ideas → `agent-todos`, not PROGRESS.  
- Active delivery → PROGRESS + runs.  
- After wave of tasks → refresh PROGRESS once, not per micro-edit.
- For schema-v2 runs, declare exact `progress_now`, `close_next`, and
  `close_open` actions in run.yaml; post-merge `run-finalize` applies them and
  records hashes/actions in finalize.json. Never guess stale checklist items.

## Night audit

Run `~/.agents/bin/night-audit .` or read `AUDIT-*.md`. Close OPEN items or spawn todos/runs.

## Anti-patterns

- ❌ Pasting full chat into PROGRESS  
- ❌ Auto-generated AGENTS.md that duplicates README  
- ❌ ADR for every session  
- ❌ Secrets in any of these files  
- ❌ Editing production code "to update docs" without a run when you are PM  
