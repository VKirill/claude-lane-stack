---
name: google-analytics
description: "[RU: ga4, гугл аналитика, аналитика 4] GA4 Data API v1beta — service account or OAuth. properties/{id}:runReport with dimensions, metrics, dateRanges, FilterExpression DSL (EXACT/CONTAINS/REGEXP, inList, numeric, between, and/or/not), orderBys, limit/offset. runRealtimeReport (30 min), runPivotReport, cohortSpec, batchRunReports (5-in-1). Admin API v1beta for customDimensions + conversionEvents. Token quotas per property and project. SKIP: Universal Analytics v3 sunset 2024-07 (→universal-analytics); Yandex.Metrika (→yandex-metrica); Search Console (→google-search-console); GTM (→google-tag-manager); BigQuery export (→bigquery); Cloud auth (→google-cloud-auth)."
stacks:
  - google-analytics
  - analytics
  - python
  - nodejs
tags:
  - analytics
  - google
  - ga4
  - reporting
  - oauth
  - marketing
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## Version Requirements (May 2026)

**Primary pins:**
- GA4 Data API: `v1beta` (stable; base `https://analyticsdata.googleapis.com/v1beta/`)
- GA4 Admin API: `v1beta` (`https://analyticsadmin.googleapis.com/v1beta/`)
- Python client: `google-analytics-data >= 0.18`
- Node.js client: `@google-analytics/data ^4.x`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-08-24

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read only the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Programmatic pulls of GA4 data for dashboards: sessions, active users, conversions by source / channel / device
- Daily GA4 snapshot to PostgreSQL for SQL analytics and LTV calculations (aggregates, not event-level)
- Real-time traffic monitoring (last 30 min) for campaign launches, deployment monitoring, alerting
- Comparative reporting across multiple periods (multiple `dateRanges` in one request)
- Complex filtering: building `FilterExpression` with `andGroup` / `orGroup` / `notExpression`, `stringFilter` (EXACT, BEGINS_WITH, ENDS_WITH, CONTAINS, FULL_REGEXP, PARTIAL_REGEXP), `inListFilter`, `numericFilter`, `betweenFilter`
- Pivot reports (2D crosstabs: source x device, country x device)
- Cohort retention reports (`firstSessionDate` cohorts, DAILY/WEEKLY/MONTHLY granularity, `cohortActiveUsers`)
- Batch efficiency: packing 5 reports into one HTTP call via `batchRunReports`
- Configuration: listing properties, custom dimensions, conversion events via Admin API v1beta
- Token budget monitoring (`returnPropertyQuota: true` and reading `PropertyQuota` in the response)
- Backend authorization: service account granted access via Admin -> Property -> Property Access Management

## Do not use this skill when

- Universal Analytics (UA, `UA-XXXXX`) — sunset 2024-07-01, API disabled. Migration is not "switch the ID"; semantics differ (sessions vs events, dimensions, attribution). Move the account to GA4 first.
- Event-level export (millions of raw rows) — Data API returns aggregates; for raw events use BigQuery Export GA4 (cascade -> `bigquery`)
- Russian analog of GA4 — `yandex-metrica` (cascade -> `yandex-metrica`); a different dimension / metric universe
- Search Console data (CTR / impressions / positions) — `google-search-console` (cascade)
- Managing containers / triggers / tags — Google Tag Manager API, `google-tag-manager` (cascade)
- Generic Google Cloud auth setup (service account creation, key issuance, `gcloud auth`) — `google-cloud-auth` (cascade)
- A/B testing inside GA4 — either GTM + Optimize (deprecated) or a dedicated feature flag service
- Writing data into GA4 — Data API is read-only; for event writes use Measurement Protocol (different API)
- Parsing the GA4 UI (Explorations, default Acquisition / Engagement reports) — Data API does not mirror UI reports 1:1; build the slice yourself

## Purpose

