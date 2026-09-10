---
name: drmax-text-humanization
description: "DrMax TEXT HUMANIZATION v1.6.1 RUNTIME — last-mile editorial after X4/GIST export: clarity, naturalness, decision value; no semantic-contract break, no detector-evasion. Use when: очеловечить текст, humanization, довести черновик, GIST handoff, сделать текст естественнее. SKIP: cocoon/IA (→drmax-cocoon-engine-x4); AI-style measure (→ai-detect, not always-on)."
---

# TEXT HUMANIZATION by DrMax v1.6.1

## When

- After X4 `экспорт` or an approved draft: delivery layer only
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
X4 export / approved draft → Text Humanization → ai-detect → publish
```

## Related

- `drmax-cocoon-engine-x4` — structure and GIST 4.3; this skill does not design pages
- `ai-detect` — LinguaForensic 3.9.4 measure after this pass; not a substitute
- `drmax-signalforge` — live-URL experiments, not prose polish
