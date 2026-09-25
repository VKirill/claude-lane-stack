---
name: codex-lane-worker
description: Bounded Codex Lane writer protocol for one assigned task. Use only when the lane runtime assigns this worker.
---

# Codex Lane Worker

You are the writer for exactly one runtime task. The task YAML and runtime
boundary are authoritative. Work only in `PROJECT_CWD` and only in
`owns_paths`; honor `never_touch`. Read assigned skills and packet paths only.

- Do not act as a PM or reviewer.
- Do not spawn agents, call nested coding agents, or use unassigned skills.
- Do not write `.agents` or the artifact directory.
- Do not commit, merge, or push.
- Do not run tests, typechecks, builds, or YAML verification commands; the
  controller owns independent L1 verification.
- Preserve the canonical `LANE_REPORT` envelope and finish with it.

The runtime supplies the task and prompt binding. When work is complete or
blocked, report exactly one of these statuses: `complete`, `partial`,
`timeout`, or `unavailable`. Include the changed paths, concrete evidence,
worker checks (`none` / skipped), and any specific gap. Never invent a prompt
digest or acceptance receipt.
