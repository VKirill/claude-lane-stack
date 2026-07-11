---
description: Cold-start project — BOARD, PROGRESS, stalled tasks, worktrees
---

Run `~/.agents/bin/resume-project` on the current project cwd (or $ARGUMENTS if a path is given).

Then summarize in Russian: **Now**, **Blocked/stalled**, **Next** 1–3 steps.  
If a run is fully done but unmerged, plan `wt-merge-main` (orchestrator merges to main — never ask the human).

Load skill `resume-project` if available.
