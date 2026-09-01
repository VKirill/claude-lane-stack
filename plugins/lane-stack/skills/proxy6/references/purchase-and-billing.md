# Purchase and billing

`buy` and `prolong` cost money immediately. This file documents the safe path.

## Canonical pre-buy sequence

ALWAYS run these four steps in this order before calling `buy`:

```
 1. getprice(count, period, version)   # confirm expected price
 2. getcount(country, version)          # confirm stock ≥ count
 3. read envelope.balance               # confirm balance ≥ price + safety_margin
 4. buy(count, period, country, version, descr=<tag>, [auto_prolong omitted])
```

Skipping step 1 → surprise pricing on tier changes.
Skipping step 2 → `error_id 300` after burning a rate-limit token.
Skipping step 3 → `error_id 400` after burning a rate-limit token, plus risk of overdraft if `auto_prolong` is on for existing proxies.
Skipping a `descr` → orphaned proxies that no later script can attribute.

## Why pre-check vs. just calling buy

`buy` is not atomic with pricing — proxy6 may have updated the tier between your last `getprice` reading and your `buy`. The pre-check serves three purposes:
1. Smoke-test that the params actually resolve to a sellable combination.
2. Detect stock shortage without spending the call's risk budget.
3. Surface tier-change incidents early ("we expected 12.50, got 13.20 — investigate").

After step 3 pricing read, compare `getprice.price` to a stored expected value. On drift > threshold (e.g. 10%), alert before calling `buy` — do not auto-buy.

## Idempotency

proxy6 does not expose an idempotency-key header. `buy` is fundamentally non-idempotent — calling it twice creates two orders and spends twice.

Mitigation patterns:
- **Single-flight lock**: take a Redis `SET key NX EX 60` lock keyed to `(descr, count, period, country, version)` before calling `buy`. Release after success.
- **Pre-flight de-dup**: call `getproxy(descr=<tag>)` first; if a fresh order with that descr exists (created < N seconds ago, matching count), skip.
- **Job framework**: BullMQ `jobId = "buy:${requestId}"` with `attempts: 1` so retries don't re-fire `buy`.

## Balance reading

Every envelope (success OR error) carries `balance` and `currency`. Cache the most recent value with its timestamp; on every read, update if newer.

Threshold pattern:
- `balance_min` = (daily_burn × buffer_days)
- Alert when `balance < balance_min`
- Refuse to call `buy` when `balance < quote.price × 1.1`

Track `daily_burn` from your DB: sum of `price` from `buy` orders in the last 7 days / 7.

## `auto_prolong` — default OFF

`auto_prolong` is the most common source of surprise charges. The flag is present-or-absent (no value). When set, proxy6 silently re-bills on expiry.

Default policy: **omit `auto_prolong` from `buy`**.

When to opt in:
- You have a budget alarm (CloudWatch / Datadog / Grafana) on `balance < threshold`.
- You have a documented "kill switch" — script to mass-disable `auto_prolong` (currently requires deleting + re-buying; proxy6 has no per-proxy off-switch API).
- The workload is long-running (months) where manual renewal is expensive.

If you opt in, also schedule a daily reconciliation: `getproxy(state=active)` and verify the total predicted renewal cost ≤ next-week budget.

## `descr` — always set, always meaningful

`descr` (max 50 chars) is the ONLY proxy6-side metadata you can attach. Use it for ops attribution.

### Tag format suggestion

`<env>:<pool>:<owner>` — for example `prod:scrape-amazon:team-data` (≤ 50 chars).

Bad descr values:
- empty
- shared (`pool1`, `default`) — can't attribute later
- containing colons that conflict with your own delimiter
- ascii-only? proxy6 accepts cyrillic, but downstream tooling may mangle non-ASCII — stick to ASCII

### Querying by descr

- `getproxy(descr=<tag>)` — list a pool.
- `setdescr(new=<new>, old=<old>)` — rename a pool (e.g. on env rename).
- `delete(descr=<tag>)` — **DO NOT USE BLINDLY**. See [pool-management.md](pool-management.md) and [wrong-vs-right.md](wrong-vs-right.md). Always run `getproxy` first to enumerate ids.

## `prolong` — money + the mixed-version trap

`prolong(period, ids)` extends the lifetime of the listed proxies for `period` days and charges accordingly.

### Same-version batches

Response includes `price`, `price_single`, `count`, `period`, and `list` of `{id → {date_end, unixtime_end}}`. Reconcile by parsing `list`.

### Mixed-version batches

If `ids` contains proxies of different `version` (e.g. some IPv4, some IPv6), `price_single` is **absent** from the response because per-proxy cost varies. `price` still equals the sum charged. To reconcile per-proxy cost, group ids by version locally and call `prolong` once per group, OR sum from per-version `getprice` calls.

Better: **always prolong within a single `descr` tag** (which by convention is single-version per the rule in [proxy-versions.md](proxy-versions.md)).

## Refund / cancellation policy

proxy6 does not expose a refund or cancellation API. `delete` removes the proxy from your account but does NOT refund the unused portion of `period`. There is no `void` for `buy`. Plan accordingly:
- Buy minimum `period` until you've validated the pool against the target.
- Use the trial periods proxy6 offers (dashboard setting) before the first programmatic `buy`.
- Treat any rejected pool as a sunk cost; `delete` clears the slot for reuse but does not return funds.

## Audit log fields per buy/prolong

For every `buy` and `prolong`, persist locally:
- timestamp
- caller (service / user)
- params (`count`, `period`, `country`, `version`, `descr`, `auto_prolong`)
- response `order_id`
- response `price`, `price_single`, `count`, `period`
- response `list` ids
- post-call `balance`

This is your reconciliation source-of-truth — proxy6's dashboard order history is your backup, not your primary.
