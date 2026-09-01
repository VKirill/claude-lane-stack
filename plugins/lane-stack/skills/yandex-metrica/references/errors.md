# Errors and retry strategy

## HTTP status code mapping

| Status | Meaning | Retry? |
|---|---|---|
| 200 | OK | n/a |
| 400 | Bad request — invalid params / expression-limit exceeded | **No** — fix the request |
| 401 | Unauthorized — missing / invalid / revoked token | **No** — reissue the token |
| 403 | Forbidden — no access to counter_id or scope too narrow | **No** — check owner / scope |
| 404 | Not found — counter_id / request_id / goal_id does not exist | **No** — verify the ID |
| 409 | Conflict — e.g. duplicate goal name | **No** — rename |
| 429 | Too Many Requests — rate limit | **Yes** — `Retry-After`, exponential backoff |
| 500 | Internal server error | **Yes** — backoff |
| 502, 503, 504 | Bad gateway / unavailable / timeout | **Yes** — backoff |

## Error response shape

```json
{
  "errors": [
    {
      "error_type": "invalid_parameter",
      "message": "Wrong parameter 'metrics' value 'ym:s:invalidMetric': metric not found",
      "location": "metrics"
    }
  ],
  "code": 400,
  "message": "Wrong parameter"
}
```

Fields:

- `code` — HTTP status
- `message` — general description
- `errors[]` — array of specific problems
- `errors[].error_type` — machine-readable type
- `errors[].message` — human-readable text
- `errors[].location` — where the problem is (param / field)

## Common `error_type` values

| error_type | Meaning | Fix |
|---|---|---|
| `invalid_parameter` | Invalid parameter value | Verify dimension/metric spelling |
| `missing_required_parameter` | Required param missing | Add `ids` / `metrics` |
| `quota_exceeded` | Quota tripped | Logs: `POST /clean`; Reporting: wait for GMT 00:00 |
| `not_found` | counter_id / request_id does not exist | Verify the ID |
| `permission_denied` | No access | Verify token scope and counter owner |
| `invalid_filter_expression` | Filter DSL syntax error | Check quoting / operators / namespace |
| `rate_limit_exceeded` | RPS exceeded | Lower concurrency, back off |
| `dimension_metric_namespace_mismatch` | Mixed namespaces | One namespace per request, or `EXISTS()` |
| `too_many_dimensions` | > 10 dimensions in the request | Trim |
| `LimitedExceededException` | Daily 5000-request budget exhausted | Wait for the reset |

## 429 Too Many Requests

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
Content-Type: application/json

{
  "code": 429,
  "message": "Too many requests",
  "errors": [{"error_type": "rate_limit_exceeded", "message": "..."}]
}
```

**Correct reaction**:

1. Read `Retry-After` (seconds)
2. If present — sleep exactly that long
3. Otherwise — exponential backoff: 1 → 2 → 4 → 8 → 16 → 32 → 60 (with jitter)
4. Max attempts 5–7, then fail

```python
import asyncio, random, httpx

async def with_retry(coro_factory, max_attempts=7):
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status not in (429, 500, 502, 503, 504):
                raise
            if attempt == max_attempts - 1:
                raise
            retry_after = e.response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else min(2 ** attempt, 60)
            wait += random.uniform(0, wait * 0.25)  # jitter
            await asyncio.sleep(wait)
```

## Common 400 cases

### `metric not found`

```json
{"errors":[{"error_type":"invalid_parameter","message":"Wrong parameter 'metrics' value 'ym:s:invalidMetric': metric not found"}]}
```

Check:

- Exact name via OpenAPI `/stat/openapi/metrics`
- Parameterization: `ym:s:goal12345reaches`, not `ym:s:goalIDreaches`
- Namespace: `ym:pv:pageviews` (views), not `ym:s:pageviews`

### `namespace mismatch`

```json
{"errors":[{"error_type":"dimension_metric_namespace_mismatch","message":"..."}]}
```

You cannot mix `ym:s:date` and `ym:pv:URL` without `EXISTS()`. Fix: either stay within one namespace or wrap with `EXISTS()` in the filter.

### `invalid date format`

`date1=01.04.2026` → 400. Only `YYYY-MM-DD`, `today`, `yesterday`, `NdaysAgo` (with `N` an integer) are accepted.

### `too many values in IN`

`IN()` accepts up to 100 values. 101+ → 400. Fix: split into multiple requests and stitch locally.

### `expression too long`

`filters` over 10 000 chars → 400. Fix: create a segment via the Management API and reference it.

## Logs-API-specific errors

### `quota_exceeded` (10 GB)

```json
{"errors":[{"error_type":"quota_exceeded","message":"Log requests sum size 10737418240 exceeds 10737418240 limit"}]}
```

Fix:

1. `GET /management/v1/counter/{id}/logrequests` — list every job
2. Find entries with `status=processed` or `cleaned_*` and `size > 0`
3. `POST /logrequest/{rid}/clean` for each with `size > 0`
4. Retry the create

### `processing_failed`

Terminal processing failure. Causes:

- Wide period + many fields → server runs out of resources
- Incompatible fields (e.g. `hits` fields with `source=visits`)
- Internal bug (rare)

Fix: shrink range / fields, recreate. If reproducible — open a support ticket.

### `awaiting_retry`

Transient error; the server will reprocess on its own. Keep polling at a longer cadence.

## Auth errors

### 401 invalid token

Causes:

- Header missing
- Typo (`OAuth ` vs `Bearer ` — both work, but the trailing space is required)
- Token revoked by the user in Yandex ID
- Token from another app with the same string (extremely rare)

Fix: reissue via OAuth flow.

### 403 access denied

Causes:

- `counter_id` does not belong to the token owner and there is no guest access
- Scope too narrow (`metrika:read` for a CRUD call → 403)
- Counter in `Deleted` status — un-delete via `POST /undelete`
- Account locked / banned

Fix: run `GET /management/v1/counters` under this token to see what is actually accessible.

## Idempotency

- **Reporting API**: GET, idempotent — retry without side effects
- **Logs API**: `POST /logrequests` (create) is **not** idempotent; a repeated POST creates a second job with a new `request_id` and burns quota. Persist `request_id` before any retry logic.
- **Management API CRUD**: PUT is idempotent; POST/DELETE are not. A repeated POST for `goal` creates duplicates.

## Logging recommendations

For every request, log:

- Your own `request_id` (UUID, distinct from Metrika's)
- timestamp, endpoint, query params (without the token!), counter_id
- response status, `code`, `errors[].error_type`
- `sampled`, `sample_share`, `data_lag` (Reporting)
- Metrika `request_id` (Logs)

On 429 / 5xx log the attempt number and pre-retry delay. After the final failure — alert.