Google Analytics Data API v1beta is the official programmatic surface for GA4. It returns the same aggregates the UI shows. Five core reporting methods: `runReport` (standard), `runRealtimeReport` (last 30 min), `runPivotReport` (crosstabs), `batchRunReports` (5 reports in 1 call), `runReport` with `cohortSpec` (cohort analysis). Admin API v1beta covers configuration (properties, customDimensions, conversionEvents). Auth: OAuth 2.0 (user consent) or service account (backend).

This skill is **high-stakes** because:

1. **Property ID is not Measurement ID.** `properties/123456789` is the numeric ID from Admin -> Property Settings. `G-XXXXXXX` is a data stream Tag ID and **will not work** in the API. `properties/G-XXX:runReport` returns 400 INVALID_ARGUMENT.
2. **The service account must be explicitly granted in Property Access Management** on the GA4 side. Holding a key file is not enough; without a Viewer / Analyst grant the API returns 403 PERMISSION_DENIED. Google emails the service account automatically.
3. **Token quota is consumed by complex requests.** Standard property: 200,000 tokens/day, 40,000/hour; per-project-per-property 14,000/hour. Long date range x many dimensions x high cardinality (`pagePath`, `eventName`) x filters can cost tens of tokens per call. Enable `returnPropertyQuota: true` and log it.
4. **Sampling can occur.** GA4 samples when event volume exceeds thresholds (different from UA, plan-dependent). Signals: `metadata.samplingMetadatas` and `metadata.dataLossFromOtherRow`. The UA 360 "no sampling" assumption does not port 1:1.
5. **dimensionFilter vs metricFilter.** `dimensionFilter` runs before aggregation (SQL WHERE), `metricFilter` after (SQL HAVING). Swapping them yields empty or surprising results.
6. **Realtime supports a limited dimension / metric set.** Many historical dimensions are missing; check the realtime metadata before authoring.
7. **`runReport` row limits:** default 10,000, max 250,000. For larger slices use `offset` / `limit` pagination or split by `dateRanges`.
8. **GA4 conversions are Key Events (since 2026).** `conversions` and `eventCount` for a specific event require `dimensionFilter` on `eventName`.
9. **Concurrent requests per property: 10.** Parallel pulls must respect that or hit 429 RESOURCE_EXHAUSTED.
10. **Audience Export is a separate async surface** with its own quotas. Do not confuse with `runReport`.

The skill owns provider-domain knowledge: endpoints, request shape, FilterExpression DSL, token budget, GA4-vs-UA semantics. Generic HTTP and auth belong to runtime skills (`httpx`, `nodejs`, `google-cloud-auth`).

## Capabilities

### Authentication: service account vs OAuth user

Two auth paths:

**Service account (backend, recommended for scripts):**
1. Create a service account in Google Cloud Console, download the JSON key
2. Enable Google Analytics Data API + Admin API in the Cloud project
3. In GA4: Admin -> Property -> Property Access Management, add the service account email (`xxx@yyy.iam.gserviceaccount.com`) with `Viewer` (or `Analyst` for marking) role
4. `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`
5. The client takes no args: `BetaAnalyticsDataClient()`

**OAuth user flow (interactive):** scope `https://www.googleapis.com/auth/analytics.readonly` (read) or `analytics.edit` (Admin API mutations). Token refresh follows standard Google OAuth.

> Full reference: [references/setup.md](references/setup.md)

### Property ID — where to find it and how to use it

`properties/{property_id}` is numeric, e.g. `properties/123456789`. It is **not** `G-XXXXXXX` (that is a Measurement ID for a data stream and is invalid here). Location: GA4 -> Admin -> Property Settings -> "Property ID" line. Pass it in code as `f"properties/{prop_id}"`.

> Full reference: [references/setup.md](references/setup.md)

### runReport — standard report

Minimum: `property`, `dateRanges`, and at least one `dimensions` or `metrics`. Full field set: `dimensions[]`, `metrics[]` (with `expression` for derived metrics), `dateRanges[]` (up to 4), `dimensionFilter`, `metricFilter`, `orderBys[]` (metric / dimension / pivot + `desc`), `limit` (max 250,000), `offset`, `metricAggregations[]` (TOTAL / MIN / MAX / COUNT), `keepEmptyRows`, `returnPropertyQuota`, `currencyCode` (ISO 4217), `cohortSpec`.

