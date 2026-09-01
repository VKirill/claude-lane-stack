---
name: yandex
description: "[RU: экосистема Яндекса] Cloud, Direct API, креативы Direct, Метрика, Вебмастер. SKILL.md — роутер; доменные доки в дочерних папках. Use when: яндекс, yandex, яндекс облако, yc, яндекс директ, объявления директ, метрика, webmaster, oauth.yandex.ru, /yandex. SKIP: Google Ads/GSC/GA4; AWS/GCP/Azure; Wordstat/SERP XML→seo-tools."
stacks:
  - yandex
  - ru
tags:
  - yandex
  - dispatcher
  - ecosystem
  - oauth
  - ru
source: vechkasov-global-skills
risk: medium
---

# Yandex ecosystem

This `SKILL.md` is a **router**. Product knowledge lives in the child folders below. Do not answer APIs from this file.

## Protocol

1. Match the task to the route table.
2. **Read** that child's `SKILL.md`.
3. Load only that child's `references/` row from its own API Reference table.
4. Two products → read both children. Do not merge their APIs, headers, or quotas.

## Use this skill when

- Any Yandex product: Cloud, Direct, Метрика, Вебмастер
- Two or more products in one request
- Shared Yandex ID / `oauth.yandex.ru`
- Slash command `/yandex`

## Do not use this skill when

- Google Ads / GSC / GA4 / AWS / GCP / Azure
- Wordstat frequency / live SERP XML → `seo-tools`
- YandexGPT, Alice, Maps, Disk, 360, AppMetrica — **no skill here**, do not invent one

## Route table

| Task | Child |
|---|---|
| `yc`, VM, managed PG/Redis, Object Storage, VPC, k8s, Lockbox, IAM | [yandex-cloud/SKILL.md](yandex-cloud/SKILL.md) |
| Direct API: кампании, ставки, Ads.add, Reports TSV, units, sandbox | [yandex-direct/SKILL.md](yandex-direct/SKILL.md) |
| Тексты объявлений, лимиты ТГО, CSV Key Collector, intent-шаблоны | [yandex-direct-creatives/SKILL.md](yandex-direct-creatives/SKILL.md) |
| Трафик, цели, `/stat/v1/data`, Logs API, counter_id | [yandex-metrica/SKILL.md](yandex-metrica/SKILL.md) |
| Индексация, переобход, sitemap, поисковые запросы сайта | [yandex-webmaster/SKILL.md](yandex-webmaster/SKILL.md) |

## Ambiguous prompts

| User says | Default | Not this |
|---|---|---|
| «позиции в Яндексе» + **свой** сайт | webmaster | xmlstock = произвольный SERP |
| «позиции» + список ключей / чужой домен | `xmlstock` | Webmaster only covers verified hosts |
| «трафик» / «конверсии с сайта» | metrica | Direct = paid clicks/CPC |
| «статистика Директа» / CPC / CTR объявлений | direct | Metrika is on-site behavior |
| «частотность» / Wordstat | `mutagen` | Webmaster shows **your** queries, not volume |
| «написать объявление» | direct-creatives | upload → then direct |
| «залить / Ads.add / ставки» | direct | creatives never calls the API |
| «сервер / база / s3 в Яндексе» | cloud | app code → language skill |

If still unclear — one question, then route.

## Cross-product

| Situation | Load in order |
|---|---|
| Написать объявления **и** залить | creatives → direct |
| Direct spend ≠ Metrika conversions | direct + metrica (`LAST_YANDEX_DIRECT_CLICK` / `LASTSIGN`) |
| Новый сайт: хостинг + счётчик + индекс | cloud → metrica → webmaster |
| Задеплоили, нужен переобход | webmaster (`recrawl/quota` first) |
| Семантика + запросы **этого** сайта | `mutagen` + webmaster |

## Shared Yandex ID

Direct / Metrika / Webmaster: app on `oauth.yandex.ru` or `oauth.yandex.com`. Scopes, TTL, and header scheme are per child `setup`. Cloud is **IAM** (`yc iam create-token`), not this OAuth.

| Product | `Authorization` |
|---|---|
| Direct | `Bearer <token>` |
| Metrika | `OAuth <token>` (`Bearer` also works) |
| Webmaster | `OAuth <token>` — **not** `Bearer` |
| Cloud | IAM token / `yc` profile |

Do not share one HTTP client across these four.

## Behavioral Traits

- Picks **one** child before writing code or curl
- Reads that child's SKILL.md; does not quote endpoints from this file
- Batch writes follow the child's high-stakes contract
- Names the child folder in the answer

## Important Constraints

- NEVER invent Yandex endpoints, units, or `yc` flags in this dispatcher
- NEVER mix Direct `Bearer`, Webmaster `OAuth`, and Cloud IAM in one client
- NEVER call Direct API from the creatives path
- ALWAYS Read the child before the first API call
- ALWAYS say «нет скилла» for GPT / Alice / Maps / Disk / 360 / AppMetrica

## Related Skills

- `seo-tools` — Mutagen (Wordstat) + xmlstock (SERP XML)
- `google` — Google-экосистема (Ads / GA4 / Search Console)
- `ru-data-compliance` — 152-ФЗ / Metrika cookies
- `linux-sysadmin` — OS on Cloud VMs

## API Reference

Children own the docs. Inventory of this skill:

| Product | File |
|---|---|
| Cloud — `yc`, managed DB, S3, VPC, k8s, IAM, Lockbox | [yandex-cloud/SKILL.md](yandex-cloud/SKILL.md) |
| Direct API v5 — JSON-RPC, units, Reports, sandbox | [yandex-direct/SKILL.md](yandex-direct/SKILL.md) |
| Direct creatives — limits, CSV, intent templates | [yandex-direct-creatives/SKILL.md](yandex-direct-creatives/SKILL.md) |
| Metrika — Reporting / Logs / Management | [yandex-metrica/SKILL.md](yandex-metrica/SKILL.md) |
| Webmaster — queries, recrawl, sitemaps, diagnostics | [yandex-webmaster/SKILL.md](yandex-webmaster/SKILL.md) |

**How to use**: open only the matching child, then that child's `references/` row.
