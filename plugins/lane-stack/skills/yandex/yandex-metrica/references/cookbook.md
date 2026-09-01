# Cookbook — yandex_metrika_api recipes
Last verified: 2026-05-17 against yandex.ru/dev/metrika/ru/

> Use these recipes via the mcp-yandex-seo tool `yandex_metrika_api` (generic gateway).
> For low-level details on dimensions, metrics, filters — see ./dimensions-and-metrics.md
> and ./reporting-api.md. All calls go to `https://api-metrika.yandex.net`.

---

## Counter discovery

### List all accessible counters

```js
yandex_metrika_api({
  endpoint: "/management/v1/counters",
  params: { per_page: 100, offset: 1 }
})
```

Returns `counters[]` with `id`, `name`, `site`, `permission`, `status`. Paginate with `offset` if you have more than 100 counters.

### Filter counters you own

```js
yandex_metrika_api({
  endpoint: "/management/v1/counters",
  params: { per_page: 100, permission: "own" }
})
```

`permission`: `own` / `view` / `edit`.

### Get full details for one counter

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678",
  params: { field: "time_zone,goals,filters,operations,grants" }
})
```

The `field` parameter controls which related sub-objects are inlined in the response.

---

## Reporting API — visits/sessions (`ym:s:`)

### Top visited pages last 7 days

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:pv:URL,ym:pv:title",
    metrics: "ym:pv:pageviews,ym:pv:users",
    date1: "7daysAgo",
    date2: "yesterday",
    sort: "-ym:pv:pageviews",
    limit: 50,
    accuracy: "full"
  }
})
```

Note: uses `ym:pv:` namespace (page views). Cannot mix with `ym:s:` in the same request.

### Traffic sources overview

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageDepth",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    accuracy: "full"
  }
})
```

`lastTrafficSource` values: `organic`, `ad`, `direct`, `referral`, `social`, `email`, `internal`, `saved`, `recommend`, `undefined`.

### Top landing (entry) URLs

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:startURL",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    limit: 50,
    accuracy: "full"
  }
})
```

### Audience by device category

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:deviceCategory",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
    date1: "30daysAgo",
    date2: "yesterday",
    accuracy: "full"
  }
})
```

`deviceCategory`: `desktop` / `mobile` / `tablet` / `tv`.

### Geography — top cities

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:regionCountry,ym:s:regionCity",
    metrics: "ym:s:users,ym:s:visits,ym:s:bounceRate",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:users",
    limit: 30,
    accuracy: "full"
  }
})
```

---

## Search phrases (replaces deleted `metrika_search_phrases`)

### Top organic search phrases

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastSearchPhrase,ym:s:lastSourceEngine",
    metrics: "ym:s:visits,ym:s:bounceRate,ym:s:pageDepth",
    filters: "ym:s:lastTrafficSource=='organic'",
    date1: "7daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    limit: 100,
    accuracy: "full"
  }
})
```

`lastSearchPhrase` is the organic keyword. `lastSourceEngine` tells you whether it came from Yandex, Google, etc.

### Search phrases for Yandex only

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastSearchPhrase",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate",
    filters: "ym:s:lastTrafficSource=='organic' AND ym:s:lastSourceEngine=='yandex'",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    limit: 200,
    accuracy: "full"
  }
})
```

---

## Traffic sources (replaces deleted `metrika_traffic_summary`)

### Visits by source + engine breakdown

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource,ym:s:lastSourceEngine",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageDepth,ym:s:avgVisitDurationSeconds",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    accuracy: "full"
  }
})
```

### Referral domains

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastReferalSource",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate",
    filters: "ym:s:lastTrafficSource=='referral'",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    limit: 50,
    accuracy: "full"
  }
})
```

### UTM campaign performance

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageDepth",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:visits",
    limit: 100,
    accuracy: "full"
  }
})
```

---

## Time-series reports

### Daily visits last 30 days

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/bytime",
  params: {
    ids: "12345678",
    metrics: "ym:s:visits,ym:s:users",
    date1: "30daysAgo",
    date2: "yesterday",
    group: "day",
    accuracy: "full"
  }
})
```

`group`: `hour` / `day` / `week` / `month`. The response contains `time_intervals` (bucket boundaries) and `data[]` where each element has `metrics[][]` (one inner array per bucket).

### Daily visits by traffic source (top 7 sources)

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/bytime",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits",
    date1: "30daysAgo",
    date2: "yesterday",
    group: "day",
    top_keys: 7,
    accuracy: "full"
  }
})
```

`top_keys` controls how many dimension values are tracked in the series (max 30).

### Monthly bounce rate trend

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/bytime",
  params: {
    ids: "12345678",
    metrics: "ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
    date1: "180daysAgo",
    date2: "yesterday",
    group: "month",
    accuracy: "full"
  }
})
```

---

## Drilldown (hierarchical)

