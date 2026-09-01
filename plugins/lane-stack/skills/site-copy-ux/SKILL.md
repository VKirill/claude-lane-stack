---
name: site-copy-ux
description: "Fill the UI block of .agents/copy/pages/<slug>.md. Krug scan, Zinsser cut, Nicely Said labels. Use when микрокопи, кнопка, форма. SKIP: long-form pitch (site-copy-headlines); tokens (project-design)."
argument-hint: "[info]"
---

# Site copy — UX

Need `pages/<slug>.md`. Else headlines skill first.
Template section: `## UI (Krug)` in `page-brief.template.md`

Sources: Krug *Don’t Make Me Think*; Zinsser *On Writing Well*; Fenton/Lee *Nicely Said*.

## MUST

1. Billboard: one H1, one primary CTA, one proof. Scan, don’t essay.
2. Trunk test: page name, site name, you-are-here.
3. Button = verb + object they want (`Get the audit`, not `Submit`).
4. Cut clutter: delete the sentence, then the word. No noun stacks.
5. Write strings only under `## UI` in that page file.
6. Skip `status: locked`. Refresh `INDEX.md` after edits.

## NEVER

- Two equal primary CTAs
- “Click here” / “Learn more”
- Puzzle nav
- Color/type decisions (that is DESIGN.md)
- Rewrite `locked`
