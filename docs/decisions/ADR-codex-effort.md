# ADR: Codex model + reasoning effort (token budget)

## Status
Accepted (2026-07-30)

## Context
Codex agents defaulted to `xhigh` (and "fast_write" still burned high/xhigh).
Light recovery and docs work do not need max reasoning cost.

## Decision

### Effort ladder (Codex `model_reasoning_effort`)

| Effort | Use |
|--------|-----|
| `low` | Almost never for product work (trivial one-liner only if PM forces) |
| `medium` | Low-risk small scope write/onboard minimal |
| `high` | **Default** for medium write, review, docs, deep onboard, controller fallback |
| `xhigh` | **Only** high-risk/emergency, or explicit `CODEX_REASONING=xhigh`, or second attempt after a failed high run |

### Model + effort matrix

| Role | Trigger | Model | Effort |
|------|---------|-------|--------|
| implementer | `risk: low` and small owns (≤3 path entries) | `gpt-5.6-terra` | `medium` |
| implementer | `risk: medium` / default | `gpt-5.6-terra` | `high` |
| implementer | `risk: high` / `high_risk_paths` / emergency / terminal recovery | `gpt-5.6-sol` | `high` |
| implementer | escalate | same model | `xhigh` only if forced |
| reviewer | default task / night chunk | `gpt-5.6-sol` | `high` |
| reviewer | escalate | `gpt-5.6-sol` | `xhigh` only if forced |
| onboarder | minimal | `gpt-5.6-terra` | `medium` |
| onboarder | deep / full | `gpt-5.6-sol` | `high` |
| docs-maintainer | default | `gpt-5.6-terra` | `high` |
| controller fallback | second writer availability failure | `gpt-5.6-sol` | `high` |

### Removed

- **`fast_write`** as a Codex effort shortcut (do not map "fast" → still-expensive high/xhigh).
- Default **`xhigh`** on implementer and night-review profile.

### Overrides

- `CODEX_MODEL`, `CODEX_REASONING` env always win when set by PM.
- Forbidden: gpt-5.5; Luna for multi-file agent work.

## Consequences
Token cost drops on routine Codex use; quality-critical paths still get Sol + high, with xhigh reserved for true hard cases.
