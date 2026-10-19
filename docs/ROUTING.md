---
title: Model routing (Fable conductor — solo)
type: component
created: 2026-07-11
updated: 2026-10-19
status: active
confidence: high
tags: [routing, providers, jev]
sources:
  - bin/pipeline_stages.py
  - bin/routing_profile.py
  - plugins/lane-stack/hooks/jev-router.ts
  - plugins/lane-stack/hooks/jev-route-core.ts
  - plugins/lane-stack/fast-jev/src/provider.ts
  - plugins/lane-stack/fast-jev/src/request.ts
  - profiles/opencode/opencode-lane/index.ts
  - board/web/js/router.js
---
# Model routing (Fable conductor — solo)

TL;DR: Routing defaults come from `stages:`; Jev provider selection is credential-aware, while agent-spawn routing classifies eligible lane agents and caches each selected route for later effort updates (`bin/pipeline_stages.py:205-300`, `plugins/lane-stack/hooks/jev-router.ts:90-129`).

## Purpose

Describe the provider, model, and effort decisions used by configured run stages and lane agent hooks (`bin/pipeline_stages.py:205-300`, `plugins/lane-stack/hooks/jev-router.ts:105-129`).

**No GPT-5.5.** Codex model choices in adoc come from the local Codex catalog,
including GPT-6 Astra/Sol/Luna. Existing project model settings are preserved.

Jev request state is bounded to 28,000 estimated tokens. The request builder
repeatedly abridges the longest text fields, retaining head and tail, until the
state fits; this is a request-size bound, not an unbounded full-text transfer
(`plugins/lane-stack/fast-jev/src/request.ts:5-38`, `plugins/lane-stack/fast-jev/src/request.ts:41-46`).
The request body contains the provider model, bounded state, and questions
(`plugins/lane-stack/fast-jev/src/request.ts:60-83`). The OpenCode lane logs
history compaction as off at startup (`profiles/opencode/opencode-lane/index.ts:220-228`).

## Jev provider and agent route

Provider IDs are `openlux` and `typesafe`; a forced `JEV_PROVIDER` with no
matching key returns no route, otherwise OpenLux is selected first when its key
exists and TypeSafe is the next option (`plugins/lane-stack/fast-jev/src/provider.ts:4-30`, `plugins/lane-stack/fast-jev/src/provider.ts:39-67`). The TypeScript provider table sets the OpenLux model to `jev-1.13.0:stable` with 1,500 ms timeout padding, and TypeSafe to `jev-latest` with no padding (`plugins/lane-stack/fast-jev/src/provider.ts:15-29`).

`jev-router` classifies only non-fork lane agent spawns. It removes the raw-task
YAML marker before sending the prompt; missing credentials, timeout, or request
failure returns the default route. A successful route is cached by agent ID and
its effort is applied on later turn steps (`plugins/lane-stack/hooks/jev-router.ts:16-20`, `plugins/lane-stack/hooks/jev-router.ts:61-88`, `plugins/lane-stack/hooks/jev-router.ts:105-129`).

The `board/web/js/router.js` hash parser is separate from model routing: it maps
`#/p/<project>` to the board and recognizes `todos`, `runs`, and `reviews`
sections (`board/web/js/router.js:9-27`).

## Roles (full stack)

| Role | Who | Default model |
|------|-----|----------------|
| Conductor (PM) | Claude **Fable / Opus** (`dev-orchestrator`) | never Sonnet as PM |
| Plan critique | **Structural** + **Jev** (default) or one-shot LLM (Qwen/Codex/Kimi/Grok/AGY/Cursor/OpenCode) → PM `decision` | `stages.plan_critique` in adoc |
| Write (all risks) | **Kimi K3-256k** (default), Qwen 3.8, Grok 4.6/4.5, or AGY 3.6 | selected programmer lane |
| Review (all shipped work) | Codex Sol night shift | gpt-5.6-sol + xhigh, read-only |
| Nightly review | Codex Sol | dedicated `night-review` profile: sol xhigh |
| Specialist (optional) | Codex Sol / other | `stages.specialist` when high_risk |
| Emergency write | Independent adoc selection | `gpt-6-luna` + high + Fast by default |
| Onboard **fast** / docs maintain | Codex **Terra** | `gpt-5.6-terra` + `high` |
| Onboard **deep** (default on full) | Codex **Sol** | `gpt-5.6-sol` + `high` |
| Run visibility wrapper | Claude **Haiku** `run-supervisor` | typed start/watch/status only |
| Diagnostic/reviewer wrappers | Claude **Sonnet** | shell-out only |