### OS → browser hierarchy

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/drilldown",
  params: {
    ids: "12345678",
    dimensions: "ym:s:operatingSystemRootName,ym:s:browserName",
    metrics: "ym:s:visits,ym:s:users",
    date1: "30daysAgo",
    date2: "yesterday",
    accuracy: "full"
  }
})
```

Each row in the response has `expand: true/false`. To drill into `Windows` (returned `id="100"`):

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/drilldown",
  params: {
    ids: "12345678",
    dimensions: "ym:s:operatingSystemRootName,ym:s:browserName",
    metrics: "ym:s:visits,ym:s:users",
    date1: "30daysAgo",
    date2: "yesterday",
    parent_id: '["100"]',
    accuracy: "full"
  }
})
```

---

## Period comparison

### This month vs last month

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/comparison",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate",
    date1_a: "2026-05-01",
    date2_a: "2026-05-16",
    date1_b: "2026-04-01",
    date2_b: "2026-04-16",
    accuracy: "full"
  }
})
```

### Last 7 days vs previous 7 days

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data/comparison",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastSearchPhrase",
    metrics: "ym:s:visits,ym:s:bounceRate",
    date1_a: "7daysAgo",
    date2_a: "yesterday",
    date1_b: "14daysAgo",
    date2_b: "8daysAgo",
    filters: "ym:s:lastTrafficSource=='organic'",
    sort: "-ym:s:visits_a",
    limit: 50,
    accuracy: "full"
  }
})
```

---

## Goal analytics

### List all goals for a counter

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/goals"
})
```

Returns `goals[]` with `id`, `name`, `type`, `conditions`.

### Goal conversion by traffic source

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits,ym:s:goal42reaches,ym:s:goal42conversionRate",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:goal42reaches",
    accuracy: "full"
  }
})
```

Replace `42` with the actual `goal_id` from the goals list.

### Goal conversion by UTM campaign

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:UTMSource,ym:s:UTMCampaign",
    metrics: "ym:s:visits,ym:s:goal42reaches,ym:s:goal42conversionRate,ym:s:goal42revenue",
    date1: "30daysAgo",
    date2: "yesterday",
    sort: "-ym:s:goal42reaches",
    accuracy: "full"
  }
})
```

### Create a URL goal (POST)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/goals",
  method: "POST",
  body: {
    goal: {
      name: "Thank you page",
      type: "url",
      is_retargeting: false,
      conditions: [
        { type: "exact", url: "https://example.com/thank-you" }
      ]
    }
  }
})
```

`conditions[].type`: `exact` / `contain` / `start` / `regexp`. Returns the created goal with its `id`.

### Create a JS-event goal (action)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/goals",
  method: "POST",
  body: {
    goal: {
      name: "Lead form submitted",
      type: "action",
      is_retargeting: false,
      conditions: [
        { type: "exact", url: "leadFormSubmit" }
      ]
    }
  }
})
```

The `url` field in the condition is the `goalName` string passed to `window.ym(..., 'reachGoal', 'leadFormSubmit')`.

---

## Filters management

### List bot/IP/domain filters

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/filters"
})
```

### Create an IP exclusion filter (POST)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/filters",
  method: "POST",
  body: {
    filter: {
      attr: "client_ip",
      type: "equal",
      value: "192.168.1.100",
      action: "exclude",
      status: "active"
    }
  }
})
```

`attr`: `client_ip` / `referer` / `url` / `title` / `uniq_id`.  
`type`: `equal` / `contain` / `start` / `regexp` / `interval` / `me`.  
`action`: `include` / `exclude` / `only_mirrors`.

### Exclude an IP range

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/filters",
  method: "POST",
  body: {
    filter: {
      attr: "client_ip",
      type: "interval",
      value: "10.0.0.0",
      value2: "10.255.255.255",
      action: "exclude",
      status: "active"
    }
  }
})
```

---

## Segments

### Create a persistent segment

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/segments",
  method: "POST",
  body: {
    segment: {
      name: "Mobile users from Moscow",
      expression: "ym:s:deviceCategory=='mobile' AND ym:s:regionCity=='Moscow'"
    }
  }
})
```

---

## Logs API — raw visits export

### Evaluate feasibility before submitting

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequests/evaluate",
  params: {
    date1: "2026-04-01",
    date2: "2026-04-30",
    source: "visits",
    fields: "ym:s:visitID,ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchPhrase,ym:s:visits,ym:s:bounceRate"
  }
})
```

Check `possible: true` before proceeding. If `possible: false`, the 10 GB quota is full — clean old jobs first.

### Submit a Logs API job (POST)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequests",
  method: "POST",
  params: {
    date1: "2026-04-01",
    date2: "2026-04-30",
    source: "visits",
    fields: "ym:s:visitID,ym:s:date,ym:s:dateTime,ym:s:lastTrafficSource,ym:s:lastSearchPhrase,ym:s:UTMSource,ym:s:UTMCampaign,ym:s:regionCity,ym:s:deviceCategory,ym:s:visits,ym:s:bounceRate",
    attribution: "LASTSIGN"
  }
})
```

Save the returned `request_id` immediately — it is needed for all subsequent steps.

### Poll job status

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequest/9876543"
})
```

Poll every 30–60 seconds. Continue when `status == "processed"`.

