# Model routing (Fable conductor — solo)

**No GPT-5.5.** Codex side uses **GPT-5.6 only**: `gpt-5.6-sol` | `gpt-5.6-terra` | `gpt-5.6-luna` (optional trivia).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Fast write | AGY Flash High | Gemini Flash High |
| Main write | Grok 4.5 | — |
| Review (all) | Codex Sol | gpt-5.6-sol + high (nightly batch) |
| Nightly review | Codex Sol | sol high (batch); pre-merge gate opt-in per project |
| Fallback write | Codex | see claude-codex table |
| Onboard **fast** / docs maintain | Codex **Terra** | `gpt-5.6-terra` + `high` |
| Onboard **deep** (default on full) | Codex **Sol** | `gpt-5.6-sol` + `high` |
| Thin wrappers (implementer/reviewer supervisors) | Claude **Sonnet** | shell-out only |

## GPT-5.6 Sol / Terra / Luna (Codex)

| Model | Use | Avoid |
|-------|-----|--------|
| **Sol** `gpt-5.6-sol` | Long-horizon multi-file write, high-risk, **review/ship**, emergency | Using for every typo |
| **Terra** `gpt-5.6-terra` | Default **scoped write**, medium features, onboard, docs refresh | Dropping effort to `low` on agent loops |
| **Luna** `gpt-5.6-luna` | Trivia: changelog line, PR one-liner, triage | Multi-step agent write/review (falls apart) |

**Effort:** agentic write/review → `high` or `xhigh`. Escalate Terra stall → Sol xhigh. Nightly review = sol high (batch, operator 2026-07-14). Gate review (opt-in, pre-merge) = sol high; escalate to xhigh when the diff touches auth/pay/schema/migrations/security/crypto/concurrency (critical paths).

## Code routing (full stack: AGY + Grok + Codex)

| Signal | Lane | Model notes |
|--------|------|-------------|
| `risk: low` UI/wiring | agy-frontend / agy-coder | Flash High |
| `risk: medium` | grok + codex-review sol high | Grok 4.5 medium + gpt-5.6-sol high |
| `risk: high` auth/pay/schema | grok + codex-review Sol xhigh | nightly (gate opt-in for pre-merge) |
| Empty-diff AGY | switch grok | — |

## Review tiers

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | night-review batch (sol): verdicts + Morning fix plan; FAIL -> morning fix task, never ignored |

Pre-merge gate is OFF by default (solo, no-user products). When a project
serves real users or money, re-enable per project: add `gate: pre-merge` to
PROGRESS.md Pointers (or set `gate: pre-merge` in a task YAML) — then
codex-reviewer (sol high; xhigh for auth/pay/schema/migrations/security)
must pass BEFORE merge for high-risk work in that project.

## Profile `claude-codex` (only Claude + Codex)

| Stage | Claude wrapper | Codex model | Effort |
|-------|----------------|-------------|--------|
| fast_write | codex-implementer | **terra** | high |
| main_write (medium) | codex-implementer | **terra** | xhigh |
| main_write (high / high_risk_paths) | codex-implementer | **sol** | xhigh |
| review (medium) | codex-reviewer | **sol** | high |
| review / ship | codex-reviewer | **sol** | high (xhigh critical paths) |
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

Foreground Bash dies ~**2 minutes**. Write lanes **must** detach:

```bash
lane-bg --dir "$ARTIFACT_DIR" -- … lane-exec … -- agy|grok|codex …
lane-wait --dir "$ARTIFACT_DIR" --once
```

See [LANE-EXEC.md](LANE-EXEC.md). PM never runs 90m Bash; multi-task uses
**progressive accept** (`MODE=start` → `lane-poll` → `MODE=finish` per task).

AGY/Grok write tasks within the same run use `lane-session` affinity. The
warmest free conversation is resumed, while concurrent tasks lease separate
slots (maximum three). Default rotation: seven successful tasks; review remains
an independent cold session.

## Parallelism (solo)

| Situation | Policy |
|-----------|--------|
| Micro path (score 0–2, low risk, ≤2 files, no `high_risk_paths`) | main checkout, single AGY lane `MODE=full`, no reviewer, verify none\|smoke |
| 1 low-risk write | main tree OK; `MODE=full` OK |
| ≥2 writes OR score ≥ 4 | worktree; max 3 **concurrent** slots; progressive accept; disjoint owns_paths |
| High risk write | solo writer |
| Human never merges | PM → `wt-merge-main` |

**Progressive accept:** when task A finishes while B still runs, accept A
immediately, free its slot, start the next ready task. Never wait for the
slowest sibling before accepting finished ones.

## Instruction design

1. MUST ≤ 7 hard rules  
2. MAY = autonomy inside owns_paths  
3. NEVER = safety + never_touch + no merge to main  
4. DONE = report + done_when + owns check  
5. Model ids live in wrappers / profile YAML — not invent 5.5  
