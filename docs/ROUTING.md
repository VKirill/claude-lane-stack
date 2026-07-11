# Model routing (Fable conductor — solo)

**No GPT-5.5.** Codex side uses **GPT-5.6 only**: `gpt-5.6-sol` | `gpt-5.6-terra` | `gpt-5.6-luna` (optional trivia).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Fast write | AGY Flash High | Gemini Flash High |
| Main write | Grok 4.5 | — |
| Gate / ship review | Codex **Sol** | `gpt-5.6-sol` + `xhigh` |
| Fallback write | Codex | see claude-codex table |
| Onboard / docs maintain | Codex **Terra** (Sol if huge monorepo) | `gpt-5.6-terra` + `high` |
| Thin wrappers (implementer/reviewer supervisors) | Claude **Sonnet** | shell-out only |

## GPT-5.6 Sol / Terra / Luna (Codex)

| Model | Use | Avoid |
|-------|-----|--------|
| **Sol** `gpt-5.6-sol` | Long-horizon multi-file write, high-risk, **review/ship**, emergency | Using for every typo |
| **Terra** `gpt-5.6-terra` | Default **scoped write**, medium features, onboard, docs refresh | Dropping effort to `low` on agent loops |
| **Luna** `gpt-5.6-luna` | Trivia: changelog line, PR one-liner, triage | Multi-step agent write/review (falls apart) |

**Effort:** agentic write/review → `high` or `xhigh`. Escalate Terra stall → Sol xhigh.

## Code routing (full stack: AGY + Grok + Codex)

| Signal | Lane | Model notes |
|--------|------|-------------|
| `risk: low` UI/wiring | agy-frontend / agy-coder | Flash High |
| `risk: medium` | grok | Grok 4.5 |
| `risk: high` auth/pay/schema | grok + **codex-review Sol xhigh** | dual |
| Empty-diff AGY | switch grok | — |
| Ship / SPEC review | codex-reviewer | Sol xhigh |

## Profile `claude-codex` (only Claude + Codex)

| Stage | Claude wrapper | Codex model | Effort |
|-------|----------------|-------------|--------|
| fast_write | codex-implementer | **terra** | high |
| main_write (medium) | codex-implementer | **terra** | xhigh |
| main_write (high / high_risk_paths) | codex-implementer | **sol** | xhigh |
| review / ship | codex-reviewer | **sol** | xhigh |
| onboard | codex-onboarder | **terra** (sol if huge) | high |
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

## Parallelism (solo)

| Situation | Policy |
|-----------|--------|
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
