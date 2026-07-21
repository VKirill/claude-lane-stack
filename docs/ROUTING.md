# Model routing (Fable conductor — solo)

**No GPT-5.5.** Codex side uses **GPT-5.6 only**: `gpt-5.6-sol` | `gpt-5.6-terra` | `gpt-5.6-luna` (optional trivia).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Write (all risks) | **AGY 3.6** (default) or **Grok 4.5** | selected programmer lane |
| Review (all shipped work) | Codex Sol night shift | gpt-5.6-sol + xhigh, read-only |
| Nightly review | Codex Sol | dedicated `night-review` profile: sol xhigh |
| Fallback write | Codex | see claude-codex table |
| Onboard **fast** / docs maintain | Codex **Terra** | `gpt-5.6-terra` + `high` |
| Onboard **deep** (default on full) | Codex **Sol** | `gpt-5.6-sol` + `high` |
| Run visibility wrapper | Claude **Haiku** `run-supervisor` | typed start/watch/status only |
| Diagnostic/reviewer wrappers | Claude **Sonnet** | shell-out only |

## GPT-5.6 Sol / Terra / Luna (Codex)

| Model | Use | Avoid |
|-------|-----|--------|
| **Sol** `gpt-5.6-sol` | Long-horizon multi-file write, high-risk, **review/ship**, emergency | Using for every typo |
| **Terra** `gpt-5.6-terra` | Default **scoped write**, medium features, onboard, docs refresh | Dropping effort to `low` on agent loops |
| **Luna** `gpt-5.6-luna` | Trivia: changelog line, PR one-liner, triage | Multi-step agent write/review (falls apart) |

**Effort:** agentic write → `high` or `xhigh`. Escalate Terra stall → Sol xhigh.
All review uses Sol xhigh through the read-only `night-review` profile.

## Code routing (full stack)

| Signal | Lane | Model notes |
|--------|------|-------------|
| `risk: low` UI/wiring | **agy** by default; `grok` selectable | Gemini 3.6 Flash high or Grok 4.5 medium |
| `risk: medium` | selected writer → Codex night shift | same receipt chain + gpt-5.6-sol xhigh nightly |
| `risk: high` auth/pay/schema | selected writer solo → Codex night shift | no silent daytime reviewer |
| Selected model/catalog/quota/auth unavailable | persisted retry once, then integrated **Sol high** fallback | same receipts; no daytime review |
| Empty-diff / task/protocol failure | retry once, then block; manual **codex-implementer** only by operator | — |

## Review tiers

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | typed Sol xhigh findings; bounded AGY/Grok repair; fresh re-review |

There is no daytime LLM review. Historical or explicitly configured
`gate: pre-merge` runs stop for an operator decision instead of silently
starting Codex. Normal review, repair, and fresh re-review run at night.

## Profile `claude-codex` (only Claude + Codex)

| Stage | Claude wrapper | Codex model | Effort |
|-------|----------------|-------------|--------|
| fast_write | codex-implementer | **terra** | high |
| main_write (medium) | codex-implementer | **terra** | xhigh |
| main_write (high / high_risk_paths) | codex-implementer | **sol** | xhigh |
| review (medium) | codex-reviewer | **sol** | xhigh |
| review / ship | codex-reviewer | **sol** | xhigh |
| onboard (fast) | codex-onboarder | **terra** | high |
| onboard (deep / full default) | codex-onboarder | **sol** | high |
| docs-maintain | codex-docs-maintainer | **terra** | high |
| emergency_write | codex-implementer | **sol** | xhigh |
| luna | — | optional trivia only | low/medium |

PM remains **Claude Fable/Opus**. Wrappers stay **Sonnet**.

See `profiles/claude-codex.yaml`.

## Profile `claude-only` (no Codex)

| Stage | Model |
|-------|-------|
| PM | Fable / Opus |
| low write | Claude Sonnet worker |
| medium/high write | Claude Opus worker |
| review | Claude Opus read-only review agent |

## Long lanes under Claude Code

Foreground Bash dies ~**2 minutes**. Daytime runs start through the durable
typed controller:

```bash
run-init "$(pwd)" "$SLUG" --score "$SCORE"
run-validate --run-dir "$RUN_DIR" --phase pre-dispatch
run-controller start --run-dir "$RUN_DIR" --project-cwd "$PROJECT_CWD"
run-controller watch --run-dir "$RUN_DIR" --timeout 240
run-controller status --run-dir "$RUN_DIR" --json
```

See [LANE-EXEC.md](LANE-EXEC.md). One source-read-only `run-supervisor` stays
visible through bounded watches; the detached deterministic controller remains
alive independently and makes all lifecycle decisions.

AGY and Grok write tasks within the same run use `lane-session` affinity. The
warmest free conversation is resumed, while concurrent tasks lease separate
slots (five by default, configurable 1–10). Default rotation: seven successful tasks; review remains
an independent cold session.
Classified provider availability failures are sanitized in `runtime.json`. The
controller waits 30 seconds by default, retries the exact selected model once, then
may use one ephemeral `gpt-5.6-sol` + `high` writer attempt. It cannot switch on
ownership, verification, cancellation, or an unknown failure.

## Parallelism (solo)

| Situation | Policy |
|-----------|--------|
| Micro path (score 0–2, low risk, ≤2 files, no `high_risk_paths`) | main checkout, durable controller around one detached **AGY/Grok** lane, no daytime reviewer |
| 1 low-risk write | main tree OK; typed `run-controller start` |
| ≥2 writes OR score ≥ 4 | worktree; provider pool default 5 / max 10; durable progressive accept; disjoint owns_paths |
| Verification | separate pool default 2 / max 10; exact task commands only |
| High risk write | solo writer |
| Human never merges | PM → `wt-merge-main` |

**Progressive accept:** when task A finishes while B still runs, verify A,
produce `owns-check.json`, and run `lane-ctl accept` immediately. Its
`acceptance.json` frees the slot; never wait for the slowest sibling.

## Instruction design

1. MUST ≤ 7 hard rules 
2. MAY = autonomy inside owns_paths 
3. NEVER = safety + never_touch + no merge to main 
4. DONE = immutable task hash + report + owns check + independent verification + acceptance receipt
5. Model ids live in wrappers / profile YAML — not invent 5.5 
