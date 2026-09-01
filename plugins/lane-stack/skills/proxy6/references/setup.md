# Setup — API key, log scrubbing, IP allowlist, rate-limit overview

This file covers everything you do BEFORE the first method call.

## Base URL pattern

```
https://px6.link/api/{api_key}/{method}/?{params}
```

- `{api_key}` — secret, taken from personal dashboard at proxy6.net.
- `{method}` — one of: `getprice`, `getcount`, `getcountry`, `getproxy`, `setdescr`, `buy`, `prolong`, `delete`, `check`, `ipauth`.
- `{params}` — query string. All methods are HTTP GET; servers accept POST but GET is documented and conventional.
- Responses are always JSON, always HTTP 200 on application errors (error info is in the envelope), HTTP 429 on rate limit only.

## Where to put the api_key

| Surface | Allowed? |
|---|---|
| Environment variable (`PROXY6_API_KEY`) | ✅ Required |
| Server-side secrets manager (Vault, Doppler, 1Password Connect, AWS SM) | ✅ |
| Docker / PM2 ecosystem env | ✅ |
| Browser bundle / client JS | ❌ NEVER — the key has full balance-spending power |
| Git history / commits | ❌ rotate immediately on leak |
| Per-developer `.env.local` (gitignored) | ✅ for dev keys only |
| Logs (access logs, APM, error traces with full URL) | ❌ scrub at reverse proxy |

## Log scrubbing — Angie / Nginx

Because the api_key is part of the URL **path**, every reverse-proxy access log captures it by default. Mask it at the edge.

### Angie / Nginx log_format with regex mask

```nginx
# /etc/nginx/conf.d/log-scrub.conf (or angie.conf)
map $request_uri $request_uri_scrubbed {
    "~^(?<prefix>/api/)[^/]+(?<suffix>/.*)$"  "${prefix}***${suffix}";
    default                                    $request_uri;
}

log_format scrubbed '$remote_addr - $remote_user [$time_local] '
                    '"$request_method $request_uri_scrubbed $server_protocol" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

access_log /var/log/angie/proxy6.access.log scrubbed;
```

This replaces the api_key segment with `***`. Verify with `tail` after a request — if you can read the key in logs, the regex didn't apply.

### APM / OTel

If you ship spans with the full URL as `http.url` attribute, configure a span processor that strips the path segment between `/api/` and the next `/`. Pino / Winston: redact `req.url`.

## IP allowlist (provider side)

proxy6.net's dashboard offers an optional **IP allowlist for API calls**. When enabled, requests from any other IP return `error_id 105`.

- Use in production — limits blast radius if the key leaks.
- Add CI / staging / prod IPs. If you use NAT egress (Cloudflare WARP, NAT gateways), add the egress range.
- Keep an off-switch — document in the runbook how to disable the allowlist when migrating IPs.

## Rate limit overview

- **Hard limit: 3 requests per second per api_key** (server side).
- Exceeding → HTTP 429 Too Many Requests on excess requests.
- Burst tolerance is small; do not assume a token-bucket of size > 3.
- Default client budget: **2 req/s** (33% headroom). See [rate-limit-and-retry.md](rate-limit-and-retry.md).

## Quick smoke test

After plumbing the api_key, the cheapest no-op call is `getprice` with no params (returns the full price matrix):

```bash
curl -sS "https://px6.link/api/${PROXY6_API_KEY}/getprice/" | jq .status
# Expected: "yes"
```

If you see:
- `"no"` with `error_id: 100` → wrong key / typo.
- `"no"` with `error_id: 105` → source IP not in dashboard allowlist.
- HTTP 429 → you already hit the rate limit; back off and retry once.
- Connection error → check network path, no TLS-MITM in the way.

## Envelope shapes (refresher)

```json
// success
{ "status": "yes", "user_id": "1", "balance": "48.80", "currency": "RUB", "...": "method-specific" }

// failure
{ "status": "no", "error_id": 100, "error": "Error key" }
```

`status`, `user_id`, `balance`, `currency` always appear on success. `error_id` + `error` always appear on failure. Read `status` first — never read domain fields without it.

## Currency

`currency` reflects your account's billing currency (`RUB` or `USD`, account-level setting). All `balance`, `price`, and `price_single` values are strings in major units of that currency. Do not assume kopecks/cents.
