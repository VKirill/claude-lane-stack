---
name: drmax-lexadapt
description: "DrMax LexAdapt v1.5 — лексическое упрощение текста под CEFR (EN) / ТРКИ (RU) без внешних словарей. Режимы Audit / Silent / Batch. Use when: упростить текст, CEFR, ТРКИ, A2 B1, readability level, lexadapt, адаптировать под уровень языка. SKIP: SEO-гуманизация (→drmax-text-humanization), AI-детект (→ai-detect), перевод (not this skill)."
---

# LexAdapt v1.5

## When

- Need simpler vocabulary for a target proficiency level
- EN → CEFR A1–C2; RU → ТРКИ levels
- Audit full report, Silent rewrite-only, or Batch ≤10 texts

## Protocol

1. Open and apply **1:1**: [ORIGINAL.md](ORIGINAL.md)
2. User must state mode + target level; default mode = Audit
3. No external lexicon APIs — LLM-only complexity estimate (approximate)
4. Preserve meaning; do not invent SEO keywords under the guise of simplification

## Place in pipeline

```
approved draft → LexAdapt (level target) → optional Humanization for rhythm
```

Usually **after** meaning is locked (GIST / fact check), not before strategy.
