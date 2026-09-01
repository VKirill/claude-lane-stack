# Error codes — all 17 codes + HTTP 429

Error envelope:

```json
{ "status": "no", "error_id": 100, "error": "Error key" }
```

Read `status` first. If `"no"`, branch on `error_id` (numeric, integer). Note: server returns HTTP 200 for ALL application errors — only the rate limiter returns HTTP 429.

Codes verbatim from proxy6.net spec.

| `error_id` | `error` | Class | Retry? |
|---|---|---|---|
| 30 | Error unknown | server | once with backoff |
| 100 | Error key | auth | NO — fix key |
| 105 | Error ip | auth/IP | NO — fix allowlist |
| 110 | Error method | bad request | NO — fix method name |
| 200 | Error count | bad request | NO — fix `count` |
| 210 | Error period | bad request | NO — fix `period` |
| 220 | Error country | bad request | NO — fix `country` |
| 230 | Error ids | bad request | NO — fix `ids` CSV |
| 240 | Error version | bad request | NO — fix `version` |
| 250 | Error descr | bad request | NO — fix `descr` (likely > 50 chars) |
| 260 | Error type | bad request | NO — fix `type` |
| 270 | Error port | bad request | NO — fix `port` (rare) |
| 280 | Error proxy str | bad request | NO — fix `proxy` arg of `check` |
| 300 | Error active proxy allow | stock | NO — call `getcount`, reduce count, or pick another country |
| 400 | Error no money | billing | NO — top up balance |
| 404 | Error not found | not-found | NO — fix ids / filters |
| 410 | Error price | pricing | NO — pricing combo invalid (period × version not sold) |

Plus the HTTP transport-level:

| HTTP | Meaning | Retry? |
|---|---|---|
| 429 | Too Many Requests — rate limit exceeded | YES — backoff per [rate-limit-and-retry.md](rate-limit-and-retry.md) |

## Symptom-indexed (read this when something's wrong)

### "auth fails immediately"
- `error_id 100` → key typo, key revoked, key for wrong environment (dev vs prod). Re-read from secrets manager, run smoke test (`curl https://px6.link/api/${KEY}/getprice/`).
- `error_id 105` → your egress IP is not in the dashboard allowlist. Either add it, or call from a permitted IP, or temporarily disable the allowlist for debugging.

### "wrote a method name and got 110"
- Typo in `{method}` segment of the URL. Allowed values listed in [methods.md](methods.md). Note trailing slash: `/buy/`, not `/buy`.

### "buying fails"
- `error_id 300` → not enough stock for the country/version combo. Run `getcount(country, version)` first.
- `error_id 400` → balance below cost. Read `balance` from previous envelope; top up; retry.
- `error_id 410` → the combination of `count × period × version` resolves to non-positive price (unsupported tier). Check `getprice` first.
- `error_id 220` → country code typo or country not stocked for this version. Run `getcountry(version)`.

### "ids-based call returns 404 or 230"
- `error_id 230` → CSV format wrong (e.g. spaces, trailing comma, non-numeric ids).
- `error_id 404` → at least one id doesn't exist OR doesn't belong to you. Run `getproxy` first and pass only ids from `list_count`.

### "descr update fails"
- `error_id 250` → `new` is empty, longer than 50 chars, or contains forbidden characters. Trim and retry.

### "check returns 280"
- `error_id 280` → the `proxy` string isn't in `ip:port:user:pass` format. Quote and URL-encode special chars.

### "everything is HTTP 429"
- Too many requests in a 1-second window. See [rate-limit-and-retry.md](rate-limit-and-retry.md). Likely culprits:
  - Parallel `getproxy` paging without shared limiter.
  - Bulk `check` on hundreds of proxies in a tight loop.
  - Multiple workers / processes sharing the same key without coordinated limiter.

### "error_id 30 with no further info"
- Unknown server error. Treated as transient. Retry once with 1–3 s backoff. If it persists, contact proxy6.net support with the `user_id` from a successful envelope.

## Schema for clients

Validate every response shape before reading domain fields:

```python
# pseudo-shape
class ErrorEnvelope(BaseModel):
    status: Literal["no"]
    error_id: int
    error: str

class SuccessEnvelope(BaseModel):
    status: Literal["yes"]
    user_id: str
    balance: str  # major units
    currency: Literal["RUB", "USD"]
```

Branch on `status`. If `"no"` → raise typed exception keyed to `error_id` so callers can branch (`InsufficientFundsError` for 400, `OutOfStockError` for 300, etc.).