### Download a part (streaming for large files)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequest/9876543/part/0/download"
})
```

Iterate `parts[]` from the status response. Response is TSV with a header row.

### Clean a processed job (free quota)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequest/9876543/clean",
  method: "POST"
})
```

Always clean after downloading all parts. Skipping fills the 10 GB quota within days.

### List all Logs API jobs

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/logrequests"
})
```

---

## Data Import

### Upload ad expenses (CSV)

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/expenses/upload",
  method: "POST",
  params: {
    source: "other_ads"
  },
  body: "<CSV content per Metrika format>"
})
```

Requires scope `metrika:expenses` in addition to `metrika:write`.

---

## Operations (URL cleanup)

### Strip UTM parameters from stored URLs

```js
yandex_metrika_api({
  endpoint: "/management/v1/counter/12345678/operations",
  method: "POST",
  body: {
    operation: {
      action: "cut_parameter",
      attr: "url",
      value: "utm_source"
    }
  }
})
```

Repeat for each UTM parameter (`utm_medium`, `utm_campaign`, `utm_term`, `utm_content`). `action` values: `cut_parameter` / `replace` / `to_lower` / `cut_fragment` / `merge_https_and_http` / `merge_www_and_without_www` / `replace_domain`.

---

## Presets (canonical built-in reports)

### Sources summary via preset

```js
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    preset: "sources_summary",
    date1: "30daysAgo",
    date2: "yesterday",
    accuracy: "full"
  }
})
```

With `preset`, omit `dimensions` and `metrics` — the server substitutes them. Other preset names: `sources_search_engines`, `geo_country`, `tech_devices`, `audience_overview`.

---

## Attribution models

### Compare LASTSIGN vs FIRST attribution

```js
// LASTSIGN (default — last significant source)
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits,ym:s:goal42reaches",
    date1: "30daysAgo",
    date2: "yesterday",
    attribution: "LASTSIGN",
    accuracy: "full"
  }
})

// FIRST (first-ever click)
yandex_metrika_api({
  endpoint: "/stat/v1/data",
  params: {
    ids: "12345678",
    dimensions: "ym:s:lastTrafficSource",
    metrics: "ym:s:visits,ym:s:goal42reaches",
    date1: "30daysAgo",
    date2: "yesterday",
    attribution: "FIRST",
    accuracy: "full"
  }
})
```

Use `LAST_YANDEX_DIRECT_CLICK` when analysing Yandex.Direct campaigns to avoid attributing Direct sessions to `direct/none`.

---

## Common pitfalls

- **Always check `sampled` in the response.** Default `accuracy=medium` can return `sample_share: 0.05` (5% of data). Use `accuracy=full` for finance-critical reports.
- **One namespace per request.** `ym:s:` and `ym:pv:` cannot appear in the same `dimensions`/`metrics`. Use `EXISTS(ym:pv:URL=='...')` in `filters` for cross-namespace filtering.
- **`date2` should not be `today`.** Sessions are finalized over 3 days. Use `yesterday` for stable figures.
- **`limit` defaults to 100.** If you need all rows, set `limit=100000` and paginate with `offset` until the response has fewer rows than `limit`.
- **`offset` is 1-based**, not 0. First page is `offset=1`.
- **5000 req/day budget.** One request with 10 dimensions beats 10 separate requests. Cache responses for 5–15 min on dashboards.
- **Logs API: always evaluate first.** `GET .../evaluate` is free and tells you if the job is feasible before burning quota.
- **Logs API: always clean after downloading.** `POST .../clean` releases quota; skipping fills the 10 GB cap within days.
- **`request_id` must be persisted before processing the response** (worker crash recovery).
- **Polling cadence for Logs API**: start at 30–60 s, not 1 s — prevents 429 and quota drain.
- **Write operations (POST/PUT/DELETE) do not use the cache** — they go directly to the API and invalidate matching GET cache entries.
- **`force_refresh: true`** forces a fresh API call and overwrites the cache entry for the same GET params.

---

## Migration from v0.4 narrow tools

| Deleted v0.4 tool | Replacement via `yandex_metrika_api` |
|---|---|
| `metrika_search_phrases` | `yandex_metrika_api({endpoint: "/stat/v1/data", params: {ids: "<counter_id>", dimensions: "ym:s:lastSearchPhrase,ym:s:lastSourceEngine", metrics: "ym:s:visits,ym:s:bounceRate,ym:s:pageDepth", filters: "ym:s:lastTrafficSource=='organic'", date1: "7daysAgo", date2: "yesterday", sort: "-ym:s:visits", limit: 100, accuracy: "full"}})` |
| `metrika_traffic_summary` | `yandex_metrika_api({endpoint: "/stat/v1/data", params: {ids: "<counter_id>", dimensions: "ym:s:lastTrafficSource", metrics: "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageDepth,ym:s:avgVisitDurationSeconds", date1: "30daysAgo", date2: "yesterday", sort: "-ym:s:visits", accuracy: "full"}})` |

Note: all v0.4 narrow Metrika tools were removed in v0.5 without a backwards-compat shim. The `yandex_metrika_api` gateway provides equivalent or wider coverage for every removed tool.
