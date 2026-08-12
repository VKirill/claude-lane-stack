# LLM pack schemas — how to author each file

Audience: `project-onboarder` / Codex. English only.  
Evidence: `path:line` or `// hypothesis`.  
Classifier: [Diátaxis](https://diataxis.fr/) × load (`always`|`on_demand`) — see `docs/llm/TAXONOMY.yaml`.  
**Omit tutorials** in the LLM pack (context bloat).

## Root session files

### CLAUDE.md — diataxis: how-to · load: always
- Canon: Anthropic Claude Code memory + lean ops.
- Must: Purpose, Stack, Commands (real), Don't/Never, Gotchas, Docs → `docs/llm/INDEX.md`.
- Size: ≤150–200 lines body before gitnexus footer.
- Must not: architecture dump, API catalog, tutorials, token tables, ascii repo tree.
- Prefer a short **Where to look** table → MODULE_MAP / API_SURFACE / ARCHITECTURE / FLOWS / RUNBOOK / `.agents/PROGRESS|LESSONS`.  
- Must say: when working under `apps/<name>`, load `apps/<name>/CLAUDE.md` + `apps/<name>/docs/` **first**.

### Per-app pack `apps/<name>/` — how-to + reference · on_demand (monorepo)

Templates: `~/.agents/templates/nested-CLAUDE.md`, `~/.agents/templates/app-pack/` (skeletons only — **fill from code**, never leave template-thin stubs).

**Why:** an agent whose cwd is `apps/api` or `apps/cabinet` must get a **working local passport** from `CLAUDE.md` + `docs/` without depending on root essays. Root `docs/llm/*` stays the monorepo map; app packs are the day-to-day truth for that workspace.

**Quality bar (refuse thin packs):** after reading the app, a coder agent must be able to answer from the local pack alone: what it owns, what it must never do, how to verify, main surfaces, and the critical local flows — with `path:line` evidence.

**Deep / full monorepo — sequential walk (required):**  
For **each** `apps/*` with `package.json` and real source, **one app at a time** (do not batch-generate identical stubs):

1. Explore that app’s entrypoints, route/handler tree, scripts, compose service if any.  
2. Write/update a **filled** local pack:

| Path | Minimum content |
|------|-----------------|
| `CLAUDE.md` | ≤60 lines: What, Owns, Never/Always (evidenced), Verify, Pointers → `./docs/` |
| `docs/INDEX.md` | Load-first list of local files + pointer to root INDEX |
| `docs/ARCHITECTURE.md` | Purpose, entrypoints table, owns/does-not-own, boundaries, verify — **not** a 5-line blurb |
| `docs/GOTCHAS.md` | Table trap/why/instead/evidence; ≥3 real rows when the app has non-trivial runtime |
| `docs/llm/API_SURFACE.yaml` | Surfaces this app owns — see projection rules below |
| `docs/llm/FLOWS.md` | ≥2 local flows with numbered steps + `path:line` (or 1 + why only one) |

3. MODULE_MAP: `docs: apps/<name>/docs/`, `nested_claude: yes`.  
4. Root CLAUDE / INDEX: when under `apps/<name>`, load that pack **first**.

**Surface projection (important):**  
After root `docs/llm/API_SURFACE.yaml` exists, build each app’s surface file by **filtering** root rows whose `path` starts with `apps/<name>/` (plus queue/export rows owned by that app). Then add any missing local-only surfaces found in code.  
- Webhooks: **one row per provider**, never `apple|google|yookassa|…` mega-id.  
- HTTP: real route **families** (`HTTP /v1/generations*`, wallet, users/me, …) — not a single `HTTP /v1/*` / `HTTP /v1/authenticated/*` covering everything.  
- Nuxt/BFF apps: catalog Nitro/`server/api` routes the app owns (group by prefix ok).  
- Worker: queue consumers as `kind: queue` with entrypoint `path:line`.

**Composition roots** (`api`, `worker`, and any app that is the HTTP/webhook/queue hub): local pack must be **usable alone**. If root has ≥10 surfaces under `apps/api/`, the api local file must not have fewer than ~half of those (project them). Thin 5–7 catch-all rows = **fail** Phase 5.

**Skip** only empty stubs; record in `APP_PACKS:`. Do **not** skip because “root maps exist”.

**packages/\*:** default no full pack; optional nested CLAUDE for hard kernels (`domain`, …).

**Refresh:** existing wiki/stub local docs → **rewrite from code**, do not retain.

Report: `APP_PACKS: created=…; updated=…; skipped=… (why per app)`.

### AGENTS.md — how-to · always
- Canon: https://agents.md/
- Must: pointer to CLAUDE and/or ≤1 screen shared build/test/never.
- Must not: paste ARCHITECTURE / MODULE_MAP.

### llms.txt — reference · always
- Canon: https://llmstxt.org/
- Must: H1, blockquote summary, links with short descriptions; no REPLACE_ME.

## docs/llm/* (machine + prose)

### TAXONOMY.yaml — reference · on_demand
Diátaxis label + load + form for every pack path. Keep in sync when files added/removed.

### INDEX.md — reference · always
Curated map. Sections by Diátaxis (reference / explanation / how-to).  
Always-load links: CLAUDE, AGENTS only (plus this INDEX). Point to MODULE_MAP / DOC_LAYOUT under on-demand sections — do not force them into always-load.

### MANIFEST.yaml — reference · on_demand
```yaml
version: 1
project: <name>
refresh: { cadence: weekly, last_full_onboard: YYYY-MM-DD, last_refresh: null, owner_role: docs-maintainer }
pack:
  always_load: [CLAUDE.md, AGENTS.md, docs/llm/INDEX.md]  # lean — no MODULE_MAP / DOC_LAYOUT here
  on_demand: [...]
```
List only existing paths. **Deep refuse** if `always_load` includes `MODULE_MAP.yaml` or `DOC_LAYOUT.md` (session bloat).

### MODULE_MAP.yaml — reference · on_demand
```yaml
modules:
  - id: <short>
    path: <dir|file>
    responsibility: <1 line>
    entrypoints: [<path:line>]
    public_contracts: [<symbol|API>]
    may_import: [<id>]
    must_not_import: [<id>]
    risks: ["… — path"]
    verify: [<cmd>|n/a]
    docs: apps/<name>/docs/    # local pack path when present
    nested_claude: yes|no
```
**Deep coverage (non-toy / monorepo):**
- ≥8 modules with real paths.
- Every `apps/*` workspace that has a `package.json` **or** is named in compose/Docker → module **or** explicit `GAPS:` why skipped (legacy stub ok).
- Isolated runners / egress / agent runtimes (names like `agent-runner`, `agent-egress`, `agent-runtime`) → modules when present.
- Hot shared libs agents touch often (feature-flags, content-scrapers, file-scanner, payment adapters cluster, ui-base) → modules when present.
- Not a per-function catalog. Group many similar payment adapters under one `payments` module if needed.
- After root maps: **sequential per-app pack walk** (see Per-app pack). Root `docs/llm/*` remains the monorepo map; app packs are scoped companions.

### API_SURFACE.yaml — reference · on_demand
```yaml
surfaces:
  - kind: http|rpc|cli|export|webhook|queue
    id: <METHOD /path | cli | export>
    path: <file:line>
    module: <id>
    purpose: <1 line>
    auth: session|api_key|none|unknown
    inputs: []
    outputs: []
    status: active|deprecated|internal
sources: [<openapi.yaml|routes|bin>]
```
**Rules:**
- One file = public capabilities. HTTP route *families* may be grouped (`HTTP /v1/users/*`).
- **Webhooks:** one surface **per provider/path family** (CloudPayments, YooKassa, Apple, Google Play, Kie, …).  
  **Forbidden:** a single catch-all `HTTP /v1/webhooks/*` when multiple providers exist.
- `auth: unknown` only with a one-line reason in `purpose` (or after genuine failed lookup). Prefer `session` / `api_key` / `none`.
- OpenAPI / route-inventory in `sources` when files exist — do not paste full OpenAPI into markdown.

### TEST_INDEX.yaml — reference · on_demand
```yaml
default: <id>|null
tests:
  - id: unit
    command: npm test
    proves: [unit_logic]
    scope: repo
    when: always
    expected: pass
    requires_env: []
```
Fill from package.json / Makefile / CI / pytest. Honest about env-gated suites.

### FLOWS.md — explanation · on_demand
3–7 flows; each step `path:line`.  
If the repo has notification SSE / message queues / bot notify:
- Include a **notification delivery** flow with: Nuxt/cabinet proxy (if any) → API stream handler → queue consumer → bot `/internal/notify` (or equivalent).  
Do not stop at “registers routes”.

### DOC_LAYOUT.md — explanation · on_demand
Table path → diataxis → load → role.

## Architecture / UI / ops

### docs/ARCHITECTURE.md — explanation · on_demand
arc42-lite + C4 ideas + matklad: Purpose, Directory Contracts, Data Flow, Entry Points, External Deps, Key Decisions. No ASCII file tree dump.

### docs/DESIGN.md — reference · on_demand · when has_ui
**Canon:** Google Labs `@google/design.md` — [design-md-standard.md](./design-md-standard.md).  
YAML front matter tokens + body sections in order. Lint: `npx @google/design.md lint docs/DESIGN.md`.  
Extract from code; `// hypothesis` if guessing.

### docs/RUNBOOK.md — how-to · on_demand · when has_deploy
Start/stop, smoke, common failures table, rollback. Evidence from compose/systemd/scripts only.

### docs/TESTING.md / deployment.md — how-to · on_demand
Prose companions to TEST_INDEX / real ship path.

### docs/GOTCHAS.md — explanation · on_demand
Proven traps with `path:line`. Prefer tables (trap / why / instead).

### docs/decisions.md — explanation · on_demand
ADR-light (context / decision / consequences / evidence).  
**Deep full:** write **3–5 ADRs mined from real invariants** (not invented product strategy). Typical sources:
- money order (debit → enqueue → refund)
- raw-body before webhook verify
- shared public-visibility predicates
- isolated agent-runner / egress
- ledger as source of truth / similar accounting SoT  
If the repo truly has no durable decisions, leave `GAPS: decisions empty — …` and keep the template — do **not** invent ADRs.

### docs/SECURITY.md / GLOSSARY.md — on_demand
Evidence only; secret *names* ok, never values.
