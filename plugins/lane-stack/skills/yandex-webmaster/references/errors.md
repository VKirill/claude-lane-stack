# Yandex.Webmaster — Error codes

API returns HTTP status + JSON `error_code` + `error_message`:

```json
{
  "error_code": "HOST_NOT_VERIFIED",
  "error_message": "Site management rights are not verified"
}
```

## Full code table

### 400 Bad Request

| Code | When |
|---|---|
| `ENTITY_VALIDATION_ERROR` | request body failed structural validation |
| `FIELD_VALIDATION_ERROR` | specific field invalid |
| `INVALID_URL` | URL invalid / not belonging to this host |

### 401 Unauthorized

| Code | When |
|---|---|
| (no body) / `INVALID_OAUTH_TOKEN` | token missing, expired, or invalid |

### 403 Forbidden

| Code | When |
|---|---|
| `INVALID_OAUTH_TOKEN` | token formally valid but not for this resource |
| `INVALID_USER_ID` | URL `{user-id}` differs from token owner |
| `ACCESS_FORBIDDEN` | app lacks required scope (e.g. `webmaster:verify`) |
| `HOSTS_LIMIT_EXCEEDED` | site-per-user limit reached |

### 404 Not Found

| Code | When |
|---|---|
| `RESOURCE_NOT_FOUND` | path does not exist (URL typo) |
| `HOST_NOT_FOUND` | site not in user's list |
| `HOST_NOT_VERIFIED` | site not verified — most analytics endpoints |
| `HOST_NOT_INDEXED` | site not yet indexed |
| `HOST_NOT_LOADED` | site data not yet loaded into the system |
| `SITEMAP_NOT_FOUND` | sitemap_id wrong / deleted |
| `TASK_NOT_FOUND` | recrawl task_id wrong / expired |
| `QUERY_ID_NOT_FOUND` | query_id no longer tracked (dropped from TOP-3000) |

### 409 Conflict (idempotency)

| Code | When | Treat as |
|---|---|---|
| `URL_ALREADY_ADDED` | URL already in recrawl queue | **success** (no quota spent) |
| `HOST_ALREADY_ADDED` | site already in list | **success** (GET hosts for host_id) |
| `SITEMAP_ALREADY_ADDED` | sitemap already added | **success** (GET to fetch sitemap_id) |
| `VERIFICATION_ALREADY_IN_PROGRESS` | verification already running | **success** (wait for completion) |

### 422 Unprocessable Entity

Min/max length violations. E.g. URL too long.

### 429 Too Many Requests

| Code | When | Strategy |
|---|---|---|
| `QUOTA_EXCEEDED` | recrawl daily quota drained | wait until 00:00 MSK |
| `TOO_MANY_REQUESTS_ERROR` | general rate limit | exponential backoff |

### 5xx Server errors

- `500`, `502`, `503`, `504` — transient Yandex issues. Retry with backoff.

## Retry strategy

```python
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
PERMANENT_4XX = {400, 401, 403, 404, 409, 422}

async def request_with_retry(http, method, url, *, attempts=5, **kw):
    for attempt in range(attempts):
        r = await http.request(method, url, **kw)

        if r.status_code == 401:
            # Try refresh token, then retry once
            if attempt == 0 and await refresh_oauth_token():
                continue
            r.raise_for_status()

        if r.status_code in PERMANENT_4XX:
            # Do not retry — logical error
            raise APIError(r.status_code, r.json())

        if r.status_code in RETRYABLE_HTTP:
            retry_after = r.headers.get("Retry-After")
            delay = int(retry_after) if retry_after else min(2 ** attempt, 60)
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)
            continue

        r.raise_for_status()
        return r.json()

    raise APIError("max attempts exceeded")
```

## Idempotency: special 409 handling

```python
async def add_sitemap_idempotent(client, host_id, sitemap_url):
    try:
        r = await client.post_user_added_sitemap(host_id, sitemap_url)
        return r["sitemap_id"]
    except APIError as e:
        if e.status == 409 and e.code == "SITEMAP_ALREADY_ADDED":
            # Sitemap already added — fetch id via GET
            existing = await client.list_user_added_sitemaps(host_id)
            for s in existing["sitemaps"]:
                if s["sitemap_url"] == sitemap_url:
                    return s["sitemap_id"]
            raise RuntimeError("409 SITEMAP_ALREADY_ADDED but not found in list")
        raise
```

Same shape for `URL_ALREADY_ADDED` (recrawl) and `HOST_ALREADY_ADDED` (site add).

## Business meaning of common codes

- **`HOST_NOT_VERIFIED`** — most common; user found the site in your UI but did not finish verification. UX issue, not a code bug.
- **`QUOTA_EXCEEDED`** — normal at high volume. Not an alert — "send the rest tomorrow". Design queues for cross-day retry.
- **`HOST_NOT_INDEXED`** / **`HOST_NOT_LOADED`** — new site, wait for Yandex to index (hours to weeks). Not a bug.
- **`INVALID_OAUTH_TOKEN`** / **401** — token expired or revoked. If retry with refresh fails, ask the user to re-authorize.
- **`HOSTS_LIMIT_EXCEEDED`** — user has too many sites in Webmaster (historical cap ~1700). Remove old ones.

## Common mistakes

- **Retrying 4xx** (except 429) — infinite loop. 400/403/404/409/422 are permanent.
- **Treating 409 as an error** — it is often correct idempotent behavior.
- **Ignoring `Retry-After`** on 429 — Yandex may return an explicit value.
- **Alerting on every 5xx** — transients are normal; let retry resolve.
- **Not distinguishing `HOST_NOT_VERIFIED` from `HOST_NOT_INDEXED`** — first = user did not finish; second = Yandex did not yet index. UX is different.
