# SEO Admin TUI (`seodoc`)

> **Default UI: Textual** (`seodoc`) — mouse, tabs, DataTables.  
> Legacy prompt_toolkit: `seodoc --legacy`. Package: `bin/seo_crm/`.


**Единая админка** SEO-оркестрации: сайдбар слева, рабочая зона справа, RU/EN, проектные артефакты, пайплайны агентов, jobs с таймаутами, OpenRouter/DeepSeek.

`seo-specialist` (Claude Code) **делегирует workers только по настройкам из seodoc** (`routing.yaml` + providers + models).

## Launch

```bash
export PATH="$HOME/.agents/bin:$PATH"
seodoc                    # admin TUI
seo-services              # same
seo-services status       # CLI providers table
seo-services test all
```

## Layout (full-width CRM)

Fullscreen terminal app (`prompt_toolkit`): header · **sidebar** · **workspace** · footer.
Widgets are real form controls (not paint-only): **TextArea** inputs, **RadioList** selects, **Buttons**.

```text
┌─ SEO CRM · seodoc │ project │ URL │ RU/EN │ repo ──────────────────────┐
├─ Navigation ──┬─ Workspace (full remaining width) ────────────────────┤
│ 📊 Dashboard  │  [fields] [dropdowns] [tables] [action buttons]       │
│ 📁 Project    │                                                        │
│ 🗺 Sitemap    │                                                        │
│ 📰 Articles   │  list | preview | generate form                        │
│ …             │                                                        │
├───────────────┴────────────────────────────────────────────────────────┤
│ status message │ Tab field │ Esc sidebar │ F5 │ C-s save │ L │ q      │
└────────────────────────────────────────────────────────────────────────┘
```

### Focus model (important)

| Key | Behavior |
|---|---|
| **↑↓** on sidebar | change section |
| **Enter** on sidebar | open section and **focus first control in workspace** |
| **Tab / Shift-Tab** | next / previous focusable field (inputs, lists, buttons) |
| **Enter** on Button / RadioList | activate / select |
| **Esc** | return focus to sidebar |
| **F5** | refresh all project data |
| **Ctrl-S** | save session + routing.yaml |
| **L** | RU ↔ EN |
| **q** / **Ctrl-Q** | quit (session saved) |

Mouse supported for buttons/lists when terminal allows.

### Sections (CRM modules)

**Work sidebar** (only operational tabs):

| Sidebar | Workspace |
|---|---|
| **Dashboard** | KPI + quick buttons |
| **Project** | repo / slug / URL · Scan · Onboard |
| **Sitemap / Meta** | scan tables |
| **Articles** | list + preview + generate form |
| **Cocoons / Semantics / SERP** | artifacts + cluster temps |
| **Pipelines / Jobs** | run scenarios · live logs |
| **Settings** | **all configuration** (sub-tabs inside) |

**Settings hub** (sub-tabs, not top-level):

| Sub-tab | Content |
|---|---|
| General | lang, repo, session paths |
| Providers | API keys (OpenRouter, DeepSeek, DataForSEO, …) |
| Proxy6 | pool + use_proxy |
| Agents | per-stage system/model |
| Models | OpenRouter catalog + assign |
| Timeouts | CLI soft/hard/idle policy |
| Help | keyboard + architecture |

Package layout (maintainable): `bin/seo_admin/` — `nav`, `forms`, `data`, `actions`, `views_work`, `views_settings`, `crm` (each ≪ 400 lines).

### Articles generation flow

1. Project → set slug + URL · Apply  
2. Articles → fill **Slug** + **Topic** (textarea)  
3. Pick agents (RadioList) for GIST / Draft / Quality  
4. Optional OpenRouter model (fuzzy complete after Models refresh)  
5. **Generate pipeline** → writes `content/pages/<slug>/brief.md` and starts job chain GIST→draft→humanize→meta  
6. Jobs → live log; Articles list refreshes when files appear

Session: `~/.agents/seo-services/tui-session.yaml`

---

## Providers

