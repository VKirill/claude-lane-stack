---
name: drmax-latent-intent
description: "DrMax Latent Intent Analyst v2.2 — статический разбор явных и скрытых интентов одного текстового запроса (human/json/minimal). Без SERP, каталога, истории и поведения. Use when: скрытый интент, latent intent, разбери запрос, подтекст запроса, что реально хочет пользователь по фразе, intent analyst. SKIP: кластеризация семантики (→Search Demand Mapper + Intent Classifier в seo-prompt-engineering-2026), SERP-проверка (→xmlstock + SERP Reality Check), полный SEO-аудит (→seo-specialist)."
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
query → Latent Intent Analyst → (optional) Search Intent Classifier + SERP
      → GIST marker / page job → content
```

## Related

- `seo-prompt-engineering-2026` (03 Search Demand Mapper, Intent Classifier, Query Modifier)
- `seo-drmax-orchestrator` (phase routing)
