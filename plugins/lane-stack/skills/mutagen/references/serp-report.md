# `mutagen.serp.report` — 22+ report types

`mutagen.serp.report` is a single endpoint switching on `report`. Each report applies to a specific element type (`keyword`, `keywords`, `domain`, `domain_with_subdomains`, `page`).

URL pattern (use POST when payload is long — see [setup.md](setup.md)):

```
http://api.mutagen.ru/json/{api_key}/mutagen.serp.report/?{params}
```

Required parameters:

- `region` (one of: `yandex_ru`, `yandex_msk`, `yandex_spb`, `yandex_minsk`, `yandex_nsk`, `yandex_ekb`, `yandex_rostov`, `yandex_kazan`, `yandex_nn`) — see [regions.md](regions.md)
- one element type (key in the params dict): `keyword` | `keywords` | `domain` | `domain_with_subdomains` | `page`
- `report` — one of the values below

Optional: `filter`, `sort`, `limit`, `count` — see [filtering.md](filtering.md).

## Report types by element

### Keyword-element reports

Element: `keyword` (single phrase) or `keywords` (CSV, max 1000 phrases).

| Report | Element | Description |
|---|---|---|
| `report_keyword_info` | keyword, keywords | Aggregate stats per phrase — frequencies, bid costs, traffic projections across positions |
| `report_keyword_tailings` | keyword | «Хвосты» — long-tail keyword variations derived from the normalised query form |
| `report_keyword_variations` | keyword, keywords | Morphological variations of the input phrase |
| `report_keyword_expansion` | keyword | «Дополняющие фразы» — related/LSI phrases co-occurring on the same SERPs |
| `report_keyword_positions_organic` | keyword | Top-50 organic results for the query, with per-domain/page metrics |
| `report_keyword_positions_ppc` | keyword | PPC advertisers showing for the keyword with traffic forecast |

### Domain-element reports (and page-level for organic)

Element: `domain` | `domain_with_subdomains` | `page` (where listed).

| Report | Element | Description |
|---|---|---|
| `report_keywords_organic` | domain, domain_with_subdomains, page | All keywords ranking in organic, with position and traffic |
| `report_keywords_organic_up` | domain, domain_with_subdomains, page | «Поднявшиеся фразы» — keywords improving in position since the last update |
| `report_keywords_organic_down` | domain, domain_with_subdomains, page | «Упавшие фразы» — keywords declining in rank |
| `report_keywords_organic_new` | domain, domain_with_subdomains, page | New keywords appearing in organic |
| `report_keywords_organic_lost` | domain, domain_with_subdomains, page | Keywords no longer ranking; prior position included |
| `report_keywords_ppc` | domain, page | Keywords for which the domain runs context ads |
| `report_keywords_ppc_history` | domain, page | Historical context-advertising keyword data |

### Pure domain reports

Element: `domain` only.

| Report | Description |
|---|---|
| `report_domain_pages` | List of indexed pages, with per-page keyword and traffic metrics |
| `report_domain_subdomains` | Subdomains with their organic/PPC performance |
| `report_domain_competitors` | Organic competitor domains (ranking for the same keywords) |
| `report_domain_competitors_ppc` | PPC competitor domains (advertising on the same keywords) |
| `report_domain_advert` | All active and inactive context advertisements |
| `report_domain_advert_active` | Currently active context advertisements only |
| `report_domain_info` | Aggregate stats: total keywords, traffic, visibility |

### Page-element reports

Element: `page` only.

| Report | Description |
|---|---|
| `report_page_info` | Page-level stats: ranking keywords, traffic, visibility |
| `report_page_competitors` | Organic competitor pages/domains for the page's queries |
| `report_page_recommended_keywords` | «Рекомендуемые ключи» — keywords competitors rank for, this page doesn't |

## Key metric columns (the response schema)

Reports return arrays of row objects. Common columns:

### Frequency / volume

