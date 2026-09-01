# Dimensions and metrics catalog

## Namespaces

| Namespace | Data level | When to use |
|---|---|---|
| `ym:s:` | Visit / session | Most reports: traffic, conversions, geo, sources |
| `ym:pv:` | Page view (hit) | Page-level analysis, content performance, exit pages |
| `ym:u:` | User (across sessions) | Cohorts, frequency, days-since-first-visit |
| `ym:up:` | User parameters | Custom user attributes (sent via JS API) |
| `ym:ad:` | Yandex.Direct | Spend, clicks, CPC from Direct |
| `ym:sp:` | Search phrases | On-site search queries |
| `ym:el:` | External links | Outbound clicks |
| `ym:dl:` | Downloads | File downloads |
| `ym:ev:` | E-commerce events | Purchases, cart, ROI |

**Rule**: dimensions and metrics in one request must share a namespace, or be joinable via `EXISTS()` in `filters`.

## Key dimensions

### `ym:s:` (sessions)

| Dimension | Description |
|---|---|
| `ym:s:date` | Visit date (YYYY-MM-DD) |
| `ym:s:datePeriod<unit>` | Bucket: day, week, month, quarter, year |
| `ym:s:hour` | Hour of visit (0–23) |
| `ym:s:dayOfWeek` | Day of week (0=Mon … 6=Sun) |
| `ym:s:lastTrafficSource` | Traffic source (organic, ad, direct, referral, social, email, internal, saved, recommend, undefined) |
| `ym:s:lastSourceEngine` | Search engine (yandex, google, bing, mail, ...) |
| `ym:s:lastSearchPhrase` | Search phrase |
| `ym:s:lastReferalSource` | Referrer site |
| `ym:s:lastSocialNetwork` | Social network |
| `ym:s:UTMSource` / `UTMMedium` / `UTMCampaign` / `UTMContent` / `UTMTerm` | UTM tags |
| `ym:s:browser` / `ym:s:browserName` | Browser |
| `ym:s:browserMajorVersion` / `MinorVersion` | Version |
| `ym:s:operatingSystem` / `ym:s:operatingSystemRoot` / `RootName` | OS |
| `ym:s:deviceCategory` | desktop / mobile / tablet / tv |
| `ym:s:mobilePhone` | Vendor |
| `ym:s:mobilePhoneModel` | Model |
| `ym:s:regionCountry` / `regionArea` / `regionCity` | Geography |
| `ym:s:isNewUser` | 'Yes' / 'No' |
| `ym:s:visitDuration` | Visit length (seconds) — used for bucketing |
| `ym:s:pageViews` | Pages per visit |
| `ym:s:goal<ID>IsReached` | Whether a given goal was reached — for filtering |
| `ym:s:startURL` | Entry URL |
| `ym:s:endURL` | Exit URL |

### `ym:pv:` (page views)

| Dimension | Description |
|---|---|
| `ym:pv:URL` | Full URL |
| `ym:pv:URLPath` | Path without query |
| `ym:pv:URLPathLevel1..5` | Path segments |
| `ym:pv:URLDomain` | Domain |
| `ym:pv:title` | `<title>` |
| `ym:pv:referer` | HTTP referer |
| `ym:pv:date` / `dateTime` | Hit date / time |

### `ym:u:` (users)

| Dimension | Description |
|---|---|
| `ym:u:userID` | Metrika client_id |
| `ym:u:firstVisitDate` | First-visit date |
| `ym:u:gender` | male / female |
| `ym:u:ageInterval` | 18–24 / 25–34 / 35–44 / 45–54 / 55+ |
| `ym:u:userVisits` / `userVisitsInterval` | Visit count |
| `ym:u:daysSinceFirstVisit` / `daysSincePreviousVisit` | Loyalty / recency |

### `ym:up:` (user params)

| Dimension | Description |
|---|---|
| `ym:up:paramsLevel1..5` | User-param hierarchy |

### `ym:ad:` (Direct)

| Dimension | Description |
|---|---|
| `ym:ad:directCampaignName` | Campaign name |
| `ym:ad:directOrder` | Ad order number |
| `ym:ad:directOrderType` | Ad type |
| `ym:ad:directPhraseOrCond` | Keyword phrase |
| `ym:ad:directBannerGroup` | Ad group |

