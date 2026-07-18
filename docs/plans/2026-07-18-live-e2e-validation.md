# Live Grok and Codex E2E validation

Date: 2026-07-18

This validation used the installed commands and real provider CLIs. It did not
use the fake providers from the unit-test suite.

## Grok writer

- Disposable repository: `/tmp/claude-lane-live-e2e-final.gXT99w`
- Run/task: `live-grok-smoke/001`, schema v2, attempt 1
- Provider: Grok CLI `0.2.103`, model `grok-4.5`
- Runtime policy: workspace sandbox, `subagents_enabled=false`
- Result: provider exit 0, valid protocol, complete report
- Ownership: passed; the only changed source file was `math_utils.py`
- Independent verification: `python3 -m unittest -v`, 2/2 passed
- Acceptance: exact task hash and attempt accepted

The run proved that the installed lane could initialize a strict task,
dispatch a real Grok writer, collect its report, enforce owned paths, execute
recorded verification, and write a deterministic acceptance receipt.

## Codex reviewer

- Provider: Codex CLI `0.144.5`
- Profile: `gpt-5.6-sol`, reasoning `xhigh`, read-only sandbox, approval `never`
- Isolation: base user config and unrelated MCP startup are disabled for the
  unattended review invocation
- Input: the real Grok diff above, bound to base commit, task hash, attempt,
  tracked diff digest, and full tree digest
- Result: structured receipt validated against the full local review schema
- Verdict: `passed`; findings: none

After enabling base-config isolation, the same real review was repeated in
32.89 seconds. It completed without unrelated MCP startup errors, produced the
same reviewed diff/tree digests, and created no project-memory files.

## Defects found by the live run

1. Global Grok and Codex session-ledger hooks could create project-memory files
   inside a reviewed worktree. Automated lanes now export
   `CLAUDE_LANE_AUTOMATION=1`; the ledger exits before creating state or project
   files. Grok also disables imported Claude compatibility hooks while keeping
   native non-ledger safety hooks.
2. Codex rejected valid local review schemas containing `uniqueItems`, `allOf`,
   and enum/const nodes without an explicit type. The reviewer now sends a
   model-compatible projection and validates the returned document against the
   unchanged, stricter local schema.

The final repeated Grok/Codex run created no `PROGRESS.md` or session-ledger
files. The fixes are also covered by unit tests.

## Regression suites

- Python: 132/132 passed
- Lane Board Node tests: 23/23 passed
- Python compile, Bash syntax, JSON Schema meta-validation, and
  `git diff --check`: passed
