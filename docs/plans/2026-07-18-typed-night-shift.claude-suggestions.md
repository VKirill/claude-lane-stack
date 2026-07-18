# Claude Companion triage

Review: `plan-red-team-20260718024351-2183f655`

Verdict: `PROCEED_WITH_GUARDS`

## Transport limitation

The Companion tmux fallback captured the marked response immediately after the
verdict and closed the reviewer session before the detailed sections were
persisted. The verdict is usable; individual Claude recommendations are not.
The implementation therefore treats the detailed review as unavailable and
adds Codex-native guards from the inspected runtime contracts.

## Triage

| Recommendation | Classification | Decision |
|---|---|---|
| Proceed only with explicit guards | accept | Patch the plan before implementation. |
| Automatic merge/deploy boundary | accept | Autofix may prepare and verify worktree changes; merge requires project opt-in. |
| Resumable repair execution | accept | Add a deterministic stateful runner; do not keep a model alive as the liveness loop. |
| Generated verification safety | accept | Reject ambiguous, empty, or shell-composed commands before dispatch. |
| Dirty main/worktree isolation | accept | Always write night fixes in a dedicated worktree and leave it recoverable on merge blockers. |
| Detailed failure scenarios | unavailable | Companion fallback did not persist them; cover with focused tests and final code review. |

No item requires a user decision because these guards narrow automation and do
not expand product, deployment, or permission scope.
