# Troubleshooting — mutagen

Symptom-indexed. Find your symptom, follow the diagnosis steps, apply the fix.

Numeric defaults referenced here are SSOT in [recommended-defaults.md](recommended-defaults.md).

---

## `balance` returns 0 or near-zero — paid calls fail

**Symptoms**

- `await client.balance()` returns `0` or a small value.
- `check_key.new` / `parser.mass.new` / `serp.report` fail with HTTP 4xx or return an error envelope.
- Existing in-flight tasks may still complete; new submissions stop.

**Diagnose**

```bash
# Smoke test from runtime container (NOT local laptop)
curl -sS "http://api.mutagen.ru/json/${MUTAGEN_API_KEY}/mutagen.balance/" | jq .
```

**Common causes**

- Account ran out of credit (most common — check dashboard `https://mutagen.ru/?api_config`).
- `auto-prolong`-style charges from previous batches drained funds since last manual top-up.
- Wrong API key for environment (dev key for prod account or vice versa).

**Fix**

1. Top up via Mutagen dashboard / payment partner.
2. Verify the key is for the correct account.
3. Set a balance alert at `7 × daily_burn` to prevent recurrence (see [pricing-and-balance.md](pricing-and-balance.md)).

---

## `check_key.get` stuck on `processed` forever

**Symptoms**

- Polling loop runs through `max_attempts` (e.g. 60 attempts × exp backoff = ~15 minutes).
- `status` stays `processed` indefinitely; never reaches `completed`.

**Diagnose**

```python
# Read the raw envelope, persist it, look for anomalies
resp = await client.check_key_get(task_id)
print(resp)

# Manually probe with curl (also confirms it isn't a client bug)
# curl -sS "http://api.mutagen.ru/json/${KEY}/mutagen.check_key.get/?task_id=<id>"
```

**Common causes**

- Mutagen's internal queue is backlogged (rare, but happens during their maintenance windows).
- The `task_id` is stale and Mutagen's records don't actually contain it (possible if very old).
- Network path returning cached responses (intermediary proxy / CDN edge cache for the same URL).

**Fix**

- Wait — try again in 5-10 minutes manually.
- Confirm the `task_id` value matches what `check_key.new` returned (no off-by-one / type coercion).
- Disable any HTTP caching middleware between client and `api.mutagen.ru`.
- If still stuck after 30 min: escalate to `support@mutagen.ru` with `task_id` + UTC timestamp; do NOT resubmit `check_key.new` (double-charge).

---

## Many `check_key` tasks return `rejected`

**Symptoms**

- Most submissions land in `rejected` terminal state.
- Pattern: specific keyword shapes (e.g. very short keys, single Latin words, brand names) more likely to be rejected.

**Diagnose**

- Log full envelope on `rejected`. Mutagen does not return a documented reason field — but the response often carries diagnostic hints.
- Cross-check the same key in the Mutagen web UI manually — does it return data there?

**Common causes**

- Phrase below provider's minimum quality threshold (too short, too generic, branded).
- Phrase is on an internal blacklist (rare).
- Account-level quota / restriction (check dashboard).

**Fix**

- Filter input keys client-side: drop empty, drop length < 2 chars, drop single-word brand stop-list.
- Route `rejected` to a manual-review queue rather than auto-resubmit.
- Pattern: if > 5% reject rate over an hour, halt the pipeline and triage.

---

## `parser.mass.id` not found / 404

**Symptoms**

- Polling a recent `mass_id` returns an error or empty envelope.
- The `mass_id` was valid moments ago.

**Diagnose**

```python
# Confirm via mass.list whether the mass_id exists
all_tasks = await client.parser_mass_list()
print([t["id"] for t in all_tasks])
```

**Common causes**

- The `mass_id` was never actually returned by `parser.mass.new` — local code dropped it (e.g. type coercion `int(undefined)` → wrong number).
- The `mass_id` belongs to a different account (wrong key used).
- The task is old enough that Mutagen pruned it (long retention but not infinite).

**Fix**

- Verify the persistence flow: `parser.mass.new` → store `id` BEFORE any polling. If your code calls `parser.mass.id` with a value that was never persisted, fix the persistence ordering.
- Cross-check API key matches the account that owns the mass_id.

---

## `serp.report` returns "wrong" filter type error

**Symptoms**

- Specific `filter_type` rejected with error envelope.
- Other filters work fine.

**Diagnose**

- Look at the column you're filtering — is it numeric, text, boolean, or timestamp?
- See [filtering.md](filtering.md) — `gr/less/range/in/not_in` are numeric (or timestamp); `like/not_like/like_any/...` are text; `is` is boolean only.

**Common causes**

- `gr` / `less` on a text column (e.g. `keyword`).
- `like` on a numeric column.
- `is` on a non-boolean column.
- `range` missing `min` or `max`.
- `like_any` / `not_like_any` / `in` / `not_in` passed an array instead of CSV string.

**Fix**

- Match `filter_type` to the column's data type per [filtering.md](filtering.md).
- For `in` / `not_in` / `like_any` / `not_like_any`, pass `val` as a comma-separated string, not a JSON array.

---

## Region mismatch — Moscow data labelled as Russia

**Symptoms**

- Numbers look surprisingly low for "Russia-wide" data.
- Or: organic competitor list reads like a Moscow-only ranking.

