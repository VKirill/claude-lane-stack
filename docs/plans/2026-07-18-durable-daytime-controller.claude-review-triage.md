# Durable daytime controller — Claude review triage

Reviewer result: 0 Critical, 2 High, 4 Medium.

## Decisions

1. **Sibling `never_touch` union — reject.** The proposed failure cannot reach the controller: `run-validate` rejects every overlap between any task `owns_paths` and any task `never_touch` before initial dispatch and before every dependency-release wave. A standalone ownership check on an invalid contract correctly fails closed.
2. **Ownership scope not bound at accept — partially accept.** `lane-ctl accept` now requires a recognized `task|run` scope, unique string task IDs, exact `[task_id]` for task scope, and the exact current `tasks/*.yaml` ID list for run scope. The suggested `shared-worktree` flag was rejected because that flag is not part of the v2 contract and the durable daytime controller intentionally operates in one shared worktree.
3. **`not_started` spin — accept with narrower fix.** A dispatched task that regresses to `not_started` now blocks immediately with a typed reason. Pending, not-yet-dispatched tasks remain eligible for dispatch. This targets the actual impossible-progress state without a wall-clock timeout that could kill legitimately slow providers.
4. **Board dead-controller contradiction — accept.** A nonterminal receipt plus controller exit or dead recorded PID is rendered as inferred `failed / operator_intervention`, matching CLI observation.
5. **Recognized stop reasons versus success — reject behavior change, accept clarity.** Recognition is only a sanitized diagnostic allowlist; it never promised success. `EndTurn` remains the sole successful reason by design. The constant was renamed and documented to remove the ambiguity.
6. **Malformed controller receipt can defeat failure recording — accept.** The controller validates receipt structure before use, atomically replaces a malformed running receipt with a canonical terminal failure, and the failure recorder has a canonical reconstruction fallback.

## Narrow verification after accepted fixes

- 6 focused Python lifecycle/acceptance tests passed.
- 9 focused Board snapshot tests passed; the full Board suite has 33 passing tests.
- Added negative coverage for tampered ownership task-set binding, provider state loss, malformed controller receipt, and dead-controller Board inference.

## Follow-up review

The reviewer rechecked only the accepted/rejected findings and returned 0
Critical / 0 High. Two below-threshold Board display notes from that pass were
also closed: malformed PID/exit receipts now infer failure, and an inferred
terminal stage outranks any receipt-supplied status string.
