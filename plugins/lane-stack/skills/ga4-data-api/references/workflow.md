# End-to-end Workflow

A condensed walk-through of GA4 Data API integration: from auth bootstrap to a daily ETL snapshot in PostgreSQL.

## 1. Bootstrap

**Two paths, pick one:**

- **Service account (backend, recommended)** — create the account in Google Cloud Console, download the JSON key, enable Google Analytics Data API + Admin API in the project.
- **OAuth user flow** — `https://www.googleapis.com/auth/analytics.readonly` scope; access + refresh token.

**Grant access on the GA4 side (most common cause of 403):**

GA4 -> Admin -> Property Access Management -> add `xxx@yyy.iam.gserviceaccount.com` -> role `Viewer` (or `Analyst`).

Find the numeric **Property ID** in Admin -> Property Settings (e.g. `381112233`). **Do not** use the Measurement ID `G-XXXXXXX` — that is a tag stream identifier and the API rejects it with 400 INVALID_ARGUMENT.

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/srv/keys/ga4-sa.json
export GA4_PROPERTY_ID=381112233
```

## 2. runReport lifecycle

`POST https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport`

Request shape (most-used fields):

| Field | Notes |
|---|---|
| `dimensions[]` | up to 9 |
| `metrics[]` | up to 10 (`expression` for derived metrics) |
| `dateRanges[]` | up to 4; `startDate`, `endDate`; `today`, `yesterday`, `NdaysAgo` shortcuts |
| `dimensionFilter` | FilterExpression tree, runs before aggregation (WHERE) |
| `metricFilter` | FilterExpression tree, runs after aggregation (HAVING) |
| `orderBys[]` | metric / dimension / pivot + `desc` |
| `limit` | default 10,000; max 250,000 |
| `offset` | pagination cursor |
| `metricAggregations[]` | TOTAL / MIN / MAX / COUNT |
| `keepEmptyRows` | bool |
| `returnPropertyQuota` | enable per-request quota stats |
| `currencyCode` | ISO 4217 |
| `cohortSpec` | cohort analysis (see step 6) |

Response: `dimensionHeaders`, `metricHeaders`, `rows[]`, `totals[]`, `metadata` (samplingMetadatas, dataLossFromOtherRow, currencyCode, timeZone), and `propertyQuota` when requested.

### Python SDK

```python
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange,
)

client = BetaAnalyticsDataClient()
resp = client.run_report(RunReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="date"), Dimension(name="sessionSourceMedium")],
    metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="conversions")],
    date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
    limit=100_000,
    return_property_quota=True,
))
print(resp.property_quota.tokens_per_day)
```

### Node SDK

```ts
import { BetaAnalyticsDataClient } from "@google-analytics/data";

const client = new BetaAnalyticsDataClient();
const [resp] = await client.runReport({
  property: `properties/${propertyId}`,
  dimensions: [{ name: "date" }, { name: "sessionSourceMedium" }],
  metrics: [{ name: "sessions" }, { name: "activeUsers" }, { name: "conversions" }],
  dateRanges: [{ startDate: "7daysAgo", endDate: "yesterday" }],
  limit: 100_000,
  returnPropertyQuota: true,
});
```

### REST + JWT fallback (httpx)

```python
import httpx, time, jwt  # pyjwt
from pathlib import Path
import json

key = json.loads(Path("/srv/keys/ga4-sa.json").read_text())
now = int(time.time())
assertion = jwt.encode(
    {
        "iss": key["client_email"],
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    },
    key["private_key"], algorithm="RS256",
)
tok = httpx.post(
    "https://oauth2.googleapis.com/token",
    data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
    timeout=10,
).json()["access_token"]

