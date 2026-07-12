# Model routing (Fable conductor — solo)

**No GPT-5.5.** Codex side uses **GPT-5.6 only**: `gpt-5.6-sol` | `gpt-5.6-terra` | `gpt-5.6-luna` (optional trivia).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Fast write | AGY Flash High | Gemini Flash High |
| Main write | Grok 4.5 | — |
| Cheap review (medium) | opencode | openrouter/z-ai/glm-5.2 (pinned) |
| Gate / ship review | Codex **Sol** | `gpt-5.6-sol` + `high` (xhigh critical paths) |
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

**Effort:** agentic write/review → `high` or `xhigh`. Escalate Terra stall → Sol xhigh. Strong review = sol high; escalate to xhigh when the diff touches auth/pay/schema/migrations/security/crypto/concurrency (critical paths).

## Code routing (full stack: AGY + Grok + Codex)

| Signal | Lane | Model notes |
|--------|------|-------------|
| `risk: low` UI/wiring | agy-frontend / agy-coder | Flash High |
| `risk: medium` | grok + opencode-reviewer | Grok 4.5 + glm-5.2 pinned |
| `risk: high` auth/pay/schema | grok + **codex-review Sol xhigh** | dual |
| Empty-diff AGY | switch grok | — |

## Review tiers

| Tier   | Trigger                                   | Reviewer |
|--------|-------------------------------------------|----------|
| none   | micro path / risk low                     | verify field + check-owns-paths only |
| cheap  | risk medium                               | opencode-reviewer (glm-5.2, pinned) |
| strong | risk high / high_risk_paths / ship        | codex-reviewer (sol high; xhigh critical paths) |

Cheap review is mechanical only (bugs, style, dependencies, obvious logic);
auth/pay/schema/security always uses `codex-reviewer`. Cheap FAIL → writer fixes
or PM escalates to `codex-reviewer`; never ignore a FAIL.

## Profile `claude-codex` (only Claude + Codex)

| Stage | Claude wrapper | Codex model | Effort |
|-------|----------------|-------------|--------|
| fast_write | codex-implementer | **terra** | high |
| main_write (medium) | codex-implementer | **terra** | xhigh |
| main_write (high / high_risk_paths) | codex-implementer | **sol** | xhigh |
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
|-------|--------|
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

See [LANE-EXEC.md](LANE-EXEC.md). PM waits on the **Agent** tool, not a 90m Bash call.

AGY/Grok write tasks within the same run use `lane-session` affinity. The
warmest free conversation is resumed, while concurrent tasks lease separate
slots (maximum three). Default rotation: seven successful tasks; review remains
an independent cold session.

## Parallelism (solo)

| Situation | Policy |
|-----------|--------|
| Micro path (score 0–2, low risk, ≤2 files, no `high_risk_paths`) | main checkout, single AGY lane, no reviewer, verify none\|smoke |
| 1 low-risk write | main tree OK |
| ≥2 writes OR score ≥ 4 | worktree; max 3 parallel; disjoint owns_paths |
| High risk write | solo writer |
| Human never merges | PM → `wt-merge-main` |

## Instruction design

1. MUST ≤ 7 hard rules  
2. MAY = autonomy inside owns_paths  
3. NEVER = safety + never_touch + no merge to main  
4. DONE = report + done_when + owns check  
5. Model ids live in wrappers / profile YAML — not invent 5.5  
