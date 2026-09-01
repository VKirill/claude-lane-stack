---
name: seo-drmax-orchestrator
description: "Оркестратор SEO-методологии DrMax 2026: единый организм discovery→strategy→execution→measurement. Маршрутизирует 25 аналитических промптов книги, prompt-канал (GIST, Assessors, Reddit Mapper, TITAN, Latent Intent, CVD, Humanization, LexAdapt, LinguaForensic 3.9.4), Доказательное SEO (NavBoost/Q*/Twiddlers), артефакты в .agents/seo/, делегирование Claude subagents + CLI (grok/qwen/kimi/deepseek). Use when: SEO проект, SEO стратегия, SEO оркестратор, веди SEO, паспорт проекта, семантический кокон, контент-конвейер SEO, аудит+план, DrMax pipeline. SKIP: один изолированный промпт без оркестрации (→seo-prompt-engineering-2026 или thin skill), pure paid ads (→ads-specialist)."
---

# SEO DrMax Orchestrator

Единая точка управления SEO-работой. **Не заменяет** оригиналы промптов — только выбирает, когда какой открыть, куда сохранить артефакт и кому делегировать.

## Source of truth

| Layer | Skill / path |
|---|---|
| **Module registry (primary routing)** | `~/.agents/seo-system/` + CLI `seo-module` |
| Analytical prompts + corpus | `seo-prompt-engineering-2026` |
| Execution / leak signals | `seo-evidence-based-2026` |
| Copy mechanics | `seo-copywriting` |
| AI detect v3.9.4 | `ai-detect` |
| Latent intent | `drmax-latent-intent` |
| Replaceability | `drmax-cvd` |
| Editorial after GIST | `drmax-text-humanization` |
| CEFR/ТРКИ simplify | `drmax-lexadapt` |
| Project layout | [references/seo-project-layout.md](references/seo-project-layout.md) |
| Prompt activation matrix | [references/activation-matrix.md](references/activation-matrix.md) |
| Worker routing | [references/worker-routing.md](references/worker-routing.md) |

**Always prefer a module scenario over ad-hoc prompt picking:**  
`seo-module scenario <module> <scenario>` then open listed originals.

**Canonical originals never rewritten.** Always open the file under  
`~/.agents/skills/seo-prompt-engineering-2026/references/originals/…`  
(or thin skill `ORIGINAL.md` symlink).

## Operating principles

1. **Passport first.** Unstructured brief → Universal Project Data Collector v2 → Validator & Normalizer. No strategy without passport.
2. **Minimum sufficient chain.** 25 book systems are a library of measurements, not a mandatory conveyor.
3. **Evidence over vibe.** SERP, GSC, Webmaster, Mutagen, Metrika — dated, regional. LLM classifies; does not invent metrics.
4. **Analytical → Execution bridge.** Every discovery insight maps to a leak signal action (`contentEffort`, `NavBoost`, `siteFocusScore`, …).
5. **Version pin.** Log system name + file path + version + model + date in every artifact.
6. **Artifacts on disk.** Chat is disposable; `.agents/seo/` is the recovery surface (like `.agents/runs/` for code).

## Phase machine

```text
0 PASSPORT → 1 DISCOVERY → 2 STRATEGY → 3 TECHNICAL
           → 4 CONTENT → 5 OFFPAGE → 6 MEASURE → (loop)
```

| Phase | Goal | Primary tools | Default outputs under `.agents/seo/<project>/` |
|---|---|---|---|
| 0 Passport | Normalize facts vs assumptions | Collector v2, Validator | `passport/project-passport.md`, `passport/gaps.md` |
| 1 Discovery | Niche, demand, audience, SERP reality | Book 01–25 selective + Intent chain + Latent Intent | `discovery/*` |
| 2 Strategy | Q* vs NavBoost, cocoons, backlog | evidence-based + TITAN OS optional | `strategy/01-strategy.md`, `strategy/backlog.yaml` |
| 3 Technical | Indexation, clutter, CWV, canonical | evidence-based technical caps | `technical/audit.md` |
| 4 Content | Page jobs, GIST, CVD, humanization | GIST 3.3, CVD, Humanization, copy | `content/**` |
| 5 Off-page | Links, listicles, entity, brand | Listicle engine, Entity Footprint | `offpage/**` |
| 6 Measure | Validate hypotheses | GSC, GA4, Metrica, Webmaster | `measurement/**` |

