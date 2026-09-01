# Batch strategy — `parser.mass` over loops, deduplication, polling

The cardinal rule: for ≥2 keys, ALWAYS use `parser.mass.new`. Never loop `parser.get`.

## Why `parser.mass` over `parser.get` loops

| Aspect | `parser.get` loop | `parser.mass.new` |
|---|---|---|
| HTTP round trips | N (one per key) | 1 submit + few polls |
| Concurrency control | Hard — limit yourself | Mutagen handles |
| Retry semantics | Per-key, complex | One mass_id to track |
| Persistence on crash | Per-key state, hard | One `mass_id` per batch |
| Effective per-keyword cost | Same or higher | Same or lower |

Only legitimate use of `parser.get`: a single probe / interactive query / proof-of-concept. Production code with > 1 key should batch.

## Canonical batch flow

```
1. Receive raw keys (from upstream — CSV, DB, user input)
2. Normalize: strip whitespace, lower-case Cyrillic, collapse multiple spaces
3. Deduplicate
4. (Optional) Split into chunks if total size very large
5. Check balance ≥ expected_cost × 2
6. Submit parser.mass.new(keys_list, name, parser, region_id)
7. Persist mass_id BEFORE the first poll
8. Poll parser.mass.id(mass_id) with exp backoff until status="finish"
9. Read .data, persist results
10. Reconcile spend against expected_cost
```

## Step 2-3: normalization + deduplication

```python
def normalize_keys(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for k in raw:
        # 1. Strip whitespace
        k = k.strip()
        # 2. Collapse internal whitespace
        k = " ".join(k.split())
        # 3. Lowercase (Cyrillic-safe via Unicode)
        k = k.casefold()
        # 4. Skip empties
        if not k:
            continue
        # 5. Dedup
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out
```

**Duplicate keys are charged separately.** A 500-key list with 80 duplicates costs 580 per-keyword rates if you don't dedup, vs 500 if you do. Always dedupe before submit.

## Step 4: chunking

Mutagen's documentation does not state a hard maximum on `keys_list` size. Practical limits:

- HTTP payload size — POST is mandatory above ~100KB total request body (see [setup.md](setup.md)).
- Polling time — larger batches take longer; very large batches may make the polling loop awkward.
- Failure blast radius — if a batch fails partway, you reprocess the whole thing.

Reasonable chunk size: **500–1000 keys per batch**. Empirically:

- 500 keys: ~1-3 minutes typical
- 1000 keys: ~3-8 minutes typical
- > 2000 keys: split

If you have 5000 keys, do 5–10 batches of 500–1000 each rather than one batch of 5000.

## Step 5: balance check

```python
balance = (await client.balance())["balance"]
expected = len(keys_list) * rates.parser_mass_per_keyword
if balance < expected * 2.0:
    raise InsufficientFunds(f"balance={balance} < expected={expected} × 2")
```

See [pricing-and-balance.md](pricing-and-balance.md).

## Step 6: submit

Use POST when the JSON-encoded `keys_list` plus other params exceeds ~100KB:

```python
resp = await http_post(
    f"http://api.mutagen.ru/json/{api_key}/mutagen.parser.mass.new/",
    json={
        "keys_list":  keys_list,       # array, OR comma-separated string
        "name":       "semantics-2026-05-q1",
        "parser":     "wordstat_qso",
        "region_id":  "213",            # Moscow
    },
)
mass_id = resp["id"]
```

## Step 7: persist `mass_id`

Before issuing the first poll, write `mass_id` to durable storage:

```sql
CREATE TABLE mutagen_parser_mass (
  mass_id      bigint PRIMARY KEY,
  name         text NOT NULL,
  parser       text NOT NULL,
  region_id    text NOT NULL,
  keys_count   int  NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  status       text NOT NULL,           -- stop | process | finish | error
  data_json    jsonb,
  completed_at timestamptz
);
```

If your process dies mid-poll, restart code can resume polling all `status NOT IN ('finish','error')` rows.

## Step 8: poll with exp backoff

```python
delay = 5.0          # initial poll delay, seconds
cap = 60.0           # max single sleep
max_attempts = 120   # ~ 30 minutes max

for attempt in range(max_attempts):
    resp = await client.parser_mass_id(mass_id)
    status = resp["status"]
    if status == "finish":
        return resp["data"]
    if status == "error":
        raise ParserMassError(mass_id, resp)
    # else: stop | process → keep polling
    await asyncio.sleep(min(delay, cap))
    delay = min(delay * 1.5, cap)
raise ParserMassTimeout(mass_id)
```

The initial delay (5 s) is higher than for `check_key` (2 s) because batches take longer to start. The cap (60 s) prevents thrash on very long batches.

## Step 9: persist results

The `data` shape depends on parser type — see [parser-types.md](parser-types.md). Persist as JSONB / JSON column tied to the `mass_id` for traceability.

For frequency parsers, an additional unnested table makes downstream queries easier:

```sql
CREATE TABLE mutagen_keyword_frequency (
  id           bigserial PRIMARY KEY,
  mass_id      bigint NOT NULL REFERENCES mutagen_parser_mass(mass_id),
  keyword      text NOT NULL,
  parser       text NOT NULL,
  region_id    text NOT NULL,
  frequency    int NOT NULL,
  observed_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (keyword, parser, region_id, mass_id)
);
```

## Step 10: reconcile

```python
balance_after = (await client.balance())["balance"]
actual = balance_before - balance_after
drift = abs(actual - expected) / expected if expected > 0 else 0
if drift > 0.05:
    logger.warning("mutagen.parser.mass spend drift %.1f%% (expected=%s actual=%s)",
                   drift * 100, expected, actual)
```

Persistent > 5% drift indicates a stale rate cache or concurrent spend — see [pricing-and-balance.md](pricing-and-balance.md).

## CSV vs array for `keys_list`

`keys_list` accepts either:

- A JSON array: `["купить мp3", "mp3 онлайн", ...]`
- A comma-separated string: `"купить мp3,mp3 онлайн,..."`

**Prefer the array form** — comma-separated strings break when a keyword itself contains a comma (rare in Russian SEO but possible in product-name niches like «iPhone 15 Pro, Max»).

## Cross-batch deduplication

Tracking results across batches:

1. Maintain a `(keyword, parser, region_id)` index of already-fetched results in your DB.
2. Before building a new batch, exclude keywords already fetched within the freshness window (e.g. 30 days).
3. Only submit the unfetched / stale subset.

This is the single biggest cost-saver in semantic-core operations — you typically re-query a 10-30% overlap month-over-month, and skipping that saves the same fraction of budget.

## Concurrency across batches

Mutagen doesn't publish a parallel-batch limit. Practical heuristic:

- Submit at most 2-3 batches in parallel per account.
- Avoid hammering with 10+ batches at once — the polling loops compete for budget.
- For very large semantic cores (10K+ keys), queue batches and process sequentially with 1-2 in flight at a time.

## Error handling

| `status` on `parser.mass.id` | Action |
|---|---|
| `stop` | initial state — keep polling |
| `process` | active — keep polling |
| `finish` | done — read `data` |
| `error` | terminal — log full response, surface to ops, do NOT auto-resubmit |

A persistent `error` status across multiple batches usually points to wrong `parser` value, malformed `keys_list`, or account-level issues. Triage manually.
