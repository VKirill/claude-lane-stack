# Logs API — raw hits export

## When to use the Logs API

- You need **raw** hits / visits with no aggregation (for your own pipeline into ClickHouse / DuckDB / BigQuery)
- The Reporting API does not expose the slice you need
- You need a full, sampling-free dataset
- You want to score multiple attribution models at once and it is easier on raw data

**Do not use** for real-time dashboards — the Logs API is asynchronous; minimum submit-to-download latency is tens of seconds at best, usually minutes to hours.

## Workflow (5 steps)

```
┌──────────┐  POST   ┌──────────┐  poll  ┌───────────┐  GET   ┌────────────┐  POST   ┌────────┐
│ evaluate ├────────►│ create   ├───────►│ status    ├───────►│ download   ├────────►│ clean  │
│  (free)  │         │  → req_id│        │ → processed│       │ /part/{n}  │         │        │
└──────────┘         └──────────┘        └───────────┘        └────────────┘         └────────┘
```

## 1. Evaluate (pre-flight — free)

```
GET /management/v1/counter/{counter_id}/logrequests/evaluate?\
date1=YYYY-MM-DD&\
date2=YYYY-MM-DD&\
source=visits&\
fields=ym:s:visitID,ym:s:date,ym:s:dateTime,ym:s:lastTrafficSource,ym:s:UTMSource,ym:s:UTMCampaign,ym:s:visits
```

Response:
```json
{
  "log_request_evaluation": {
    "possible": true,
    "max_possible_day_quantity": 365,
    "expected_size": 154872931,
    "log_request_sum_max_size": 10737418240,
    "log_request_sum_size": 2147483648
  }
}
```

- `possible: false` — the export will not run (10 GB quota or other limit exceeded)
- `max_possible_day_quantity` — how many days you can actually export (if you asked for 365 and got 90 — trim the range)
- `expected_size` — estimated size in bytes
- `log_request_sum_size` / `log_request_sum_max_size` — current quota usage / cap

**Always** call `evaluate` before `create` for wide date ranges — it is free and saves the quota.

## 2. Create (submit the job)

```
POST /management/v1/counter/{counter_id}/logrequests?\
date1=YYYY-MM-DD&\
date2=YYYY-MM-DD&\
source=visits&\
fields=ym:s:visitID,ym:s:date,ym:s:dateTime,ym:s:lastTrafficSource&\
attribution=LASTSIGN
```

Response:
```json
{
  "log_request": {
    "request_id": 9876543,
    "counter_id": 12345678,
    "source": "visits",
    "date1": "2026-04-01",
    "date2": "2026-04-30",
    "fields": ["ym:s:visitID","ym:s:date","ym:s:dateTime","ym:s:lastTrafficSource"],
    "status": "created",
    "size": 0,
    "parts": [],
    "attribution": "LASTSIGN"
  }
}
```

**Persist `request_id` to the DB immediately** — before continuing to handle the response. If the process crashes, you need that `request_id` to avoid creating a duplicate (and burning quota).

### Sources

- `visits` — visit-level aggregates (one row per session)
- `hits` — individual page views (one row per hit)

### Fields

CSV of dimension/metric names. **Limit**: ≤ 3000 chars in total. `visits` accepts `ym:s:*` fields; `hits` accepts `ym:pv:*`. Full list in OpenAPI: `/logs/openapi/getFields`.

### Attribution (only for `source=visits`)

`FIRST`, `LAST`, `LASTSIGN` (default), `LAST_YANDEX_DIRECT_CLICK`, `CROSS_DEVICE_*`, `AUTOMATIC`.

## 3. Poll status

```
GET /management/v1/counter/{counter_id}/logrequest/{request_id}
```

Response:
```json
{
  "log_request": {
    "request_id": 9876543,
    "status": "processed",
    "size": 154872931,
    "parts": [
      {"part_number": 0, "size": 67108864},
      {"part_number": 1, "size": 67108864},
      {"part_number": 2, "size": 20655203}
    ]
  }
}
```

