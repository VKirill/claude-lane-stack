---
name: resume-project
description: Cold-start project context for orchestrator or human. Use when user says resume, продолж, where were we, cold start, or starting a new orchestrator session on an existing repo.
---

# Resume project

## MUST

1. Run (prefer compact day brief):

```bash
/home/ubuntu/.agents/bin/resume-project "$(pwd)"
# or explicitly:
/home/ubuntu/.agents/bin/resume-project "$(pwd)" --compact
```

This regenerates `.agents/HANDOFF.json` + `HANDOFF.md` and prints them first.

2. Synthesize in RU (short) **from HANDOFF**, not from raw BOARD dump:
   - **Now**
   - **Blocked** + `next_act` (e.g. `fix_contract` — do **not** re-dispatch writer)
   - **Next** typed acts only
   - Profile: `main_write` + workspace mode

3. Day policy reminder: write → L1 verify → accept → merge. **No daytime LLM review.**
   Night-shift owns review/fix.

4. If stalled tasks: re-dispatch or mark blocked — do not ignore.
   For schema v2, never mutate task YAML after first start.

5. Do **not** dump full files into chat — point paths. Full archaeology only if needed:
   `resume-project . --full`

## MAY

- `mcp__agentmemory__memory_smart_search` for prior decisions
- `night-audit` if user asks overnight review
- `handoff-write .` alone to refresh without full resume

## NEVER

- Ask human to merge branches
- Start coding as PM
- Blind retry when `next_act` is `fix_contract` (missing check.py, lane mismatch)
