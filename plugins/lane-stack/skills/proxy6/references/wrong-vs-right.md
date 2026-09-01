# Wrong vs Right — paired anti-patterns

Each pair is a real production failure mode (security, money, destructive, or rate-limit). Numeric defaults reference [recommended-defaults.md](recommended-defaults.md).

---

## 1. API key in source code

### ❌ Wrong

```python
client = Proxy6Client(api_key="ABCD1234EFGH5678")  # hardcoded
```

```ts
const KEY = "ABCD1234EFGH5678";
fetch(`https://px6.link/api/${KEY}/getproxy/`);
```

Key ends up in:
- Git history (anyone with repo access can spend your balance)
- Docker images (compromised registry = leak)
- Frontend bundles if the file is imported into client code
- CI logs if printed during build

### ✅ Right

```python
client = Proxy6Client()  # reads PROXY6_API_KEY from env
```

```ts
const key = process.env.PROXY6_API_KEY;
if (!key) throw new Error("PROXY6_API_KEY not set");
```

Plus: store in secrets manager (Vault / Doppler / 1Password Connect / AWS SM), rotate quarterly, alert on key not in expected scope.

---

## 2. API key visible in reverse-proxy access logs

### ❌ Wrong

```nginx
# default log_format includes $request_uri verbatim
access_log /var/log/nginx/access.log combined;
```

Result: every request line contains `/api/ABCD1234.../getproxy/` — the key is plaintext in logs anyone with shell access can read.

### ✅ Right

```nginx
map $request_uri $request_uri_scrubbed {
    "~^(?<prefix>/api/)[^/]+(?<suffix>/.*)$"  "${prefix}***${suffix}";
    default                                    $request_uri;
}
log_format scrubbed '... "$request_method $request_uri_scrubbed $server_protocol" ...';
access_log /var/log/nginx/proxy6.access.log scrubbed;
```

Verify with `tail` after one real request: the key segment must read `***`.

---

## 3. Buying without pre-flight checks

### ❌ Wrong

```python
# Hope for the best
order = await client.buy(
    count=100, period=30, country="us", version="6",
    descr="prod:scraper",
)
```

Failure modes hit in order: `error_id 220` (US has no IPv6 stock today), `error_id 300` (count > stock), or `error_id 400` (balance too low). Each one burns a rate-limit token and surprises the caller.

### ✅ Right

```python
# 1. Price quote
quote = await client.getprice(count=100, period=30, version="6")
# 2. Stock check
stock = await client.getcount(country="us", version="6")
if int(stock.count) < 100:
    raise OutOfStock("only %s available" % stock.count)
# 3. Balance check (use envelope or fresh probe)
balance = float(quote.balance)
if balance < float(quote.price) * 1.10:
    raise InsufficientFunds(f"balance {balance} < quote*1.10 {float(quote.price)*1.10}")
# 4. Buy
order = await client.buy(
    count=100, period=30, country="us", version="6",
    descr="prod:scraper",
)
```

See [purchase-and-billing.md](purchase-and-billing.md) for the full sequence.

---

## 4. Blind `delete` by `descr`

### ❌ Wrong

```python
# "Clean up the test pool"
await client.delete(descr="prod:scraper-A:reviews")
```

If anyone else (or a past you) ever tagged a proxy with the same `descr`, you just deleted it. There is NO undo and NO refund.

### ✅ Right

```python
# Dry run
got = await client.getproxy(descr="prod:scraper-A:reviews")
ids = list(got.list.keys())
print(f"About to delete {len(ids)} proxies: {ids}")
input("Proceed? [y/N] ").strip().lower() == "y" or sys.exit()

await client.delete(ids=ids)
```

In the canonical client, `delete(descr=...)` without `ids` raises by default (`confirm_dry_run=True`). See `Proxy6Client.delete` in [integration-python.md](integration-python.md) and `client.delete` in [integration-node.md](integration-node.md).

---

## 5. `ipauth` partial overwrite — wiping production

### ❌ Wrong

```python
# "Add the new CI runner IP"
await client.ipauth(ip=["10.20.30.40"])
```

`ipauth` REPLACES the full list. Production NAT egress IPs are now removed from the bound list — every prod worker without password auth instantly fails.

### ✅ Right

```python
# Always pass the FULL union
desired = {
    "203.0.113.1",       # prod NAT egress
    "203.0.113.2",       # prod NAT egress (secondary)
    "198.51.100.10",     # CI runner #1
    "10.20.30.40",       # CI runner #2 (new)
}
await client.ipauth(ip=sorted(desired))
```

Pull `desired` from a single source-of-truth registry (YAML in infra repo). See [ipauth-strategy.md](ipauth-strategy.md).

---

## 6. Enabling `auto_prolong` without budget alarm

### ❌ Wrong

```python
await client.buy(
    count=100, period=7, country="ru", version="4",
    descr="prod:scraper", auto_prolong=True,
)
# 7 days later: proxy6 charges you for 100 more × period.
# 21 days later: balance is empty, scrapers fail with error_id 400, ops paged at 3am.
```

### ✅ Right

```python
# Option A — keep auto_prolong OFF (default)
await client.buy(
    count=100, period=7, country="ru", version="4",
    descr="prod:scraper",  # no auto_prolong
)