### Lifecycle states

| Status | Meaning | Action |
|---|---|---|
| `created` | Queued | keep polling |
| `processed` | Ready | proceed to download |
| `awaiting_retry` | Transient error, will retry | keep polling |
| `processing_failed` | Terminal error | log + recreate (or use fewer fields) |
| `canceled` | Cancelled via API/UI | recreate |
| `cleaned_by_user` | Removed via `POST /clean` | recreate if still needed |
| `cleaned_automatically_as_too_old` | Auto-removed after 7 days | recreate if still needed |

### Polling cadence

No hard requirement; reasonable defaults:

- First 1–2 minutes: every 15–30 s
- 2–15 minutes: every minute
- > 15 minutes: every 2–5 min
- > 1 hour: every 5–10 min

To avoid burning the 5000 req/day budget, start at one-minute intervals. Honor `Retry-After` on 429.

## 4. Download parts

`parts[]` contains `{part_number, size}` entries. Download each part with its own request:

```
GET /management/v1/counter/{counter_id}/logrequest/{request_id}/part/{n}/download
```

Returns **TSV** (tab-separated values) with the header in the first row.

```python
async def download_part(client, counter_id, request_id, part_number, dest_path):
    url = f"/management/v1/counter/{counter_id}/logrequest/{request_id}/part/{part_number}/download"
    async with client.stream("GET", url) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
```

Download parts in **parallel** within the rate limit (3 concurrent per user_login). Stream large parts (multi-GB) — do not buffer in memory.

## 5. Clean (free the quota)

```
POST /management/v1/counter/{counter_id}/logrequest/{request_id}/clean
```

**Critical**: call this **right after** every part is confirmed on disk. Skipping it keeps the bytes counting against the 10 GB-per-counter quota. An active export without `clean` will trip `400 quota_exceeded` within 1–2 days.

After `clean`, status becomes `cleaned_by_user` and parts can no longer be downloaded. If you still need the data — recreate the job.

## Auxiliary endpoints

```
GET  /management/v1/counter/{id}/logrequests             # list all jobs
POST /management/v1/counter/{id}/logrequest/{rid}/cancel # cancel an active job
```

## Limits

| Limit | Value |
|---|---|
| Max range per request | 365 days (1 year) |
| `fields` total length | 3000 characters |
| Prepared-log storage | 10 GB per counter |
| Auto-cleanup for un-cleaned logs | 7 days |
| Logs API rate limit | 10 req/s per IP |
| Parallel requests | 3 per user_login |
| Data freshness | at least 3 days behind (session tail) |

Metrika Pro raises the storage quota (exact value via support).

## TSV format and parsing

- Header in line 1: column names (= `fields`)
- Delimiter: TAB (`\t`)
- Multi-line values escaped JSON-style (`\n` → `\\n`)
- Decimal separator: `.`
- Encoding: UTF-8 without BOM

Parse via `polars.scan_csv(separator='\t')`, `pandas.read_csv(sep='\t')`, or ClickHouse `INSERT FROM INFILE FORMAT TabSeparatedWithNames`.

## Recipe — atomic worker

```
1. SELECT FROM tasks WHERE status='pending' AND counter_id=:cid LIMIT 1 FOR UPDATE SKIP LOCKED
2. evaluate(date1, date2, fields)
   if not possible → mark 'unfeasible', return
3. UPDATE tasks SET status='creating'
4. POST create → request_id
5. UPDATE tasks SET request_id=:rid, status='polling'
6. loop:
     GET status
     if processed → break
     if processing_failed → UPDATE status='failed', return
     sleep with backoff
7. for part_number in parts:
     download to S3/local
     UPDATE tasks.downloaded_parts += 1
8. POST clean
9. UPDATE tasks SET status='done', cleaned_at=NOW()
```

Persistence is mandatory at every step — a worker restart must never produce duplicates.
