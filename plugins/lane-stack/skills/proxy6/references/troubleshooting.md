# Troubleshooting — proxy6

Symptom-indexed. Find your symptom, follow the diagnosis steps, apply the fix.

Numeric defaults referenced here are SSOT in [recommended-defaults.md](recommended-defaults.md).

---

## HTTP 429 storm — every call fails

**Symptoms**
- Many requests return HTTP 429 in a short window
- Retry loop never recovers; backoff stretches further each attempt
- Multiple workers / processes share the same api_key

**Diagnose**
```bash
# 1. Count the rate in your own logs over the last minute
grep "proxy6 call" app.log | awk '{print $1}' | uniq -c | sort -rn | head

# 2. Confirm no second process is using the same key
ps -ef | grep -i proxy6
```

**Common causes**
- Limiter local to one process while many processes share the key
- `getproxy` paging in parallel (loops without limiter)
- `check` looped over a pool for ban detection (see wrong-vs-right pair 12)
- Limiter reservoir set too high (> 3) or `minTime` < 333 ms

**Fix**
- Move the limiter to a shared resource — Bottleneck with IORedis store, or a single proxy process all workers call into
- Reduce `reservoir` to 3 and `minTime` to 340 ms ([recommended-defaults.md](recommended-defaults.md))
- Sequence parallel paging — one call at a time

---

## `error_id 100` — Error key

**Symptoms**
- Every call returns `status: "no"`, `error_id: 100`
- Worked yesterday, fails today

**Diagnose**
```bash
# Re-read the key from the secret source
echo "${PROXY6_API_KEY}" | head -c 4   # first 4 chars to confirm correct key, do NOT print all

# Smoke test
curl -sS "https://px6.link/api/${PROXY6_API_KEY}/getprice/" | jq .
```

**Common causes**
- Key was rotated in the dashboard but not in the secrets manager
- Wrong key for environment (dev key against prod resources)
- Leading / trailing whitespace in the env value
- Multiple `.env` files merged in wrong order

**Fix**
- Re-pull from secrets manager, restart service
- Confirm with smoke test from the runtime container, not local

---

## `error_id 105` — Error ip

**Symptoms**
- `status: "no"`, `error_id: 105` on all calls
- Just deployed / migrated infra

**Diagnose**
```bash
# Find your actual egress IP
curl -sS https://ifconfig.me
# Cross-check with proxy6 dashboard allowlist
```

**Common causes**
- Migrated to a new VPS / NAT gateway whose IP isn't in the dashboard allowlist
- CI runner IP changed (GitHub Actions hosted runners rotate)
- IPv6 path active when allowlist only knows IPv4 (or vice versa)
- The `ipauth` call was used incorrectly thinking it would set API allowlist (it does not — see [ipauth-strategy.md](ipauth-strategy.md))

**Fix**
- Add the new egress IP to the dashboard allowlist
- For CI: either pin to a self-hosted runner with stable egress, or use a fixed-egress proxy in front
- Disable allowlist temporarily ONLY while migrating, then re-enable with updated set

---

## `error_id 300` — out of stock

**Symptoms**
- `buy` returns `error_id: 300`
- Stock was fine yesterday

**Diagnose**
```python
stock = await client.getcount(country=country, version=version)
print(stock.count)  # check current stock
```

**Common causes**
- Country/version combo genuinely sold out (common for niche countries)
- Asked for more than `getcount` reports (bursty cleanup ran in another process and bought through the stock)
- Country code typo (`uk` vs `gb`, `ua` vs `ru`)

**Fix**
- Reduce `count` to ≤ `getcount.count`
- Pick a fallback country (config-driven priority list)
- Try a different version (IPv6 stocks differ from IPv4)

---

## `error_id 400` — Error no money

**Symptoms**
- `buy` or `prolong` returns `error_id: 400`
- Existing scrapers continue to work (until proxies expire)

**Diagnose**
- Check `balance` and `currency` from any successful envelope
- Pull recent transactions from proxy6 dashboard
- Sum predicted next-7-day spend from `auto_prolong` proxies via `getproxy(state=active)` × `getprice`

**Common causes**
- `auto_prolong` charged the account between scheduled top-ups
- Tier-change drift — actual cost > expected (rare but happens)
- Manual `buy` for a one-off campaign forgotten

**Fix**
- Top up via dashboard / payment partner
- Disable `auto_prolong` on inactive pools — `delete` and re-`buy` with auto_prolong off
- Add a balance alert at `7 × daily_burn` per [recommended-defaults.md](recommended-defaults.md)

---

## `error_id 410` — Error price (price ≤ 0)

**Symptoms**
- `getprice` or `buy` returns `error_id: 410`
- Specific count/period/version combination triggers it

**Common causes**
- The combination is not sold (e.g. extremely short `period` for a tier that requires minimum days)
- `count = 0` or negative
- `period = 0`

**Fix**
- Re-check the spec / dashboard for valid `period` minimums for that version
- Increase `period` (e.g. minimum 5–7 days)
- Confirm `count` ≥ 1

---

## `error_id 404` — not found on prolong / delete / setdescr

