# `check_key` async lifecycle — deep dive

`mutagen.check_key.*` is the most operationally hazardous part of the API because:

1. Every `check_key.new` debits the merchant balance (paid call).
2. The lifecycle has TWO terminal failure states (`rejected`, `error`) and ONE terminal success (`completed`).
3. Naive polling burns latency budget; tight loops waste resources.
4. Without persisting `task_id`, crash-recovery code re-submits and double-charges.

This file is the canonical reference for getting the pattern right.

## State machine

```
                       ┌──────────────────────────────┐
                       │  mutagen.check_key.new(key)  │
                       └──────────────┬───────────────┘
                                      │  returns {task_id, status}
                                      ▼
                              ┌───────────────┐
                              │   created     │  (initial state)
                              └───────┬───────┘
                                      │  poll check_key.get(task_id)
                                      ▼
                              ┌───────────────┐
                              │   processed   │  (worker active)
                              └───┬───────┬───┘
                                  │       │
                                  │       │  poll again
                                  │       ▼
                                  │   continues until terminal
                                  ▼
                       ┌──────────┴──────────┬────────────────┐
                       ▼                     ▼                ▼
                ┌─────────────┐      ┌─────────────┐   ┌─────────────┐
                │  completed  │      │  rejected   │   │    error    │
                │  (success)  │      │ (terminal)  │   │ (terminal)  │
                └─────────────┘      └─────────────┘   └─────────────┘
```

**`rejected`** — Mutagen refused the task. Documented reasons aren't published; observed triggers in the field: malformed key, restricted phrase, account-level limits, internal QoS. Do NOT auto-resubmit blindly.

**`error`** — parsing/query failure on Mutagen's side. Similar to `rejected` operationally: terminal, requires triage.

**`completed`** — success. Response now contains all data fields (`key`, `strong`, `wordstat`, `tails`, `direct`, `vital`, `vital_site`).

## Polling pattern (canonical)

Defaults in [recommended-defaults.md](recommended-defaults.md).

```python
# Conceptual flow (full Python in integration-python.md)
task_id = (await client.check_key_new(key))["task_id"]
# 1. PERSIST task_id IMMEDIATELY to durable storage keyed by `key`
await store.save(key, task_id)

# 2. Poll with exponential backoff
delay = 2.0           # seconds, initial
cap = 30.0            # seconds, max single sleep
max_attempts = 60     # ~ 10 minutes max total
for attempt in range(max_attempts):
    resp = await client.check_key_get(task_id)
    status = resp["status"]
    if status == "completed":
        return resp                          # success
    if status in ("rejected", "error"):
        raise CheckKeyTerminalError(status)  # do NOT resubmit
    # else: created | processed → keep polling
    await asyncio.sleep(min(delay, cap))
    delay = min(delay * 1.5, cap)            # exp backoff
raise CheckKeyTimeoutError(task_id)
```

The exponential factor 1.5 is gentler than 2.0 — gives smoother backoff for a paid API where you don't want to overshoot the result-ready window.

## Idempotency — the critical rule

`check_key.new` is **NOT idempotent at the API level**. Calling it twice with the same `key` returns two different `task_id`s — and charges twice.

Client-side idempotency:

1. Before calling `check_key.new(key)`, look up `task_id` for this `key` in your durable store.
2. If a `task_id` exists:
   - If the prior result is `completed` and recent enough (TTL up to you, e.g. 7 days), return cached result.
   - If the prior result is `created` / `processed` and not too old (e.g. < 1 hour), continue polling that `task_id`.
   - If the prior result is `rejected` / `error`, return that — do NOT auto-retry.
3. Only if no prior `task_id` exists do you submit `check_key.new`.

Storage shape (PostgreSQL example):

```sql
CREATE TABLE mutagen_check_key (
  key            text PRIMARY KEY,
  task_id        bigint NOT NULL,
  status         text NOT NULL,         -- created|processed|completed|rejected|error
  result_json    jsonb,
  submitted_at   timestamptz NOT NULL DEFAULT now(),
  completed_at   timestamptz,
  UNIQUE (task_id)
);
```

## Handling `rejected` / `error`

Both are terminal. Recommended handling:

1. Log the terminal state with the original `key`, `task_id`, and the full envelope.
2. Surface to ops / dashboard — don't silently swallow.
3. Decide policy: either
   - Treat as final (most batch SEO use cases); record and continue.
   - OR manual-review queue; an operator decides whether to re-submit with a cleaned key.
4. Do NOT auto-resubmit in the polling loop. If you need automated retry on `rejected`, wrap it at the OUTSIDE layer with a clear deduplication policy (e.g. retry once after 24 h with key normalization).

## Crash recovery

If your process dies mid-poll:

1. On restart, scan durable store for `status in ('created','processed')` and `submitted_at > now() - interval '1 hour'`.
2. For each, resume polling with the persisted `task_id` — do NOT re-submit.
3. Tasks older than your max polling window: mark `status='timeout'` and reconcile manually.

## Batching strategy

`check_key` doesn't have a batch primitive — it's strictly per-keyword. For large semantic cores:

1. Submit N `check_key.new` calls (paced — see [recommended-defaults.md](recommended-defaults.md) for concurrency).
2. Collect all `task_id`s.
3. Poll them in a shared loop with shared backoff, not per-task tight loops.
4. Persist as you go.

For Wordstat frequency on many keywords, use `parser.mass.new` instead — it's the batch primitive. See [batch-strategy.md](batch-strategy.md).

## What `strong` actually means

`strong` is Mutagen's proprietary competition score. Observed scale: ~1–25+ (no documented upper cap). Higher = harder to rank. SEO heuristic conventions in the RU community:

- `strong ≤ 5` — низкая конкуренция, can rank with thin content
- `5 < strong ≤ 12` — средняя конкуренция, requires solid content + some backlinks
- `12 < strong ≤ 18` — высокая конкуренция, mature site + linking strategy
- `strong > 18` — очень высокая конкуренция, top brands; consider niching down

These thresholds are **community convention**, NOT specified by Mutagen. Treat as a relative ordering signal, not an absolute threshold.

## `vital` / `vital_site` — тематический сайт

If Yandex has designated a "vital site" for the query (тематический сайт — usually a brand's official site shown specially in SERP), `vital_site` carries that URL. When non-empty, organic competition for non-brand sites is effectively harder than `strong` alone suggests — Yandex pins the vital above algorithmic results.

Pattern: when reporting `strong` to ops/content teams, also surface `vital_site` if non-empty.

## Required imports / dependencies

Nothing Mutagen-specific. The HTTP client is provided by the runtime skill (`httpx`, `nodejs`). Mutagen does not publish an official SDK in either language.