> Full reference: [references/run-report.md](references/run-report.md)

### FilterExpression DSL

A tree DSL: each node is either a `filter` (leaf), an `andGroup` / `orGroup` (container with `expressions[]`), or a `notExpression` (unary with `expression`). A leaf `filter` carries `fieldName` plus one of: `stringFilter` (matchType EXACT, BEGINS_WITH, ENDS_WITH, CONTAINS, FULL_REGEXP, PARTIAL_REGEXP + `caseSensitive`), `inListFilter` (`values[]`), `numericFilter` (EQUAL, LESS_THAN, GREATER_THAN, ...), `betweenFilter` (`fromValue`, `toValue`). Nesting is arbitrary.

> Full reference: [references/filters-and-expressions.md](references/filters-and-expressions.md)

### dimensionFilter vs metricFilter

`dimensionFilter` filters **before** aggregation (like SQL WHERE). `metricFilter` filters **after** (SQL HAVING). Example: `dimensionFilter` on `eventName == "purchase"` keeps only purchase events; `metricFilter` on `totalRevenue > 100` keeps rows where revenue exceeds 100 after aggregation. Swapping the two leads to unexpected zeros.

> Full reference: [references/filters-and-expressions.md](references/filters-and-expressions.md)

### runRealtimeReport — last 30 minutes

Window: 30 minutes (60 for GA4 360). Supports `dimensions`, `metrics`, `dimensionFilter`, `metricFilter`, `limit`, `metricAggregations`, `orderBys`, `returnPropertyQuota`, `minuteRanges[]` (up to 2; `startMinutesAgo` defaults to 29, `endMinutesAgo` to 0). Dimensions / metrics are a narrower set: `unifiedScreenName`, `country`, `city`, `deviceCategory`, `eventName` are available; many historical dimensions are not.

> Full reference: [references/realtime.md](references/realtime.md)

### runPivotReport — 2D crosstabs

Returns data in pivot format (Excel-style pivot table). Each `pivots[]` entry is a separate axis with `fieldNames[]` (dimensions for that axis), `orderBys[]`, `offset`, `limit`, `metricAggregations[]`. Dimensions are visible only if included in a pivot. Typical use: source x device, country x deviceCategory.

> Full reference: [references/pivot-and-cohort.md](references/pivot-and-cohort.md)

### cohortSpec — cohort analysis

Used inside `runReport` via `cohortSpec`. A cohort groups users by `firstSessionDate` (or another dimension). `cohortsRange.granularity` is DAILY / WEEKLY / MONTHLY; `startOffset` / `endOffset` set the observation window. Cohort dimensions: `cohort`, `cohortNthDay`, `cohortNthWeek`, `cohortNthMonth`. Cohort metrics: `cohortActiveUsers`, `cohortTotalUsers`.

> Full reference: [references/pivot-and-cohort.md](references/pivot-and-cohort.md)

### batchRunReports — 5 in 1

Up to 5 `RunReportRequest` objects in a single HTTP call on the same property. Cuts latency and overhead. Ideal for dashboards: 5 different slices (sessions by source, conversions by event, countries, devices, pages) in one request.

> Full reference: [references/batch-and-quotas.md](references/batch-and-quotas.md)

### Quota model

Standard property:
- **Core Tokens / property / day:** 200,000
- **Core Tokens / property / hour:** 40,000
- **Core Tokens / project / property / hour:** 14,000
- **Concurrent Requests / property:** 10
- **Server Errors / project / property / hour:** 10
- **Thresholded Requests / property / hour:** 120

GA4 360 multiplies these by 10x. Realtime and Funnel categories share the same shape with independent counters. Token cost grows with: date range length, dimension / metric count, dimension cardinality (`pagePath`, `eventName` are expensive), filter complexity, and property event volume. Enable `returnPropertyQuota: true` and read `PropertyQuota` from the response.