**Diagnose**

```python
# Cross-check known geo-skewed query at different regions
freq_global = (await client.parser_get("доставка цветов", "wordstat_qso", "0"))["data"]["frequency"]
freq_msk    = (await client.parser_get("доставка цветов", "wordstat_qso", "213"))["data"]["frequency"]
print(freq_global, freq_msk)  # global should be much larger
```

**Common causes**

- `region` set to `yandex_msk` but project intent is federal — wrong region for the analysis goal.
- `region_id="213"` (Moscow) on `parser.mass.new` while `serp.report` uses `yandex_ru` — incomparable data across the same project.

**Fix**

- Document the project's chosen region once (constant / config field).
- For `serp.report` and `parser.mass.new`, use the matching region pair — see [regions.md](regions.md) for the mapping table.

---

## GET request rejected — URL too long (128KB)

**Symptoms**

- HTTP 414 (URI Too Long) or connection-reset on a `serp.report` / `parser.mass.new` call.
- Works fine with small `keywords` / `keys_list` / short filter chain.

**Diagnose**

```python
url = build_url(method, params)
print(len(url))   # if close to or > 100_000 bytes — switch to POST
```

**Fix**

- Switch the offending call to POST with JSON body.
- Rule of thumb: switch to POST when URL > 100 KB to leave headroom under the 128 KB hard limit. See [setup.md](setup.md).

---

## UTF-8 / encoding issues — Cyrillic mangled

**Symptoms**

- Frequencies all return 0 for Cyrillic queries.
- Mutagen response contains `?????` or `ÐºÑƒÐ¿Ð¸Ñ‚ÑŒ` (mojibake) instead of the original phrase.
- Worked on dev laptop, fails on production server.

**Diagnose**

```bash
locale            # confirm LANG=ru_RU.UTF-8 or C.UTF-8
echo "купить" | hexdump -C   # check byte sequence is UTF-8
python -c "import sys; print(sys.stdout.encoding)"
```

**Common causes**

- Source file saved as `cp1251` / `windows-1251` (legacy RU editors).
- CSV opened without explicit `encoding="utf-8"`.
- Container `LANG` defaults to `C` (ASCII-only); Cyrillic gets replaced with `?`.
- A reverse proxy or middleware re-encoding the body.

**Fix**

```python
with open("seeds.csv", encoding="utf-8") as f:  # explicit
    keys = f.read().splitlines()
```

```Dockerfile
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
```

Confirm with the diagnostic before retrying paid calls.

---

## Concurrent processes spending the same account

**Symptoms**

- Balance drops faster than your expected spend.
- Tasks come back unexpectedly fast (or slow) because another process is also polling.
- Reconciliation reports > 5% drift between expected and actual spend.

**Diagnose**

```bash
# Who's running scripts that load MUTAGEN_API_KEY?
ps -ef | xargs -I{} sh -c 'cat /proc/{}/environ 2>/dev/null | tr "\0" "\n" | grep -l MUTAGEN' 2>/dev/null
```

**Common causes**

- A cron / scheduled task running in parallel with interactive scripts.
- A teammate using the same key.

**Fix**

- Isolate by account: separate keys for separate workloads.
- Centralise spend tracking: a single SpendTracker process / table that everyone writes to.
- Reconcile daily against the dashboard ledger.

---

## Stuck `parser.mass` — never reaches `finish`

**Symptoms**

- `status` stays `process` for hours.
- Other batches finish normally.

**Diagnose**

- Check `parser.mass.list()` for this `mass_id` and others — is it ONE batch stuck or all?
- Look at the `count` and `time` fields; reasonable elapsed time for the size?

**Common causes**

- Very large batch + complex `parser` (e.g. `wordstat_key` for 1000+ keys takes long).
- Rare keywords with no Wordstat data — Mutagen may retry internally.
- Provider-side incident (rare).

**Fix**

- Increase `max_attempts` for large batches (e.g. 240 attempts × 60 s cap = 4 h).
- Split large batches into smaller chunks (500-1000 keys) — see [batch-strategy.md](batch-strategy.md).
- If a single batch has been stuck > 1 h for a normal size, escalate to support.

---

## `serp.report` returns unexpected huge result

**Symptoms**

- A report meant to be "around 1000 keywords" returns 50,000.
- Spend on that single call is much higher than estimated.

**Diagnose**

- Was a `count: 1` probe done first?
- Are filters correctly typed and column-matched?

**Common causes**

- No `limit` set → unbounded pull.
- Filter omitted or syntactically wrong (not applied).
- Element type confusion: `domain` vs `domain_with_subdomains` — the latter is much larger.

**Fix**

- ALWAYS set `limit` and run `count: 1` probe first — see [filtering.md](filtering.md).
- Verify filter syntax: each filter object needs `column`, `filter_type`, and the right `val` / `min` / `max`.

---

## How to escalate to Mutagen support

When the above doesn't resolve:

1. Capture: account email (from dashboard), failing method name, `task_id` or `mass_id`, UTC timestamp, masked URL (key removed).
2. Email `support@mutagen.ru` with the captured info.
3. Do NOT share the API key — they look up by account email.
4. Mention what changed (deploy, key rotation, infra migration) — usually it's the last change.
5. For public-service deployment approval (per attribution requirement), also email `support@mutagen.ru` — see [setup.md](setup.md).
