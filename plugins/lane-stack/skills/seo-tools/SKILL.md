---
name: seo-tools
description: "[RU: SEO-инструментарий] Роутер платных SEO-API: Mutagen (Wordstat, конкуренция, биды) и xmlstock (SERP XML Яндекс/Google). SKILL.md не содержит API — читает дочерний SKILL.md. Use when: seo tools, частотность, вордстат, wordstat, позиции сайта, парсинг выдачи, mutagen, xmlstock, /seo-tools. SKIP: Вебмастер/GSC своего сайта→yandex/google; SEO-копирайтинг→seo-copywriting; стратегия→seo-evidence-based-2026; Ahrefs/Semrush."
stacks:
  - seo
  - ru-seo
tags:
  - seo
  - dispatcher
  - mutagen
  - xmlstock
  - ru
source: vechkasov-global-skills
risk: high-stakes
---

# SEO tools

This `SKILL.md` is a **router**. Tool knowledge lives in the child folders. Do not answer APIs from this file.

Inventory is two tools now. To add a third: drop a folder next to `mutagen/` / `xmlstock/` and add one row to the tables below.

## Protocol

1. Match the task to the route table.
2. **Read** that child's `SKILL.md`.
3. Load only that child's `references/` named in its API Reference table.
4. Two tools → read both. Do not merge their APIs, keys, or billing.

## Use this skill when

- Частотность / Wordstat / конкуренция фразы / биды Директа
- Позиции в выдаче Яндекса или Google по списку ключей
- Парсинг SERP / сниппетов / `site:` индексация через XML
- Slash command `/seo-tools`

## Do not use this skill when

- Поисковые запросы **своего** сайта → `yandex` (Вебмастер) или `google` (Search Console)
- Написать SEO-текст → `seo-copywriting`
- SEO-стратегия / кокон → `seo-evidence-based-2026`
- Key Collector desktop, Ahrefs, Semrush, официальный Wordstat API — **нет скилла**
- Свой скрапер SERP через прокси → `proxy6`

## Route table

| Task | Child |
|---|---|
| Точная частотность, `strong`, биды Direct, Wordstat колонки, кластеризация | [mutagen/SKILL.md](mutagen/SKILL.md) |
| Живая выдача, позиции, сниппеты, `site:`, картинки/видео, Яндекс XML / Google XML | [xmlstock/SKILL.md](xmlstock/SKILL.md) |

`mutagen.serp.report` — отчёты Mutagen по своей базе, **не** живой XML. Живой SERP → `xmlstock`.

## Ambiguous prompts

| User says | Default | Not this |
|---|---|---|
| «частотность» / Wordstat / «сколько ищут» | `mutagen` | xmlstock не считает частотность |
| «конкуренция ключа» / `strong` / биды | `mutagen` | Direct API → `yandex` |
| «позиции по ключам» / ТОП-10 / сниппеты | `xmlstock` | Mutagen SERP-отчёт — другая база |
| «позиции **моего** сайта в Вебмастере/GSC» | `yandex` / `google` | xmlstock = произвольный SERP |
| «проиндексирован ли URL» через `site:` | `xmlstock` | переобход → Webmaster/GSC |
| «семантика + позиции» | `mutagen` → `xmlstock` | не одним API |

If still unclear — one question, then route.

## Cross-product

| Situation | Load in order |
|---|---|
| Собрать ядро, потом снять позиции | `mutagen` → `xmlstock` |
| Частотность + запросы **этого** сайта | `mutagen` + `yandex` (webmaster) |
| Позиции Google + GSC своего домена | `xmlstock` + `google` (search-console) |

## Money

Both tools **charge per call**. Read the child's billing rules before any batch.

| Tool | Wallet |
|---|---|
| `mutagen` | `mutagen.balance()`; persist `task_id` / `mass_id` — repeat `*.new` double-charges |
| `xmlstock` | ЛК / error 200; persist `req_id` — repeat `delayed=1` double-charges |

Do not share API keys or one HTTP client across the two.

## Behavioral Traits

- Picks **one** child before curl
- Reads that child's SKILL.md; does not quote endpoints from this file
- Checks balance / quota **before** a paid batch
- Names the child folder in the answer

## Important Constraints

- NEVER invent Mutagen methods or xmlstock error codes in this dispatcher
- NEVER mix Mutagen `serp.report` with xmlstock live SERP
- NEVER resubmit a paid job without checking persisted `task_id` / `req_id`
- ALWAYS Read the child before the first paid call
- ALWAYS say «нет скилла» for Ahrefs / Semrush / Key Collector / official Wordstat API

## Related Skills

- `yandex` — Вебмастер (запросы **своего** сайта), Direct
- `google` — Search Console (запросы **своего** сайта)
- `proxy6` — свой скрапинг SERP, если xmlstock не подходит
- `seo-copywriting`, `seo-evidence-based-2026` — текст и стратегия, не API

## API Reference

Children own the docs. Inventory of this skill:

| Tool | File |
|---|---|
| Mutagen — Wordstat, `strong`, биды, parser.mass, serp.report | [mutagen/SKILL.md](mutagen/SKILL.md) |
| xmlstock — Яндекс/Google XML SERP, Live, async req_id | [xmlstock/SKILL.md](xmlstock/SKILL.md) |

**How to use**: open only the matching child, then that child's `references/` row. New tool later = new folder + one row here.
