# Search Analytics — searchanalytics.query

`POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query`

`siteUrl` in the path is fully URL-encoded: `https%3A%2F%2Fwww.example.com%2F` or `sc-domain%3Aexample.com`.

## Request body schema

```jsonc
{
  "startDate": "2026-05-01",          // YYYY-MM-DD, Pacific Time
  "endDate":   "2026-05-13",
  "dimensions": ["query", "page"],    // 0..N of {date,hour,query,page,country,device,searchAppearance}
  "type": "web",                      // web | discover | googleNews | news | image | video
  "aggregationType": "auto",          // auto | byPage | byProperty | byNewsShowcasePanel
  "dimensionFilterGroups": [{
    "groupType": "and",               // only "and"
    "filters": [{
      "dimension": "country",
      "operator": "equals",           // equals|notEquals|contains|notContains|includingRegex|excludingRegex
      "expression": "rus"
    }]
  }],
  "rowLimit": 25000,                  // 1..25000; default 1000
  "startRow": 0,                      // pagination offset
  "dataState": "final"                // final | all | hourly_all
}
```

## Response schema

```jsonc
{
  "rows": [
    {
      "keys": ["buy a cake", "https://example.com/cake"],
      "clicks": 12.0,
      "impressions": 320.0,
      "ctr": 0.0375,                  // 0..1
      "position": 4.2
    }
  ],
  "responseAggregationType": "byProperty",
  "metadata": {
    "first_incomplete_date": "2026-05-13",
    "first_incomplete_hour": "2026-05-14T07:00:00-07:00"
  }
}
```

`keys[]` is parallel to `dimensions[]` in the request. If `dimensions=[]`, `keys` is omitted — a single period-aggregated row is returned.

## Dimensions deep dive

| Dimension | Format | Notes |
|---|---|---|
| `date` | `YYYY-MM-DD` | Pacific Time |
| `hour` | ISO-8601 `2026-05-13T14:00:00-07:00` | requires `dataState: "hourly_all"`; depth — 8 days |
| `query` | string | search query; **anonymized** queries are hidden — totals will not match verbose mode |
| `page` | URL | landing page |
| `country` | ISO 3166-1 alpha-3 **lowercase** | `usa`, `rus`, `deu`, `bra` |
| `device` | `DESKTOP` / `MOBILE` / `TABLET` | uppercase in filters |
| `searchAppearance` | `AMP_BLUE_LINK`, `RICH_RESULT`, `VIDEO`, ... | **cannot be combined with other dimensions in one request**; first call for discovery, second call to filter by a feature |

## aggregationType

| Value | Behavior |
|---|---|
| `auto` (default) | `byPage` if `dimensions` contains `page`, otherwise `byProperty` |
| `byProperty` | one visit / impression per query = 1 across the property |
| `byPage` | impressions counted per page (one query that saw 3 pages of your site = 3 impressions) |
| `byNewsShowcasePanel` | Google News Showcase panel only |

The response's `responseAggregationType` shows what Google actually used.

## dimensionFilterGroups operators

```jsonc
{
  "groupType": "and",
  "filters": [
    { "dimension": "country", "operator": "equals", "expression": "rus" },
    { "dimension": "device",  "operator": "equals", "expression": "MOBILE" },
    { "dimension": "query",   "operator": "includingRegex", "expression": "^buy .*" },
    { "dimension": "page",    "operator": "contains", "expression": "/blog/" }
  ]
}
```

- Only `groupType: "and"` — `or` is not supported. For OR semantics: issue several requests and merge client-side.
- Regex follows RE2 syntax (no lookbehind, no backreferences).

## Pagination — 25,000-row hard cap

```python
def paginate(client, site_url, body):
    rows = []
    start = 0
    LIMIT = 25_000
    while True:
        body["rowLimit"] = LIMIT
        body["startRow"] = start
        resp = client.searchanalytics().query(siteUrl=site_url, body=body).execute()
        batch = resp.get("rows", [])
        rows.extend(batch)
        if len(batch) < LIMIT:
            break             # last page (zero or < LIMIT)
        start += LIMIT
    return rows
```

- Stop when fewer than `LIMIT` rows return (including 0).
- `startRow` past the end yields an empty `rows`, not a 400 — though pathological values can produce "invalid start row" 400s.

## Data freshness lag

- Final data (default `dataState: "final"`): 2-3 day delay for most queries, up to 4 days for the long tail and `country` / `device` breakdowns.
- `dataState: "all"` — includes fresh, recomputable rows (last 2-3 days). Good for "yesterday" dashboards, unsafe for historical reports.
- `metadata.first_incomplete_date` — Google tells you the earliest day still subject to change.
- Discover data (`type: "discover"`) lags further and only appears when the property has meaningful Discover traffic.

## Best practices for "all your data"

1. Before any bulk fetch, run a pilot `dimensions: ["date"]` query to confirm data exists for the period.
2. Top-50k queries: two calls with `rowLimit=25000`, `startRow=0` then `startRow=25000`.
3. Granular split: instead of one 30-day request with `dimensions=[query,page,country,device]`, loop per day (`startDate=endDate=D`). Otherwise total volume, quota, and response size all balloon.
4. Hourly data — its own pipeline: only 8 days of history, `dataState: "hourly_all"`, `dimensions=["hour"]` or `["hour","query"]`.

## Sample request — top-50 mobile pages, Russia, last 28 days

```jsonc
POST /webmasters/v3/sites/sc-domain%3Aexample.com/searchAnalytics/query
{
  "startDate": "2026-04-15",
  "endDate":   "2026-05-12",
  "dimensions": ["page"],
  "type": "web",
  "dimensionFilterGroups": [{
    "groupType": "and",
    "filters": [
      { "dimension": "country", "operator": "equals", "expression": "rus" },
      { "dimension": "device",  "operator": "equals", "expression": "MOBILE" }
    ]
  }],
  "rowLimit": 50,
  "startRow": 0,
  "dataState": "final"
}
```