## Key metrics

### `ym:s:` metrics

| Metric | Counts |
|---|---|
| `ym:s:visits` | Number of visits (sessions) |
| `ym:s:users` | Unique users |
| `ym:s:pageviews` | Page views (within sessions) |
| `ym:s:bounceRate` | Bounce rate (% < 15 s or 1 page) |
| `ym:s:percentNewVisitors` | % new visitors |
| `ym:s:pageDepth` | Avg pages per visit |
| `ym:s:avgVisitDurationSeconds` | Avg visit length, seconds |
| `ym:s:goal<ID>reaches` | Goal N reaches |
| `ym:s:goal<ID>conversionRate` | Conversion rate for goal N (%) |
| `ym:s:goal<ID>users` | Unique users who reached the goal |
| `ym:s:goal<ID>revenue` | Revenue for goal N |
| `ym:s:sumGoalReachesAny` | Sum of reaches across all goals |
| `ym:s:anyGoalConversionRate` | CR for any goal |
| `ym:s:robotPercentage` | % robots |
| `ym:s:cookieEnabledPercentage` | % with cookies |
| `ym:s:productImpressionsUniq` / `productBasketsUniq` / `productPurchasedUniq` | E-commerce funnel |
| `ym:s:ecommercePurchases` | Purchases |
| `ym:s:ecommerceRevenuePerVisit` | Revenue per visit |

### `ym:pv:` metrics

| Metric | Counts |
|---|---|
| `ym:pv:pageviews` | Page views |
| `ym:pv:users` | Unique users on the page |

### `ym:u:` metrics

| Metric | Counts |
|---|---|
| `ym:u:users` | Unique users |
| `ym:u:visitsPerUser` | Avg visits per user |

### `ym:ad:` metrics (Direct)

| Metric | Counts |
|---|---|
| `ym:ad:clicks` | Clicks from Direct |
| `ym:ad:RUBAdCost` | Spend in RUB |
| `ym:ad:<currency>AdCost` | Spend in another currency |
| `ym:ad:visits` | Visits attributed to a Direct click |

## Goals (`goal<ID>`)

`<ID>` is the `goal_id` returned by the Management API:

```
GET /management/v1/counter/{counter_id}/goals
```

Goal metrics always follow `ym:s:goal<ID><suffix>`:

- `reaches` — number of reaches
- `users` — unique users
- `conversionRate` — CR (%)
- `revenue` — revenue
- `bounceRate` — bounce rate within goal-reaching sessions
- `visits` — visits with the goal

## Parameterization

Some dimensions take an integer parameter: `ym:s:paramsLevel<N>`, `ym:s:goal<ID>IsReached`. `<N>` and `<ID>` must be concrete integers, not the literal `<ID>`.

## Where to find the full list

Full catalog: https://yandex.com/dev/metrika/en/stat/openapi/dimensions and https://yandex.com/dev/metrika/en/stat/openapi/metrics — OpenAPI description, filterable by namespace / type / availability. Names are stable — `ym:s:visits` has existed since 2013.

## Common recipes

1. **Traffic sources by day**:
   `dimensions=ym:s:date,ym:s:lastTrafficSource&metrics=ym:s:visits,ym:s:users`
2. **Goal conversion by UTM**:
   `dimensions=ym:s:UTMSource,ym:s:UTMCampaign&metrics=ym:s:visits,ym:s:goal12345reaches,ym:s:goal12345conversionRate`
3. **Geography**:
   `dimensions=ym:s:regionCountry,ym:s:regionCity&metrics=ym:s:users,ym:s:bounceRate`
4. **Top pages**:
   `dimensions=ym:pv:URLPath&metrics=ym:pv:pageviews,ym:pv:users&sort=-ym:pv:pageviews`
5. **Cohorts by first-visit date**:
   `dimensions=ym:u:firstVisitDate&metrics=ym:u:users,ym:u:visitsPerUser`
6. **Direct spend vs revenue**:
   `dimensions=ym:ad:directCampaignName&metrics=ym:ad:clicks,ym:ad:RUBAdCost,ym:s:goal12345revenue`
