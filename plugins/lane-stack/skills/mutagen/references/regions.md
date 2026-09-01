# Regions — `region` (serp.report) and `region_id` (parser)

The two method families use **different** region parameters with different value formats. Treat them as separate concepts.

## `region` — for `mutagen.serp.report`

String enum. Required for every `serp.report` call.

| Value | Geo | Notes |
|---|---|---|
| `yandex_ru` | Россия (global) | Keyword-only — supports a subset of reports |
| `yandex_msk` | Москва | Most common default for RU SEO |
| `yandex_spb` | Санкт-Петербург | |
| `yandex_minsk` | Минск (Беларусь) | RU language, Belarus geo |
| `yandex_nsk` | Новосибирск | |
| `yandex_ekb` | Екатеринбург | |
| `yandex_rostov` | Ростов-на-Дону | |
| `yandex_kazan` | Казань | |
| `yandex_nn` | Нижний Новгород | |

### `yandex_ru` is restricted

`yandex_ru` is the global RU dataset and is keyword-only — only keyword-element reports (`report_keyword_*`) accept it. Domain-element and page-element reports require a specific city region.

If you call a domain report with `region: yandex_ru`, the API returns an error or no data. Use one of the city regions instead.

### Picking a region

| Audience / market | Region |
|---|---|
| Federal RU brand, Moscow office | `yandex_msk` |
| St. Petersburg local business | `yandex_spb` |
| Belarus market (RU-language) | `yandex_minsk` |
| Regional / city-targeted ad campaign | the matching city code |
| Cross-region competitive analysis | run separately for each region, compare client-side |

**Region mismatch is a common silent error.** Yandex SERPs differ markedly between Moscow and other cities (especially for commercial intent). Querying `yandex_msk` and presenting it as "Russia-wide" data over-weights Moscow visibility/competition.

## `region_id` — for parser methods (`parser.get`, `parser.mass.new`)

String containing one or more numeric Yandex region codes, separated by commas. Prefix `-` excludes a region.

- Default `"0"` — no region filter (global RU data).
- Single region: `"213"` (Moscow).
- Multiple inclusive: `"213,2"` (Moscow + St. Petersburg).
- Mixed include/exclude: `"225,-213"` (all of Russia except Moscow).

### Common numeric codes

These are the standard Yandex region IDs (the same ones used elsewhere in the Yandex ecosystem):

| Code | Geo |
|---|---|
| `0` | Default / no region |
| `225` | Россия |
| `213` | Москва |
| `2` | Санкт-Петербург |
| `65` | Новосибирск |
| `54` | Екатеринбург |
| `39` | Ростов-на-Дону |
| `43` | Казань |
| `47` | Нижний Новгород |
| `149` | Беларусь |
| `157` | Минск |

For other regions, consult the Yandex region tree (`https://yandex.ru/dev/jsapi-region-tree/`) — the codes are stable and shared across Yandex products.

### Why parser methods use a different format

Parser methods are deeper Wordstat passes; Mutagen lets you specify any numeric Yandex region ID (or combination), not only the 9 reporting regions exposed in `serp.report`. The numeric format gives flexibility (combine regions, exclude regions) at the cost of being less self-documenting.

## Frequency-vs-region semantics

The same `wordstat_qso` query against different regions returns wildly different `frequency` values:

- `region_id="0"` (no region) → broadest count, often 10× to 100× higher than a single city
- `region_id="213"` (Moscow) → Moscow-only count
- `region_id="225"` (Russia) → all-of-Russia count, smaller than no-region (because no-region includes CIS / Belarus / Ukraine)

**Implication for SEO planning**: pick the region once at the start of the project and use it consistently across `parser.mass.new` calls. Mixing regions inside one semantic-core analysis gives incomparable numbers.

## Cross-method consistency

When you use both `serp.report` (for ranking analysis) and `parser.mass.new` (for frequency collection) on the same project:

| `serp.report` `region` | Corresponding parser `region_id` |
|---|---|
| `yandex_msk` | `213` |
| `yandex_spb` | `2` |
| `yandex_minsk` | `157` |
| `yandex_nsk` | `65` |
| `yandex_ekb` | `54` |
| `yandex_rostov` | `39` |
| `yandex_kazan` | `43` |
| `yandex_nn` | `47` |
| `yandex_ru` | `225` (closest equivalent, but see semantics note above) |

Document the project's region choice in code (e.g., a constant or config field) so all calls use the same value.

## Verification pattern

When in doubt about whether the region took effect:

1. Run a small probe — `wordstat_qso` for a clearly geo-skewed query like «доставка цветов» — at `region_id="0"` and `region_id="213"`.
2. The Moscow result should be a small fraction of the global result.
3. If they're equal, the region parameter wasn't applied — recheck encoding and parameter name.
