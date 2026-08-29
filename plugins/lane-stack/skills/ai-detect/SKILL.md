---
name: ai-detect
description: "Детекция и коррекция AI-сгенерированного текста по методике DrMax LinguaForensic v3.9.4 (284 лингвистических признака + 16 структурных маркеров + knockoff + fluency F1–F7 + GEO G0–G5 + adversarial humanization + Programmatic/Affiliate SEO domain + alignment-style proxies). 5 режимов: быстрая детекция, полная детекция, стратегический рерайт, сравнительный анализ, циклический рерайт. Use when: проверь текст на AI, роботность, AI-детект, детекция текста, похоже на нейросеть, гуманизация, очеловечить текст, рерайт под человека, снизить детектируемость, цитируемость в AI Overview, GEO-оптимизация текста, LinguaForensic, knockoff, fluency. SKIP: написание нового текста с нуля без детекта (→seo-copywriting / GIST), SEO-аудит страницы (→seo-evidence-based-2026), типографика (→ru-text), редактура без детекта (→drmax-text-humanization)."
---

# LinguaForensic AI Text Detector v3.9.4

## Protocol

1. Open the **canonical original** and apply it **byte-identically** — do not summarize, translate, or “improve” the skill text:
   - Primary: [references/AI-detect-v-3-9-4-full.md](references/AI-detect-v-3-9-4-full.md)
   - Same file in corpus: `~/.agents/skills/seo-prompt-engineering-2026/references/originals/drmax-prompt-channel/83/AI-detect-v-3-9-4-full.md`
2. Older versions in `references/` (`v3.8.6`, `v3.8.12`, `v3.8.5`, `v3.4`) are **historical only** — use them only to reproduce an old report.
3. Output is probabilistic. Never claim “proved authorship”.
4. For pure editorial naturalness **without** detector optimization → use `drmax-text-humanization` (downstream of GIST).
5. For replaceability / AI Overview survival (not style) → use `drmax-cvd`.

## Version map

| Version | Status | Path |
|---|---|---|
| **3.9.4 full** | **Current for new work** | `references/AI-detect-v-3-9-4-full.md` |
| 3.8.12 | Superseded (prompt-channel post 70) | corpus `.../70/AI-detect-v-3-8-12.md` |
| 3.8.6 | Superseded (previous skill body) | `references/AI-detect-v-3-8-6.md` if present |
| 3.8.5 / 3.4 | Archive | `references/` |

## Related

- `drmax-text-humanization` — editorial layer after GIST (not detector evasion)
- `drmax-cvd` — Content Value Detector / replaceability
- `seo-prompt-engineering-2026` — full DrMax prompt corpus + routing
- `seo-drmax-orchestrator` — when this fits in a full SEO pipeline
