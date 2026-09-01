# Pool management — organising, rotating, recovering

`descr` is the only proxy6-side metadata, so it bears almost the whole weight of operational structure. This file covers how to use it well plus rotation, ban detection, and lifecycle.

## Tagging conventions

One `descr` value = one logical pool. Conventions that work in production:

| Pattern | Example | Use case |
|---|---|---|
| `<env>:<service>:<purpose>` | `prod:scraper-amz:reviews` | Multi-service shared key |
| `<env>:<pool-uuid>` | `prod:p-7f3a92` | Many similar pools, version-controlled |
| `<env>:<owner>:<region>` | `prod:adops-eu:de` | Geo-targeted ad ops |

Cap at 50 chars (provider limit). Stick to ASCII (`A-Za-z0-9:_-`) to avoid weird shell/regex bugs in your tooling.

One version + one country per descr (see [proxy-versions.md](proxy-versions.md)). Mixed pools complicate `prolong` accounting.

## Building the in-memory pool

Refresh from `getproxy(state=active, descr=<tag>)` at process start and every N minutes (default 60 min).

```python
# pseudocode
pool = sorted(
    (Proxy(**p) for p in resp["list"].values() if p["active"] == "1"),
    key=lambda p: p.unixtime_end,
    reverse=True,
)
```

Don't trust an in-memory pool older than its TTL. Stale entries lead to scrapers hitting deleted/expired proxies for hours.

## Rotation strategies

### Sticky (per-worker)

Each worker picks one proxy at start; holds it until ban or expiry. Lowest TLS / connection churn.

```python
proxy = pool.pick(worker_id_hash)  # deterministic from worker id
```

Use when: per-worker session is long-lived (logged-in account, cookie-laden scrape, long-poll subscription).

### Round-robin (per-request)

Each request picks the next proxy in a rotating list.

```python
proxy = pool.next()  # advances internal cursor
```

Use when: anonymous scraping, target rate-limits per IP, want maximum distribution.

### Weighted-fresh

Prefer proxies with the longest remaining lifetime. Ageing proxies serve fewer requests; expiry-renewal is gentler.

```python
proxy = random.choices(pool.items, weights=[p.remaining_seconds for p in pool.items])[0]
```

Use when: pool size is small and you can't afford a "just-died" proxy mid-request.

## Ban detection

Track per-proxy stats in process memory (or Redis for multi-process):
- `success_count`
- `error_count` (target site 4xx, 5xx, captcha, connection refused, timeout)
- `last_used_at`

On rolling-window error ratio > threshold (default 30% over 50 requests), quarantine the proxy.

Quarantine policy:
1. Mark `active=quarantined` in local state.
2. Skip in rotation for N minutes (default 30 min — may be temp rate-limit, not perma-ban).
3. After cooldown, run one probe request. If success, return to pool. If fail, mark `dead`.
4. Dead proxies: cycle out at next refresh; queue replacement `buy`.

Do NOT call proxy6 `check` for routine ban detection — that's a proxy6-side reachability check, not a target-site check, and it costs a rate-limit token.

## Replacement / "drain & refill"

When pool drops below `min_size`:
1. Compute `delta = target_size - current_size`.
2. Pre-flight: `getprice(delta, period, version)` + `getcount(country, version)`.
3. `buy(count=delta, period, country, version, descr=<same tag>)`.
4. Merge response `list` into local pool.

Scheduled (e.g. nightly) refill is gentler than reactive — avoids spike requests at the worst moments.

## Scheduled cleanup

Expired proxies (`active=0`) clutter `getproxy` results without value. Daily cleanup:

```python
# Pseudocode
expired = await client.getproxy(state="expired", descr=tag)
ids = [p["id"] for p in expired["list"].values()]
if ids:
    # Dry-run print
    print(f"Will delete {len(ids)} expired proxies: {ids}")
    await client.delete(ids=",".join(ids))
```

Keep this as a separate cron / scheduled job, never inline in the scraping path. Run with `state=expired` filter — NEVER `state=all` + descr filter where you might pick up still-active proxies.

## Recovery flow — pool went bad

When a whole pool is misbehaving (target site banned the entire descr):
1. Pause scrapers using that descr (set a feature flag).
2. `getproxy(descr=<tag>)` — enumerate.
3. Decide: replace the whole pool (delete + buy in a different country/version) OR change the target-side strategy (slow down, add UA rotation, etc.) without touching the pool.
4. If replacing: `delete(ids=<csv>)` of the bad pool, `buy(count=N, ...)` with the new params, same descr (or a versioned descr like `:rev-2`).
5. Resume scrapers after warm-up.

## Pool sizing

Rule of thumb:
- One proxy can typically handle `requests_per_second_target_site × 60` requests per minute against a single target without flagging.
- Pool size ≥ `(total RPM target) / (proxy RPM safe limit)` + 30% headroom.
- Add `+1` per concurrent worker even if the math says less — workers need exclusive sticky IPs.

These are guides; benchmark against your specific target.