## Pipeline stages (`adoc` → Stages tab)

Configured under `stages:` in `.agents/routing.profile.yaml`:

| Stage | Default | Purpose |
|-------|---------|---------|
| `plan_critique` | on · `advisory` · **`jev`** | Structural extracts owns/verify/DAG. **Jev** (`typesafe/jev-1.13` via OpenRouter Decisions) sets `ship/revise/revise_required`, fat-task split, risk on `run.yaml`, and can demote soft warns. Leftover yaml `provider: agy` is remapped to Jev at load (no `adoc` needed). `structural` skips the model. Qwen/Codex/… still work if set explicitly. Night-fix compile, leftover verify class, `run-init --brief`, `jev-intent`, `jev-review` (git diff hunks; accept retries the same session once, then blocks), and `browser-qa` REPORT also call Jev as a typed judge — never as a writer. |
| `write` | mirrors `main_write` | Daytime implementer |
| `night_review` | from night-shift | Codex review + fix budget |
| `specialist` | off · `high_risk` | Optional read-only domain pass (auth/pay/schema) |
| `browser_qa` | on · **`jev`** · `typesafe/jev-1.13` · `chrome-qa` · `auto` | Live browser QA: DOM table → Jev click/type (`browser-qa-jev`). `codex` / `claude` still available |

`browser_qa` provider is `jev` (`browser-qa-jev`: CDP snapshot → Jev Choice → click;
TYPE_TEXT via a small OpenRouter model; DONE checked against Expected), `codex`
(`codex exec` + browser plugins), or `claude` (Haiku + `chrome-devtools` MCP). `backend`
picks which Chrome it drives: `live-chrome` (user's own browser via the Codex Chrome
extension / `chrome-devtools --autoConnect`), `chrome-qa` (dedicated profile from
`chrome-qa start`, port 9333), or `headless`. `approve` is `auto` (`codex exec
--approve-for-me`) or `never` (stop and ask before actions).

```bash
plan-critique --run-dir .agents/runs/<slug>
: 'Read decision before dispatch: ship | revise | revise_required (+ pm_action)'
plan-critique --run-dir ... --ack --note "micro path, thin plan OK"
: 'structural only (skip LLM):'
plan-critique --run-dir ... --structural-only
```

Artifacts: `artifacts/critique.json` (includes `decision`, `pm_action`, `llm_pass`),
`critique.md`. PM **must** honor `revise_required` by editing contracts and
re-running critique before `run-controller` / writers.
`run-validate --phase pre-dispatch` auto-runs critique when the artifact is missing.

## Existing GPT-5.6 profiles (Codex)

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
| `risk: low` UI/wiring | **kimi** by default; `qwen`/`grok`/`agy` selectable | Kimi K3-256k (effort via `KIMI_MODEL_THINKING_EFFORT`), Qwen 3.8 max, Grok 4.6/4.5 effort from `run.yaml` risk (`low`/`medium`/`high`; retry +1 notch, cap `high`; `LANE_JEV_EFFORT=0` keeps profile), or Gemini 3.6 Flash high |
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
| emergency_write | `emergency-writer` | adoc `emergency_writer` (default `gpt-6-luna`) | high, Fast |

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

Kimi, Qwen, AGY, Grok, Cursor, and Codex write tasks within the same run use
`lane-session` affinity. The warmest free conversation is resumed, while concurrent
tasks lease separate slots (five by default, configurable 1–10). Default rotation:
ten successful tasks (`workspace.session_max_tasks` in `routing.profile.yaml`,
adoc Work tab `[` `]` / `,` `.`; `1` = new session every task). Review remains
an independent cold session.
Classified provider availability failures are sanitized in `runtime.json`. The
controller uses a 30-second retry backoff by default, retries eligible tasks, and
can start one Codex fallback only when provider metadata marks the failure
fallback-eligible (`bin/run-controller:1196-1257`, `bin/run-controller:1682-1725`).

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

## How it works

