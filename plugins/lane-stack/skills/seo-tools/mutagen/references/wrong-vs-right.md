# Wrong vs Right — paired anti-patterns

Each pair is a real failure mode (money, async correctness, encoding, security). Numeric defaults reference [recommended-defaults.md](recommended-defaults.md).

---

## 1. API key in source code

### ❌ Wrong

```python
client = MutagenClient(api_key="ABCD1234EFGH5678")
```

```ts
const KEY = "ABCD1234EFGH5678";
fetch(`http://api.mutagen.ru/json/${KEY}/mutagen.balance/`);
```

The key grants full balance-spending power. Once it's in git history, anyone with read access can drain the account.

### ✅ Right

```python
import os
client = MutagenClient(os.environ["MUTAGEN_API_KEY"])
```

```ts
const key = process.env.MUTAGEN_API_KEY;
if (!key) throw new Error("MUTAGEN_API_KEY not set");
```

Plus: store in secrets manager, rotate periodically, alert on unexpected use.

---

## 2. API key in reverse-proxy access logs

### ❌ Wrong

```nginx
access_log /var/log/nginx/access.log combined;
```

Every request line in the log contains `/json/ABCD1234.../mutagen.balance/`. Shell access = leaked key.

### ✅ Right

```nginx
map $request_uri $request_uri_scrubbed {
    "~^(?<prefix>/json/)[^/]+(?<suffix>/.*)$"  "${prefix}***${suffix}";
    default                                     $request_uri;
}
log_format scrubbed '... "$request_method $request_uri_scrubbed $server_protocol" ...';
access_log /var/log/nginx/mutagen.access.log scrubbed;
```

Verify with `tail` after one real request — the key segment must read `***`.

---

## 3. Calling `check_key.new` without persistent task_id lookup

### ❌ Wrong

```python
# Retry-on-failure: just call new again
async def check(key):
    try:
        resp = await client.check_key_new(key)
        return await poll(resp["task_id"])
    except Exception:
        # Retry
        resp = await client.check_key_new(key)  # double-charged!
        return await poll(resp["task_id"])
```

Every `check_key.new` is paid. The retry above charges twice for one logical operation.

### ✅ Right

```python
async def check(key, store):
    task_id = await store.get(key)
    if task_id is None:
        resp = await client.check_key_new(key)   # paid
        task_id = resp["task_id"]
        await store.put(key, task_id)            # persist BEFORE polling
    return await poll(task_id)
```

On retry, lookup the persisted `task_id` and resume polling — no new charge.

See [check-key-async-pattern.md](check-key-async-pattern.md).

---

## 4. Tight-loop polling — no backoff

### ❌ Wrong

```python
while True:
    resp = await client.check_key_get(task_id)
    if resp["status"] == "completed":
        return resp
    # Just try again right away
```

Burns CPU and rate-limit budget. With many parallel `check_key` tasks, this can effectively DDoS the account and stall everything.

### ✅ Right

```python
delay = 2.0
for _ in range(60):
    resp = await client.check_key_get(task_id)
    if resp["status"] == "completed":
        return resp
    if resp["status"] in ("rejected", "error"):
        raise MutagenTerminalError(resp["status"])
    await asyncio.sleep(min(delay, 30.0))
    delay *= 1.5
raise MutagenTerminalError("timeout")
```

Exp backoff 2 s → 30 s cap, max 60 attempts — see [recommended-defaults.md](recommended-defaults.md).

---

## 5. Buying without balance pre-check

### ❌ Wrong

```python
# 1500 keys submitted blind
mass_id = (await client.parser_mass_new(keys, "batch", "wordstat_qso"))["id"]
```

If balance is already low, this fails partway with an HTTP error or fills the batch with errors — and you've burned the partial spend regardless.

### ✅ Right

```python
expected = len(keys) * rates.parser_mass_per_keyword
balance = await client.balance()
if balance < expected * 2.0:
    raise InsufficientFunds(f"balance={balance}, need {expected * 2.0}")
