# Claude Companion review triage

Date: 2026-07-18

Scope: final reviewer-only pass for `docs/plans/2026-07-18-typed-night-shift.md` using the review pack in `docs/plans/2026-07-18-typed-night-shift.code-review-pack.md`.

## Review decisions

| Review ID | Captured verdict | Decision | Reason |
| --- | --- | --- | --- |
| `code-review-20260718041817-2a6369fa` | `APPROVE_WITH_FIXES` | `reject` | The fallback outbox stopped immediately after the verdict and contains no finding, evidence, file, line, or requested fix. It is an incomplete transport artifact, not actionable review evidence. |
| `code-review-20260718043535-e641b9db` | `APPROVE` | `accept` | The reviewer reports a direct inspection of the critical orchestration CLIs, finding schema, and tests, with no P0/P1 finding. |
| `release-readiness-review-20260718095010-0945cf23` | `NOT_READY` | `accept` | The release review found that direct schema-v2 `lane-ctl verify` still executed task strings through `/bin/bash -c`, bypassing the night runner's validator. |
| `release-readiness-review-20260718101727-f60d25f5` | `READY` | `reject` | The fallback capture says no blocking gaps but ends at the empty `Residual Risks` heading. It is not a complete review artifact. |
| `release-readiness-review-20260718102020-103988e2` | `READY_WITH_RISK` | `reject` | The forced retry contains only the review ID and verdict, with no risk, evidence, compatibility assessment, or test assessment. |

The accepted initial review requested no source change. The later release review
did identify one release blocker; its recommendation was accepted, implemented,
and re-verified before publication.

## Codex evidence check

Codex independently checked the high-risk controls named in the review pack:

- legacy and schema-v2 verification reject missing or empty commands;
- task review receipts bind the task hash, attempt, base commit, tracked diff, and untracked content digest;
- generated verification commands are parsed as argument arrays and reject unsafe executables, network/package tooling, and shell composition;
- repair dispatch revalidates the canonical finding and blocks stale or terminal findings;
- reviewed worktree drift is rejected before the task commit;
- task commit and completed merge recovery use durable identities and are covered by crash-window tests;
- automatic merge requires both an explicit CLI request and project policy opt-in, and schema-v2 merge refuses unrelated dirty state;
- Grok runtime receipts whitelist structured usage fields and record stderr only as bounded byte/digest diagnostics.

The final local suites passed: 132 Python tests and 23 board parser/snapshot/watch tests.

## Post-review hardening

Codex classified unrestricted `provider_version` and `stopReason` receipt strings as a non-blocking P2. The finding was accepted and fixed after Claude's P0/P1 approval: `lane-session` now persists only an extracted version token, maps unknown stop reasons to `Other`, and never writes the original control strings to the provider diagnostic log. A negative test injects a secret-shaped value into both fields and proves it is absent from both artifacts.

The release-readiness P0 was also accepted and fixed. Verification safety now
lives in shared `bin/verification_safety.py`; both `night-fix-runner` and
`lane-ctl` use it. Schema-v2 commands are rejected before provider launch when
they contain shell composition, unsafe executables, package mutation/fetch, or
worktree escapes. The allowlist is frozen in attempt control, and verification
runs the parsed argv directly without a shell. A regression test first
reproduced the bypass and now proves that neither the provider nor the injected
command starts.

## Residual control-plane finding

The Claude Companion fallback outbox can be written as soon as the streamed response contains its marker and verdict, before the rest of the response is available. A verdict-only `APPROVE_WITH_FIXES` therefore must not be treated as a complete review.

Until the external companion plugin is corrected, automation must require either a terminal completion signal plus a complete structured finding set, or an explicit `APPROVE` artifact with the reviewed scope. Partial fallback artifacts remain diagnostic only and cannot create repair tasks.

The post-fix release review was attempted twice. Both Claude sessions completed,
but `captured_from_tmux_fallback` persisted only partial answers. Neither partial
artifact reported a P0/P1 blocker; neither is accepted as release evidence. The
release decision therefore rests on the accepted original blocker, the direct
execution-boundary fix, the red-then-green regression test, and the complete
132 Python plus 23 Node verification suites.