> Full reference: [references/batch-and-quotas.md](references/batch-and-quotas.md)

### Admin API v1beta

GA4 configuration: `accounts.list`, `properties.list`, `properties.get`, `customDimensions.list`, `customMetrics.list`, `conversionEvents.list` (deprecated, replaced by Key Events), `properties.runAccessReport`. Requires scope `analytics.readonly` (read) or `analytics.edit` (mutations). Python: `google-analytics-admin`; Node: `@google-analytics/admin`.

> Full reference: [references/admin-api.md](references/admin-api.md)

### Sampling

GA4 samples when event volume for the requested slice exceeds threshold (plan-dependent, different from UA). Response signals: `metadata.samplingMetadatas` (per `dateRange`) and `metadata.dataLossFromOtherRow` (true when cardinality cap truncated rows into the `(other)` bucket). 360 has higher thresholds but is not "zero sampling". To reduce sampling: fewer dimensions, shorter date range, prefilter before selection.

> Full reference: [references/run-report.md](references/run-report.md)

### End-to-end API workflow

For the integrated walkthrough (bootstrap, request lifecycle, pagination, quota budgeting, daily ETL with PostgreSQL UPSERT), see the workflow reference.

> Full reference: [references/workflow.md](references/workflow.md)

## Quick Reference Tables

### Endpoints

| Method | Endpoint |
|---|---|
| Run report | `POST /v1beta/properties/{id}:runReport` |
| Run pivot report | `POST /v1beta/properties/{id}:runPivotReport` |
| Run realtime | `POST /v1beta/properties/{id}:runRealtimeReport` |
| Batch run reports | `POST /v1beta/properties/{id}:batchRunReports` |
| Batch pivot reports | `POST /v1beta/properties/{id}:batchRunPivotReports` |
| Check compatibility | `POST /v1beta/properties/{id}:checkCompatibility` |
| Get metadata | `GET /v1beta/properties/{id}/metadata` |
| Admin: list properties | `GET /v1beta/properties?filter=parent:accounts/{aid}` |
| Admin: custom dimensions | `GET /v1beta/properties/{id}/customDimensions` |
| Admin: conversion events (deprecated 2026 → use keyEvents) | `GET /v1beta/properties/{id}/conversionEvents` |
| Admin: key events | `GET /v1beta/properties/{id}/keyEvents` |

Base hosts: `https://analyticsdata.googleapis.com` (Data) and `https://analyticsadmin.googleapis.com` (Admin).

### Common dimensions

| Category | Dimensions |
|---|---|
| Time | `date` (YYYYMMDD), `dateHour`, `hour`, `dayOfWeek`, `dayOfWeekName` |
| Traffic source | `sessionSource`, `sessionMedium`, `sessionSourceMedium`, `sessionCampaignName`, `firstUserSource`, `firstUserMedium`, `defaultChannelGroup`, `sessionDefaultChannelGroup` |
| Page / screen | `pagePath`, `pageTitle`, `pageLocation`, `hostName`, `unifiedScreenName` |
| Device | `deviceCategory`, `browser`, `operatingSystem`, `mobileDeviceModel`, `screenResolution` |
| Geo | `country`, `countryId`, `region`, `city`, `cityId`, `continent` |
| Event | `eventName`, `isKeyEvent` |
| User | `newVsReturning`, `userAgeBracket`, `userGender` (thresholded) |
| E-commerce | `transactionId`, `itemName`, `itemId`, `itemBrand`, `itemCategory`, `itemVariant`, `currencyCode` |

### Common metrics

| Category | Metrics |
|---|---|
| Users | `activeUsers`, `totalUsers`, `newUsers` |
| Engagement | `sessions`, `screenPageViews`, `eventCount`, `engagementRate`, `averageSessionDuration`, `bounceRate`, `userEngagementDuration` |
| Conversion | `conversions`, `keyEvents`, `eventValue` |
| Revenue | `totalRevenue`, `purchaseRevenue`, `averagePurchaseRevenue`, `itemRevenue`, `transactions` |