1. Stage defaults are created from the selected write provider and optional night-review provider (`bin/pipeline_stages.py:205-256`).
2. The router checks lane markers and classifies eligible spawned agents with Jev (`plugins/lane-stack/hooks/jev-router.ts:90-113`).
3. Provider selection reads explicit provider and credentials; the default order is OpenLux then TypeSafe (`plugins/lane-stack/fast-jev/src/provider.ts:39-67`).
4. Requests are bounded to the configured token budget by abridging the longest string fields while retaining their head and tail (`plugins/lane-stack/fast-jev/src/request.ts:11-46`).
5. The router caches successful route choice by agent ID and applies its effort on turn steps (`plugins/lane-stack/hooks/jev-router.ts:105-129`).

| Route case | Inputs | Output | Failure behavior |
|---|---|---|---|
| Default stages | Write provider/model/effort and night settings | Full stage map; invalid write provider resolves to Kimi (`bin/pipeline_stages.py:205-256`). |
| Forced Jev provider | `JEV_PROVIDER` and matching API key | Selected OpenLux or TypeSafe route | Missing forced-provider key returns no route (`plugins/lane-stack/fast-jev/src/provider.ts:39-54`). |
| Automatic Jev provider | Available provider keys | OpenLux if keyed, otherwise TypeSafe | No key returns no route (`plugins/lane-stack/fast-jev/src/provider.ts:39-67`). |
| Agent-spawn classifier | Non-fork prompt plus lane marker | Cached subagent model and effort | Missing credentials, timeout, or parse/fetch error uses the current effort and Sonnet default route (`plugins/lane-stack/hooks/jev-router.ts:61-88`, `plugins/lane-stack/hooks/jev-route-core.ts:124-126`). |
| Request state | Arbitrary Jev state and questions | JSON request with bounded state | Longest fields are head/tail abridged until estimated state size fits (`plugins/lane-stack/fast-jev/src/request.ts:11-46`, `plugins/lane-stack/fast-jev/src/request.ts:60-83`). |

## Business rules

- `default_stages` accepts only configured write-stage providers; invalid write provider falls back to Kimi (`bin/pipeline_stages.py:33-50`, `bin/pipeline_stages.py:205-215`).
- A forced Jev provider is not silently replaced when its key is absent (`plugins/lane-stack/fast-jev/src/provider.ts:39-54`).
- AGY effort suffix wins over requested effort; `xhigh` maps to `high` because the CLI accepts low, medium, and high (`bin/routing_profile.py:44-59`).
- Browser hash routes are a separate UI router and map project pages to board, todos, runs, or reviews (`board/web/js/router.js:9-27`).

## Public commands and interfaces

| Interface | Purpose |
|---|---|
| `default_stages(...)` | Construct defaults for plan critique, write, review, specialist, onboarding, memory, docs, and browser QA (`bin/pipeline_stages.py:205-300`). |
| `resolveJevRoute(read)` | Resolve provider key from environment/settings (`plugins/lane-stack/fast-jev/src/provider.ts:57-67`). |
| `register(on, options)` | Register lane agent spawn and turn-step hooks (`plugins/lane-stack/hooks/jev-router.ts:105-129`). |
| `parseRoute(hash)` | Parse Lane Board hash navigation (`board/web/js/router.js:9-20`). |

## Gotchas

- Jev does not receive unlimited text: `boundState` abridges long state fields (`plugins/lane-stack/fast-jev/src/request.ts:11-46`).
- A Jev route error leaves the original spawned model and effort in use (`plugins/lane-stack/hooks/jev-router.ts:61-88`, `plugins/lane-stack/hooks/jev-router.ts:105-113`).
- AGY effort values outside the accepted set normalize to high (`bin/routing_profile.py:47-59`).

<!-- lane-pilot:backlinks -->
## Referenced by

- [docs/BEGINNER.de.md](BEGINNER.de.md)
- [docs/BEGINNER.es.md](BEGINNER.es.md)
- [docs/BEGINNER.fr.md](BEGINNER.fr.md)
- [docs/BEGINNER.ja.md](BEGINNER.ja.md)
- [docs/BEGINNER.ko.md](BEGINNER.ko.md)
- [docs/BEGINNER.md](BEGINNER.md)
- [docs/BEGINNER.pt-BR.md](BEGINNER.pt-BR.md)
- [Beginner guide](BEGINNER.ru.md)
- [docs/BEGINNER.zh-CN.md](BEGINNER.zh-CN.md)
- [docs/SOLO-ORCHESTRATION.md](SOLO-ORCHESTRATION.md)
- [Claude Lane Stack architecture](architecture.md)
- [Claude Lane Stack overview](overview.md)
