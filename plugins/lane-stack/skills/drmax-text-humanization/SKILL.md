---
name: drmax-text-humanization
description: "DrMax TEXT HUMANIZATION v1.6.1 RUNTIME — редакционный слой после GIST: ясность, естественность, decision value без ломки semantic contract и без detector-evasion. Use when: очеловечить текст, humanization, довести черновик, GIST handoff, сделать текст естественнее, editorial rewrite SEO. SKIP: детекция AI (→ai-detect), упрощение под CEFR/ТРКИ (→drmax-lexadapt), создание структуры с нуля (→GIST)."
---

# TEXT HUMANIZATION by DrMax v1.6.1

## When

- После GIST Creation / rewrite: delivery layer only
- Draft is factually approved; need natural professional prose
- **Not** for gaming AI detectors (that is a different, discouraged goal)

## Protocol

1. Load runtime skill **1:1**: [ORIGINAL.md](ORIGINAL.md)
2. Optional help + scenarios:
   - [HELP.md](HELP.md)
   - [SCENARIOS.md](SCENARIOS.md)
3. Prefer `GIST HUMANIZATION HANDOFF` if available
4. Priority: facts → semantic contract → decision architecture → safety → decision value → specificity → clarity → readability → style
5. Do **not** change protected facts, conditions, limits, or unique GIST factors for “smoothness”

## Place in pipeline

```
GIST draft (+ handoff) → Text Humanization → (optional) ai-detect check → publish
```

## Related

- GIST v3.3 in `seo-prompt-engineering-2026`
- `ai-detect` — separate detector pass, not a substitute for humanization
- `drmax-lexadapt` — proficiency-level simplification (different goal)
