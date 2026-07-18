# Claude Companion code-review pack

Reviewer-only pass. Do not modify source files.

## Plan

- `docs/plans/2026-07-18-typed-night-shift.md`
- `docs/plans/2026-07-18-typed-night-shift.claude-suggestions.md`

## Scope

Typed Claude -> Grok -> Codex night orchestration: schema-v2 lane lifecycle, run-scoped Grok sessions with subagents disabled, structured Codex review findings, isolated repair worktrees, exact re-review receipts, deterministic acceptance, merge recovery, board projections, install/profile/docs.

## Changed files

- `CHANGELOG.md`
- `README.md`
- `README.ru.md`
- `agents/claude/codex-reviewer.md`
- `agents/claude/dev-orchestrator.md`
- `agents/claude/grok-implementer.md`
- `agents/claude/lane-supervisor.md`
- `agents/codex/instructions/reviewer.md`
- `agents/codex/instructions/writer-emergency.md`
- `agents/codex/reviewer.md`
- `agents/codex/writer-emergency.md`
- `agents/grok/writer.md`
- `bin/check-owns-paths`
- `bin/lane-ctl`
- `bin/lane-heartbeat`
- `bin/lane-session`
- `bin/lane-stall-check`
- `bin/night-fix-runner`
- `bin/night-review`
- `bin/night-review-all`
- `bin/night-review-engine`
- `bin/night-shift`
- `bin/night-shift-all`
- `bin/resume-project`
- `bin/run-board`
- `bin/run-finalize`
- `bin/run-init`
- `bin/run-validate`
- `bin/verification_safety.py`
- `bin/wt-create`
- `bin/wt-merge-main`
- `board/server/lib/parsers.mjs`
- `board/server/lib/parsers.test.mjs`
- `board/server/lib/snapshot.mjs`
- `board/server/lib/snapshot.test.mjs`
- `board/server/lib/watch.mjs`
- `board/server/lib/watch.test.mjs`
- `docs/FILE-CONTRACT.md`
- `docs/LANE-EXEC.md`
- `docs/LANGUAGE.md`
- `docs/PROJECT-MEMORY.md`
- `docs/ROUTING.md`
- `docs/SOLO-ORCHESTRATION.md`
- `docs/decisions.md`
- `docs/plans/`
- `docs/plans/2026-07-18-typed-night-shift.code-review-pack.md`
- `install.sh`
- `profiles/codex/`
- `schemas/`
- `skills/lane-contract/SKILL.md`
- `skills/orchestrator-lanes/SKILL.md`
- `skills/project-memory/SKILL.md`
- `skills/resume-project/SKILL.md`
- `templates/run-contract/`
- `tests/test_contract_views.py`
- `tests/test_install.py`
- `tests/test_lane_ctl.py`
- `tests/test_lane_session.py`
- `tests/test_night_fix_runner.py`
- `tests/test_night_review.py`
- `tests/test_night_shift.py`
- `tests/test_night_shift_all.py`
- `tests/test_run_contract.py`
- `tests/test_run_finalize.py`
- `tests/test_wt_create.py`
- `tests/test_wt_merge_main.py`

## Verification

- `python3 -m unittest discover -s tests -v`: 132/132 passed.
- `node --test board/server/lib/*.test.mjs`: 23/23 passed.
- Python compile, Bash syntax, Node syntax: passed.
- All JSON schemas passed Draft 2020-12 meta-schema validation.
- `git diff --check`: passed.
- Live Grok writer and Codex reviewer evidence is recorded in
  `docs/plans/2026-07-18-live-e2e-validation.md`.

## Known risks and review questions

- GitNexus cannot resolve the extensionless Python CLIs, so their automated impact result is UNKNOWN.
- Confirm empty verification cannot pass legacy or v2 smoke/tests tasks.
- Confirm `review.json` is bound to exact task/attempt/base/worktree and post-review tracked or untracked edits cannot be accepted or committed.
- Confirm generated verification cannot fetch packages, execute shell composition, or escape the worktree.
- Confirm direct schema-v2 `lane-ctl` start/verify applies the same safety gate
  and executes a parsed argv vector without `/bin/bash -c`.
- Confirm changed/closed canonical findings cannot dispatch stale Grok repair tasks.
- Confirm task-commit and completed-merge recovery are idempotent after crash windows.
- Confirm merge still requires CLI request plus project policy opt-in and refuses dirty schema-v2 worktrees.
- Confirm runtime receipts do not leak provider stderr, exception messages, secrets, or arbitrary protocol fields.
- Identify only P0/P1 correctness, security, data-loss, or missing-test findings. Classify lower-priority suggestions separately.
