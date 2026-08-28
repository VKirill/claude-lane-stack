---
name: memory-maintainer
description: "Opt-in SMA fact-corpus refresh (shell-out to adoc stages.memory). Drafts only via lane-memory write. No feature code."
model: sonnet
background: true
tools: Bash, Read, Grep, Glob
skills:
  - lane-memory
  - project-life
---

# memory-maintainer

Shell-out. Provider/model come from **adoc** `stages.memory`.

```bash
export PATH="$HOME/.agents/bin:$PATH"
memory-maintain-project "$PROJECT_CWD" "${SINCE:-24 hours ago}"
```

If `stages.memory.enabled` is false, the script exits 0 with SKIP. Do not
invent a corpus. Last line: `DONE <report>` or `FAILED <reason>`.
