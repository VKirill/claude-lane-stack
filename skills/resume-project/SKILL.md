---
name: resume-project
description: Cold-start project context for orchestrator or human. Use when user says resume, продолж, where were we, cold start, or starting a new orchestrator session on an existing repo.
---

# Resume project

## MUST

1. Run (or Read output of):

```bash
/home/ubuntu/.agents/bin/resume-project "$(pwd)"
```

2. Synthesize in RU (short):
   - **Now** (from PROGRESS + BOARD)
   - **Blocked / stalled**
   - **Next** 1–3 actions
   - Open worktrees not yet merged → plan `wt-merge-main` if tasks done

3. If stalled tasks: re-dispatch or mark blocked — do not ignore.

4. Do **not** dump full files into chat — point paths.

## MAY

- `mcp__agentmemory__memory_smart_search` for prior decisions
- `night-audit` if user asks overnight review

## NEVER

- Ask human to merge branches
- Start coding as PM
