# Errors — HTTP codes and reason codes

Google APIs return errors in the standard `googleapis.com` envelope:

```jsonc
{
  "error": {
    "code": 403,
    "message": "User does not have sufficient permission for site 'sc-domain:example.com'.",
    "errors": [
      {
        "message": "User does not have sufficient permission for site 'sc-domain:example.com'.",
        "domain": "global",
        "reason": "forbidden"
      }
    ],
    "status": "PERMISSION_DENIED"
  }
}
```

## HTTP statuses

| HTTP | reason | Smell | Action |
|---|---|---|---|
| 400 | `badRequest` / `invalid` | invalid body / dimensions / dates / URL | check formatting; URL-encode `siteUrl` / `feedpath` |
| 401 | `authError` / `unauthenticated` | access_token expired / invalid | refresh, retry once |
| 403 | `forbidden` | service account not in property; missing scope | add SA in GSC UI; correct scope (webmasters vs readonly) |
| 403 | `insufficientPermissions` | OAuth missing scope | re-consent with the required scope |
| 404 | `notFound` | siteUrl / feedpath unknown to the user | check `sites.list`; add the property |
| 429 | `rateLimitExceeded` | per-user QPM | exp backoff |
| 429 | `userRateLimitExceeded` | per-user 100s window | exp backoff + lower concurrency |
| 429 | `quotaExceeded` | per-project / per-site QPM | exp backoff, shard across properties |
| 429 | `dailyLimitExceeded` | per-day cap (URL Inspection 2000/day in particular) | wait until PT midnight reset, shard by property |
| 500 | `backendError` / `internalError` | transient | retry with jitter (3-5x) |
| 503 | `backendError` | transient (Google overloaded) | exp backoff, max 60 s |

## Reason codes — common semantics

- `inspectionUrl is not under siteUrl` (400) — URL Inspection: `inspectionUrl` is outside the property. Fix: for URL-prefix double-check the exact protocol and trailing slash in `siteUrl`; for domain check the host.
- `User does not have sufficient permission for site` (403) — for a service account this almost always means the SA email is missing from the GSC UI, or present with `permissionLevel: siteUnverifiedUser`.
- `The site is not a verified site` (403) — property was added but verification (HTML / DNS) was never completed.
- `invalid_grant` on refresh token (400 from `oauth2.googleapis.com`) — refresh_token expired (Testing mode) or user revoked. Re-consent required.

## Retry strategy

```python
def with_retry(fn, *, max_attempts=5):
    import time, random
    for attempt in range(max_attempts):
        try:
            return fn()
        except HttpError as e:
            status = e.resp.status
            reason = _reason(e)
            if status == 401:
                refresh_token_and_retry_once()
                continue
            if status == 429 and reason == "dailyLimitExceeded":
                raise   # do not retry; wait for daily reset
            if status in (429, 500, 503) or (status == 429 and reason in {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"}):
                sleep = (2 ** attempt) + random.uniform(0, 1)
                sleep = min(sleep, 60)
                time.sleep(sleep)
                continue
            raise
    raise RuntimeError("max retries exhausted")
```

- `dailyLimitExceeded` — **never retry**; wait for PT midnight reset.
- 401 — refresh **once**; if still 401 → fatal auth error.
- 429 short-window — exponential backoff with jitter, max 60 s.
- 500 / 503 — retry up to 5 times.
- 400 / 403 / 404 — **do not** retry; configuration / semantics error.

## URL Inspection — special case

URL Inspection lives on a separate 2000/day/property quota. On `dailyLimitExceeded` Google cuts you off immediately — no soft slowdown. Worker design:

- Per-property counter (Redis: `INCR gsc:inspect:{property}:{date}`, TTL until PT midnight).
- At 1900/2000 — stop the worker for that property until next day.
- URL prioritization: new / changed (from sitemap diff) first → old URLs re-checked every N days.

## Sample — error parsing (Python)

```python
from googleapiclient.errors import HttpError
import json

try:
    resp = svc.searchanalytics().query(...).execute()
except HttpError as e:
    body = json.loads(e.content.decode())
    err = body.get("error", {})
    status = err.get("code")
    reason = (err.get("errors", [{}])[0].get("reason"))
    message = err.get("message")
    raise RuntimeError(f"GSC {status}/{reason}: {message}") from e
```
