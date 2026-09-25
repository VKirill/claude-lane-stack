---
name: design-taste
description: "Context-first anti-slop visual review for landing pages, portfolios, and existing web UI. Audits evidence, hierarchy, rhythm, assets, states, and purposeful motion. Adapted from Leonxlnx/taste-skill. Use when: UI слоп, нейрослоп дизайн, taste, иерархия, воздух, Inter, фиолетовый градиент, три карточки. SKIP: DESIGN.md extraction (project-design), gray prototypes (page-prototype), product code (writer via web-design), Russian copy (ru-check)."
argument-hint: "[info]"
license: MIT
---

# Design taste

Lane adapter of [taste-skill](https://github.com/Leonxlnx/taste-skill). It reviews
landing pages, portfolios, and redesigns, and guides isolated branded mockups.
It does not write product UI, and it
does not turn cabinets, admin screens, or data tables into landing pages.

## Info (print and stop)

If `$ARGUMENTS` is `info` / `справка`, print this block verbatim, then stop:

```text
design-taste — визуальный аудит и направление для изолированного макета.

1) Design read: kind / audience / job / vibe / evidence from the brief, screen and DESIGN.md.
2) Three dials: DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY. Existing tokens win.
3) Evidence audit: type, color, layout/rhythm, assets, states, motion, a11y.
4) Preflight: every finding has evidence, impact and an owner.

Агент: design-lead MODE=audit или MODE=mockup
Чинить: UI-ран после «делай»
Роутер: /lane-stack:web-design info
```

## Design read (before the checklist)

Read the brief, requested route or screenshot, relevant `DESIGN.md`, current
components, and the project's stack before judging taste. Identify:

- page kind and user job (landing, portfolio, editorial, redesign, cabinet);
- audience, references, vibe, brand assets, tokens, and existing component language;
- accessibility, responsive, performance, and product constraints.

Write one line: `Reading this as: <kind> for <audience>, serving <job>, with a
<vibe> language, using evidence from <paths/screenshots>.`

For an existing UI, describe what is already true before proposing change.
Preserve information architecture, working accessibility patterns, and the
project's brand unless the brief asks for a change. If evidence is missing,
write `DEGRADED: <missing evidence>` and make the smallest safe recommendation.
Ask one question only when two plausible design reads would lead to different work.

### Three dials

Use the existing `DESIGN.md` reading when it exists. Otherwise choose a starting
range from the brief; these are review dials, not quotas:

| Surface | VARIANCE | MOTION | DENSITY |
|---|---:|---:|---:|
| Marketing / landing | 7–8 | 5–6 | 3–4 |
| Portfolio / editorial | 6–8 | 4–7 | 2–4 |
| Cabinet / admin / operate | 3–4 | 2–3 | 5–7 |
| Trust / a11y-first | 3–4 | 2–3 | 4–5 |

Low variance favors a stable grid; high variance can justify asymmetry only when
it helps the page job. Motion and density must follow the same reading.

## Evidence audit

Report findings as `finding → evidence (path, line, screenshot, or observed
state) → impact → recommendation → owner`. Classify by consequence: blocker
(primary task cannot be completed), major (material usability/accessibility
barrier), or minor (polish). Do not call a pattern
slop merely because it is common; explain why it fails this page's job.

Review these headings:

- **Type:** role hierarchy, readable measure, line-height, weight contrast, tracking,
  number alignment, wrapping, and whether the existing typeface fits the brand.
- **Color and surfaces:** one coherent palette, contrast, surface hierarchy,
  border/shadow logic, and consistent lighting. Inter is valid when the brand or
  product already uses it; do not swap fonts for novelty.
- **Layout and rhythm:** container, alignment, grid, responsive changes, section
  pacing, baseline alignment, and a spacing scale that comes from the project
  tokens. Use cards only when elevation communicates hierarchy.
- **Assets and content:** real project assets first, correct aspect ratios and
  crops, meaningful alt text, and no fake screenshots or decorative assets that
  compete with the job. Record an asset gap instead of inventing a replacement.
- **States:** hover, focus-visible, active, disabled, loading, empty, error, and
  current navigation state where the surface needs them. Check keyboard behavior.
- **Motion:** every animation must communicate hierarchy, storytelling, feedback,
  or a state change. Match the motion dial, use the project's existing tools, and
  provide a `prefers-reduced-motion` path. If the reason cannot be stated in one
  sentence, remove the animation.

## Tells (flag, do not auto-restyle off-brand)

- Inter + slate-900 + purple/blue glow gradient as a default without brand evidence.
- Centered hero + three equal feature cards + icon tile above every heading.
- Nested cards, everything wrapped in a card, or equal-height cards without a job.
- Pure `#000` / `#fff` with untinted gray text on a colored surface.
- `h-screen` heroes, flex percentage math, no max-width, or a broken mobile crop.
- A new font, icon family, animation library, or design system added for taste.
- Missing hover / focus / empty / error / loading states, wrapped desktop CTA, or
  placeholder copy and imagery presented as finished content.

Do not copy arbitrary font bans, palette hex lists, word or cell-count quotas,
GSAP skeletons, or upstream framework defaults. Follow this project's stack,
tokens, accessibility baseline, and existing icon family.

## Practical preflight

Before handing off an audit, confirm:

- the design read and dial choice are supported by the brief or observed UI;
- each high-priority finding has concrete evidence and a named owner;
- type, palette, spacing rhythm, assets, and surfaces form one coherent system;
- interactive states and responsive behavior cover the important user path;
- motion is purposeful, does not cause layout shift, and honors reduced motion;
- recommendations fit existing `DESIGN.md` and the project's framework.

Gray page composition belongs to `page-prototype` and ignores this skill's
palette guidance. Design-lead may write audit findings and `DESIGN.md` Don'ts,
or make an isolated branded static mockup under `.agents/prototypes/` without
touching product files; a writer changes product files only inside its
`owns_paths`. The orchestrator supplies screenshots and routes the work.

## NEVER

- Invent a second palette or typeface when `DESIGN.md` has one.
- Add `next/font`, `motion/react`, shadcn, GSAP, or a new icon package “for taste”.
- Treat dashboards, admin, or operate UI as Awwwards landings.
- Use a missing screenshot as permission to invent a visual direction.
