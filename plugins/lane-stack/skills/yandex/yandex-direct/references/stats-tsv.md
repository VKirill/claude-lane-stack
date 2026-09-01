# Reports API (StatsTSV) — TSV lifecycle with polling

This reference covers the Yandex Direct API v5 statistics endpoint (the "Reports" service that returns TSV files).

## Endpoint

```
POST https://api.direct.yandex.com/json/v5/reports
```

Sandbox: `https://api-sandbox.direct.yandex.com/json/v5/reports` (limit: one campaign per call).

## Headers

| Header | Required | Value |
|---|---|---|
| `Authorization: Bearer <token>` | yes | OAuth |
| `Client-Login: <login>` | for agencies | Client login |
| `Accept-Language: ru\|en` | no | Message language |
| `processingMode` | yes | `online` / `offline` / `auto` |
| `returnMoneyInMicros` | no | `false` — money in rubles; `true` (default) — micros |
| `skipReportHeader` | no | `true` — omit title rows from TSV |
| `skipColumnHeader` | no | `true` — omit column-name row |
| `skipReportSummary` | no | `true` — omit summary footer |

## processingMode

| Mode | Description | When to use |
|---|---|---|
| `online` | Synchronous, waits up to 5 minutes | Small queries, real-time |
| `offline` | Queue, returns `201`/`202` + `Retry-After` | Large queries (>1M rows, long periods) |
| `auto` | Server picks based on volume | Default for mixed load |

## Request body

```json
{
  "params": {
    "SelectionCriteria": {
      "DateFrom": "2026-01-01",
      "DateTo": "2026-01-31",
      "Filter": [
        { "Field": "CampaignId", "Operator": "IN", "Values": ["12345", "12346"] }
      ]
    },
    "FieldNames": ["Date", "CampaignId", "CampaignName", "Impressions", "Clicks", "Cost"],
    "ReportName": "campaigns-jan-2026-v1",
    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
    "DateRangeType": "CUSTOM_DATE",
    "Format": "TSV",
    "IncludeVAT": "NO",
    "IncludeDiscount": "NO"
  }
}
```

## ReportName — critical identifier

`ReportName` is the unique key of the export job inside the account. On first call the server stores payload + name and queues the job. Subsequent calls with the same payload + same name return the same job status (or the finished TSV).

**Important**: when polling with `processingMode: offline` send an identical body each time. Changing `FieldNames` or `Filter` produces a new job and burns fresh units.

## DateRangeType values

- `TODAY`, `YESTERDAY`, `LAST_3_DAYS`, `LAST_5_DAYS`, `LAST_7_DAYS`
- `THIS_WEEK_MON_TODAY`, `THIS_WEEK_SUN_TODAY`, `LAST_WEEK`, `LAST_BUSINESS_WEEK`
- `LAST_WEEK_SUN_SAT`, `LAST_14_DAYS`, `LAST_30_DAYS`, `LAST_90_DAYS`, `LAST_365_DAYS`
- `THIS_MONTH`, `LAST_MONTH`, `ALL_TIME`
- `CUSTOM_DATE` (requires `DateFrom`, `DateTo`)
- `AUTO`

## ReportType

| Type | Purpose |
|---|---|
| `ACCOUNT_PERFORMANCE_REPORT` | Whole account aggregate |
| `CAMPAIGN_PERFORMANCE_REPORT` | Per campaign |
| `ADGROUP_PERFORMANCE_REPORT` | Per ad group |
| `AD_PERFORMANCE_REPORT` | Per ad |
| `CRITERIA_PERFORMANCE_REPORT` | Per criterion (keyword, retargeting, audience) |
| `CUSTOM_REPORT` | Custom dimensions |
| `SEARCH_QUERY_PERFORMANCE_REPORT` | Per search query |
| `GEO_PERFORMANCE_REPORT` | Per geography |
| `REACH_AND_FREQUENCY_PERFORMANCE_REPORT` | Reach and frequency |

## HTTP status

| HTTP | Meaning | Client action |
|---|---|---|
| `200 OK` | Body is finished TSV | Parse and persist |
| `201 Created` | Queued | Sleep `Retry-After`, repeat identical POST |
| `202 Accepted` | Forming | Same as 201 |
| `400 Bad Request` | Bad params | Inspect `error` JSON, do not retry |
| `429 Too Many Requests` | Parallel/RPS limit | Backoff |
| `500 Internal` | Server error | Backoff, retry |
| `502/503/504` | Transient | Backoff, retry |

## Polling algorithm

```
1. POST /json/v5/reports with processingMode: offline.
2. HTTP 200 -> parse body as TSV, done.
3. HTTP 201/202:
     - Read Retry-After (seconds), default 60.
     - Sleep that long (+ 10% jitter).
     - Repeat the SAME POST with the SAME body.
4. HTTP 400 -> do not retry; read JSON error.
5. HTTP 5xx -> exponential backoff, max 3-5 attempts.
```

**Never poll faster than `Retry-After`** — violation tightens limits or temporarily blocks the IP/account.

## Parallel jobs

- Max **5 simultaneous** export jobs per account.
- Excess -> `error 8` (Forbidden) or HTTP 429.
- Sandbox enforces the same limit.

## TSV layout

With all headers on:

```
"Report name"
"Date range"
Date	CampaignId	CampaignName	Impressions	Clicks	Cost
2026-01-01	12345	"Test campaign"	1500	23	125.50
...
Total rows: N
```

With `skipReportHeader=true&skipColumnHeader=true&skipReportSummary=true` only data rows remain (best for direct DB ingestion).

Separator: `\t`. Decimal: dot. Encoding: UTF-8. Newline: `\n` (LF).

## IncludeVAT / IncludeDiscount

- `IncludeVAT: YES|NO` — include VAT in `Cost`.
- `IncludeDiscount: YES|NO` — apply discounts.

Accounting reconciliation -> `IncludeVAT: YES`. Optimization -> `NO`.

## returnMoneyInMicros

- `true` (default): `Cost` as integer micro-rubles (×1 000 000).
- `false`: rubles with decimal point (e.g. `125.50`). Convenient but watch float precision.

## Cancelling

No direct cancellation API. A stuck job expires automatically within a few hours. To start over, change `ReportName` and submit a new one.

## Idempotent worker with persistence

```sql
CREATE TABLE direct_stats_jobs (
  id          BIGSERIAL PRIMARY KEY,
  client      TEXT NOT NULL,
  report_name TEXT NOT NULL,
  payload     JSONB NOT NULL,
  status      TEXT NOT NULL DEFAULT 'queued',
  http_code   INT,
  retry_after INT,
  last_poll   TIMESTAMPTZ,
  result_path TEXT,
  request_id  TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (client, report_name)
);
```

Worker picks rows with `status IN ('queued','processing')`, resends the identical payload, updates `status` and `retry_after`.

## Common mistakes

- **Polling faster than `Retry-After`** -> 429 / temp ban.
- **Changing `ReportName` between polls** -> every call is a new job, fresh units spent.
- **Large period with `processingMode: online`** -> 5-minute timeout. Switch to `offline`.
- **Not skipping the title rows** -> 1-3 garbage rows in data. Use `skipReportHeader=true&skipColumnHeader=true&skipReportSummary=true` plus a fixed schema in code.
- **Floats for `Cost`** with `returnMoneyInMicros: false` -> precision loss. Use `Decimal` or stay with integer micros.
- **More than 5 parallel jobs** -> 429. Queue + semaphore in client.