### FilterExpression operators

| Filter | Operators |
|---|---|
| `stringFilter` | EXACT, BEGINS_WITH, ENDS_WITH, CONTAINS, FULL_REGEXP, PARTIAL_REGEXP (+ `caseSensitive`) |
| `inListFilter` | `values[]` (+ `caseSensitive`) |
| `numericFilter` | EQUAL, LESS_THAN, LESS_THAN_OR_EQUAL, GREATER_THAN, GREATER_THAN_OR_EQUAL |
| `betweenFilter` | `fromValue`, `toValue` (inclusive) |
| Logical | `andGroup.expressions[]`, `orGroup.expressions[]`, `notExpression.expression` |

### OrderBy variants

| Variant | Fields | Notes |
|---|---|---|
| Metric | `metric.metricName` | Sort by metric value |
| Dimension | `dimension.dimensionName` + `orderType` (ALPHANUMERIC, CASE_INSENSITIVE_ALPHANUMERIC, NUMERIC) | Sort by dimension value |
| Pivot | `pivot.metricName` + `pivot.pivotSelections[]` | `runPivotReport` only |
| Direction | `desc: true` | Ascending by default |

## Common Mistakes

1. **Using Measurement ID `G-XXXXXXX` instead of Property ID.** The API expects the numeric ID; `G-XXXXX` belongs to a Tag data stream, not the reporting surface.
2. **Forgetting to grant the service account access.** Key in place, API still 403. Open Admin -> Property Access Management and add the email.
3. **Enabling Data API in Cloud Console but forgetting Admin API** (or vice versa). Enable both for the full picture.
4. **Confusing `dimensionFilter` and `metricFilter`.** `eventName == "purchase"` belongs in `dimensionFilter`; `totalRevenue > 100` belongs in `metricFilter`.
5. **Requesting UA-style metrics.** There is no plain `users`; use `activeUsers`, `totalUsers`, `newUsers`. `pageviews` -> `screenPageViews`. `goalCompletionsAll` -> `conversions` or `keyEvents`.
6. **Realtime with dimensions from the standard API.** Realtime supports a narrow set. Verify via `getMetadata` for realtime.
7. **Expecting `limit > 250,000`.** Paginate via `offset` or split by `dateRanges`.
8. **One huge request for 18 months x 5 dimensions x `pagePath`.** Burns thousands of tokens. Split by week, cache in DB, refresh incrementally.
9. **Parallelizing more than 10 requests per property.** 429 follows. Use a semaphore at 8.
10. **Skipping `returnPropertyQuota`.** Quota issues become un-debuggable after the fact.
11. **Trusting total = sum(rows).** With `metricAggregations: [TOTAL]`, totals arrive in a separate field with their own aggregation rules.
12. **Sampling causing "weird numbers".** Check `response.metadata.samplingMetadatas` before investigating data.
13. **Ignoring the `(other)` bucket.** When cardinality is high, GA4 collapses the tail. `dataLossFromOtherRow: true` means filter further or drop dimensions.
14. **Treating GA4 as a drop-in for UA.** Sessions count differently (session timeout, cross-device); bounce became engaged sessions. Do not compare absolute numbers 1:1 with a UA dashboard.
15. **Committing service account keys to git.** Use `.env` only or a secrets manager. A leak grants access to every property in the grant list.

## Red Flags

