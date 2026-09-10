---
name: drmax-brandcore
description: "DrMax BrandCore v0.8 + Navigator v1.1.4 — company SSoT for LLM content (claims, facts, products, legal). Use when: BrandCore, брендкор, паспорт бренда, источник правды о компании, claims, что можно писать о фирме. SKIP: cocoon/IA (→drmax-cocoon-engine-x4); locales split (→drmax-market-scoped); page experiment (→drmax-signalforge)."
---

# BrandCore + Navigator

Not part of Cocoon Engine X4. Fill once per project; attach the **filled** file to later generation.

## When

- New project needs a company truth file
- Generation must not invent claims, prices, legal, metrics
- Update / migrate an existing BRANDCORE.md

## Protocol

1. Read [START.md](START.md), then both originals **1:1**:
   - [ORIGINAL.md](ORIGINAL.md) — BRANDCORE.md v0.8 (what)
   - [NAVIGATOR.md](NAVIGATOR.md) — BrandCore Navigator v1.1.4 (how)
2. Navigator leads the dialogue. BRANDCORE.md wins on structure, status scale, BLOCKING fields.
3. Never mark a field `подтверждено` without an explicit human yes.
4. Never invent legal, numbers, claims, licenses, names, palette.
5. Write the filled file under `.agents/seo/<slug>/passport/BRANDCORE.md` (or the path the user names).
6. After fill: later content jobs attach that file; do not reload Navigator unless updating.

## Place in pipeline

```
brief / site → BrandCore fill → attach filled file
→ X4 / SignalForge / Humanization (facts from BrandCore only)
```