# Option B — opt in, with guard rails
await client.buy(
    count=100, period=7, country="ru", version="4",
    descr="prod:scraper",
    auto_prolong=True,
)
# REQUIRED additionally:
#  - daily metric: proxy6_balance gauge alert at < 7 × daily_burn
#  - documented kill switch: script to delete + re-buy without auto_prolong
#  - reconciliation cron: sum predicted renewal cost ≤ next-week budget
```

If you can't write the three guard rails, do not enable `auto_prolong`.

---

## 7. Hardcoded proxy strings — no refresh path

### ❌ Wrong

```python
# Set once and forgotten
PROXIES = [
    {"host": "185.22.134.250", "port": 7330, "user": "5svBNGSn", "pass": "9WJpHKf"},
    {"host": "185.22.134.251", "port": 7331, "user": "tJk1Eg",   "pass": "P3w8Fr"},
]
```

When these expire (`date_end` reached), every request fails. The script has no way to discover replacements; ops has to redeploy.

### ✅ Right

```python
async def refresh_pool(client: Proxy6Client, descr: str) -> list[Proxy]:
    resp = await client.getproxy(state="active", descr=descr)
    return list(resp.list.values())

# Refresh on startup and every 60 minutes
pool = await refresh_pool(client, "prod:scraper-A:reviews")
```

See [pool-management.md](pool-management.md).

---

## 8. Ignoring 429 — naive retry storm

### ❌ Wrong

```python
async def call(url):
    while True:
        resp = await httpx.get(url)
        if resp.status_code == 200:
            return resp.json()
        # Just try again right away
```

The first 429 triggers an immediate second request that's also 429, multiplying the load. With multiple workers, this can hold the key offline for minutes.

### ✅ Right

```python
@retry(
    retry=retry_if_exception_type(Proxy6RetryableError),
    wait=wait_random_exponential(multiplier=0.5, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def call(url):
    await bucket.acquire()  # token bucket first
    resp = await httpx.get(url)
    if resp.status_code == 429:
        raise Proxy6RetryableError("rate limit")
    ...
```

See [rate-limit-and-retry.md](rate-limit-and-retry.md).

---

## 9. Mixed-version `prolong` — assuming uniform `price_single`

### ❌ Wrong

```python
resp = await client.prolong(period=30, ids=mixed_ids)
per_proxy_cost = float(resp.price_single)  # KeyError / AttributeError — field is absent
```

### ✅ Right

```python
# Group by version BEFORE prolonging
by_version = group_proxies_by_version(local_pool, mixed_ids)
totals = []
for version, ids in by_version.items():
    resp = await client.prolong(period=30, ids=ids)
    totals.append((version, resp.price, resp.price_single))
```

Or simpler: structure your descr tags so one tag = one version, then call `prolong` once per tag.

---

## 10. Logging the full URL — leaking the key into APM

### ❌ Wrong

```python
logger.info("GET %s", url)  # url contains api_key in path
```

```ts
console.log(`fetched ${url}`);  // ditto
```

OpenTelemetry / Pino / Winston / Datadog all happily index this. The key is now in your APM forever.

### ✅ Right

```python
logger.info(
    "proxy6 call method=%s params=%s status=%s",
    method,
    {k: v for k, v in params.items() if k != "api_key"},
    response_status,
)
```

```ts
log.info({ method, params: sanitised, status: res.status }, "proxy6 call");
```

Span name `proxy6.<method>` with attributes for method, status, latency, attempt. NEVER `http.url`.

---

## 11. Using `descr` longer than 50 chars

### ❌ Wrong

```python
descr = f"prod:scraper-A:team-data-platform-2026:run-{uuid4()}"  # 70+ chars
await client.buy(..., descr=descr)
# error_id 250
```

### ✅ Right

```python
# Validate client-side BEFORE wasting a rate-limit token
descr = f"prod:scraper-A:run-{short_id}"  # ≤ 50 chars
assert len(descr) <= 50, "descr too long"
await client.buy(..., descr=descr)
```

Or in the typed client, reject in the constructor via a Pydantic field validator or Zod refinement.

---

## 12. Running `check` in a loop for ban detection

### ❌ Wrong

```python
for proxy in pool:
    status = await client.check(proxy_id=proxy.id)
    if not status.proxy_status:
        pool.quarantine(proxy)
```

`check` is a rate-limit-budgeted call (1 token each). A pool of 100 proxies costs 50 seconds of budget for one round. And `check` tests proxy6's view, not your target site's view.

### ✅ Right

Detect bans from target-site responses in your scraping client:

```python
async def request_via_proxy(proxy, url):
    try:
        resp = await target_http.get(url, proxies=proxy.url)
        if resp.status_code in (403, 429, 503):
            pool.record_error(proxy)
        else:
            pool.record_success(proxy)
        return resp
    except (ConnectError, TimeoutError):
        pool.record_error(proxy)
        raise

# Quarantine when rolling error_rate > 30%
```

Only call `check` when investigating one specific proxy interactively. See [pool-management.md](pool-management.md).