- **403 on `runReport`** — service account missing from Property Access Management, Data API disabled in the Cloud project, or OAuth scope insufficient
- **400 INVALID_ARGUMENT with `properties/G-XXX`** — Measurement ID passed instead of Property ID
- **429 RESOURCE_EXHAUSTED** — token or concurrent budget exhausted. Read `PropertyQuota`, wait for the hourly / daily reset, or change strategy
- **`response.metadata.dataLossFromOtherRow: true`** — cardinality cap hit, `(other)` bucket present, slice incomplete
- **Non-empty `response.metadata.samplingMetadatas`** — data is sampled. Reduce scope.
- **Empty `rows[]` despite expected data** — `dimensionFilter` too strict, wrong `eventName`, or no data in `dateRange`
- **Sudden drop versus the GA4 UI** — identity settings differ (Blended vs Observed vs Device-only), `currencyCode` differs, or a property filter differs
- **`totalRevenue` reads 0 but UI does not** — wrong metric (`totalRevenue` vs `purchaseRevenue` vs `eventValue`)
- **Long-running request > 30s** — split by `dateRanges` or move to Audience Export for very large slices

## Behavioral Traits

- **Property ID is sacred.** Every code example must check that the numeric ID is used. If the snippet says `G-XXXXX`, stop and explain.
- **Quota-aware by default.** Always pass `returnPropertyQuota: true` in scripts and log tokens. At scale, track a daily budget counter in Redis.
- **Fail loudly on 403.** Do not swallow permission errors as "no data". Re-check Property Access Management.
- **Sampling check.** Inspect `metadata.samplingMetadatas` on every response before using the data for decisions.
- **Cache aggressively.** Identical slices get re-requested often. Persist to a DB with TTL equal to the GA4 stabilization window (~48h for conversions).
- **GA4 is not UA.** Never help "port a UA report 1:1 to GA4" without discussing semantic differences first.

## Important Constraints

- **GA4 properties only.** UA is not supported. If a user shares `UA-XXXXX-Y`, stop and ask for a GA4 Property ID.
- **Read-only.** Data API does not write events. For writes use Measurement Protocol (a different surface).
- **v1beta semantics may shift.** It is a beta; breaking changes are possible. Verify against the production docs for critical integrations.
- **Realtime != historical.** 30-minute window, narrow dimension set. Do not use it as a daily reporting source.
- **Token quota is not a rate limit.** Resets are hourly / daily / weekly. Sleeping 5 seconds does not help on token quotas; it helps on concurrent quotas.
- **Service account key files are secrets.** Never publish.
- **Identity settings affect numbers.** Property -> Reporting Identity (Blended / Observed / Device-only) changes user deduplication. The API returns the configured model, not raw data.

## Related Skills

- `yandex-metrica` — Russian GA4 analogue; different semantics (visits vs sessions, goals vs events) and a separate API
- `google-search-console` — query / CTR / impression / position data from Google Search; pair with GA4 for the marketing funnel
- `bigquery` (cascade) — GA4 raw event export. When you need event-level data, CRM joins, or ML, use BigQuery, not the Data API
- `google-tag-manager` (cascade) — container, tag, and trigger management; not a reporting source
- `google-cloud-auth` (cascade) — generic service account setup, IAM, `gcloud` CLI
- `httpx` / `nodejs` — runtime HTTP, retries, rate limiting for downstream pipelines
- `postgresql` / `pandas` / `polars` — downstream storage and analytics over snapshots

## API Reference Table

| Topic | Reference |
|---|---|
| Setup (auth, property_id, scopes) | [references/setup.md](references/setup.md) |
| runReport (full schema, fields, examples) | [references/run-report.md](references/run-report.md) |
| FilterExpression DSL | [references/filters-and-expressions.md](references/filters-and-expressions.md) |
| Pivot and Cohort | [references/pivot-and-cohort.md](references/pivot-and-cohort.md) |
| Realtime API | [references/realtime.md](references/realtime.md) |
| Batch + Quota | [references/batch-and-quotas.md](references/batch-and-quotas.md) |
| Admin API v1beta | [references/admin-api.md](references/admin-api.md) |
| Errors (400/401/403/429/500) | [references/errors.md](references/errors.md) |
| End-to-end workflow + daily ETL | [references/workflow.md](references/workflow.md) |
| Integration (Python + Node + REST, PG schema, queries) | [references/integration.md](references/integration.md) |
