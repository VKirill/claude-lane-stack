# End-to-end workflows — bootstrap to daily ETL

Pragmatic, ordered recipe for a brand-new Yandex.Direct integration. Each step lists the goal, request example, response excerpt, and the gotcha that breaks production for someone every quarter.

## 1. Bootstrap — OAuth + sandbox + endpoint

### Goal

Land in a state where a valid OAuth token can hit either production or sandbox.

### Steps

1. Register the app at `https://oauth.yandex.ru/client/new` with scope `direct:api` (advertiser) or `direct:agency` (agency operating on clients).
2. Run the OAuth code flow:

   ```
   GET https://oauth.yandex.ru/authorize?
       response_type=code&
       client_id=<CLIENT_ID>&
       state=<csrf>&
       force_confirm=yes
   ```

   Then exchange the code:

   ```
   POST https://oauth.yandex.ru/token
   Content-Type: application/x-www-form-urlencoded

   grant_type=authorization_code&code=<code>&client_id=<CLIENT_ID>&client_secret=<SECRET>
   ```

   Response (truncated):

   ```json
   {
     "access_token": "y0_AgAAAA...",
     "refresh_token": "1:...",
     "expires_in": 31536000,
     "token_type": "bearer"
   }
   ```

3. Sandbox is auto-provisioned for the same Yandex ID on first call to `api-sandbox.direct.yandex.com`. There is no separate sign-up.
4. Pick the endpoint:
   - Production: `https://api.direct.yandex.com/json/v5/{service}`
   - Sandbox: `https://api-sandbox.direct.yandex.com/json/v5/{service}`

Gotchas: 1-month sandbox inactivity drop (recreate fixtures); token lifetime up to 1 year (refresh via `grant_type=refresh_token`); wrong scope → every call fails `52` / `506`.

## 2. JSON envelope — first authenticated call

### Goal

Confirm headers, body shape, and response parsing.

### Required headers

| Header | Value | When |
|---|---|---|
| `Authorization` | `Bearer <token>` | Always |
| `Content-Type` | `application/json; charset=utf-8` | POST |
| `Client-Login` | `<client-login>` | Agency only |
| `Accept-Language` | `en` or `ru` | Optional |
| `Use-Operator-Units` | `true` | Agency optional |
| `Accept-Encoding` | `gzip` | Recommended |

### Body shape

```json
{
  "method": "<methodName>",
  "params": { ... }
}
```

### Smoke call

```bash
curl -sS -X POST https://api-sandbox.direct.yandex.com/json/v5/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept-Language: en" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Accept-Encoding: gzip" \
  -d '{
    "method": "get",
    "params": {
      "SelectionCriteria": {},
      "FieldNames": ["Id", "Name", "State", "Status", "Type"],
      "Page": { "Limit": 10 }
    }
  }'
```

### Response

```json
{ "result": { "Campaigns": [] } }
```

Successful responses always live under `result`; failures live under `error`:

```json
{
  "error": {
    "request_id": "1742...",
    "error_code": 53,
    "error_string": "Authentication error",
    "error_detail": "Token is invalid"
  }
}
```

### Parse `Units` from response headers

```
Units: 12/4988/5000
Units-Used-Login: example-client
RequestId: 1742...
```

Store all three in structured logs. Without `RequestId` support cannot help.

Gotchas: missing `Client-Login` in agency mode silently routes to the agency account or returns `54` (assert `Units-Used-Login`); HTTP 200 may carry an `error` body — inspect the JSON, not the HTTP status.

## 3. Campaigns lifecycle — add → update → state transitions

### State machine

```
DRAFT --(moderate)--> MODERATION --> ACCEPTED --(suspend)--> SUSPENDED
                                       |               --(resume)--> ON
                                       v
                                    REJECTED
                                       |
                                       v
   ACCEPTED/SUSPENDED/OFF/ENDED --(archive)--> ARCHIVED --(unarchive)--> OFF
```

`Status` (DRAFT / MODERATION / ACCEPTED / REJECTED) is moderation state. `State` (ON / OFF / SUSPENDED / ENDED / CONVERTED / ARCHIVED) is operational state.

### Add (sandbox)

```json
{
  "method": "add",
  "params": {
    "Campaigns": [{
      "Name": "Smoke-search-en",
      "StartDate": "2026-05-20",
      "TextCampaign": {
        "BiddingStrategy": {
          "Search": {
            "BiddingStrategyType": "WB_MAXIMUM_CLICKS",
            "WbMaximumClicks": {
              "WeeklySpendLimit": 1000000000,
              "BidCeiling": 100000000
            }
          },
          "Network": { "BiddingStrategyType": "SERVING_OFF" }
        }
      }
    }]
  }
}
```

Money fields are in **micro-currency** — `1000000000` = 1 000 ₽.

### Response

```json
{ "result": { "AddResults": [{ "Id": 12345 }] } }
```

Batch responses may mix per-item `Id` and `Errors[]`. Always iterate.

### Update

