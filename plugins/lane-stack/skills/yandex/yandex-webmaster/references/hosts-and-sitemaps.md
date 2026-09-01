# Yandex.Webmaster — Hosts, verification, sitemaps

## User

```
GET /v4/user
Authorization: OAuth <token>
```

```json
{ "user_id": 1234567 }
```

Fetch once, persist. Used by all other paths.

## Hosts CRUD

### List sites

```
GET /v4/user/{user-id}/hosts
```

Response:

```json
{
  "hosts": [
    {
      "host_id": "https:example.com:443",
      "ascii_host_url": "https://example.com:443/",
      "unicode_host_url": "https://example.com:443/",
      "verified": true,
      "main_mirror": { "host_id": "...", "ascii_host_url": "..." },
      "host_data_status": "OK"
    }
  ]
}
```

- `host_id` — internal id, **persist**, never guess.
- `verified` — without `true` most analytics endpoints return 404.
- `host_data_status`: `NOT_INDEXED`, `NOT_LOADED`, `OK`.
- `main_mirror` — primary mirror; `https://example.com` and `http://example.com` get different `host_id`s but share `main_mirror`.

### Add site

```
POST /v4/user/{user-id}/hosts
Content-Type: application/json

{ "host_url": "https://example.com" }
```

Success — 201. Errors: 409 `HOST_ALREADY_ADDED`, 403 `HOSTS_LIMIT_EXCEEDED`.

> Verify against current docs: exact site-count limit (historically ~1703) — check or measure.

### Delete site

```
DELETE /v4/user/{user-id}/hosts/{host-id}
```

The site disappears from the dashboard, analytics are wiped. Irreversible.

### Site info

```
GET /v4/user/{user-id}/hosts/{host-id}
```

Same shape as one element of `/hosts`.

### Summary

```
GET /v4/user/{user-id}/hosts/{host-id}/summary
```

Aggregated stats: pairs/state, SQI, problem counts by severity. Useful for dashboards.

## Verification

### State

```
GET /v4/user/{user-id}/hosts/{host-id}/verification
```

```json
{
  "verification_uin": "abc123def456",
  "verification_state": "VERIFIED",
  "verification_type": "META_TAG",
  "applicable_verifiers": ["DNS", "HTML_FILE", "META_TAG", "TXT_FILE"]
}
```

States:

| State | Meaning |
|---|---|
| `NONE` | not verified |
| `IN_PROGRESS` | check in progress (Yandex waiting for file/record) |
| `VERIFIED` | confirmed |
| `VERIFICATION_FAILED` | failed (file missing, DNS not set) |
| `INTERNAL_ERROR` | Yandex-side error |

### Start verification

```
POST /v4/user/{user-id}/hosts/{host-id}/verification?verification_type={DNS|HTML_FILE|META_TAG|TXT_FILE}
```

Response — same object as `GET`, including `verification_uin` (the token to publish on the site/DNS).

Verifier types:

| Type | How it works |
|---|---|
| `DNS` | TXT record on the domain: `yandex-verification: <uin>` |
| `HTML_FILE` | File `yandex_<uin>.html` at site root with body `<html><body>Verification: <uin></body></html>` |
| `META_TAG` | `<meta name="yandex-verification" content="<uin>" />` inside `<head>` of homepage |
| `TXT_FILE` | File with unique name (legacy) |
| `AUTO` / `DELEGATED` / `PDD` | system / delegated domains / Yandex Mail for domain — typically not requested manually |

409 `VERIFICATION_ALREADY_IN_PROGRESS` — already running; idempotent success.

### Owners (verified managers)

```
GET /v4/user/{user-id}/hosts/{host-id}/owners
```

Other users that have verified ownership for this site.

## Sitemaps

### All sitemaps (bot-discovered)

```
GET /v4/user/{user-id}/hosts/{host-id}/sitemaps?limit=10&from={sitemap-id}
```

- `limit`: 1-100, default 10
- `from`: pagination — `sitemap_id` to continue after

```json
{
  "sitemaps": [
    {
      "sitemap_id": "c7-fe:80-c0",
      "sitemap_url": "https://example.com/sitemap.xml",
      "last_access_date": "2024-01-15T10:30:00.000+03:00",
      "errors_count": 0,
      "urls_count": 1500,
      "children_count": 0,
      "sources": ["ROBOTS_TXT", "WEBMASTER"],
      "sitemap_type": "SITEMAP"
    }
  ]
}
```

- `sources`: how Yandex learned about the sitemap (`ROBOTS_TXT`, `WEBMASTER`, `INDEX_SITEMAP`)
- `sitemap_type`: `SITEMAP` or `INDEX` (index sitemap = catalogue of children)

### One sitemap

```
GET /v4/user/{user-id}/hosts/{host-id}/sitemaps/{sitemap-id}
```

Same shape — with current `errors_count` and `urls_count` after re-processing.

### User-added sitemaps

```
GET /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps
```

Only sitemaps the user explicitly submitted (not those discovered via `robots.txt`).

### Add sitemap

```
POST /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps
Content-Type: application/json

{ "url": "https://example.com/sitemap.xml" }
```

Response 201:

```json
{ "sitemap_id": "c7-fe:80-c0" }
```

409 `SITEMAP_ALREADY_ADDED` — catch, fetch `sitemap_id` via GET; **not** an error.

### Delete

```
DELETE /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps/{sitemap-id}
```

Removes from user-added. If the sitemap is also in `robots.txt` it stays in the general list.

### One user-added sitemap

```
GET /v4/user/{user-id}/hosts/{host-id}/user-added-sitemaps/{sitemap-id}
```

## Important URLs (key-page monitoring)

```
GET  /v4/user/{user-id}/hosts/{host-id}/important-urls
POST /v4/user/{user-id}/hosts/{host-id}/important-urls
```

List of priority URLs the bot tracks separately (indexing history, changes).

> Verify against current docs: exact max URLs (typically ~100).

## SQI history

```
GET /v4/user/{user-id}/hosts/{host-id}/sqi-history?date_from=&date_to=
```

Time series of SQI (site quality index) for charting.
