# Module: html-markdown

## Purpose
Детерминированный HTML → Markdown: меньше токенов агентам при анализе контента/SERP-страниц.

## CLI

```bash
seo-html2md page.html                 # → page.md
seo-html2md page.html -o out.md
seo-html2md - --stdout < page.html    # stdin
cat page.html | seo-html2md -
```

## Auto on scan
`seo-scan` writes both:
- `snapshot.html` (raw, truncated)
- `snapshot.md` (markdown via `seo_html2md.html_to_markdown`)

Agents **must prefer** `snapshot.md` + `analysis.md` over raw HTML.

## Implementation
- Prefer `html2text` if installed
- Pure `HTMLParser` fallback otherwise (no network, deterministic)

## Routing flag
`routing.fetch.html_to_markdown: true` (default) — documents intent; scan always produces md when conversion succeeds.
