# Result codes — full table, retry strategy, partial errors

## Error shape

### Top-level (whole call failed)

```json
{
  "error": {
    "request_id": "1742...",
    "error_code": 53,
    "error_string": "Authentication error",
    "error_detail": "OAuth token is invalid"
  }
}
```

HTTP is almost always `200 OK` — JSON-RPC semantics. Only system-level failures return 4xx/5xx.

### Per-item (partial errors in a batch)

```json
{
  "result": {
    "AddResults": [
      { "Id": 12345 },
      {
        "Errors": [
          { "Code": 8000, "Message": "Wrong value", "Details": "..." }
        ]
      },
      {
        "Id": 12346,
        "Warnings": [
          { "Code": 9001, "Message": "Will be moderated", "Details": "..." }
        ]
      }
    ]
  }
}
```

Each array element is an independent result. **Never treat a batch as successful without per-item inspection.**

## Common codes (cross-service)

| Code | Name | Retry? | Action |
|---|---|---|---|
| 1 | InternalError | maybe (1–2x) | Backoff. If persistent, send `RequestId` to support. |
| 2 | InvalidArgument | **no** | Bad request body. Do not retry. |
| 8 | Forbidden | **no** | Wrong rights. Check OAuth scope, role. |
| 9 | NotAllowedYet | maybe | Resource not ready (moderation, etc.). Retry later. |
| 12 | ServiceTemporarilyUnavailable | **yes** | Temporary outage. Exponential backoff. |
| 13 | InvalidProtocol | no | Malformed protocol. Inspect body. |
| 14 | InvalidJsonFormat | no | Malformed JSON. |
| 17 | BadRequest | **no** | Limit exceeded (e.g. >10 000 IDs) or bad field format. |
| 32 | InvalidLanguage | no | `Accept-Language` not supported. |
| 52 | NoRights | **no** | OAuth scope too narrow (need `direct:api` / `direct:agency`). |
| 53 | AuthenticationError | **no** | Token broken / expired / invalid. |
| 54 | InvalidLogin | **no** | `Client-Login` does not exist or no access. |
| 56 | NotFound | **no** | Object (campaign / adgroup / ad) does not exist. |
| 58 | LimitReached | **no** | Object-count limit (campaigns, groups, ads in account). |
| 152 | PreconditionFailed | **no** | State precondition not met (cannot `delete` with stats, etc.). |
| 153 | UnitsLimitExceeded | **no** | Daily units exhausted. Wait until 00:00 UTC reset. |
| 506 | TokenRevoked | **no** | User revoked the token. Start OAuth refresh / re-auth. |

## Auth-specific

| Code | Name | Action |
|---|---|---|
| 1000 | InternalError | Internal auth error. Backoff. |
| 1001 | NotAuthorized | Missing `Authorization` header. Add it. |
| 1002 | InvalidToken | Token invalid. Refresh / re-auth. |
| 1003 | UserBlocked | Account is blocked. Do not retry, escalate. |

## Service-specific (5000–9999)

Each service owns a range.

### CampaignsService (5000–5999)

| Code | Meaning |
|---|---|
| 5001 | Cannot delete campaign with statistics |
| 5002 | Strategy not compatible with campaign type |
| 5003 | StartDate cannot be in the past |
| 5004 | Account campaign limit exceeded |
| 5005 | Campaign name already taken / business rule violation (see notes) |
| 5006 | DailyBudget too small / large |
| 5007 | Ad-group limit in campaign reached |

**5005 live-proven cases (account ki.vech):**
- Attempting to disable ALL autotargeting categories → `"Запрещено выключать все категории в автотаргетинге"`. At least one category must stay `YES`.
- May also fire on DailyBudget range violations alongside 6000.

**6000 live-proven case:**
- Setting `DailyBudget` on a campaign that uses an auto strategy (e.g. `WB_MAXIMUM_CLICKS`) → error 6000 `"Inconsistent object state — Daily budget can only be used in conjunction with manual strategies"`. With auto strategies the spend cap goes inside the strategy as `WeeklySpendLimit`. Set `DailyBudget` only for manual strategies (`HIGHEST_POSITION`, `AVERAGE_CPC`).

