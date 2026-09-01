# Integration — Python, Node.js, REST, PG schema, queries

## Python client (`google-analytics-data`)

### Install

```bash
pip install google-analytics-data google-analytics-admin
```

### Service account auth

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/secure/path/ga4-key.json
```

### Базовый клиент

```python
# ga4_client.py
import logging
import os
from typing import Any
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, RunReportResponse,
    Filter, FilterExpression, FilterExpressionList, OrderBy,
    MetricAggregation, MinuteRange, RunRealtimeReportRequest,
    BatchRunReportsRequest,
)

log = logging.getLogger(__name__)


class GA4Client:
    def __init__(self, property_id: str):
        if not property_id.isdigit():
            raise ValueError(
                f"property_id must be numeric, got {property_id!r}. "
                f"Don't use Measurement ID (G-XXXXX) — find numeric Property ID "
                f"in GA4 Admin → Property Settings."
            )
        self.property = f"properties/{property_id}"
        self.client = BetaAnalyticsDataClient()

    def run_report(
        self,
        dimensions: list[str],
        metrics: list[str],
        start_date: str,
        end_date: str,
        dimension_filter: FilterExpression | None = None,
        metric_filter: FilterExpression | None = None,
        order_bys: list[OrderBy] | None = None,
        limit: int = 10_000,
        offset: int = 0,
    ) -> RunReportResponse:
        req = RunReportRequest(
            property=self.property,
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimension_filter=dimension_filter,
            metric_filter=metric_filter,
            order_bys=order_bys or [],
            limit=limit,
            offset=offset,
            return_property_quota=True,
            keep_empty_rows=False,
        )
        resp = self.client.run_report(req)
        self._log_quota(resp)
        self._warn_on_sampling(resp)
        return resp

    def _log_quota(self, resp: RunReportResponse) -> None:
        q = resp.property_quota
        if not q:
            return
        log.info(
            "GA4 quota: day=%d/%d, hour=%d/%d, project_hour=%d/%d, concurrent=%d/%d",
            q.tokens_per_day.consumed, q.tokens_per_day.remaining,
            q.tokens_per_hour.consumed, q.tokens_per_hour.remaining,
            q.tokens_per_project_per_hour.consumed, q.tokens_per_project_per_hour.remaining,
            q.concurrent_requests.consumed, q.concurrent_requests.remaining,
        )

    def _warn_on_sampling(self, resp: RunReportResponse) -> None:
        md = resp.metadata
        for sm in md.sampling_metadatas:
            if sm.samples_read_count < sm.sampling_space_size:
                ratio = sm.samples_read_count / max(sm.sampling_space_size, 1)
                log.warning("GA4 sampling: %.2f%% of events used", ratio * 100)
        if md.data_loss_from_other_row:
            log.warning("GA4 data loss from (other) row — cardinality cap hit")


def rows_to_dicts(resp: RunReportResponse) -> list[dict[str, Any]]:
    dim_names = [h.name for h in resp.dimension_headers]
    met_names = [h.name for h in resp.metric_headers]
    out = []
    for row in resp.rows:
        d = dict(zip(dim_names, (v.value for v in row.dimension_values)))
        m = dict(zip(met_names, (v.value for v in row.metric_values)))
        out.append({**d, **m})
    return out
```

### Использование

```python
ga4 = GA4Client("381112233")
resp = ga4.run_report(
    dimensions=["date", "sessionSourceMedium", "deviceCategory"],
    metrics=["sessions", "activeUsers", "conversions", "totalRevenue"],
    start_date="30daysAgo",
    end_date="yesterday",
    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    limit=1000,
)
rows = rows_to_dicts(resp)
```

## Node.js client (`@google-analytics/data`)

### Install

```bash
npm install @google-analytics/data @google-analytics/admin
```

### Базовый клиент

```typescript
// ga4-client.ts
import {BetaAnalyticsDataClient, protos} from '@google-analytics/data';

type IRow = protos.google.analytics.data.v1beta.IRow;
type IRunReportResponse = protos.google.analytics.data.v1beta.IRunReportResponse;

export class GA4Client {
  private client: BetaAnalyticsDataClient;
  private property: string;