mass_id = (await client.parser_mass_new(keys, "batch", "wordstat_qso"))["id"]
```

Safety factor of 2.0 covers tariff drift and concurrent spend. See [pricing-and-balance.md](pricing-and-balance.md).

---

## 6. Loop `parser.get` instead of `parser.mass.new`

### ❌ Wrong

```python
results = {}
for key in keys:               # 500 keys
    resp = await client.parser_get(key, "wordstat_qso", "213")
    while resp["status"] != "finish":
        await asyncio.sleep(2)
        resp = await client.parser_get(key, "wordstat_qso", "213")
    results[key] = resp["data"]["frequency"]
```

500 HTTP submits + 500 polling loops + 500 separate paid calls. Slow, brittle, expensive.

### ✅ Right

```python
keys = normalize_keys(raw)  # dedupe + normalize
mass_id = await client.parser_mass_new(
    keys_list=keys, name="batch-1",
    parser="wordstat_qso", region_id="213",
)
data = await client.parser_mass_with_polling(mass_id)
# data is now a single dict with all 500 results
```

One submit, one polling loop, deduped — every key charged once. See [batch-strategy.md](batch-strategy.md).

---

## 7. Not deduplicating `keys_list`

### ❌ Wrong

```python
# Raw input from CSV — 580 rows, 80 dupes
keys = open("seeds.csv").read().splitlines()
await client.parser_mass_new(keys_list=keys, ...)
```

You just paid for 580 keyword-lookups when the unique set is 500. 16% wasted spend.

### ✅ Right

```python
def normalize(raw):
    seen, out = set(), []
    for k in raw:
        k = " ".join(k.strip().split()).casefold()
        if k and k not in seen:
            seen.add(k); out.append(k)
    return out

keys = normalize(open("seeds.csv").read().splitlines())
await client.parser_mass_new(keys_list=keys, ...)
```

Dedup is the single biggest waste-elimination win in SEO batches.

---

## 8. GET with > 50 keys (URL > 128KB)

### ❌ Wrong

```python
keys = [...]  # 300 long Cyrillic phrases
url = f"http://api.mutagen.ru/json/{api_key}/mutagen.parser.mass.new/"
params = {"keys_list": ",".join(keys), "name": "x", "parser": "wordstat_qso"}
resp = await client.get(url, params=params)  # URL ~ 200 KB → provider rejects
```

The 128 KB limit on GET kills the call silently or with a confusing error.

### ✅ Right

```python
resp = await client.post(url, json={
    "keys_list": keys,
    "name": "x",
    "parser": "wordstat_qso",
})
```

`parser.mass.new` and `serp.report` with long params should ALWAYS use POST. Rule of thumb: if URL > 100 KB, switch to POST. See [setup.md](setup.md).

---

## 9. Wrong region — Moscow data labelled as "Russia"

### ❌ Wrong

```python
# Project is for federal scope, but we're querying Moscow only
report = await client.serp_report(
    region="yandex_msk",   # Moscow
    domain="example.ru",
    report="report_keywords_organic",
)
# Ops dashboard says "Russia organic keywords: 12000"
```

Moscow SERP differs from regional SERPs; reporting Moscow-only data as "Russia-wide" misleads strategy.

### ✅ Right

```python
# Either: explicitly use yandex_ru (keyword-only reports)
# Or: run separately for each target region, store with region label
results_by_region = {}
for r in ("yandex_msk", "yandex_spb", "yandex_ekb"):
    results_by_region[r] = await client.serp_report(region=r, ...)
```

Document the project's region choice in code as a constant. See [regions.md](regions.md).

---

## 10. Auto-resubmit on `rejected` / `error`

### ❌ Wrong

```python
for _ in range(5):
    resp = await client.check_key_new(key)        # paid every time
    task_id = resp["task_id"]
    final = await poll(task_id)
    if final["status"] == "completed":
        break
    # rejected or error — try again
```

`rejected` and `error` are terminal. The phrase is probably malformed or restricted; resubmitting charges again and lands in the same terminal state.

### ✅ Right

```python
task_id = await store.get(key) or (await client.check_key_new(key))["task_id"]
await store.put(key, task_id)
final = await poll(task_id)
if final["status"] in ("rejected", "error"):
    await mark_for_manual_review(key, task_id, final)
    return None