```json
{
  "method": "update",
  "params": {
    "Campaigns": [{
      "Id": 12345,
      "DailyBudget": { "Amount": 5000000000, "Mode": "STANDARD" }
    }]
  }
}
```

### Suspend / resume / archive

```json
{ "method": "suspend", "params": { "SelectionCriteria": { "Ids": [12345] } } }
```

- `delete` only works for campaigns **without statistics**. Otherwise → `error 5001`. Use `archive`.
- `archive` is terminal until `unarchive`; fields become read-only.
- `suspend` propagation can take a few minutes for in-flight impressions.

## 4. AdGroups + Ads + Keywords

### Order of operations

```
Campaigns.add -> AdGroups.add -> Ads.add (Status=DRAFT) -> Ads.moderate -> ACCEPTED
                                Keywords.add (per AdGroup)
                                NegativeKeywords on Campaign / AdGroup / Keyword
```

### AdGroups.add

```json
{
  "method": "add",
  "params": {
    "AdGroups": [{
      "Name": "Search RU brand",
      "CampaignId": 12345,
      "RegionIds": [225],
      "NegativeKeywords": { "Items": ["free", "torrent"] },
      "TextAdGroup": {}
    }]
  }
}
```

### Ads.add (TextAd)

```json
{
  "method": "add",
  "params": {
    "Ads": [{
      "AdGroupId": 67890,
      "TextAd": {
        "Title": "Buy our widget online",
        "Title2": "Free delivery in MSK",
        "Text": "Premium widgets with 2-year warranty. Limited offer.",
        "Href": "https://example.com/widget",
        "Mobile": "NO"
      }
    }]
  }
}
```

After `add` the ad is `DRAFT`. Call `Ads.moderate` to push it to `MODERATION`. Any `update` to ad copy resets `Status` to `MODERATION`.

### Keywords.add

```json
{
  "method": "add",
  "params": {
    "Keywords": [{
      "Keyword": "buy widget online",
      "AdGroupId": 67890,
      "NegativeKeywords": { "Items": ["free"] }
    }]
  }
}
```

### Match operators

| Operator | Meaning |
|---|---|
| `!word` | Exact form |
| `+word` | Stop-word is required |
| `"phrase"` | Only these words |
| `[phrase]` | Fixed order |
| `(a\|b)` | Alternation |
| `-word` | Negative |

Gotchas: up to 1 000 ads / keywords per `add` call; 10 campaigns per `Campaigns.add`; `>10 000` IDs in `SelectionCriteria.Ids` → `error 17` (chunk in 10k).

## 5. Bids — manual vs auto-strategies, search vs network split

### Auto-strategies

Apply at campaign level via `BiddingStrategy`:

```json
{
  "BiddingStrategy": {
    "Search": {
      "BiddingStrategyType": "WB_MAXIMUM_CONVERSION_RATE",
      "WbMaximumConversionRate": {
        "WeeklySpendLimit": 10000000000,
        "BidCeiling": 500000000,
        "GoalId": 99887766
      }
    },
    "Network": { "BiddingStrategyType": "NETWORK_DEFAULT" }
  }
}
```

Allowed strategy types: `HIGHEST_POSITION`, `WB_MAXIMUM_CLICKS`, `WB_MAXIMUM_CONVERSION_RATE`, `AVERAGE_CPC`, `AVERAGE_CPA`, `WEEKLY_CLICK_PACKAGE`, `AVERAGE_ROI`, `PAY_FOR_CONVERSION`, `SERVING_OFF`. Network adds `NETWORK_DEFAULT`.

### Manual bids — KeywordBids.set

```json
{
  "method": "set",
  "params": {
    "KeywordBids": [{
      "KeywordId": 11111,
      "SearchBid": 5000000,
      "NetworkBid": 2000000
    }]
  }
}
```

Manual bids are ignored under auto-strategies; only `HIGHEST_POSITION` / `AVERAGE_CPC` honor them.

### Micro-currency reminder

All money fields × 1 000 000. `MaxCpc: 50` = 0.00005 ₽ (no serving). `MaxCpc: 50_000_000` = 50 ₽.

### Bid modifiers

```json
{
  "method": "set",
  "params": {
    "BidModifiers": [{
      "CampaignId": 12345,
      "MobileAdjustment": { "BidModifier": 150 }
    }]
  }
}
```

`100` = unchanged, `50` = -50%, `200` = +100%, range usually `[0..1300]`.

Gotchas: search vs network must live in separate campaigns (different auctions); strategy switch propagates within ~1 hour, not instantly; auto-strategies need a 1–2 week learning period.

## 6. Reports — submit, poll, persist

### Goal

Pull TSV statistics safely, with `Retry-After`-aware polling and idempotent persistence.

### Submit

```
POST https://api.direct.yandex.com/json/v5/reports
Authorization: Bearer <token>
Client-Login: example-client            (agency)
Content-Type: application/json; charset=utf-8
Accept-Language: en
processingMode: offline
returnMoneyInMicros: false
skipReportHeader: true
skipColumnHeader: true
skipReportSummary: true
```

Body:

