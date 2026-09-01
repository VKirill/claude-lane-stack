---
name: google
description: "[RU: экосистема Google] Ads (RSA/PMax), Analytics GA4, Search Console, GTM, Cloud auth. SKILL.md — роутер; доменные доки в дочерних папках. Use when: google, гугл, google ads, гугл реклама, ga4, гугл аналитика, gsc, search console, gtm, тег менеджер, oauth google, service account, /google. SKIP: Я.Директ/Метрика/Вебмастер→yandex; VK/TG Ads; Wordstat/SERP XML→seo-tools; Ads API / GCP compute / BigQuery / Gemini (нет скилла)."
stacks:
  - google
  - ru
tags:
  - google
  - dispatcher
  - ecosystem
  - oauth
  - ru
source: vechkasov-global-skills
risk: medium
---

# Google ecosystem

This `SKILL.md` is a **router**. Product knowledge lives in the child folders below. Do not answer APIs from this file.

## Protocol

1. Match the task to the route table.
2. **Read** that child's `SKILL.md`.
3. Load only that child's `references/` row from its own API Reference table.
4. Two products → read both children. Do not merge their APIs, headers, or quotas.

## Use this skill when

- Any Google product we cover: Ads, Analytics (GA4), Search Console, Tag Manager, Cloud auth
- Two or more of those in one request
- Shared Google OAuth / service account / ADC / `invalid_grant`
- Slash command `/google`

## Do not use this skill when

- Яндекс (Директ / Метрика / Вебмастер / Cloud) → `yandex`
- VK Ads / Telegram Ads → `telegram-ads-spec`
- Wordstat / live SERP XML → `seo-tools`
- Google Ads **API** (CampaignsService-style code) — **no skill**, do not invent one
- GCP compute / BigQuery / Gemini / nano-banana — **no skill here**

## Route table

| Task | Child |
|---|---|
| RSA / PMax / Display / Demand Gen / лимиты 30/90, политики, РФ-бан Ads | [google-ads/SKILL.md](google-ads/SKILL.md) |
| GA4: `runReport`, property_id, агрегаты, token quotas | [google-analytics/SKILL.md](google-analytics/SKILL.md) |
| GSC: queries, CTR, urlInspection, sitemap, Indexing API | [google-search-console/SKILL.md](google-search-console/SKILL.md) |
| GTM: контейнер, теги/триггеры/переменные, publish, rollback, etag | [google-tag-manager/SKILL.md](google-tag-manager/SKILL.md) |
| OAuth / SA key.json / ADC / scopes / `invalid_grant` | [google-cloud-auth/SKILL.md](google-cloud-auth/SKILL.md) |

Нет дочернего скилла: Google Ads API, GCP compute, BigQuery, Gemini.

## Ambiguous prompts

| User says | Default | Not this |
|---|---|---|
| «позиции в Google» + **свой** сайт | `google-search-console` | xmlstock = произвольный SERP |
| «позиции» + список ключей / чужой домен | `xmlstock` | GSC only covers verified properties |
| «трафик» / «конверсии с сайта» | `google-analytics` | GSC = search queries; Ads = paid |
| «статистика объявлений» / CPC / CTR ads | `google-ads` (кабинет) | GA4 = on-site; нет Ads API скилла |
| «написать RSA / PMax» | `google-ads` | сначала `russia-context` |
| «Google Ads в Россию» | `google-ads` → Я.Директ | размещение в РФ недоступно |
| «запросы / индекс / sitemap Google» | `google-search-console` | GA4 не знает поисковые запросы |
| «Measurement ID G-XXXX» в API | `google-analytics`: это **не** Property ID | остановиться, взять numeric ID |
| «поставить GTM / тег / опубликовать контейнер» | `google-tag-manager` | GA4 = отчёты; auth = ключи |
| «invalid_grant / SA / refresh token / ADC» | `google-cloud-auth` | не чинить токен внутри GA4/GSC/GTM |

If still unclear — one question, then route.

## Cross-product

| Situation | Load in order |
|---|---|
| Любой Google API без рабочего токена | `google-cloud-auth` → продукт |
| Креативы Ads + измерение на сайте | `google-ads` → `google-analytics` |
| Новый сайт: индекс + счётчик | `google-search-console` → `google-analytics` |
| Органика vs поведение | `google-search-console` + `google-analytics` (не склеивать 1:1) |
| Теги на сайте + отчёты GA4 | `google-tag-manager` → `google-analytics` |
| РФ-таргет вместо Google Ads | `yandex` → `yandex-direct-creatives` |

## Shared Google auth

Auth bootstrap is **`google-cloud-auth`**: OAuth user flow, service account JWT, ADC, scopes, `invalid_grant`. A key file is not enough — grant the SA email in the **product** UI.

| Product | Grant |
|---|---|
| `google-analytics` | Admin → Property Access Management (`Viewer`+) |
| `google-search-console` | Settings → Users (`Restricted` / `Full`; Indexing API needs **Owner**) |
| `google-tag-manager` | Account/Container access in GTM UI (`tagmanager.readonly` / `.edit.containers` / `.publish`) |
| `google-ads` | no API — кабинет / YAML validator |

Do not share one client across GA4 Data API, GSC Webmasters, and GTM: different hosts, scopes, quotas.

Property ID (`properties/123`) ≠ Measurement ID (`G-XXXX`) ≠ GSC `siteUrl` (`https://…/` or `sc-domain:`) ≠ GTM Account/Container IDs.

## Behavioral Traits

- Picks **one** child before writing code or curl
- Reads that child's SKILL.md; does not quote endpoints from this file
- Auth errors first → `google-cloud-auth`, then the product child
- For Ads: reads `russia-context` before any creative
- Names the child folder in the answer

## Important Constraints

- NEVER invent Google endpoints or quotas in this dispatcher
- NEVER mix GA4 Property ID, Measurement ID, GSC siteUrl, and GTM container IDs
- NEVER propose Google Ads for placement **in RF**
- NEVER use Indexing API for regular pages (JobPosting / BroadcastEvent only — child's rule)
- NEVER publish GTM live without the child's two-step `create_version` → `publish`
- ALWAYS Read the child before the first API call
- ALWAYS say «нет скилла» for Ads API / GCP compute / BigQuery / Gemini

## Related Skills

- `yandex` — Яндекс-экосистема (зеркало: Direct / Метрика / Вебмастер)
- `seo-tools` — Mutagen (Wordstat) + xmlstock (SERP XML)
- `telegram-ads-spec` — TG Ads
- `ad-creatives-frameworks` — 4U / AIDA for headlines
- `legal-ru-marketing` — RU compliance (не политики Google Ads)

## API Reference

Children own the docs. Inventory of this skill:

| Product | File |
|---|---|
| Google Ads — форматы, лимиты, policies, РФ-контекст, validator | [google-ads/SKILL.md](google-ads/SKILL.md) |
| Google Analytics (GA4 Data API) — runReport, filters, realtime, quotas | [google-analytics/SKILL.md](google-analytics/SKILL.md) |
| Search Console — searchanalytics, urlInspection, sitemaps | [google-search-console/SKILL.md](google-search-console/SKILL.md) |
| Tag Manager API v2 — tags/triggers/variables, publish, rollback | [google-tag-manager/SKILL.md](google-tag-manager/SKILL.md) |
| Cloud auth — OAuth, SA, ADC, scopes, invalid_grant | [google-cloud-auth/SKILL.md](google-cloud-auth/SKILL.md) |

**How to use**: open only the matching child, then that child's `references/` row.
