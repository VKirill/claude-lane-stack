---
name: site-copy-audience
description: "Fill .agents/copy/ANAMNESIS.md, audience.md, buyer-personas/*.md from templates. StoryBrand, Dunford, Revella. Use when ЦА, персона, оффер, BrandScript. SKIP: headlines only (site-copy-headlines)."
argument-hint: "[info]"
---

# Site copy — audience

Load `copy-project-life` first if `.agents/copy/` is missing.
Templates: `copy-project-life/references/{ANAMNESIS,audience,buyer-persona,voice}.template.md`

Sources (method, not reprints): Miller *StoryBrand 2.0*; Dunford *Obviously Awesome*; Kraus/Revella *Buyer Personas*; Ries/Trout *Positioning*.

## MUST

1. First full analysis (`product:` empty): run `copy-project-life/references/first-interview.md` (2–3 questions per turn) before drafting themes. Then fill files from answers.
2. Fill `ANAMNESIS.md` from what the human already said. Empty `proof.happy_customer_pattern` → do not invent positioning (Dunford skip).
3. Fill `audience.md` in this order:
   - hero want (customer = hero, brand = guide)
   - external / internal / philosophical; they buy **internal**
   - `if_we_vanished` (status quo, not a logo list)
   - feature → so what → 1–4 value themes
   - five rings or `unknown`
   - grunt test (offer / life better / how to buy)
4. One file per persona: `buyer-personas/p1.md` (p2… if they really differ). Story + rings. No “Maria, 34, yoga”.
5. `voice.md` only points at `docs/DESIGN.md` + banned words.

## NEVER

- Fake quotes
- Brand as hero
- H1 before `audience.md` is fillable