```json
{
  "params": {
    "SelectionCriteria": {
      "DateFrom": "2026-05-01",
      "DateTo": "2026-05-15"
    },
    "FieldNames": ["Date", "CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Conversions"],
    "ReportName": "campaigns-may-2026-v1",
    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
    "DateRangeType": "CUSTOM_DATE",
    "Format": "TSV",
    "IncludeVAT": "NO",
    "IncludeDiscount": "NO"
  }
}
```

### Response codes

| HTTP | Meaning | Client action |
|---|---|---|
| 200 | TSV ready, body is the file | Parse and persist |
| 201 | Queued | Sleep `Retry-After`, repeat **identical** body |
| 202 | Forming | Same |
| 400 | Bad params | Inspect JSON error, do not retry |
| 5xx | Transient | Exponential backoff |

### Polling pseudocode

```
body = build_payload()
while True:
    r = POST(/json/v5/reports, body)
    if r.status == 200:
        parse_tsv(r.text); break
    if r.status in (201, 202):
        retry = int(r.headers.get("Retry-After", "60"))
        sleep(retry + retry * 0.1)
        continue
    if r.status == 400:
        raise BadRequest(r.text)
    if 500 <= r.status < 600:
        backoff(); continue
```

### Persist idempotently

```sql
CREATE TABLE IF NOT EXISTS direct_stats_jobs (
  id          BIGSERIAL PRIMARY KEY,
  client      TEXT NOT NULL,
  report_name TEXT NOT NULL,
  payload     JSONB NOT NULL,
  status      TEXT NOT NULL DEFAULT 'queued',
  result_path TEXT,
  request_id  TEXT,
  UNIQUE (client, report_name)
);
```

### Gotchas

- **Body must stay identical between polls** — any change (e.g. mutating `FieldNames`) starts a new job and burns units.
- **Max 5 parallel reports** per account; exceed → `error 8` / HTTP 429.
- **`processingMode: online`** is capped at 5 minutes — fall back to `offline` for wide periods.
- **Skip-header flags** strip title, column, and summary rows; turn them on for clean DB ingest.

## 7. Error handling — partial errors and retry policy

JSON-RPC: HTTP is almost always 200; failures live in `error` (top-level) or `Errors[]` (per item in a batch). Always iterate result arrays.

Retry guide (full table in [errors.md](errors.md)):

- **Retriable with backoff**: `1`, `9`, `12` (exponential 1s → 32s, ±20% jitter, max 3–5 attempts).
- **Non-retriable business errors**: `2`, `8`, `17`, `52`, `53`, `54`, `56`, `152`, `506`. Log + alert.
- **Quota exhausted**: `58`, `153` — pause until 00:00 UTC reset; persist cursor.
- **Token revoked**: `506`, `1002`, `1003` — refresh / re-auth; set "auth degraded" sentinel.

Service ranges: `5000–5999` campaigns, `6000–6999` ad groups, `7000–7999` ads, `8000–8999` keywords, `9000–9999` bids.

Idempotent retry for writes:

1. Look up business key in `direct_idempotency`.
2. If `direct_id` present → previous call succeeded, skip.
3. Otherwise `get` from Direct by business key. If exists → store `Id`, skip.
4. Only when neither side knows the object → safe to retry `add`.

For `update` / `set`, send absolute values (not deltas) so retries are idempotent.

## 8. Daily ETL — schedule + persistence

### Pipeline

```
00:30 UTC  campaign-snapshot job
           (Changes.check -> if any -> Campaigns.get diff -> upsert direct_campaigns_cache)

00:45 UTC  ad-snapshot job
           (Ads.get for changed AdGroups -> upsert)

01:00 UTC  reports submit
           (CAMPAIGN_PERFORMANCE_REPORT, LAST_7_DAYS, processingMode=offline)
           one job per client_login, max 5 parallel

every 5m   reports poll worker
           SELECT * FROM direct_stats_jobs WHERE status IN ('queued','processing')
           identical body repost; respect Retry-After

on 200     stream TSV to staging.direct_stats
           UPSERT into facts table with (date, client, campaign_id, ad_group_id, ad_id) PK
```

### PostgreSQL skeleton

Tables: `direct_campaigns_cache` (latest snapshot), `direct_idempotency` (business_key → direct_id), `direct_audit` (every write), `direct_stats_jobs` (TSV polling state). Full SQL in `references/integration.md`.

### Observability minimum

- Structured log per call: `service`, `method`, `units_consumed`, `units_remaining`, `units_used_login`, `request_id`, `http`, `error_code`.
- Alerts: `remaining / daily_limit < 0.2`, `error 153`, `error 506` / `1002`, polling stuck >3 cycles.
- Daily roll-up: total units per client, top methods by cost.

### Gotchas

- **`Changes.check` is cheap** — use it for polling instead of full `Campaigns.get` every cycle.
- **Reports archive grows fast** — partition `direct_stats_facts` by month, drop >24 months.
- **Token revocation is a global event**: set an "auth degraded" sentinel that halts the entire client until refresh succeeds, otherwise the loop burns request counters.
