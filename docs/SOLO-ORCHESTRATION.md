# Solo orchestration (one human + one PM)

You work **alone** through **dev-orchestrator**. No multi-developer merge dance.

## Non-negotiables

1. **Orchestrator owns `main`.** Workers never push/merge to main. PM merges when the run is green.  
2. **You never merge.** If PM asks you to merge, PM is wrong — fix the skill.  
3. **Parallel only with ownership.** Disjoint `owns_paths` or serial.  
4. **Worktree for parallel / score≥4.** Isolated branch → PM merges to main → deletes worktree.  
5. **Fresh worker context.** Each task = new Agent spawn. PM handoffs when context fat.  
6. **Board is truth.** `.agents/runs/BOARD.md` + run `STATUS.md`.  
7. **Stall is recoverable.** No heartbeat → stalled → re-dispatch or other lane.

## End-state of every run

```
main  ←  contains the feature (merged by PM)
.worktrees/<slug>  ←  gone
.agents/runs/<slug>/MERGE.md  ←  how/when merged
PROGRESS.md  ←  Now/Next updated
```

## Commands PM uses

| Command | When |
|---------|------|
| `project-memory-init` | new repo once |
| `resume-project` | cold start / new session |
| `wt-create <repo> <slug>` | start isolated run |
| `lane-heartbeat …` | worker or supervisor pulse |
| `run-board <repo>` | refresh BOARD.md |
| `lane-stall-check <repo>` | find zombies |
| `check-owns-paths <task.yaml>` | after write lane |
| `wt-merge-main <repo> <slug>` | ship to main (PM only) |
| `night-audit <repo>` | overnight audit file |

## Human UX

- Talk only to **dev-orchestrator**.  
- Say what you want; do not manage branches.  
- Cold start: `/resume-project` or «продолжи» → PM reads BOARD + PROGRESS.  
- If something stuck >5 min: «проверь stall» → PM runs stall-check + re-dispatch.

## Language

All agent-written files **English**. Chat with human **Russian**. See [LANGUAGE.md](LANGUAGE.md).