resp = httpx.post(
    f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
    headers={"Authorization": f"Bearer {tok}"},
    json={
        "dimensions": [{"name": "date"}, {"name": "sessionSourceMedium"}],
        "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "conversions"}],
        "dateRanges": [{"startDate": "7daysAgo", "endDate": "yesterday"}],
        "returnPropertyQuota": True,
    },
    timeout=30,
).json()
```

## 3. FilterExpression DSL

A tree of nodes. Containers: `andGroup`, `orGroup`, `notExpression`. Leaf: `filter` with `fieldName` plus one of `stringFilter` / `inListFilter` / `numericFilter` / `betweenFilter`.

| Filter | Operators / fields |
|---|---|
| `stringFilter` | matchType EXACT, BEGINS_WITH, ENDS_WITH, CONTAINS, FULL_REGEXP, PARTIAL_REGEXP + `caseSensitive` |
| `inListFilter` | `values[]` + `caseSensitive` |
| `numericFilter` | EQUAL, LESS_THAN, LESS_THAN_OR_EQUAL, GREATER_THAN, GREATER_THAN_OR_EQUAL |
| `betweenFilter` | `fromValue`, `toValue` (inclusive) |

`dimensionFilter` runs **before** aggregation (SQL WHERE). `metricFilter` runs **after** aggregation (SQL HAVING). Mixing them up yields empty results or surprising zeros.

```json
{
  "dimensionFilter": {
    "andGroup": {
      "expressions": [
        {"filter": {"fieldName": "eventName",
                     "stringFilter": {"matchType": "EXACT", "value": "purchase"}}},
        {"notExpression": {"expression": {"filter": {"fieldName": "deviceCategory",
                     "inListFilter": {"values": ["tablet"]}}}}}
      ]
    }
  },
  "metricFilter": {
    "filter": {"fieldName": "totalRevenue",
               "numericFilter": {"operation": "GREATER_THAN",
                                  "value": {"doubleValue": 100}}}
  }
}
```

## 4. runRealtimeReport

Last 30 minutes (60 for GA4 360). Endpoint: `POST /v1beta/properties/{id}:runRealtimeReport`.

Differences vs `runReport`:

- No `dateRanges`. Use `minuteRanges[]` (up to 2; `startMinutesAgo` default 29, `endMinutesAgo` default 0).
- Narrower dimension / metric set (e.g. `unifiedScreenName`, `country`, `city`, `deviceCategory`, `eventName`).

```python
from google.analytics.data_v1beta.types import RunRealtimeReportRequest, MinuteRange

resp = client.run_realtime_report(RunRealtimeReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="country")],
    metrics=[Metric(name="activeUsers")],
    minute_ranges=[MinuteRange(start_minutes_ago=29, end_minutes_ago=0)],
))
```

## 5. runPivotReport

Pivot table on top of `runReport`. Each entry in `pivots[]` is an axis with `fieldNames[]`, `orderBys[]`, `offset`, `limit`, `metricAggregations[]`. Dimensions appear in the result only if they belong to a pivot.

```python
from google.analytics.data_v1beta.types import RunPivotReportRequest, Pivot, OrderBy

resp = client.run_pivot_report(RunPivotReportRequest(
    property=f"properties/{property_id}",
    dimensions=[Dimension(name="country"), Dimension(name="deviceCategory")],
    metrics=[Metric(name="sessions")],
    date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
    pivots=[
        Pivot(field_names=["country"], limit=10,
              order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)]),
        Pivot(field_names=["deviceCategory"], limit=3),
    ],
))
```

## 6. runReport with cohortSpec

Cohort retention. Used inside `runReport` via `cohortSpec`. A cohort groups users by `firstSessionDate` (or another dimension); `cohortsRange.granularity` is DAILY / WEEKLY / MONTHLY; `startOffset` / `endOffset` define the observation window. The cohort date range comes from `cohortSpec`, not from `dateRanges`.

Cohort dimensions: `cohort`, `cohortNthDay`, `cohortNthWeek`, `cohortNthMonth`. Cohort metrics: `cohortActiveUsers`, `cohortTotalUsers`.

```json
{
  "dimensions": [{"name": "cohort"}, {"name": "cohortNthWeek"}],
  "metrics": [{"name": "cohortActiveUsers"}],
  "cohortSpec": {
    "cohorts": [{"name": "cohort_0",
                  "dimension": "firstSessionDate",
                  "dateRange": {"startDate": "2026-04-01", "endDate": "2026-04-07"}}],
    "cohortsRange": {"granularity": "WEEKLY", "startOffset": 0, "endOffset": 4}
  }
}
```

## 7. batchRunReports

Up to 5 `RunReportRequest` objects in a single HTTP call on the same property. Reduces overhead and round-trip latency; tokens are billed per inner request, not per batch.

```python
from google.analytics.data_v1beta.types import BatchRunReportsRequest

batch = client.batch_run_reports(BatchRunReportsRequest(
    property=f"properties/{property_id}",
    requests=[req_sessions_by_source, req_conversions_by_event,
              req_countries, req_devices, req_pages],
))
for r in batch.reports:
    handle(r)
```

## 8. Admin API v1beta

Base host: `https://analyticsadmin.googleapis.com`.

| Use | Endpoint |
|---|---|
| List accounts | `GET /v1beta/accounts` |
| List properties under an account | `GET /v1beta/properties?filter=parent:accounts/{aid}` |
| Get property | `GET /v1beta/properties/{id}` |
| Custom dimensions | `GET /v1beta/properties/{id}/customDimensions` |
| Custom metrics | `GET /v1beta/properties/{id}/customMetrics` |
| Conversion events (legacy, replaced by Key Events) | `GET /v1beta/properties/{id}/conversionEvents` |

Python: `google-analytics-admin` (`AnalyticsAdminServiceClient`). Node: `@google-analytics/admin`. Scope: `analytics.readonly` for reads, `analytics.edit` for mutations.

