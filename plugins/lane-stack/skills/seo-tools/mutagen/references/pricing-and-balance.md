# Pricing and balance safety

Mutagen is **pay-per-call**. Every paid method debits the account balance immediately on submit. This file documents the safety pattern; it does NOT hardcode ruble amounts because the tariff schedule changes over time.

## Source of truth for current pricing

- Live tariff: `https://mutagen.ru/?p=price`
- Account dashboard: `https://mutagen.ru/?api_config`
- The API documentation page (`https://mutagen.ru/?p=api`) does NOT publish per-call costs.

**Treat per-call pricing as an account-level configuration value**: store it in your config / env / database, not in source code. When Mutagen changes the tariff, update one config value, not 15 source files.

Example shape (per-account known-rate cache):

```yaml
# mutagen-rates.yaml — kept up to date with the dashboard
check_key_per_call:           0.30    # рубли per check_key.new
parser_get_per_call:          0.10
parser_mass_per_keyword:      0.05
serp_report_keyword_info:     0.50
serp_report_keywords_organic: 5.00
# ... etc
```

## What gets billed

| Method | Billing |
|---|---|
| `mutagen.balance` | Free |
| `mutagen.progects` | Free |
| `mutagen.progect.keywords` | Free |
| `mutagen.check_key.new` | **PAID** per call |
| `mutagen.check_key.get` | Free (reading a result) |
| `mutagen.parser.get` | **PAID** per call |
| `mutagen.parser.mass.new` | **PAID** per keyword in `keys_list` |
| `mutagen.parser.mass.list` | Free |
| `mutagen.parser.mass.id` | Free |
| `mutagen.serp.report` | **PAID** per call; cost depends on report type and result size |

**Probe with `count: 1` first** on `serp.report` before pulling a large list — see [filtering.md](filtering.md). The probe is much cheaper than the full pull.

## Pre-flight balance check pattern

Before any paid batch, check balance and gate execution:

```python
# Pseudo — full Python in integration-python.md
async def gate_balance(client, expected_cost: float, safety: float = 2.0) -> None:
    balance = (await client.balance())["balance"]
    if balance < expected_cost * safety:
        raise InsufficientFunds(
            f"balance={balance} < expected_cost={expected_cost} × safety={safety}"
        )
```

The safety factor (2.0 = 100% headroom) covers:

- Tariff drift between when you cached the rate and now.
- Other processes / scripts spending against the same account concurrently.
- Cost variance for variable-cost reports (`serp.report` size).

For high-cost single calls (e.g. domain-wide `report_keywords_organic` on a large site), gate against `expected_cost × 1.5` minimum; for cheap calls, `× 2.0` is reasonable.

## Estimating expected cost

For batch operations:

```python
n_unique_keys = len(dedup(raw_keys_list))
expected_cost = n_unique_keys * config.parser_mass_per_keyword
```

For `serp.report`:

```python
# 1. Probe row count
count_resp = await client.serp_report(..., count=1)
n_rows = count_resp["count"]
# 2. Multiply by per-row or per-call rate (depends on the report)
expected_cost = estimate_cost(report_type, n_rows)
```

## Daily / weekly spend budget

For automated pipelines, set hard daily limits in code:

```python
DAILY_BUDGET_RUB = 500.0
spent_today = await spend_tracker.sum_today()
if spent_today + expected_cost > DAILY_BUDGET_RUB:
    raise DailyBudgetExceeded()
```

Persist `spent_today` to PostgreSQL / Redis. Reset at midnight UTC or local time per your op convention.

## Balance alert thresholds

Set alerts at:

| Threshold | Severity |
|---|---|
| balance < expected daily burn × 7 | warn (a week's runway) |
| balance < expected daily burn × 2 | critical (top up now) |
| balance < expected daily burn × 0.5 | page on-call |
| balance == 0 or check_key returns ouf-of-funds | block all paid operations |

Polling cadence for the balance metric: every 5 minutes is enough; faster wastes the free `balance` call budget.

## Cost-aware patterns

### Deduplicate before batching

Duplicate keys are charged. Always dedupe before `parser.mass.new`:

```python
keys_list = sorted(set(k.strip().lower() for k in raw_input))
```

See [batch-strategy.md](batch-strategy.md) for the full canonical batch flow.

### Reuse `task_id` instead of resubmitting

`check_key.new` is non-idempotent — calling twice on the same key charges twice. Persist `task_id` per key and reuse on retry. See [check-key-async-pattern.md](check-key-async-pattern.md).

### Probe `serp.report` size first

```python
# Wrong: pull full list, get billed for thousands of rows
report = await client.serp_report(..., report="report_keywords_organic")

# Right: probe, then decide
count = (await client.serp_report(..., report="report_keywords_organic", count=1))["count"]
if count > 5000:
    # Tighten filter and re-probe instead of paying for 5000+ rows
    ...
```

### Don't `parser.get` in a loop

A 50-keyword loop of `parser.get` costs the same per-call overhead 50 times. `parser.mass.new` with the same 50 keys is the same effective cost OR cheaper, depending on tariff structure — and it's one HTTP round trip + one polling loop instead of 50.

## Reconciliation

Server-side ground truth is the Mutagen dashboard ledger. Reconcile client-side spend estimates against the dashboard:

1. Snapshot dashboard balance at start of day.
2. Track every paid call locally (method, params, expected_cost).
3. Snapshot dashboard balance at end of day.
4. `actual_delta = start - end` vs `sum(expected_cost)` — should match within ±5%.

Drift indicates either:

- Stale local rate cache (tariff changed).
- Another process spending on the same account.
- Variable-cost report types where you under-estimated.

## Refunds

Mutagen does not document a refund API. Treat all paid operations as final. The only "refund-like" pattern is: if a `check_key.new` returns `rejected` after the call already debited (depends on Mutagen internals — sometimes the charge is reversed, sometimes not), open a support ticket at `support@mutagen.ru` with `task_id` and timestamp.

## Public-service attribution (legal / compliance)

If you display Mutagen-sourced numbers in a public-facing service, you owe attribution per the docs:

> «Обязательным условием является размещении рядом с полученными через API данными информации о том, что они получены из Мутагена.»

This is a contractual condition, not a cost knob, but worth tracking in the same compliance section as billing.
