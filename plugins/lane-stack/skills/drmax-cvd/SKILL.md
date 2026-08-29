---
name: drmax-cvd
description: "DrMax CVD Content Value Detector v2.3 — оценка заменяемости текста AI-суммаризацией и Ranking Survival Probability (не стиль, не keywords). Use when: заменяемость контента, AI Overview убьёт страницу, replaceability, content value detector, CVD, выживет ли статья в AI search, RSP. SKIP: детекция роботности стиля (→ai-detect), гуманизация (→drmax-text-humanization), создание контента (→GIST в seo-prompt-engineering-2026)."
---

# Content Value Detector v2.3

## When

- Страница/черновик уже есть — вопрос: **останется ли ценность**, если AI Overview отдаст summary
- Приоритизация, какие URL переписывать под non-replaceable value
- Gate перед публикацией programmatic / bulk content

## Protocol

1. Open and apply **1:1**: [ORIGINAL.md](ORIGINAL.md)
2. Require full text T (not title-only). Optional: URL, owned-audience size
3. CVD does **not** score grammar, keywords, or technical SEO
4. Pair with:
   - GIST replaceability test (semantic non-substitutability)
   - `ai-detect` only if style/authorship risk is also in scope
5. Same-Model Risk: if one model does summary + unitization, flag it

## Place in pipeline

```
draft/page → CVD (replaceability/RSP) → if weak: GIST rebuild unique factors
                                      → if style risk: Text Humanization / ai-detect Mode B
```

## Related

- GIST v3.3 (`seo-prompt-engineering-2026`)
- `ai-detect` v3.9.4
- `seo-evidence-based-2026` (contentEffort, AI Overview resilience)