  constructor(propertyId: string) {
    if (!/^\d+$/.test(propertyId)) {
      throw new Error(
        `property_id must be numeric, got "${propertyId}". ` +
        `Don't use Measurement ID (G-XXXXX) — find numeric Property ID in GA4 Admin.`
      );
    }
    this.property = `properties/${propertyId}`;
    this.client = new BetaAnalyticsDataClient();
  }

  async runReport(opts: {
    dimensions: string[];
    metrics: string[];
    startDate: string;
    endDate: string;
    dimensionFilter?: any;
    metricFilter?: any;
    orderBys?: any[];
    limit?: number;
  }): Promise<IRunReportResponse> {
    const [resp] = await this.client.runReport({
      property: this.property,
      dimensions: opts.dimensions.map(name => ({name})),
      metrics:    opts.metrics.map(name => ({name})),
      dateRanges: [{startDate: opts.startDate, endDate: opts.endDate}],
      dimensionFilter: opts.dimensionFilter,
      metricFilter:    opts.metricFilter,
      orderBys:        opts.orderBys ?? [],
      limit:  String(opts.limit ?? 10_000),
      returnPropertyQuota: true,
      keepEmptyRows: false,
    });

    this.logQuota(resp);
    this.warnOnSampling(resp);
    return resp;
  }

  private logQuota(resp: IRunReportResponse): void {
    const q = resp.propertyQuota;
    if (!q) return;
    console.info('GA4 quota:', {
      day:          `${q.tokensPerDay?.consumed}/${q.tokensPerDay?.remaining}`,
      hour:         `${q.tokensPerHour?.consumed}/${q.tokensPerHour?.remaining}`,
      project_hour: `${q.tokensPerProjectPerHour?.consumed}/${q.tokensPerProjectPerHour?.remaining}`,
      concurrent:   `${q.concurrentRequests?.consumed}/${q.concurrentRequests?.remaining}`,
    });
  }

  private warnOnSampling(resp: IRunReportResponse): void {
    const md = resp.metadata;
    for (const sm of md?.samplingMetadatas ?? []) {
      const read = Number(sm.samplesReadCount ?? 0);
      const total = Number(sm.samplingSpaceSize ?? 1);
      if (read < total) {
        console.warn(`GA4 sampling: ${((read / total) * 100).toFixed(2)}% used`);
      }
    }
    if (md?.dataLossFromOtherRow) {
      console.warn('GA4 data loss from (other) row — cardinality cap');
    }
  }
}

export function rowsToObjects(resp: IRunReportResponse): Record<string, string>[] {
  const dimNames = (resp.dimensionHeaders ?? []).map(h => h.name!);
  const metNames = (resp.metricHeaders    ?? []).map(h => h.name!);
  return (resp.rows ?? []).map((row: IRow) => {
    const out: Record<string, string> = {};
    (row.dimensionValues ?? []).forEach((v, i) => out[dimNames[i]] = v.value!);
    (row.metricValues    ?? []).forEach((v, i) => out[metNames[i]] = v.value!);
    return out;
  });
}
```

## REST-only вариант (без google-cloud SDK)

Для окружений, где недоступен Google SDK (edge runtimes, экзотические среды).

```python
# rest_ga4.py
import time
import jwt   # PyJWT
import httpx

GA4_BASE = "https://analyticsdata.googleapis.com/v1beta"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def build_jwt_assertion(sa: dict) -> str:
    """sa — словарь из service-account JSON."""
    now = int(time.time())
    payload = {
        "iss":   sa["client_email"],
        "scope": SCOPE,
        "aud":   OAUTH_TOKEN_URL,
        "exp":   now + 3600,
        "iat":   now,
    }
    return jwt.encode(payload, sa["private_key"], algorithm="RS256",
                      headers={"kid": sa["private_key_id"]})


