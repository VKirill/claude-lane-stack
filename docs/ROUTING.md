# Model routing (Fable conductor — solo)

## Roles

| Role | Who | Job |
|------|-----|-----|
| Conductor | Fable (dev-orchestrator) | Plan, task files, route, accept, **merge main**, ship |
| Fast write | AGY Gemini Flash High | low/UI/boilerplate |
| Main write | Grok 4.5 | medium/high implementation |
| Gate | GPT-5.6-sol (Codex) | review, high-stakes correctness |
| Fallback write | Codex | only if both write lanes down |

## Code routing

| Signal | Lane |
|--------|------|
| `risk: low`, wiring, tests-only, UI polish | `agy-coder` / `agy-frontend` |
| `risk: medium` feature body | `grok` |
| `risk: high` auth/pay/schema/secrets | `grok` + **mandatory** `codex-review` |
| paths touch auth/pay/migration/middleware | `high_risk_paths: true` → dual: write + codex-review |
| SPEC / final ship | `codex-review` on full run diff |
| Empty-diff AGY fail | switch to `grok` immediately |

## Parallelism (solo)

| Situation | Policy |
|-----------|--------|
| 1 write task, low risk | main tree OK; PM commits on main |
| ≥2 write tasks OR score ≥ 4 | **worktree**; max **3** parallel; disjoint owns_paths |
| High risk write | **solo** (no parallel with other writers) |
| Review | parallel with unrelated write only if disjoint |

## Non-code

| Task | Lane |
|------|------|
| Research bulk / draft docs | AGY |
| Product options | Fable + user |
| Security audit of plan/diff | Codex review |

## Instruction design

1. MUST ≤ 7 hard rules  
2. MAY = autonomy inside owns_paths  
3. NEVER = safety + never_touch + no merge to main  
4. DONE = report.md + done_when evidence + owns check  
5. Detail lives in **task YAML**, not agent soul
