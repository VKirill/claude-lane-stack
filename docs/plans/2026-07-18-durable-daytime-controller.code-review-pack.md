# Durable daytime controller — final code review pack

## Review contract

- Role: reviewer-only; do not modify files.
- Scope: uncommitted durable daytime orchestration changes against `main`.
- Acceptance: report only concrete correctness, safety, lifecycle, or missing-test findings with `file:line` evidence. A clean result means no Critical or High findings and no unhandled fail-open path.
- Daytime contract: Grok is the only code writer. One read-only `run-supervisor` observes one durable deterministic controller. There is no daytime LLM review. The existing independent nightly Codex review -> Grok repair -> Codex re-review loop remains unchanged.

## Files to review

Core runtime and contracts:

- `bin/run-controller`
- `bin/check-owns-paths`
- `bin/lane-ctl`
- `bin/lane-session`
- `bin/agents-doctor`
- `install.sh`
- `schemas/run-controller-v1.schema.json`
- `agents/claude/run-supervisor.md`
- `agents/claude/dev-orchestrator.md`
- `agents/claude/lane-supervisor.md`
- `agents/claude/grok-implementer.md`
- `profiles/full.yaml`

Observability:

- `board/server/lib/parsers.mjs`
- `board/server/lib/snapshot.mjs`
- `board/server/lib/watch.mjs`
- `board/server/server.mjs`
- `board/web/js/lifecycle.mjs`
- `board/web/js/components/drawer.js`
- `board/web/js/views/board.js`
- `board/web/js/views/runs.js`
- `board/web/css/views.css`

Tests:

- `tests/test_run_controller.py`
- `tests/test_run_controller_live.py`
- `tests/test_run_controller_schema.py`
- `tests/test_contract_views.py`
- `tests/test_lane_ctl.py`
- `tests/test_lane_session.py`
- `tests/test_install.py`
- `tests/test_agents_doctor.py`
- `tests/test_progressive_accept.sh`
- `board/server/lib/api.test.mjs`
- `board/server/lib/parsers.test.mjs`
- `board/server/lib/snapshot.test.mjs`
- `board/server/lib/watch.test.mjs`
- `board/web/js/lifecycle.test.mjs`

Documentation is changed to match the same contract but is secondary to runtime correctness.

## Verification already run

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 163 passed.
- `node --test board/server/lib/*.test.mjs board/web/js/*.test.mjs`: 33 passed.
- `bash tests/test_progressive_accept.sh`: passed.
- `bash tests/test_lane_poll.sh`: passed.
- A real two-task shared-worktree live run reached accepted through the actual detached stack; both nohup and user-systemd controller backends were exercised.
- A live Claude `run-supervisor` profile probe loaded Haiku with only `Read` and typed `Bash`, then read a terminal accepted controller receipt.
- Active repository, installed runtime, and Claude agent/skill/command files contain no per-request dollar budget setting.

## Known risk questions

1. Does the controller always fail closed for missing/incomplete provider reports, invalid provider terminal reasons, controller crashes, inconsistent accepted receipts, verification failure, and ownership failure?
2. Can the separate provider and verification pools exceed their declared 1-10 bounds or incorrectly block provider refill?
3. Can run-scoped ownership allow changes outside the validated union, or can a sibling task make another honest lane fail spuriously?
4. Is `run-validate --phase pre-dispatch` enforced at startup and before every dependency-release wave?
5. Can Board show `done`/`accepted` without a trusted acceptance receipt, or hide the exact attempt/PID/liveness/exit/heartbeat/report/reason/next-action facts?
6. Does the new supervisor stay read-only and bounded while still making controller progress visible?
7. Did any daytime change weaken or replace the independent nightly review/fix/re-review loop?