**Symptoms**
- `prolong`, `delete`, or `setdescr` returns `error_id: 404`

**Diagnose**
```python
# Confirm the ids you're passing exist and belong to you
got = await client.getproxy(state="all")
known_ids = set(got.list.keys())
print(set(target_ids) - known_ids)  # ids you THINK exist but don't
```

**Common causes**
- Stale local cache — proxies expired or were already deleted
- Trying to act on someone else's id (impossible, but can look this way if you stored ids from a different key's pool)
- Off-by-one in CSV construction (e.g. trailing empty id from `.split(",")` on `"1,2,3,"`)

**Fix**
- Refresh from `getproxy` first
- Strip empty values from the CSV: `",".join(filter(None, ids))`

---

## `descr` overflow — `error_id 250`

**Symptoms**
- `buy` or `setdescr` returns `error_id: 250`
- The `descr` looked fine in logs

**Common causes**
- `descr` ≥ 51 chars (provider hard limit is 50)
- Empty `descr` in `setdescr.new`

**Fix**
- Truncate / restructure tag (e.g. use short id instead of UUID)
- Add client-side validation: `assert 1 <= len(descr) <= 50`

---

## Mixed-version `prolong` — missing `price_single`

**Symptoms**
- `prolong` response has `price` but no `price_single`
- Accounting code raises `KeyError` / `undefined`

**Cause**
- `ids` mixed across versions (e.g. some IPv4 + some IPv6)

**Fix**
- Group `ids` by `version` locally, call `prolong` once per group
- Or stick to the convention "one descr = one version" and `prolong` within a descr

See [methods.md](methods.md) `prolong` notes and [purchase-and-billing.md](purchase-and-billing.md).

---

## Accidentally deleted a pool via `descr` filter

**Symptoms**
- Scrapers report all-proxies-down
- `getproxy` shows the pool empty
- `delete` was called with `descr=...` earlier

**Recovery**
- There is NO undo and NO refund — proxies are gone
- Buy a replacement pool with the same `descr` and same `count`/`period`/`country`/`version`
- Pause affected scrapers; warm up the new pool; resume

**Prevention**
- The canonical client refuses `delete(descr=...)` without `ids` unless `confirm_dry_run=False`
- Always run `getproxy(descr=...)` first, print every id, get explicit confirmation, THEN `delete(ids=...)`

See [wrong-vs-right.md](wrong-vs-right.md) pair 4.

---

## Workers can't reach proxies after deploy (ipauth wipeout)

**Symptoms**
- All workers from prod NAT get "407 Proxy Authentication Required" or connection refused via the proxy
- Worked before deploy

**Diagnose**
```python
# Inspect the bound list — call ipauth with a no-op... but there is no read endpoint
# Best: maintain the bound-IP registry in your infra repo and diff it
```

**Cause**
- Someone called `ipauth(ip=<partial list>)` — full-replace semantics kicked the prod IPs out

**Fix**
- Restore: call `ipauth(ip=<full prior union from registry>)`
- Postmortem: enforce "always pass the full union, sourced from registry" rule in code review (see [ipauth-strategy.md](ipauth-strategy.md))

---

## Pool sized correctly but scrapers fail with high error rate

**Symptoms**
- Per-proxy error rate > 30% rolling
- Target site returns 403 / captcha
- proxy6 `check` reports the proxies as reachable

**Diagnose**
- Is this a proxy-reputation problem (target banned the IP) or a target-side change (new anti-bot)?
- Try a fresh proxy from a different country/version — does it succeed?

**Fix**
- If reputation: rotate the pool — `delete` bad pool + `buy` new pool with new country/version. Don't reuse descr if you also want to invalidate cached state.
- If target-side: don't burn the pool. Add UA rotation, slow down, add cookies/session — the proxy is fine.

See [pool-management.md](pool-management.md) recovery flow.

---

## Calls work locally but fail in Docker / production

**Symptoms**
- `error_id 105` only in containerised env
- Works on dev laptop

**Cause**
- Container egress IP is different from your dashboard allowlist
- Egress goes through a NAT gateway you haven't added

**Fix**
- Run `curl https://ifconfig.me` INSIDE the container to discover the egress
- Add that IP to the dashboard allowlist

---

## Latency-driven retries — timeout but server eventually responds

**Symptoms**
- p99 latency spikes > 10 s
- Retries pile up

**Diagnose**
- Check upstream network (regional routing issues to proxy6 servers)
- Check your container's DNS resolution time (re-resolves on every request?)

**Fix**
- Pin `timeout=10 s` ([recommended-defaults.md](recommended-defaults.md))
- Use `AbortSignal.timeout` / `httpx` per-request timeout (not a global default that races with the limiter)
- Enable HTTP keep-alive to amortise TLS handshakes

---

## How to escalate to proxy6 support

When the above doesn't resolve:
1. Capture: `user_id` from a successful envelope, `error_id` + `error` from the failing call, UTC timestamp, the masked URL (key removed).
2. Open a ticket via proxy6.net support channel.
3. Do NOT share the api_key — they don't need it; they look up by `user_id`.
4. Mention what changed (deploy, key rotation, infra migration) — usually it's the last change.
