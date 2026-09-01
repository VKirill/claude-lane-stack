# Yandex.Webmaster — Search Queries Analytics

## What this is

Endpoints for **search query** stats — what users searched and saw / clicked for your site in Yandex Search. This is **not** Wordstat (general phrase volume) — these are **already happened** shows for your site in SERP.

## Indicators

| Indicator | Meaning |
|---|---|
| `TOTAL_SHOWS` | times shown in SERP for that query |
| `TOTAL_CLICKS` | clicks from SERP to your site |
| `AVG_SHOW_POSITION` | average shown position (1.0 = always #1) |
| `AVG_CLICK_POSITION` | average position when clicked |

`query_indicator` is repeatable (`?query_indicator=TOTAL_SHOWS&query_indicator=TOTAL_CLICKS`).

CTR is not returned explicitly — compute as `TOTAL_CLICKS / TOTAL_SHOWS`.

## Device filter

```
device_type_indicator={ALL|DESKTOP|MOBILE|TABLET|MOBILE_AND_TABLET}
```

Default — `ALL`. Useful for mobile-only analytics.

## Date range

```
date_from=2024-01-01
date_to=2024-01-31
```

Omit → defaults to "last week" per docs.

**Effective retention**: Webmaster keeps detailed data for a limited window (~90 days empirically). Older ranges return empty value arrays without an explicit error. For long history — accumulate locally (see `integration.md` Postgres schema).

> Verify against current docs: exact max retention for search-queries (~90 days mentioned in some articles, not officially fixed).

## 1. Popular queries

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/popular
    ?order_by={TOTAL_SHOWS|TOTAL_CLICKS}
    [&query_indicator=...]
    [&device_type_indicator=ALL]
    [&date_from=][&date_to=]
    [&offset=0][&limit=500]
```

**Required**: `order_by`.

**Limits**:
- `offset` — min 0, default 0
- `limit` — 1-500, default 500
- Total available: TOP-3000 queries → paginate 6 pages of 500

**Response**:

```json
{
  "queries": [
    {
      "query_id": "abc123",
      "query_text": "buy bicycle moscow",
      "indicators": {
        "TOTAL_SHOWS": 1234,
        "TOTAL_CLICKS": 56,
        "AVG_SHOW_POSITION": 4.2,
        "AVG_CLICK_POSITION": 3.8
      }
    }
  ],
  "date_from": "2024-01-08",
  "date_to": "2024-01-14",
  "count": 3000
}
```

- `query_id` — stable id, **persist it** to build per-query history.
- `date_from`/`date_to` in the response may differ from the request (rounded to whole days).
- `count` — total available, not the row count of this response.

## 2. History — all queries aggregated

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/all/history
    [&query_indicator=...]
    [&device_type_indicator=ALL]
    [&date_from=][&date_to=]
```

Returns aggregated time series across all queries.

**Response**:

```json
{
  "indicators": {
    "TOTAL_SHOWS": [
      {"date": "2024-01-08T00:00:00.000+03:00", "value": 12500.0},
      {"date": "2024-01-09T00:00:00.000+03:00", "value": 13100.0}
    ],
    "TOTAL_CLICKS": [...]
  },
  "date_from": "2024-01-08",
  "date_to": "2024-01-14"
}
```

## 3. History — one specific query

```
GET /v4/user/{user-id}/hosts/{host-id}/search-queries/{query-id}/history
    [&query_indicator=...]
    [&device_type_indicator=ALL]
    [&date_from=][&date_to=]
```

`query-id` comes from `popular` response.

**Response** — same shape as `all/history`, but for one query.

Error 404 `QUERY_ID_NOT_FOUND` — query expired or never existed. Possible if it fell out of TOP-3000.

## Typical patterns

### Daily snapshot of all queries

```python
# 1. Pull TOP-3000 with TOTAL_SHOWS + TOTAL_CLICKS + AVG_SHOW_POSITION
for offset in range(0, 3000, 500):
    page = await client.search_queries_popular(
        host_id, order_by="TOTAL_SHOWS",
        indicators=["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION", "AVG_CLICK_POSITION"],
        offset=offset, limit=500,
        date_from=yesterday, date_to=yesterday,
    )
    upsert_to_db(page["queries"])
```

### Tracking priority queries

```python
# Keep a list of query_id values you care about in the DB
priority_queries = await db.fetch_priority_queries(host_id)

for query in priority_queries:
    history = await client.search_query_history(
        host_id, query["query_id"],
        indicators=["AVG_SHOW_POSITION", "TOTAL_SHOWS"],
        date_from=last_30_days_ago,
    )
    persist_history(query["query_id"], history)
```

## Errors

| HTTP | Code | When |
|---|---|---|
| 200 | — | ok |
| 403 | `INVALID_USER_ID` | token belongs to another user |
| 404 | `HOST_NOT_VERIFIED` | site not verified |
| 404 | `HOST_NOT_INDEXED` / `HOST_NOT_LOADED` | site not yet indexed by Yandex |
| 404 | `QUERY_ID_NOT_FOUND` | (only for `{query-id}/history`) query no longer tracked |

## Common mistakes

- **Omitting `query_indicator`** → `queries` returns with empty `indicators`. Always specify the metrics you need.
- **Using `query_text` as the history key** — text may be normalized by Yandex. Use `query_id`.
- **Requesting `popular` with `limit > 500`** — silently clamped to 500. Paginate.
- **Treating `count` as the number of rows returned** — it is the total available (up to 3000), not the response size.
- **Skipping daily snapshots** — in 90 days you cannot build year-over-year charts. Persist daily.
