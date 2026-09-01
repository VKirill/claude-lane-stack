# Limits and Units — points-based economy

## What units are

Every API call burns units from a per-account daily allowance. This is a **separate economy from the ad budget** — even with millions in ad spend, no units → no API.

## Where to read units

Response header:

```
Units: 12/4988/5000
```

— consumed in this call / remaining today / daily cap. Parse it **after every** response.

```
Units-Used-Login: example-client
```

— which login was charged. Useful when `Use-Operator-Units: true` is set to verify the agency was charged, not the client.

## Daily allowance dynamics

New apps start around 3 000–5 000 units/day. The limit then evolves:

- Active usage → cap grows.
- Repeated overuse or long idle → cap shrinks.
- The formula is not published; rough heuristic: yesterday's spend × coefficient.

The cap **resets at 00:00 UTC** (03:00 MSK).

## Method cost (orders of magnitude)

Prices vary and change; treat as guidance.

### Read (get)

| Call | Cost |
|---|---|
| `Campaigns.get` (empty FieldNames) | ~10 units |
| `Campaigns.get` (full FieldNames) | ~20–40 units |
| `Ads.get` (full `TextAdFieldNames`) | ~30–60 units |
| `Keywords.get` | ~10–20 units |
| `Dictionaries.get` | free or very cheap |
| `Changes.check` | cheap, designed for polling |

Cost also scales with the number of returned objects (wider `FieldNames` → more).

### Write (add / update / delete)

| Call | Cost |
|---|---|
| `Campaigns.add` (1 campaign) | ~20–50 units |
| `AdGroups.add` (1 group) | ~10–20 units |
| `Ads.add` (1 ad) | ~10–15 units |
| `Keywords.add` (1 keyword) | ~5–10 units |
| `Bids.set` / `KeywordBids.set` | ~5–15 units per bid |
| `Campaigns.suspend/resume` | ~10 units per campaign |
| `Ads.moderate` | ~10 units per ad |
| `Campaigns.delete/archive` | ~10–30 units |

Cost is roughly linear — a 1 000-keyword batch costs ~5 000–10 000 units.

### Reports

- Enqueue (first POST) — ~10–20 units.
- Polling status — **free** (HTTP 201/202).
- Final TSV download (HTTP 200) — free after ready.

Large reports do not scale linearly with volume — but `processingMode: online` on a wide period can burn five minutes of wall-clock and put load on the server.

## Cost-saving strategy

1. **Minimal `FieldNames`**. Ask only for what is needed. Type-specific FieldNames (`TextCampaignFieldNames`) come separately.
2. **Cache `Dictionaries.get`** for a day — regions, currencies barely change.
3. **`Changes.check` for polling** — fetch only modified objects instead of full `Campaigns.get` every 5 minutes.
4. **Reports** for stats, not `Campaigns.get` on a tight loop.
5. **`Accept-Encoding: gzip`** — does not change unit cost, but cuts bandwidth and time.
6. **`Use-Operator-Units: true`** when handling many clients — spend the agency's bigger cap.
7. **Parallelism with caution** — 2–3 parallel calls is fine. More raises 429 / `error 12` and burns units on retries.

## Parallel calls

- Recommended: **up to 5** parallel calls on one OAuth token.
- Above ~10 parallel — HTTP 429 / `error 12` becomes likely.
- A 100–300 ms pause between batch operations smooths out high-throughput pipelines.

## Object limits (not units)

| Object | Limit |
|---|---|
| Campaigns in account | up to 3 000 |
| Active campaigns | ~1 500–2 000 |
| Groups per campaign | up to 1 000 |
| Ads per group | up to 50 |
| Keywords per group | up to 200 (recommended), hard cap ~1 000 |
| Negative keywords per campaign | up to 20 000 characters |
| Negative keywords per group | up to 4 096 characters / ~700 phrases |
| Parallel reports | 5 |

## Batch limits

| Method | Max per call |
|---|---|
| `Campaigns.add` | 10 |
| `AdGroups.add` | 1 000 |
| `Ads.add` | 1 000 |
| `Keywords.add` | 1 000 |
| `SelectionCriteria.Ids` | 10 000 |
| `Page.Limit` (for `get`) | 10 000 |

## Sandbox limits

- Same structure but a **separate sandbox wallet** (production units are untouched).
- Daily allowance roughly 1 000–5 000 units.
- Campaigns are deleted after 1 month of inactivity.
- Reports: one campaign per call.

## Handling `error 153` (UnitsLimitExceeded)

1. **Stop.** Pause every write. Read calls are also pointless.
2. Persist a cursor for the in-flight batch.
3. Wait **until 00:00 UTC** — daily reset.
4. Resume from the cursor afterwards.
5. Long-term: optimize (`Changes.check`, caching) or request a higher limit from support.

## Monitoring

Wire this into the client:

```python
@dataclass
class UnitsHeader:
    consumed: int
    remaining: int
    daily_limit: int
    used_login: str

# after every response
parse_units(response.headers["Units"])
if units.remaining / units.daily_limit < 0.2:
    alert("Direct units below 20%")
if units.remaining < 100:
    pause_writes()
```

## Best practices

- **One token = one account.** No shared tokens across apps — units collide.
- **Log `Units-Used-Login`** — for agencies it tells you which client is consuming the cap.
- **Daily roll-up**: total units per client, weekly trend, projection for tomorrow.
- **Throttle at 80%**: when `remaining / daily_limit < 0.2` slow writes hard and reserve units for critical operations only.