| Column | Meaning |
|---|---|
| `world_wsn` | Global broad-match Wordstat frequency (across regions) |
| `world_wsqso` | «Точная частотность» globally — `"[!фраза]"` |
| `region_wsn` | Regional broad-match frequency |
| `region_wsq` | Regional phrase-match frequency |
| `region_wsqso` | Regional точная частотность — main planning column |

### Ranking / traffic

| Column | Meaning |
|---|---|
| `position` | SERP position (organic: 1–50) |
| `position_progress` | Rank change vs. last data refresh |
| `domain_organic_wsqso` | Domain monthly traffic estimate (organic) |
| `visibility` | Search visibility index (0–100000 scale) |
| `visibility_30` / `_90` / `_180` / `_365` | Historical visibility snapshots |
| `organic_results` | Total organic results for the query |

### Paid (Direct / PPC) — bid forecasts

Mirrors the `parser.get(parser="direct")` shape but at row-of-report level:

| Column | Block |
|---|---|
| `min_bid` | Минимальная ставка (RUB) |
| `first_premium_shows` / `_clicks` / `_bid` / `_budget` / `_ctr` | Топ премиум блок |
| `premium_shows` / `_clicks` / `_bid` / `_budget` / `_ctr` | Премиум блок (~62% трафика) |
| `first_place_shows` / `_clicks` / `_bid` / `_budget` / `_ctr` | Первое место (~9% трафика) |
| `std_shows` / `_clicks` / `_bid` / `_budget` / `_ctr` | Стандарт / гарантированные показы |

### Domain / page meta

| Column | Meaning |
|---|---|
| `pages` | Indexed page count |
| `domain_organic_keywords` | Unique ranking keywords for the domain |
| `domain_organic_keywords_top1_procent` / `_top3_procent` / `_top5_procent` / `_top10_procent` / `_top20_procent` / `_top30_procent` | % of keywords in each top-N tier |
| `has_question` | Boolean — query contains a question mark |
| `has_toponym` | Boolean — query contains a geographic / toponym term |

## Composition with filter / sort / limit

Example: top-50 Moscow long-tail keywords under «купить квадроцикл» with точная частотность ≥ 100 and at most 7 words, sorted by descending global frequency:

```json
{
  "region": "yandex_msk",
  "keyword": "купить квадроцикл",
  "report": "report_keyword_tailings",
  "filter": [
    {"column": "region_wsqso", "filter_type": "gr_or_eq", "val": 100},
    {"column": "words",        "filter_type": "less_or_eq", "val": 7}
  ],
  "sort":  "-world_wsn",
  "limit": 50
}
```

See [filtering.md](filtering.md) for filter syntax in detail.

## Probing row count cheaply

Before fetching a large result set, use `count: 1` to get only the row count:

```json
{
  "region": "yandex_msk",
  "domain": "example.ru",
  "report": "report_keywords_organic",
  "count":  1
}
```

Response:

```json
{ "count": 18472 }
```

Then decide whether to paginate via `limit` or refine filters before paying for the full data fetch.

## Pricing note

The documentation does not publish per-report pricing in the API page. Check the current tariff via your dashboard (`https://mutagen.ru/?p=price`). Different report types have very different costs — `report_keyword_info` is typically cheap, large domain reports (`report_keywords_organic` on huge domains) are expensive. Always run a `count: 1` probe before pulling a long list.

## When to pick which report

| Goal | Report |
|---|---|
| Получить ставки и частотность для конкретной фразы | `report_keyword_info` |
| Собрать хвосты под seed-фразу | `report_keyword_tailings` |
| Найти LSI / co-mentioned phrases | `report_keyword_expansion` |
| Понять конкурентов в выдаче по фразе | `report_keyword_positions_organic` |
| Анализ домена — что ранжируется | `report_keywords_organic` |
| Динамика — что упало / поднялось | `report_keywords_organic_down` / `_up` |
| Что нового / потеряли | `report_keywords_organic_new` / `_lost` |
| Конкуренты домена | `report_domain_competitors` |
| Сравнение страницы со страницами конкурентов | `report_page_competitors` |
| Найти пробелы в семантике страницы | `report_page_recommended_keywords` |
