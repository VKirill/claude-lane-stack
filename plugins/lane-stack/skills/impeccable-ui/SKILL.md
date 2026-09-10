---
name: impeccable-ui
description: "Structure/a11y/responsive UI checks and command map. Adapted from pbakaus/impeccable. Use when: impeccable, audit UI, a11y, адаптив, harden, layout, typeset, critique structure. SKIP: visual slop-only (design-taste); DESIGN.md extract (project-design); Vue without a run (writer); PRODUCT.md / hooks."
argument-hint: "[info]"
license: Apache-2.0
---

# Impeccable UI

Lane adapter of [impeccable](https://github.com/pbakaus/impeccable).
Upstream is 23 slash commands + a binary + edit-hooks. **We do not install that.**

Visitor mode (pick from the surface, not the company):

| Mode | Surfaces |
|---|---|
| Persuade | marketing, landing, pricing |
| Operate | cabinet, admin, settings, tools |
| Read | docs, help |
| Experience | portfolio, gallery |

## Info (print and stop)

If `$ARGUMENTS` is `info` / `справка`: print the block below **verbatim**, then **stop**.

```text
impeccable-ui — структура и техника UI. Не хуки и не PRODUCT.md.

Оценка (design-lead, без кода)
- critique / typeset / layout / bolder / quieter / distill
- отчёт + Don'ts в DESIGN.md

Чинить (writer в ране)
- audit / harden / adapt / polish / animate / onboard
- craft-floor: references/craft-floor.md

Чужое
- clarify → copy-lead
- document / extract → project-design
- init / PRODUCT.md / hooks / live → нельзя

Роутер: /lane-stack:web-design info
```

## Command map

| Upstream | Lane |
|---|---|
| `critique` `typeset` `layout` `bolder` `quieter` `distill` | `design-lead` `MODE=audit` |
| `audit` `harden` `adapt` `polish` `animate` `onboard` `colorize` `optimize` | writer run, after «делай» |
| `clarify` | `copy-lead` |
| `document` `extract` `shape` | `project-design` / `page-prototype` |
| `init` `live` `hooks` `doctor` `craft` | **refuse** |

Optional CLI: if `impeccable` is already on `PATH`, `impeccable detect <path>` is allowed as evidence. Do not download the binary, do not enable hooks.

## Audit dimensions (report 0–4 each)

1. Accessibility — contrast, labels, keyboard, headings, `prefers-reduced-motion`.
2. Performance — layout-property animation, lazy images, unused motion.
3. Theming — hardcoded hex vs `DESIGN.md` tokens.
4. Responsive — fixed widths, 44px targets, no horizontal dump on 375px.
5. States — hover/disabled/loading/empty/error actually exist.

Critique (design-lead) is **one pass**. Do not spawn dual sub-agents. If no screenshot: write `DEGRADED: no screenshot` and continue on source.

## NEVER

- `npx impeccable install`, `~/.impeccable`, project `.impeccable/` hooks.
- Write `PRODUCT.md`. Product truth is `CLAUDE.md`.
- Replace `DESIGN.md` via upstream `document`. That is `design-lead` extract.
- Fix Vue from the audit agent.
