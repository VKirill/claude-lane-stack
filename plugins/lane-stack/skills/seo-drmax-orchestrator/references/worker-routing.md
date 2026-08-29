# Worker routing — Claude subagents vs CLI models

Orchestrator decides **who** runs a step. Contract always includes: original prompt path, pinned version, inputs paths, output path under `.agents/seo/`, acceptance checks.

## Live config (preferred)

Per-stage systems live in `~/.agents/seo-services/routing.yaml` (edit via **seodoc → Agents / Embed / Cluster** or `seo-routing`).

```bash
seo-routing resolve intent_analysis
seo-dispatch <proj> <run> <task> --stage intent_analysis --original … --output …
# --executor overrides routing when set explicitly
```

| Catalog | Values |
|---|---|
| Writers | `claude-code` `qwen` `kimi` `codex` `cursor` `grok` `deepseek-flash` `deepseek-pro` `deepseek-v4-*` `gpt` **`openrouter`** |
| Transcription | `groq` `codex` |
| Embeddings | `openai` `gemini` `openrouter` (+ model id) |
| Clustering SERP | `xmlstock`\|`xmlriver` × `yandex`\|`google` × TOP 10/20/30 + soft/hard temperature |
| DeepSeek limits | concurrency only: flash **2500**, pro **500** (official) — client uses **100%** of those ceilings (`seo-deepseek limits`) |
| OpenRouter | `seodoc` → Models: filter + assign `system=openrouter` + model id |

**Single settings UI:** `seodoc` (admin). Orchestrator must not invent executors outside `routing.yaml`.

Global `default_system` applies when a stage has no override. Project may override via `.agents/seo/<slug>/routing.yaml`.

### Timeouts (do not kill mid-work)

`~/.agents/seo-services/timeouts.yaml` — each CLI has `soft_sec`, `hard_sec`, `idle_sec`, `kill_policy`.  
Default for agents: `never_while_running` until hard ceiling or idle-after-soft.

## Decision table

| Task shape | Executor | Why |
|---|---|---|
| Ambiguous diagnosis, prioritization, client coaching | Claude `seo-specialist` (main) | Judgment + multi-skill routing |
| One heavy DrMax system (TITAN, full Assessor, long GIST) | Claude subagent with skill preload | Large context, quality |
| Latent intent / CVD / LexAdapt on **many** items | CLI batch (`qwen` / `deepseek` / `kimi`) | Cheap volume; tight JSON schema |
| Article drafts from approved GIST plan | `grok` or `qwen` with GIST contract attached | Throughput |
| Humanization pass | `drmax-text-humanization` on mid-tier model | Editorial, lower stakes than strategy |
| ai-detect full mode | Strong model; Mode B can be separate call | Knockoff needs isolation |
| Mutagen / xmlstock / GSC / GA4 / Webmaster | Main agent Bash+curl via API skills | Deterministic tools |
| SERP harvest for clustering | `seo-serp-save` (+ proxy6 if enabled) | Persist dumps; re-cluster with new temperature |
| Page HTML for agents | `seo-scan` → `snapshot.md` / `seo-html2md` | Fewer tokens than raw HTML |
| Site code / template SEO fixes | `dev-orchestrator` + writer lanes | Owns paths, tests, merge |
| Image/schema only | narrow subagent or script | Isolation |
| Transcription | `groq` or `codex` per routing | Audio/video → text |
| Embeddings (markers / assist) | `openai` or `gemini` per routing | Vector stage only when methodology needs it |

## CLI invocation contract (pattern)

Never: «сделай по DrMax». Always:

1. Attach or `cat` the **original** prompt file into the CLI context.
2. Attach project passport + evidence files (not chat gossip).
3. Specify output schema and path: e.g. `.agents/seo/<p>/content/pages/<slug>/draft.md`
4. Require provenance footer: model, prompt version path, date.
5. Orchestrator validates output before next phase.

Example shape (illustrative):

```bash
# Pseudocode — use the project's actual CLI wrappers
cat ORIGINALS/GIST-v3.3.md PASSPORT.md BRIEF.md | \
  grok --system-from-stdin -o .agents/seo/acme/content/pages/foo/gist-plan.md
```

## Provider preferences (defaults, override per cost)

| Phase | Default |
|---|---|
| Passport / strategy | Claude high |
| Discovery prompts 01–25 selective | Claude or strong CLI |
| SERP/freq harvest | scripts + mutagen/xmlstock |
| Bulk clustering assist | deepseek/qwen |
| Draft writing | grok / qwen |
| CVD + humanization | mid model |
| Detector full | Claude or strong CLI |
| Final gate | Claude |

## Parallelism

- Independent discovery dimensions (e.g. 11 seasonality ∥ 12 geo) may run in parallel.
- Ordered chains (Reddit 0→6, Listicle 00→06, competitor bonus chain) stay serial.
- Content pages in different cocoons may parallelize after strategy lock.

## Failure handling

1. Missing input → pause chain, write `passport/gaps.md`
2. Model refused / truncated → retry once with same original; then escalate model
3. Contradicts SERP evidence → prefer evidence; mark model claim hypothesis
4. Two workers disagree → Claude adjudicates with both artifacts linked