| ID | Group | What |
|---|---|---|
| `xmlstock` | SERP | Yandex XML / Live + Google SERP |
| `xmlriver` | SERP | Yandex + Google SERP |
| `mutagen` | Keywords | Wordstat freq, competition, SERP reports |
| **`dataforseo`** | All-in-one | SERP, keywords, backlinks, on-page, labs, … |
| **`proxy6`** | Proxy | [px6.net](https://px6.net/ru/developers) — only API key; pool for fetch/SERP |
| **`openrouter`** | LLM | API key → load all models; assign per stage |
| **`deepseek`** | LLM | Official API; concurrency flash=2500 / pro=500 (no RPM) |
| `yandex_oauth` | Yandex | Shared OAuth app + token |
| `yandex_webmaster` | Yandex | Indexation, queries, recrawl |
| `yandex_metrica` | Yandex | Counters / reports |
| `gsc` | Google | Search Console (service account JSON) |
| `ga4` | Google | Analytics 4 (service account JSON) |

### Where secrets live

| Path | Content |
|---|---|
| `~/secrets/xmlstock.env` | `XMLSTOCK_USER`, `XMLSTOCK_KEY` |
| `~/secrets/xmlriver.env` | `XMLRIVER_USER`, `XMLRIVER_KEY` |
| `~/secrets/mutagen.env` | `MUTAGEN_API_KEY` |
| `~/secrets/dataforseo.env` | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |
| `~/secrets/proxy6.env` | `PROXY6_API_KEY` |
| `~/secrets/yandex-oauth.env` | client + token |
| `~/secrets/yandex-webmaster.env` | token + host (legacy shared) |
| `~/secrets/yandex-metrica.env` | token + counter |
| `~/secrets/gsc.env` | path to SA JSON + site |
| `~/secrets/ga4.env` | path to SA JSON + property |
| `~/secrets/seo-tools.env` | **unified export** (all merged) |

Files are `chmod 600`. Never commit.

Non-secret registry: `~/.agents/seo-services/providers.yaml`  
Routing: `~/.agents/seo-services/routing.yaml`  
Project opt-in: `.agents/seo/services.yaml`  
Project routing override: `.agents/seo/<slug>/routing.yaml`

---

## Proxy6 / px6.net

Docs: https://px6.net/ru/developers · API base `https://px6.link/api/{key}/{method}/`

1. Providers → **Proxy6** → paste API key → `s` save → `e` enable → `t` test  
2. **Proxy** tab → `r` refresh pool (`getproxy`) → list of `ip:port`  
3. `f` toggle `fetch.use_proxy` · Cluster tab has own `use_proxy` for SERP  
4. Cache: `~/.agents/seo-services/proxy6-pool.json` (≈1h)

Used by: `seo-scan` fetch, `seo-serp-save` (when clustering.use_proxy), any code calling `seo_proxy_lib.fetch_url`.

---

## Agent routing (per stage)

File: `~/.agents/seo-services/routing.yaml`

| Stage | Typical use |
|---|---|
| `default_system` | fallback for all stages without override |
| `deep_research` | heavy research |
| `discovery` | prompts 01–25 / niche |
| `intent_analysis` | latent intent / bulk intent |
| `strategy` | Q* / NavBoost / TITAN |
| `technical` | technical audit |
| `content_gist` | GIST plan / draft |
| `content_quality` | CVD / humanization / assessor |
| `brand_entity` | entity / SERM |
| `offpage` | links / listicle |
| `measurement` | GSC / Metrika interpretation |
| `clustering` | LLM clustering layer after SERP |
| `transcription` | **groq** \| **codex** only |
| `embeddings` | **openai** \| **gemini** (+ model) |

### Writer systems understood by harness

`claude-code` · `qwen` · `kimi` · `codex` · `cursor` · `grok` · `deepseek-flash` · `deepseek-pro` · `deepseek-v4-flash` · `deepseek-v4-pro` · `gpt` · **`openrouter`** (+ model id)

### OpenRouter

1. Providers → **OpenRouter** → API key → `s` save → `t` test  
2. **Models** → `r` load catalog → `/` filter → Enter assigns `system=openrouter` + model to current assign-stage (`a` cycles stage)

### DeepSeek rate limits (official)

Source: https://api-docs.deepseek.com/quick_start/rate_limit/

| Model | Concurrency (account) |
|---|---|
| deepseek-v4-flash | **2500** |
| deepseek-v4-pro | **500** |

No published RPM/TPM caps. **Client defaults = 100% of official concurrency** (flash **2500**, pro **500** in-flight). Override only if you need lower caps: `routing.yaml` → `deepseek.max_parallel_*`. Keep-alive may hold connection up to **10 minutes** before inference — timeouts treat this as normal (`deepseek-api` / `agent-worker` = `never_while_running`).

```bash
seo-deepseek limits          # official + client caps
seo-deepseek chat --model deepseek-flash --prompt "ping"
```

### CLI timeouts

`~/.agents/seo-services/timeouts.yaml` (seeded on install).  
Policy `never_while_running`: do **not** kill a working agent/CLI before `hard_sec` unless idle past `idle_sec` after soft.

### Pipelines

Built-ins: intent→GIST→draft · quality gate · discovery soft/hard · live-rescan · openrouter intent bulk.  
Enter runs a **job**; progress on **Jobs** tab with live log tail.

CLI:

```bash
seo-routing show
seo-routing set-default claude-code
seo-routing set-stage intent_analysis deepseek-flash
seo-routing set-stage embeddings openai --model text-embedding-3-small
seo-routing resolve deep_research
seo-dispatch <proj> <run> <task> --stage intent_analysis --original … --output …
```

TUI: **Agents** tab → ↑↓ stage → Enter pick system → `d` promote stage system to global default → `S` save.

---

## Clustering / SERP

TUI **Cluster** tab or:

```bash
seo-routing set-cluster --provider xmlstock --engine yandex --top 10 --temperature 0.2
seo-serp-save acme --query "…" --queries-file queries.txt
```

| Field | Values |
|---|---|
| serp_provider | `xmlstock` \| `xmlriver` |
| engine | `yandex` \| `google` |
| top_n | `10` \| `20` \| `30` |
| temperature | `0.0`–`1.0` for **LLM** clustering after SERP is saved |
| save_serp | keep dumps under project |
| use_proxy | fetch SERP via proxy6 |

### SERP artifacts (project)

```text
.agents/seo/<slug>/evidence/serp/<engine>-top<N>-<ts>/
  <query>.raw
  manifest.json          # provider, engine, top_n, temperature_default, queries
.agents/seo/<slug>/evidence/serp/LATEST   # dir name pointer
```

Change temperature later without re-fetch:

```bash
seo-routing set-cluster --temperature 0.4
# re-run clustering stage on evidence/serp/LATEST
```

---

## Embeddings

When DrMax-style pipelines need vectors (markers / assist clustering):

- system: `openai` or `gemini`
- model e.g. `text-embedding-3-small` / Gemini embedding id

TUI **Embed** → Enter pick system · `m` edit model · `S` save.

---

## HTML → Markdown (token saving)

```bash
seo-html2md page.html -o page.md
cat page.html | seo-html2md -
```

`seo-scan` automatically writes `snapshot.md` next to `snapshot.html`.  
Agents must prefer markdown (+ `analysis.md`) over raw HTML.

---

## Providers tab keys (legacy)

| Key | Action |
|---|---|
| ↑↓ | Select provider / field |
| Enter | Edit field value |
| e | Enable / disable |
| s | Save secrets to disk |
| t | Test selected |
| a | Test all enabled |
| T | Test all |
| u | Export unified `seo-tools.env` |
| p | Wire project `services.yaml` (CLI) |
| Tab / 1–8 | Tabs |
| q | Quit |

## CLI recipes

```bash
# DataForSEO
seo-services set dataforseo \
  DATAFORSEO_LOGIN='you@example.com' \
  DATAFORSEO_PASSWORD='api-password'
seo-services enable dataforseo
seo-services test dataforseo

# Proxy6
seo-services set proxy6 PROXY6_API_KEY='…'
seo-services test proxy6

# XMLStock
seo-services set xmlstock XMLSTOCK_USER=123 XMLSTOCK_KEY=...
seo-services test xmlstock

# Export for agents
seo-services export
# → source ~/secrets/seo-tools.env
```

## DataForSEO official MCP (integrated)

Package: [`dataforseo-mcp-server`](https://github.com/dataforseo/mcp-server-typescript)  
Install: `~/.agents/mcp/dataforseo-mcp-server`  
Launcher: `seo-dataforseo-mcp`  
Claude registration: MCP server name **`dataforseo`**

1. `seodoc` → DataForSEO → login + API password → **s** save → **e** enable → **t** test  
2. `seo-services export` (optional)  
3. Restart Claude / `ccs` so MCP starts with fresh env  

| TUI / secrets file | Official MCP |
|---|---|
| `DATAFORSEO_LOGIN` | `DATAFORSEO_USERNAME` |
| `DATAFORSEO_PASSWORD` | `DATAFORSEO_PASSWORD` |
| `ENABLED_MODULES` | `ENABLED_MODULES` |

## Agent integration

`seo-specialist` should:

1. Prefer enabled providers from `~/.agents/seo-services/providers.yaml` or project `services.yaml`
2. Resolve worker via `seo-routing resolve <stage>` or `seo-dispatch --stage`
3. Prefer `snapshot.md` and SERP dumps over raw HTML
4. If credentials missing → tell human to run `seodoc`
