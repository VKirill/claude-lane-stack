# Reporting API — `/stat/v1/data*`

## Endpoints

| URL | Purpose |
|---|---|
| `GET /stat/v1/data` | Tabular report: rows × dimensions × metrics |
| `GET /stat/v1/data/bytime` | Time series for charts (`group=day/week/month`) |
| `GET /stat/v1/data/drilldown` | Hierarchical drill-down (by `parent_id`) |
| `GET /stat/v1/data/comparison` | Compare two segments or periods (A/B) |
| `GET /stat/v1/data/comparison/drilldown` | Comparison + drill-down |

Host: `https://api-metrika.yandex.net`. Header: `Authorization: OAuth <token>`.

## Full `/stat/v1/data` parameter set

| Param | Type | Default | Description |
|---|---|---|---|
| `ids` | int / CSV | **required** | counter_id (or several, comma-separated) |
| `dimensions` | CSV | (none) | up to 10; e.g. `ym:s:date,ym:s:lastTrafficSource` |
| `metrics` | CSV | **required** | at least 1; e.g. `ym:s:visits,ym:s:users` |
| `date1` | str | `6daysAgo` | `YYYY-MM-DD`, `today`, `yesterday`, `NdaysAgo` |
| `date2` | str | `today` | same; **do not** request `today` for final figures |
| `filters` | str | (none) | DSL: `ym:s:lastTrafficSource=='organic'` |
| `sort` | CSV | (none) | `-ym:s:visits` (minus = DESC) |
| `limit` | int | 100 | max 100000 |
| `offset` | int | 1 | 1-based, not 0 |
| `accuracy` | str / float | `medium` | `low`/`medium`/`high`/`full` or 0.01–1 |
| `proposed_accuracy` | bool | false | server returns `proposed_accuracy_val` |
| `preset` | str | (none) | name of a built-in report (sources, geo, etc.) |
| `group` | str | `week` | for `/bytime`: `all`/`day`/`week`/`month`/`hour`/`minute` |
| `attribution` | str | `LASTSIGN` | attribution model (see below) |
| `direct_client_logins` | CSV | (none) | Direct client logins for `ym:ad:*` slices |
| `include_undefined` | bool | false | include rows with null dimensions |
| `lang` | str | `ru` | `ru` / `en` — label language |
| `request_domain` | str | `ru` | regional config |
| `currency` | str | (counter) | override money-metric currency |
| `quantile` | float | (none) | quantile for percentile metrics |
| `timezone` | str | (counter) | override counter TZ |
| `row_ids` | str | (none) | for `/bytime`: explicit row keys |
| `top_keys` | int | 7 | for `/bytime`: top-N keys; max 30 |
| `parent_id` | str | (none) | for `/drilldown`: path to a node |

### `accuracy` — sampling control

| Value | Effect |
|---|---|
| `low` | fastest, heavy sampling possible |
| `medium` (default) | compromise — typical `sample_share` ~0.1–1 |
| `high` | minimize sampling |
| `full` / `1` | 100% of data, slower |
| `0.5` | use exactly 50% of the sample |

### Attribution models

| Value | Description |
|---|---|
| `FIRST` | First-ever click in the visit history |
| `LAST` | Last click (literally the previous visit) |
| `LASTSIGN` (default) | Last significant click (not direct/none) |
| `LAST_YANDEX_DIRECT_CLICK` | Last Yandex.Direct click |
| `CROSS_DEVICE_FIRST` | First, cross-device (by `yandex_uid`) |
| `CROSS_DEVICE_LAST` | Last, cross-device |
| `CROSS_DEVICE_LASTSIGN` | Last significant, cross-device |
| `CROSS_DEVICE_LAST_YANDEX_DIRECT_CLICK` | Last Direct click, cross-device |
| `AUTOMATIC` | Auto-select by source type |

## Sample request and response