Full activation rules: [references/activation-matrix.md](references/activation-matrix.md).

## Hard stop rules

- Missing required input → return `missing data` + collection plan; do not hallucinate.
- No fresh SERP for intent/page-type claims → mark as hypothesis with date/region.
- Conflicting prompt versions → **newest official** for new work; pin version in artifact.
- YMYL / legal / medical → human gate before publish.
- Do not run full 25-prompt chain for a single meta rewrite.

## Delegation (orchestrator behavior)

You **plan and gate**. Heavy or bulk work goes to workers:

| Work class | Preferred executor |
|---|---|
| Strategy, prioritization, ambiguous diagnosis | Claude (this agent / `seo-specialist`) high effort |
| Single DrMax prompt execution with large context | Claude subagent **or** CLI with full original attached |
| Bulk SERP / frequency / clustering pre-compute | Deterministic scripts + `mutagen` / `xmlstock` |
| Draft generation at scale | CLI: `grok` / `qwen` / `kimi` / `deepseek` with GIST contract |
| Detector / CVD / humanization pass | Dedicated skill + cheaper model if contract is tight |
| Code changes on client site | hand off `dev-orchestrator` with tasks from `runs/` |

See [references/worker-routing.md](references/worker-routing.md).

## Project bootstrap (harness CLI — preferred)

```bash
export PATH="$HOME/.agents/bin:$PATH"

# Prefer onboard (passport + optional first scan) over bare seo-init:
seo-onboard live --slug <project-slug> --url https://example.com --brand "…" --niche "…"
# or: seo-onboard greenfield --slug <project-slug> --brand "…" --niche "…" --geo "…"

seo-resume .
seo-scan <project-slug> --rescan                 # new version of site scan
seo-scan <project-slug> --page https://…/path    # versioned page analysis

seo-run-init <project-slug> <run-slug> --title "..." --phase discovery
seo-task <project-slug> <run-slug> add --title "..." --system "..." --original /abs/path --output path
seo-task <project-slug> <run-slug> accept 001
seo-prompt-log <project-slug> --system "..." --path "..." --artifact path
seo-board . && seo-handoff-write .
```

Docs:

- `~/.agents/docs/seo/SOLO-SEO-ORCHESTRATION.md` — control plane  
- `~/.agents/docs/seo/METHODOLOGY-END-TO-END.md` — books OT→DO + chapter map  
- `~/.agents/docs/seo/SEO-SERVICES-TUI.md` — data providers

Update `STATUS.md` after every phase transition. Promote execution work into  
`.agents/seo/<project-slug>/runs/<slug>/` (PLAN + tasks) when implementable.

## Compatibility with code orchestration

- SEO **strategy/docs** live under `.agents/seo/`
- Site **code implementation** of SEO fixes lives under `.agents/runs/` via `dev-orchestrator`
- Bridge: write `runs/<slug>/tasks/*.yaml` with `owns_paths` for templates/content files, or export `tasks.yaml` for the human to promote

## Anti-patterns

- Using chat summary of a DrMax prompt as if it were the original
- Mixing GIST marker, SERP cluster, and “page” as one object
- Detector-evasion framed as “humanization”
- Strategy without passport
- Link building before content/entity baseline
- Inventing `siteAuthority` numbers

## Related skills (load as needed)

`seo-prompt-engineering-2026`, `seo-evidence-based-2026`, `seo-copywriting`,  
`ai-detect`, `drmax-latent-intent`, `drmax-cvd`, `drmax-text-humanization`, `drmax-lexadapt`,  
`google`, `yandex`, `seo-tools`, `proxy6` (children: `mutagen`, `xmlstock`, `google-search-console`, `google-analytics`, `google-cloud-auth`, `yandex-webmaster`, `yandex-metrica`)
