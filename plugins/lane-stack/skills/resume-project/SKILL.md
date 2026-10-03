---
name: resume-project
description: Cold-start project context for orchestrator or human. Use when user says resume, продолж, where were we, cold start, /lane-stack:resume-project, or starting a new orchestrator session on an existing repo. Inside Lane Pilot read PROGRESS/ROADMAP and the Lane Pilot run tools instead of the CLI. Slash /lane-stack:resume-project runs the CLI. Info card only when args are exactly info.
argument-hint: "[path|--compact|info]"
user-invocable: false
---

# Resume project

Default: run. Info card only if `$ARGUMENTS` is exactly `info`.

> **Inside a Lane Pilot chat** (`LANE_PILOT_AGENT_TYPE` set / tools `lane_pilot_*` present) cold start is not the CLI: read `.agents/PROGRESS.md`, `.agents/plans/ROADMAP.md` and the open counts in `.agents/todos/INDEX.md`, then take the run state from the Lane Pilot tools (`lane_pilot_workspace_status`, `lane_pilot_gate_report`) and prior decisions from hub memory (`lane-memory search`, `lane_pilot_memory_context`). Answer in Russian: Now / Blocked / Next. Day policy there: writer → plan and code critique → acceptance → merge, all by Lane Pilot. HANDOFF/BOARD, `next_act` and `resume-project` below are the terminal harness.

## Procedure (terminal)

1. Run (prefer compact day brief):

```bash
export PATH="$HOME/.agents/bin:$PATH"
resume-project "$(pwd)" --compact
```

This regenerates `.agents/HANDOFF.json` + `HANDOFF.md` and prints them first.

2. Synthesize in RU (short) **from HANDOFF**, not from raw BOARD dump:
   - **Now**
   - **Blocked** + `next_act` (e.g. `fix_contract` — do **not** re-dispatch writer)
   - **Next** typed acts only
   - Profile: `main_write` + workspace mode

3. Day policy reminder (terminal): write → L1 verify → accept → merge. No daytime LLM review; night-shift owns review/fix.

4. If stalled tasks: re-dispatch or mark blocked — do not ignore.
   For schema v2, never mutate task YAML after first start.

5. Do **not** dump full files into chat — point paths. Full archaeology only if needed:
   `resume-project . --full`

## Optional

- `lane-memory search` for prior decisions (hub memory)
- `night-audit` if user asks overnight review
- `handoff-write .` alone to refresh without full resume

## Boundaries

- Merging is yours or the controller's, so do not ask the human to merge branches.
- The PM plans and verifies; coding goes to a writer lane.
- When `next_act` is `fix_contract` (missing check.py, lane mismatch) repair the contract first: a blind retry fails the same way.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop. Do not run resume-project.
