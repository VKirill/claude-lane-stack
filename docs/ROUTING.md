# Model routing (Fable conductor — solo)

**No GPT-5.5.** Codex side uses **GPT-5.6 only**: `gpt-5.6-sol` | `gpt-5.6-terra` | `gpt-5.6-luna` (optional trivia).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Plan critique | **Structural** + optional one-shot LLM (Qwen/Codex/Kimi/Grok/AGY) → PM `decision` | `stages.plan_critique` in adoc |
| Write (all risks) | **Kimi K3-256k** (default), Qwen 3.8, Grok 4.5, or AGY 3.6 | selected programmer lane |
| Review (all shipped work) | Codex Sol night shift | gpt-5.6-sol + xhigh, read-only |
| Nightly review | Codex Sol | dedicated `night-review` profile: sol xhigh |
| Specialist (optional) | Codex Sol / other | `stages.specialist` when high_risk |
| Fallback write | Codex | see claude-codex table |
| Onboard **fast** / docs maintain | Codex **Terra** | `gpt-5.6-terra` + `high` |
| Onboard **deep** (default on full) | Codex **Sol** | `gpt-5.6-sol` + `high` |
| Run visibility wrapper | Claude **Haiku** `run-supervisor` | typed start/watch/status only |
| Diagnostic/reviewer wrappers | Claude **Sonnet** | shell-out only |

## Pipeline stages (`adoc` → Stages tab)

Configured under `stages:` in `.agents/routing.profile.yaml`:

| Stage | Default | Purpose |
|-------|---------|---------|
| `plan_critique` | on · `advisory` · `structural` | Pre-dispatch PLAN/SPEC/task quality; when provider ≠ structural, **invokes** that model and writes PM `decision` |
| `write` | mirrors `main_write` | Daytime implementer |
| `night_review` | from night-shift | Codex review + fix budget |
| `specialist` | off · `high_risk` | Optional read-only domain pass (auth/pay/schema) |

```bash
plan-critique --run-dir .agents/runs/<slug>
# Read decision before dispatch:
#   ship | revise | revise_required  (+ pm_action)
# gate mode after fail:
plan-critique --run-dir ... --ack --note "micro path, thin plan OK"
# structural only (skip LLM):
plan-critique --run-dir ... --structural-only
```

Artifacts: `artifacts/critique.json` (includes `decision`, `pm_action`, `llm_pass`),
`critique.md`. PM **must** honor `revise_required` by editing contracts and
re-running critique before `run-controller` / writers.
`run-validate --phase pre-dispatch` auto-runs critique when the artifact is missing.

## GPT-5.6 Sol / Terra / Luna (Codex)

| Model | Use | Avoid |
|-------|-----|--------|
| **Sol** `gpt-5.6-sol` | Long-horizon multi-file write, high-risk, **review/ship**, emergency | Using for every typo |
| **Terra** `gpt-5.6-terra` | Default **scoped write**, medium features, onboard, docs refresh | Dropping effort to `low` on agent loops |
| **Luna** `gpt-5.6-luna` | Trivia: changelog line, PR one-liner, triage | Multi-step agent write/review (falls apart) |

**Effort** (`writer.reasoning_effort` / adoc Effort): `low` · `medium` · `high` · `xhigh` · `max`.
Independent of model tier. Default for daytime codex writer: **max**.

**Fast mode** (`writer.service_tier` / adoc **Fast mode**): Codex ChatGPT credit
speed boost — **not** the same as Luna and **not** reasoning effort.

| `service_tier` | Effect | Cost (GPT-5.6 ChatGPT credits) |
|----------------|--------|--------------------------------|
| `standard` (default for lanes) | normal latency | 1× |
| `fast` | ~1.5× speed (`features.fast_mode`) | ~2.5× |

```yaml
writer:
  provider: codex
  model: gpt-5.6-luna
  reasoning_effort: max
  service_tier: fast   # or standard
```

CLI: `adoc --apply --writer-provider codex --service-tier fast` ·
`run-controller start … --service-tier fast` · `lane-ctl start … --fast-mode`.
Interactive Codex (`/fast on`) and host `~/.codex/config.toml` do **not** leak
into lane writers (ephemeral bare profile).

## Code routing (full stack)

| Signal | Lane | Model notes |
|--------|------|-------------|
| `risk: low` UI/wiring | **kimi** by default; `qwen`/`grok`/`agy` selectable | Kimi K3-256k (effort via `KIMI_MODEL_THINKING_EFFORT`), Qwen 3.8 max, Grok 4.5 medium, or Gemini 3.6 Flash high |
| `risk: medium` | selected writer → Codex night shift | same receipt chain + gpt-5.6-sol xhigh nightly |
| `risk: high` auth/pay/schema | selected writer solo → Codex night shift | no silent daytime reviewer |
| Selected model/catalog/quota/auth unavailable | persisted retry once, then integrated **Sol high** fallback | same receipts; no daytime review |
| Empty-diff / task/protocol failure | retry once, then block; manual **emergency-writer** only by operator | — |

## Review tiers

| Tier    | Trigger                            | Review |
|---------|-------------------------------------|--------|
| none    | micro path / risk low               | verify field + check-owns-paths only |
| nightly | everything else (medium/high/ship)  | typed Sol xhigh findings; bounded Qwen/AGY/Grok repair; fresh re-review |

There is no daytime LLM review. Historical or explicitly configured
`gate: pre-merge` runs stop for an operator decision instead of silently
starting Codex. Normal review, repair, and fresh re-review run at night.

## Profile `claude-codex` (only Claude + Codex)

Daytime write is still the **conveyor**: `run-supervisor` → process `codex exec`
(lane-writer). Role agents below are for review / onboard / emergency only.

| Stage | Claude role agent | Codex process model | Effort |
|-------|-------------------|---------------------|--------|
| fast_write / main_write | `run-supervisor` (provider=codex) | **luna** (daytime default) | **max** |
| review / ship | `night-reviewer` | **sol** | high (xhigh escalate) |
| onboard (fast) | `project-onboarder` | **terra** | high |
| onboard (deep) | `project-onboarder` | **sol** | high |
| docs-maintain | `docs-maintainer` | **terra** | high |
| emergency_write | `emergency-writer` | **sol** | high (xhigh escalate) |

PM remains **Claude Fable/Opus**. Role wrappers stay **Sonnet/Haiku**.

See `profiles/claude-codex.yaml`, `agents/claude/README.md`.

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

Kimi, Qwen, AGY, and Grok write tasks within the same run use `lane-session` affinity. The
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
| Micro path (score 0–2, low risk, ≤2 files, no `high_risk_paths`) | main checkout, durable controller around one detached **Kimi/Qwen/AGY/Grok** lane, no daytime reviewer |
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
