---
name: drmax-latent-intent
description: "DrMax Latent Intent Analyst v2.2 — static explicit+hidden intents for one query text (human/json/minimal). No SERP, catalog, history, behavior. Use when: скрытый интент, latent intent, разбери запрос, подтекст запроса, intent analyst. SKIP: cocoon/cluster (→drmax-cocoon-engine-x4, TGA M06); SERP (→xmlstock)."
---

# Latent Intent Analyst v2.2

## When

- Один запрос / фраза / title / H1 — нужен разбор **явных + latent** интентов
- До page design / GIST: понять job запроса без подмешивания SERP
- Спор «какой page type нужен» на уровне формулировки

## Protocol

1. Open and apply **1:1**: [ORIGINAL.md](ORIGINAL.md)
2. On first use in session (or `/help`) — print the skill’s help block first
3. Modes: `human` (default) | `json` | `minimal`
4. **Do not** invent SERP, product catalog, session history, or behavioral data — out of scope for v2.2
5. After analysis, if the decision needs ranking proof → hand off to live SERP (`xmlstock` / GSC) + `10-SERP Reality Check` / Search Intent Classifier

## Place in pipeline

```
one query → Latent Intent Analyst → SERP if the page-type claim needs proof
```

Do not run this in the same job as X4 (TGA already has M06).

## Related

- `drmax-cocoon-engine-x4` — cluster / page set
- `seo-drmax-orchestrator` — phase routing
