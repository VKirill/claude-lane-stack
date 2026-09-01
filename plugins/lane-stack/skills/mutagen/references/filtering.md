# Filtering, sorting, row-count — `serp.report`

`mutagen.serp.report` accepts three composition parameters: `filter`, `sort`, `limit`. Plus `count: 1` for row-count probes.

## `filter` — array of filter objects

Each filter object has the shape:

```json
{ "column": "<column_name>", "filter_type": "<op>", "val": <value>, "min": <value>, "max": <value>, "or": 1 }
```

Only `column` and `filter_type` are required. The remaining keys depend on the operator. Multiple filters in the array combine with AND by default; insert `{"or": 1}` markers (or set `"or": 1` on a filter) to switch to OR-blocks.

## 17 filter types

| `filter_type` | Alias | Condition | Required params | Applies to |
|---|---|---|---|---|
| `gr` | `>` | Greater than | `val` | numeric, timestamp |
| `gr_or_eq` | `>=` | Greater than or equal | `val` | numeric, timestamp |
| `less` | `<` | Less than | `val` | numeric, timestamp |
| `less_or_eq` | `<=` | Less than or equal | `val` | numeric, timestamp |
| `eq` | `=` | Exact equality | `val` | all types |
| `not_eq` | `!=` | Not equal | `val` | all types |
| `range` | — | Between min and max (inclusive) | `min`, `max` | numeric only |
| `in` | — | One of a list (max 1024 values) | `val` (CSV string) | numeric, text |
| `not_in` | — | Not in list (max 1024 values) | `val` (CSV string) | numeric, text |
| `like` | — | Substring contains | `val` | text, URL |
| `not_like` | — | Substring does NOT contain | `val` | text, URL |
| `like_any` | — | Contains any of (max 1024 values) | `val` (CSV string) | text, URL |
| `not_like_any` | — | Contains none of (max 1024 values) | `val` (CSV string) | text, URL |
| `like_start` | — | Begins with | `val` | text |
| `like_finish` | — | Ends with | `val` | text |
| `is` | — | Boolean check (1 / 0) | `val` | boolean fields only |

### Examples by filter type

```json
[
  {"column": "region_wsqso", "filter_type": "gr_or_eq", "val": 100},
  {"column": "words",        "filter_type": "range",    "min": 2, "max": 7},
  {"column": "keyword",      "filter_type": "like_any", "val": "купить,заказать,доставка"},
  {"column": "keyword",      "filter_type": "not_like", "val": "бесплатно"},
  {"column": "has_question", "filter_type": "is",       "val": 0}
]
```

This filters to: regional точная частотность ≥ 100 AND word count between 2 and 7 inclusive AND keyword contains any of («купить», «заказать», «доставка») AND keyword does not contain «бесплатно» AND query is NOT a question.

## OR-blocks via `"or": 1`

Default combination is AND across all filters. To start an OR-block, set `"or": 1` on the filter object that begins the block. The OR-block continues until the next non-or filter (which closes it back to AND).

Example: get keywords where `region_wsqso ≥ 100` AND (`min_bid > 10` OR `domain_organic_keywords > 1000`):

```json
[
  {"column": "region_wsqso",           "filter_type": "gr_or_eq", "val": 100},
  {"column": "min_bid",                "filter_type": "gr",       "val": 10},
  {"column": "domain_organic_keywords","filter_type": "gr",       "val": 1000, "or": 1}
]
```

Read the `"or": 1` as "this filter joins with the previous via OR (rather than AND)".

If you find logic confusing, build the report in two passes:

1. Pull the broader AND-filtered set.
2. Filter the result client-side with explicit booleans.

This costs more API budget but eliminates ambiguity for complex predicates.

## `sort` — single column, asc or desc

```json
{ "sort": "region_wsqso" }       // ascending
{ "sort": "-region_wsqso" }      // descending
```

Only one column per request. To sort by multiple columns, pull the result and sort client-side.

## `limit` — cap rows returned

```json
{ "limit": 100 }
```

Without `limit`, the report returns the full set — for large domains this is hundreds of thousands of rows and a large bill. **Always set `limit` explicitly**, even if you think the result is small. Probe with `count: 1` first when in doubt.

## `count: 1` — row-count probe

```json
{
  "region": "yandex_msk",
  "domain": "example.ru",
  "report": "report_keywords_organic",
  "filter": [{"column": "region_wsqso", "filter_type": "gr_or_eq", "val": 100}],
  "count":  1
}
```

Response:

```json
{ "count": 18472 }
```

The `count` flag returns ONLY the row count — no data payload, much cheaper than the full report. Use BEFORE every potentially large pull. Pattern:

1. Build the filter chain.
2. Issue with `count: 1` — read `N`.
3. If `N` is acceptable for your budget, re-issue without `count` and with appropriate `limit`.
4. If `N` is too large, tighten filters and probe again.

## Column reference

Column names available depend on the `report` type. The full list is documented in [serp-report.md](serp-report.md) under "Key metric columns". Most-used:

- `region_wsqso`, `region_wsn`, `world_wsqso`, `world_wsn` — frequency variants
- `position`, `position_progress` — ranking
- `min_bid`, `premium_bid` (+ block-suffixed variants) — bid amounts
- `keyword`, `domain`, `page` — text identifiers
- `words` — word count in the keyword
- `has_question`, `has_toponym` — boolean structural flags
- `visibility`, `visibility_30`, etc. — domain visibility metrics

If you specify an unknown column or use `gr` on a non-numeric column, the API returns an error envelope — surface it in your client.

## Cost-aware filtering

Filtering happens server-side, so well-targeted filters dramatically reduce result size and per-request cost. Tightening rules of thumb:

1. Always set a `region_wsqso` minimum (≥ 30 for low-volume niches, ≥ 100 for general work, ≥ 1000 for high-volume planning).
2. Cap `words` (`less_or_eq` 7-10) to drop ultra-long-tail garbage.
3. Use `not_like_any` to exclude obvious irrelevant intent words ("бесплатно", "торрент", etc.).
4. Probe with `count: 1` before every full pull.