```

Surface terminal states to an ops queue or dead-letter. Don't auto-cycle on terminal states.

---

## 11. Logging the full request URL — leaking key

### ❌ Wrong

```python
logger.info("GET %s", url)  # url contains api_key in path
```

```ts
console.log(`fetched ${url}`);
```

OpenTelemetry / Pino / Datadog index this. Your key is now in your APM history.

### ✅ Right

```python
logger.info(
    "mutagen call method=%s params=%s status=%s",
    method,
    {k: v for k, v in params.items() if k != "api_key"},
    response_status,
)
```

```ts
log.info({ method, params: sanitized, status: res.status }, "mutagen call");
```

Span name `mutagen.<method>` with attributes only — never the full `http.url`.

---

## 12. Probe-less `serp.report` pull

### ❌ Wrong

```python
report = await client.serp_report(
    region="yandex_msk",
    domain="huge-marketplace.ru",
    report="report_keywords_organic",
)
# 180_000 rows, surprise large bill
```

### ✅ Right

```python
n = (await client.serp_report(
    region="yandex_msk",
    domain="huge-marketplace.ru",
    report="report_keywords_organic",
    count=1,
))["count"]
if n > 5000:
    raise ValueError(f"refuse full pull of {n} rows; tighten filters")
report = await client.serp_report(
    region="yandex_msk",
    domain="huge-marketplace.ru",
    report="report_keywords_organic",
    limit=5000,
)
```

`count: 1` is much cheaper than the full pull. See [filtering.md](filtering.md).

---

## 13. Non-UTF-8 encoding silently corrupts Cyrillic

### ❌ Wrong

```python
import requests
# Default encoding mismatch on Windows / legacy systems
url = "http://api.mutagen.ru/json/{}/{}/?key=мp3".format(api_key, method)
resp = requests.get(url.encode("cp1251"))  # WRONG
```

```python
# Reading from a CSV opened in default Windows encoding
with open("seeds.csv") as f:   # implicit cp1251 on RU Windows
    keys = f.read().splitlines()  # Cyrillic mangled
```

Mojibake silently — Mutagen receives garbage and either errors or returns zero-frequency for everything.

### ✅ Right

```python
# Explicit UTF-8 everywhere
with open("seeds.csv", encoding="utf-8") as f:
    keys = f.read().splitlines()

# HTTP client handles UTF-8 by default — don't override
resp = await client.get(url, params={"key": "мp3"})
```

Confirm encoding via terminal: `LANG=ru_RU.UTF-8`. See [setup.md](setup.md).

---

## 14. Mixing parser types in a comparison

### ❌ Wrong

```python
# "Compare frequency of phrase A and phrase B"
freq_a = await client.parser_get("phrase a", "wordstat_n",   "213")
freq_b = await client.parser_get("phrase b", "wordstat_qso", "213")
print(freq_a["data"]["frequency"] / freq_b["data"]["frequency"])
```

`wordstat_n` is broad; `wordstat_qso` is точная — different counts entirely. The ratio is meaningless.

### ✅ Right

```python
# Same parser type for all phrases in one analysis
freq_a = await client.parser_get("phrase a", "wordstat_qso", "213")
freq_b = await client.parser_get("phrase b", "wordstat_qso", "213")
```

Document the chosen parser type in your project — see [parser-types.md](parser-types.md).

---

## 15. Missing public-service attribution

### ❌ Wrong

A public-facing dashboard showing Mutagen-sourced metrics (frequency / strong / bids) without crediting Mutagen.

### ✅ Right

Display the required attribution adjacent to Mutagen-sourced data per the docs:

> «Обязательным условием является размещении рядом с полученными через API данными информации о том, что они получены из Мутагена.»

Concretely: a small label «данные получены из Мутагена» (or equivalent) next to each block of Mutagen-derived numbers. Plus written approval from `support@mutagen.ru` before deploying the public service.