### AdGroupsService (6000–6999)

| Code | Meaning |
|---|---|
| 6001 | CampaignId does not exist |
| 6002 | RegionIds — invalid region |
| 6003 | Group limit in campaign |
| 6004 | NegativeKeywords too long |

### AdsService (7000–7999)

| Code | Meaning |
|---|---|
| 7001 | Headline exceeds character limit |
| 7002 | Text exceeds character limit |
| 7003 | DisplayUrlPath invalid |
| 7004 | Href is not a valid URL |
| 7005 | AdGroupId does not exist |
| 7006 | VCardId / SitelinkSetId does not exist |
| 7007 | Ad limit in group |
| 7008 | Already in moderation |

### KeywordsService (8000–8999)

| Code | Meaning |
|---|---|
| 8001 | Invalid keyword phrase |
| 8002 | Keyword limit in group exceeded |
| 8003 | Phrase too long |
| 8004 | Negative-keyword limit exceeded |
| 8005 | Duplicate keyword in group |

**8000 live-proven case:**
- Sending `TextAdGroupAutoTargeting` or `TextAdGroup.AutoTargeting` in an `adgroups.add/update` payload → error 8000 `"Wrong value — unknown parameter"`. Autotargeting for a search `TEXT_AD_GROUP` is configured via the `---autotargeting` keyword (Keywords service), not on the AdGroup object.

### BidsService / KeywordBidsService (9000–9999)

| Code | Meaning |
|---|---|
| 9001 | Bid below minimum |
| 9002 | Bid above maximum |
| 9003 | Strategy does not allow manual bid |
| 9004 | KeywordId does not exist |

## Warnings

`Warnings[]` are non-blocking advisories. The operation **succeeded**, but you should know:

| Code | Meaning |
|---|---|
| 9001 | Will be sent to moderation |
| 9002 | Bid adjusted to allowed range |
| 9003 | StartDate moved to today |
| 9100 | Some fields ignored |

Log warnings, do not block.

## Retry strategy

### Retriable (with backoff)

`1`, `9`, `12` — exponential backoff: 1s → 2s → 4s → 8s → 16s, max 3–5 attempts. Jitter ±20%.

### Non-retriable (business errors)

`2`, `8`, `17`, `52`, `53`, `54`, `56`, `152`, `506` — do not retry; log + alert.

### Quota exhausted

`58`, `153` — pause until reset (00:00 UTC for units); persist a batch cursor.

## Idempotent retry for write operations

**Danger**: retrying `add` blindly can create a duplicate when the first request was received but the response was lost.

Strategy:
1. Before retry — `get` by business key (Name + CampaignId).
2. If the object exists — skip (return stored Id).
3. Otherwise — retry `add`.

Alternative: ask support to look up `RequestId` outcome — there is no API endpoint for "status by RequestId".

## Error logging

Always log:
- `RequestId` (from response headers)
- `error_code`, `error_string`, `error_detail`
- Request body (with `Authorization` and `Client-Login` redacted)
- HTTP status
- Timestamp

Alerts:
- `153` (UnitsLimitExceeded) — critical, suspend writes.
- `506` / `1002` — critical, kick off auth flow.
- `1003` (UserBlocked) — critical, escalate.
- `58` (LimitReached) — warning, audit account limits.

## Common mistakes in error handling

- **Ignoring Warnings** — a batch becomes `ACCEPTED`, but a warning said "bid was floored" → no impressions. Log + surface in UI.
- **Treating HTTP 200 as success** — check `error` in body and per-item `Errors[]` for batches.
- **Retrying `2` (InvalidArgument)** — will never succeed; wastes time and units.
- **Retrying `54` (InvalidLogin)** — configuration issue; retries are useless.
- **Aggressive retries on `12`** without backoff — makes the outage worse.
