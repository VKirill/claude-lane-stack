---
name: design-taste
description: "Anti-slop visual review for web UI. Design read, three dials, AI-tell checklist. Adapted from Leonxlnx/taste-skill. Use when: UI слоп, нейрослоп дизайн, taste, иерархия, воздух, Inter, фиолетовый градиент, три карточки. SKIP: DESIGN.md extract (project-design); product code (writer via web-design); Russian copy slop (ru-check)."
argument-hint: "[info]"
license: MIT
---

# Design taste

Lane adapter of [taste-skill](https://github.com/Leonxlnx/taste-skill) (`design-taste-frontend`).
Upstream writes code. **Here it only reviews** unless a writer already has UI `owns_paths`.

## Info (print and stop)

If `$ARGUMENTS` is `info` / `справка`: print the block below **verbatim**, then **stop**.

```text
design-taste — визуальный антислоп. Не код.

1) Design read: kind / audience / vibe / existing brand (одна строка).
2) Три крутилки: VARIANCE / MOTION / DENSITY. Кабинет = низкий variance.
3) Чеклист tells. Канон = DESIGN.md этой поверхности.

Агент: design-lead MODE=audit
Чинить: UI-ран после «делай»
Роутер: /lane-stack:web-design info
```

## Design read (before the checklist)

One line: `Reading this as: <page kind> for <audience>, <vibe>, tokens from <DESIGN.md path>.`

Cabinet / admin / operate UI: do **not** apply landing-page chaos (asymmetric hero, cinematic motion).
Marketing / landing: landing rules below are in play.

If the brief is ambiguous, ask **one** question. Do not guess a new brand.

### Dials

| Surface | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| Marketing / landing (default) | 7–8 | 5–6 | 3–4 |
| Portfolio / editorial | 6–8 | 4–7 | 2–4 |
| Cabinet / admin / operate | 3–4 | 2–3 | 5–7 |
| Trust / a11y-first | 3–4 | 2–3 | 4–5 |

`DESIGN.md` overrides the table.

## Tells (flag, do not auto-restyle off-brand)

- Inter + slate-900 + purple/blue glow gradient as the default look.
- Centered hero + three equal feature cards + icon tile above each heading.
- Nested cards; everything wrapped in a card.
- Pure `#000` / `#fff` with untinted gray text on a colored surface.
- `h-screen` heroes, flex `%` column math, no max-width.
- Lucide-everywhere + rocket/shield clichés (if the app already uses one icon set, keep it).
- Missing hover / focus / empty / error. Wrapped desktop CTA.
- Serif display “because creative” when the brand is sans.

Full redesign audit list: upstream `redesign-existing-projects` — use the same headings (type, color, layout, states) against **this** stack. Do not migrate to React/Tailwind/Motion.

## Who writes

| Role | May do |
|---|---|
| `design-lead` | Don'ts in `DESIGN.md`, audit file. No Vue/CSS. |
| Writer | Fix inside `owns_paths`. Keep tokens. Read `web-design/references/layout.md`. |
| Orchestrator | Screenshot + spawn. No product edit. |

## NEVER

- Invent a second palette or typeface when `DESIGN.md` has them.
- Add next/font, `motion/react`, shadcn, or a new icon package “for taste”.
- Treat dashboards as Awwwards landings.