## 9. Quota management

Standard property (multiply by 10 for GA4 360):

| Category | Limit |
|---|---|
| Core tokens / property / day | 200,000 |
| Core tokens / property / hour | 40,000 |
| Core tokens / project / property / hour | 14,000 |
| Concurrent requests / property | 10 |
| Server errors / project / property / hour | 10 |
| Thresholded requests / property / hour | 120 |

Realtime and Funnel categories track independent counters with the same numeric tiers.

Always set `returnPropertyQuota: true` and read `response.propertyQuota`:

```python
pq = resp.property_quota
print(pq.tokens_per_day.consumed, pq.tokens_per_day.remaining)
print(pq.tokens_per_hour.consumed, pq.tokens_per_hour.remaining)
print(pq.concurrent_requests.consumed)
```

Track a daily counter in Redis. Throttle parallelism with a semaphore (8 is safer than the 10 hard cap). On 429 RESOURCE_EXHAUSTED, back off until the hourly / daily reset; do not retry tight.

## 10. Daily ETL into PostgreSQL

**Schedule.** A cron / BullMQ job at ~03:00 local pulls yesterday + a 2-day backfill window (GA4 numbers keep moving for ~48h for conversions).

**Schema (idempotent UPSERT):**

```sql
CREATE TABLE ga4_daily_traffic (
  property_id     text        NOT NULL,
  report_date     date        NOT NULL,
  source          text        NOT NULL,
  medium          text        NOT NULL,
  campaign        text        NOT NULL DEFAULT '(none)',
  device_category text        NOT NULL,
  sessions        bigint      NOT NULL DEFAULT 0,
  active_users    bigint      NOT NULL DEFAULT 0,
  new_users       bigint      NOT NULL DEFAULT 0,
  conversions     numeric     NOT NULL DEFAULT 0,
  total_revenue   numeric     NOT NULL DEFAULT 0,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (property_id, report_date, source, medium, campaign, device_category)
);

CREATE INDEX ga4_daily_traffic_date_idx ON ga4_daily_traffic (report_date DESC);
```

**Pull and write:**

```python
import psycopg
from psycopg.rows import dict_row

rows = []
for r in resp.rows:
    rows.append((
        property_id, r.dimension_values[0].value,  # date YYYYMMDD
        r.dimension_values[1].value, r.dimension_values[2].value,
        r.dimension_values[3].value, r.dimension_values[4].value,
        int(r.metric_values[0].value or 0),
        int(r.metric_values[1].value or 0),
        int(r.metric_values[2].value or 0),
        float(r.metric_values[3].value or 0),
        float(r.metric_values[4].value or 0),
    ))

with psycopg.connect(DSN) as conn, conn.cursor() as cur:
    cur.executemany("""
        INSERT INTO ga4_daily_traffic
          (property_id, report_date, source, medium, campaign,
           device_category, sessions, active_users, new_users,
           conversions, total_revenue)
        VALUES (%s, to_date(%s,'YYYYMMDD'), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (property_id, report_date, source, medium, campaign, device_category)
        DO UPDATE SET
          sessions      = EXCLUDED.sessions,
          active_users  = EXCLUDED.active_users,
          new_users     = EXCLUDED.new_users,
          conversions   = EXCLUDED.conversions,
          total_revenue = EXCLUDED.total_revenue,
          updated_at    = now();
    """, rows)
```

**Funnel example (Acquisition -> Purchase):**

```sql
SELECT
  report_date,
  SUM(sessions)                                AS sessions,
  SUM(active_users)                            AS users,
  SUM(conversions)                             AS conversions,
  ROUND(100.0 * SUM(conversions) / NULLIF(SUM(sessions), 0), 2) AS cr_pct
FROM ga4_daily_traffic
WHERE report_date >= current_date - INTERVAL '30 days'
GROUP BY report_date
ORDER BY report_date;
```

**Cohort retention (after persisting cohort report):**

```sql
SELECT
  cohort_start,
  week_offset,
  ROUND(100.0 * active_users / NULLIF(FIRST_VALUE(active_users)
        OVER (PARTITION BY cohort_start ORDER BY week_offset), 0), 2) AS retention_pct
FROM ga4_cohort_weekly
ORDER BY cohort_start, week_offset;
```

**Operational checklist:**

- Re-pull the trailing 48h every run; UPSERT keeps history monotonic.
- Log `propertyQuota` consumption per pull; alert at >70% daily.
- Inspect `metadata.samplingMetadatas` and `metadata.dataLossFromOtherRow` before trusting the numbers.
- Cap parallelism with a semaphore; never exceed 8 concurrent requests per property.
- Keep service account keys in a secrets manager, never in git.
