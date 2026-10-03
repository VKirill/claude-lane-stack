---
name: copy-project-life
description: "Карта файлов копирайта в .agents/copy/: шаблоны, статусы, цепочка audience→headlines→ux. Use when seeding or navigating that folder. SKIP: writing copy in chat (copywriter); SEO-ключи; код и DESIGN.md."
argument-hint: "[info]"
---

# Copy project life

Templates live next to this file: `references/*.template.md`.
Copy them onto disk. Do not invent a second layout.

## Info

If `$ARGUMENTS` is exactly `info`, print `references/info.md` verbatim (Russian), then stop.

## MUST — seed + first interview

1. `mkdir -p .agents/copy/buyer-personas .agents/copy/pages .agents/copy/research/inbox .agents/copy/research/used .agents/copy/research/dead`
2. If a file is missing, copy the matching template from this skill’s `references/`:

| Disk | Template |
|---|---|
| `INDEX.md` | `INDEX.template.md` |
| `ANAMNESIS.md` | `ANAMNESIS.template.md` |
| `audience.md` | `audience.template.md` |
| `buyer-personas/p1.md` | `buyer-persona.template.md` |
| `voice.md` | `voice.template.md` |
| `pages/<slug>.md` | `page-brief.template.md` |

Move leftover dumps out of the research root (once):

```bash
d=.agents/copy/research
mkdir -p "$d/inbox"
for f in web.md web.json x.md deep.md deep.json deep-job.json; do
  [ -f "$d/$f" ] && mv "$d/$f" "$d/inbox/$(date +%F)-$f"
done
```

3. First full analysis: `product:` empty **or** no `.agents/copy/` → load `references/first-interview.md`. Ask 2–3 questions per turn. Write answers after each batch. Do not re-ask what the site/passport already answers.
4. Fill only known fields. Unknown stays `unknown`.
5. After offer + audience are fillable: `site-copy-audience`. If the human asked full analysis: then headlines → ux. Wireframe only if they asked: `page-prototype`. Russian sentences: `ru-text` (typography silent). «вычитай» → `ru-check`. «оцени» → `ru-score`. Chat Russian. Keys English.
6. After any status change: update `INDEX.md` and `updated:`. Do not rewrite `locked`.

## NEVER

- Invent buyer quotes
- Edit product Vue/CSS (`.agents/prototypes/` gray HTML is OK)
- Start a run
- Rewrite a `locked` file
- Append research into one `web.md`