```bash
curl -sS -H "Authorization: OAuth $TOKEN" \
  "https://api-metrika.yandex.net/stat/v1/data?\
ids=12345678&\
dimensions=ym:s:date,ym:s:lastTrafficSource&\
metrics=ym:s:visits,ym:s:users,ym:s:bounceRate&\
date1=2026-04-01&date2=2026-04-30&\
sort=-ym:s:visits&limit=100&\
accuracy=full&\
attribution=LASTSIGN"
```

Response:
```json
{
  "query": {
    "ids": [12345678],
    "dimensions": ["ym:s:date","ym:s:lastTrafficSource"],
    "metrics": ["ym:s:visits","ym:s:users","ym:s:bounceRate"],
    "date1": "2026-04-01",
    "date2": "2026-04-30",
    "filters": "",
    "limit": 100,
    "offset": 1,
    "attribution": "lastsign"
  },
  "data": [
    {
      "dimensions": [
        {"name": "2026-04-15"},
        {"name": "organic", "id": "organic"}
      ],
      "metrics": [12453, 9871, 23.45]
    }
  ],
  "total_rows": 1453,
  "total_rows_rounded": false,
  "sampled": false,
  "contains_sensitive_data": false,
  "sample_share": 1.0,
  "sample_size": 12453,
  "sample_space": 12453,
  "data_lag": 119,
  "totals": [389172, 215430, 28.12],
  "min": [12, 5, 0.0],
  "max": [15324, 11234, 89.5]
}
```

**Fields to always inspect**:

- `sampled` — `true`/`false`; always check
- `sample_share` — sample fraction (1.0 = 100%)
- `sample_size` / `sample_space` — absolute size comparison
- `total_rows` — for pagination (compare with `offset + limit`)
- `data_lag` — minutes from real-time to this dataset
- `totals` — sums per metric
- `query` — what the server actually applied (diagnostic)

## Pagination

```python
async def paginate(client, base_params):
    offset = 1
    while True:
        params = {**base_params, "offset": offset, "limit": 100000}
        r = await client.get("/stat/v1/data", params=params)
        rows = r.json()["data"]
        if not rows:
            break
        yield from rows
        if len(rows) < 100000:
            break
        offset += 100000
```

Avoid paginating with `limit < 100000` if you can — it lowers your RPS budget.

## `/stat/v1/data/bytime` — series

```
?ids=12345678
&metrics=ym:s:visits
&date1=30daysAgo&date2=yesterday
&group=day
&top_keys=7
&dimensions=ym:s:browser
```

Returns `data[]`; each element has `dimensions[]` (series key) and `metrics[][]` (arrays of values per time bucket). Inner-array length equals the number of buckets — line them up against `time_intervals`.

## `/stat/v1/data/drilldown`

Hierarchical expansion. For each `dimension` node the response includes `expand: true/false` (whether it can be drilled further). To expand, re-request with `parent_id=<path>`.

```
GET /stat/v1/data/drilldown?ids=...&dimensions=ym:s:operatingSystemRootName,ym:s:browserName&metrics=ym:s:visits
```

First response is the root level (OS roots). To expand `Windows` (id=100):
```
GET ...&parent_id=["100"]
```

## `/stat/v1/data/comparison` — comparison

Parameters are duplicated with `_a` and `_b` suffixes:
```
?ids=12345678
&metrics=ym:s:users
&dimensions=ym:s:trafficSource
&date1_a=2026-04-01&date2_a=2026-04-30
&date1_b=2026-03-01&date2_b=2026-03-31
```

Use for week-over-week, month-over-month, or A/B segment comparisons.

## POST for long parameters

When the URL exceeds 8 KB (long `filters`, many `direct_client_logins`) — switch to POST with `application/x-www-form-urlencoded` or `application/json`. Endpoints and params are unchanged.

## Preset

`preset` names a built-in report — equivalent to a fixed `dimensions+metrics+filters` combo. Examples: `sources_summary`, `sources_search_engines`, `geo_country`, `tech_devices`. With a `preset` you do not pass `dimensions`/`metrics` — they are substituted. Convenient for canonical dashboards.

## Direct integration

`ym:ad:*` namespace + `direct_client_logins=login1,login2` returns data sourced from Yandex.Direct directly (requires `metrika:read` and a counter linked to a Direct account).
