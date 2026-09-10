---
name: seo-drmax-orchestrator
description: "SEO harness router for current DrMax: X4 cocoons, BrandCore, Humanization, ai-detect 3.9.4, SignalForge, Latent Intent, Market-Scoped. Phases + artifacts in .agents/seo/, seo-dispatch workers. Use when: SEO проект, оркестратор, паспорт, кокон, контент-конвейер, seo-resume. SKIP: one isolated skill (open that thin skill); paid ads (→ads-specialist)."
---

# SEO DrMax Orchestrator

Chooses **which current skill** to open, where to write, whom to dispatch. Does not replace originals.

## Source of truth

| Layer | Skill / path |
|---|---|
| Module registry | `~/.agents/seo-system/` + `seo-module` |
| Cocoon / IA / GIST 4.3 / Mapper | `drmax-cocoon-engine-x4` |
| Brand SSoT | `drmax-brandcore` |
| Last-mile prose | `drmax-text-humanization` |
| AI-style measure | `ai-detect` v3.9.4 |
| Live URL experiment | `drmax-signalforge` |
| One query | `drmax-latent-intent` |
| Locales | `drmax-market-scoped` |
| Project layout | [references/seo-project-layout.md](references/seo-project-layout.md) |
| Activation | [references/activation-matrix.md](references/activation-matrix.md) |
| Workers | [references/worker-routing.md](references/worker-routing.md) |

Prefer `seo-module scenario <module> <scenario>`, then open the listed **current** original.

Canonical originals: thin skill `ORIGINAL.md` / `originals/`. Do not rewrite.

Do not revive GIST 3.3, book cocoons, CVD, or LexAdapt. Current originals live in the thin DrMax skills.

## Operating principles

1. **Passport first.** Messy brief → onboard collector if needed; claims → BrandCore. No strategy without passport (unless the human skips and gaps are logged).
2. **Minimum chain.** X4 is one system, not 25 book prompts.
3. **Evidence over vibe.** SERP, GSC, Webmaster, Mutagen, Metrika — dated, regional.
4. **Version pin.** System + path + version + model + date on every artifact.
5. **Disk is recovery.** `.agents/seo/` survives the chat.

## Phase machine

```text
0 PASSPORT → 1 DISCOVERY → 2 STRATEGY → 3 TECHNICAL
           → 4 CONTENT → 5 OFFPAGE → 6 MEASURE → (loop)
```

| Phase | Primary | Outputs |
|---|---|---|
| 0 Passport | BrandCore; onboard if brief is messy | `passport/` |
| 1 Discovery | X4 research / Mapper; else Latent Intent (one query) | `discovery/` |
| 2 Strategy | X4 graph + backlog | `strategy/` |
| 3 Technical | Indexation, clutter, CWV, canonical | `technical/` |
| 4 Content | X4 GIST 4.3 → export → Humanization → ai-detect | `content/` |
| 5 Off-page | BrandCore; locales → Market-Scoped | `offpage/` |
| 6 Measure | GSC / GA4 / Metrica; live URL → SignalForge | `measurement/` |

## Hard stop rules

- Missing input → `missing data` + collection plan; do not hallucinate.
- No fresh SERP for page-type claims → hypothesis + date/region.
- Newest official wins for new work.
- YMYL / legal / medical → human gate.
- Do not mix X4 roles. Do not run Latent Intent inside an X4 job.

## Delegation

| Work class | Executor |
|---|---|
| Strategy, diagnosis | `seo-specialist` |
| Full X4 / BrandCore session | This agent, one chat, originals attached |
| Bulk latent-intent / drafts | `seo-dispatch` + CLI |
| SERP / freq | `mutagen` / `xmlstock` |
| Humanization | `drmax-text-humanization` |
| Site code | `dev-orchestrator` |

See [references/worker-routing.md](references/worker-routing.md).

## Project bootstrap

```bash
export PATH="$HOME/.agents/bin:$PATH"
seo-onboard live --slug <project-slug> --url https://example.com --brand "…" --niche "…"
seo-resume .
seo-scan <project-slug> --page https://…/path
seo-run-init <project-slug> <run-slug> --title "..." --phase discovery
seo-board . && seo-handoff-write .
```

## Anti-patterns

- Chat summary of a DrMax prompt as the original
- GIST 3.3 / book cocoon / TGA-only for new work
- Detector-evasion called “humanization”
- Strategy without passport
- Inventing metrics