async def get_access_token(sa: dict) -> str:
    assertion = build_jwt_assertion(sa)
    async with httpx.AsyncClient(timeout=10) as cli:
        r = await cli.post(OAUTH_TOKEN_URL, data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion":  assertion,
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def run_report_rest(sa: dict, property_id: str, body: dict) -> dict:
    token = await get_access_token(sa)
    url = f"{GA4_BASE}/properties/{property_id}:runReport"
    async with httpx.AsyncClient(timeout=60, http2=True) as cli:
        r = await cli.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()
```

В production кэшировать access_token до его истечения (`expires_in: 3599`), не выпускать на каждый запрос.

## Token budget tracker (Redis)

```python
import redis.asyncio as redis

R = redis.from_url("redis://localhost:6379/0")

async def track_quota(property_id: str, resp) -> None:
    q = resp.property_quota
    if not q:
        return
    now_hour = int(time.time()) // 3600
    now_day  = int(time.time()) // 86400

    pipe = R.pipeline()
    pipe.hset(f"ga4:quota:{property_id}:hour:{now_hour}",
              "consumed", q.tokens_per_hour.consumed)
    pipe.expire(f"ga4:quota:{property_id}:hour:{now_hour}", 7200)

    pipe.hset(f"ga4:quota:{property_id}:day:{now_day}",
              "consumed", q.tokens_per_day.consumed)
    pipe.expire(f"ga4:quota:{property_id}:day:{now_day}", 172800)
    await pipe.execute()


async def can_query(property_id: str, threshold: float = 0.9) -> bool:
    """Возвращает False если >90% дневной квоты выжжено."""
    now_day = int(time.time()) // 86400
    consumed = await R.hget(f"ga4:quota:{property_id}:day:{now_day}", "consumed")
    if not consumed:
        return True
    return int(consumed) < int(200_000 * threshold)
```

## Batch report worker (5-in-1)

```python
from google.analytics.data_v1beta.types import (
    BatchRunReportsRequest, RunReportRequest, DateRange, Dimension, Metric,
)

def daily_dashboard_batch(property_id: str, day: str):
    """5 виджетов дашборда в одном запросе."""
    base = dict(
        date_ranges=[DateRange(start_date=day, end_date=day)],
        return_property_quota=True,
    )
    requests = [
        RunReportRequest(**base,
            dimensions=[Dimension(name="sessionSourceMedium")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            limit=20),
        RunReportRequest(**base,
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions"), Metric(name="conversions")]),
        RunReportRequest(**base,
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="activeUsers")],
            limit=20),
        RunReportRequest(**base,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            limit=30),
        RunReportRequest(**base,
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews")],
            limit=20),
    ]

    client = BetaAnalyticsDataClient()
    batch = client.batch_run_reports(BatchRunReportsRequest(
        property=f"properties/{property_id}",
        requests=requests,
    ))
    return list(batch.reports)
```

## PostgreSQL schema — daily snapshots

```sql
-- Дневной слепок по основным срезам
CREATE TABLE ga4_daily_traffic (
    property_id     BIGINT       NOT NULL,
    date            DATE         NOT NULL,
    source          TEXT         NOT NULL DEFAULT '(not set)',
    medium          TEXT         NOT NULL DEFAULT '(not set)',
    device_category TEXT         NOT NULL DEFAULT '(not set)',
    country         TEXT         NOT NULL DEFAULT '(not set)',
    sessions        BIGINT       NOT NULL DEFAULT 0,
    active_users    BIGINT       NOT NULL DEFAULT 0,
    new_users       BIGINT       NOT NULL DEFAULT 0,
    page_views      BIGINT       NOT NULL DEFAULT 0,
    engagement_rate NUMERIC(6,4),
    avg_session_sec NUMERIC(8,2),
    bounce_rate     NUMERIC(6,4),
    conversions     BIGINT       NOT NULL DEFAULT 0,
    total_revenue   NUMERIC(14,2) NOT NULL DEFAULT 0,
    purchase_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    ingested_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    is_sampled      BOOLEAN      NOT NULL DEFAULT false,
    PRIMARY KEY (property_id, date, source, medium, device_category, country)
);

CREATE INDEX ix_ga4_daily_property_date ON ga4_daily_traffic (property_id, date DESC);
CREATE INDEX ix_ga4_daily_source ON ga4_daily_traffic (property_id, source, medium);

-- Конверсии по событиям отдельно (более granular)
CREATE TABLE ga4_daily_events (
    property_id   BIGINT       NOT NULL,
    date          DATE         NOT NULL,
    event_name    TEXT         NOT NULL,
    is_key_event  BOOLEAN      NOT NULL DEFAULT false,
    event_count   BIGINT       NOT NULL DEFAULT 0,
    total_users   BIGINT       NOT NULL DEFAULT 0,
    event_value   NUMERIC(14,2),
    ingested_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (property_id, date, event_name)
);

-- Бюджет токенов на день для аналитики потребления
CREATE TABLE ga4_quota_log (
    property_id   BIGINT       NOT NULL,
    hour_utc      TIMESTAMPTZ  NOT NULL,
    tokens_used   INT          NOT NULL,
    requests      INT          NOT NULL,
    last_response JSONB,
    PRIMARY KEY (property_id, hour_utc)
);

-- Snapshot на конкретный day делается ON CONFLICT DO UPDATE
-- (потому что GA4 «стабилизирует» данные ~48h, делать ре-fetch для last 3 days)
```

### Upsert pattern

```sql
INSERT INTO ga4_daily_traffic (
    property_id, date, source, medium, device_category, country,
    sessions, active_users, new_users, page_views,
    engagement_rate, avg_session_sec, conversions, total_revenue, is_sampled
) VALUES (...)
ON CONFLICT (property_id, date, source, medium, device_category, country) DO UPDATE SET
    sessions        = EXCLUDED.sessions,
    active_users    = EXCLUDED.active_users,
    new_users       = EXCLUDED.new_users,
    page_views      = EXCLUDED.page_views,
    engagement_rate = EXCLUDED.engagement_rate,
    avg_session_sec = EXCLUDED.avg_session_sec,
    conversions     = EXCLUDED.conversions,
    total_revenue   = EXCLUDED.total_revenue,
    is_sampled      = EXCLUDED.is_sampled,
    ingested_at     = now();
```

## Sample queries (на собранных данных)

### Traffic by source — last 30 days

```sql
SELECT
    source,
    medium,
    SUM(sessions)      AS sessions,
    SUM(active_users)  AS users,
    SUM(conversions)   AS conversions,
    ROUND(SUM(conversions)::numeric / NULLIF(SUM(sessions),0) * 100, 2) AS cr_pct
FROM ga4_daily_traffic
WHERE property_id = 381112233
  AND date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY source, medium
HAVING SUM(sessions) > 100
ORDER BY sessions DESC
LIMIT 50;
```

### Conversion funnel by event sequence

```sql
SELECT
    date,
    SUM(CASE WHEN event_name = 'view_item'      THEN event_count END) AS view_item,
    SUM(CASE WHEN event_name = 'add_to_cart'    THEN event_count END) AS add_to_cart,
    SUM(CASE WHEN event_name = 'begin_checkout' THEN event_count END) AS begin_checkout,
    SUM(CASE WHEN event_name = 'purchase'       THEN event_count END) AS purchase
FROM ga4_daily_events
WHERE property_id = 381112233
  AND event_name IN ('view_item','add_to_cart','begin_checkout','purchase')
  AND date >= CURRENT_DATE - INTERVAL '14 days'
GROUP BY date
ORDER BY date DESC;
```

### Retention cohort

```sql
-- Предполагает, что cohort report сохраняется отдельно в ga4_cohort_retention
SELECT
    cohort_week,
    nth_week,
    cohort_active_users::numeric / cohort_total_users * 100 AS retention_pct
FROM ga4_cohort_retention
WHERE property_id = 381112233
  AND cohort_week >= CURRENT_DATE - INTERVAL '8 weeks'
ORDER BY cohort_week DESC, nth_week ASC;
```

## GA4 vs UA

**Universal Analytics (UA) sunset с 1 июля 2024.** API отключен. Автомиграции нет.

| UA | GA4 |
|---|---|
| `ga:sessions` | `sessions` (считается иначе) |
| `ga:users` | `activeUsers` / `totalUsers` / `newUsers` |
| `ga:pageviews` | `screenPageViews` |
| `ga:bounceRate` | `engagementRate` (≠ 1 - bounceRate) |
| `ga:goalCompletionsAll` | `conversions` (key events) |
| Views | Streams (web/iOS/Android) |

GA4 — event-based, UA — session/pageview-based. Числа разные из-за разной модели, не из-за бага. Перестраивать дашборды на GA4-нативные термины.
