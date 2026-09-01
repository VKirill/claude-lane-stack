# JSON envelope and required headers

## Endpoint pattern

```
POST https://api.direct.yandex.com/json/v5/{service}
POST https://api-sandbox.direct.yandex.com/json/v5/{service}
POST https://api.direct.yandex.com/json/v5/reports        # reports — separate URL
```

`{service}` is the lower-case service name: `campaigns`, `adgroups`, `ads`, `keywords`, `bids`, `bidmodifiers`, `keywordbids`, `agencyclients`, `clients`, `dictionaries`, `changes`, `audiencetargets`, `retargetinglists`, `sitelinks`, `vcards`, `feeds`, `negativekeywordsharedsets`, `dynamictextadtargets`.

## Request body

```json
{
  "method": "<methodName>",
  "params": { ... }
}
```

- `method` — string, one of `get`, `add`, `update`, `delete`, `suspend`, `resume`, `archive`, `unarchive`, `moderate`, `set`, `setAuto`, etc.
- `params` — object with method-specific fields. For `get` — `SelectionCriteria` + `FieldNames` (+ `Page` for pagination). For `add` — an array of objects of the relevant type.

## Headers — required

| Header | Value | When |
|---|---|---|
| `Authorization` | `Bearer <OAuth-token>` | Always |
| `Content-Type` | `application/json; charset=utf-8` | Always for POST |
| `Client-Login` | `<client-login>` | Agency operating on a client account |

## Headers — optional

| Header | Value | Effect |
|---|---|---|
| `Accept-Language` | `ru` or `en` | Language of error messages and texts in responses. Default `en`. |
| `Use-Operator-Units` | `true` | Charge agency units instead of client's. Agency context only. |
| `Accept-Encoding` | `gzip` | Compression — critical for large `get` and Reports. |

## Response headers

| Header | Contents |
|---|---|
| `RequestId` | Unique request id. Always log it — support cannot help without it. |
| `Units` | `<consumed>/<remaining>/<daily-limit>` — units spent / left today / daily cap. Parse after every response. |
| `Units-Used-Login` | The login that paid. Cross-check against expectations (agency vs. client). |
| `Retry-After` | (Reports) Seconds before the next poll on 201/202. |

## Response body — success

```json
{
  "result": { ... }
}
```

For batch methods `result` contains arrays `AddResults`, `UpdateResults`, `DeleteResults`, `ActionResult` (for `suspend` / `resume` / `archive` / ...) with per-item status:

```json
{
  "result": {
    "AddResults": [
      { "Id": 12345 },
      { "Errors": [{ "Code": 8000, "Message": "...", "Details": "..." }] },
      { "Id": 12346, "Warnings": [{ "Code": 9001, "Message": "..." }] }
    ]
  }
}
```

**Critical**: HTTP 200 + `result` ≠ fully successful batch. Iterate the array and handle each element.

## Response body — top-level error

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

## Pagination

In `params.Page`:
```json
{
  "Page": {
    "Limit": 1000,
    "Offset": 0
  }
}
```

- `Limit` — up to 10 000 for most methods.
- If more pages exist, response includes `LimitedBy: <offset_reached>`; next call: `Offset: LimitedBy`.

## SelectionCriteria.Ids — limit 10 000

```json
{
  "SelectionCriteria": { "Ids": [1, 2, 3, ...] }
}
```

More than 10 000 → `error 17` (BadRequest). Chunk client-side.

## Minimal request examples

### `Campaigns.get`

```json
{
  "method": "get",
  "params": {
    "SelectionCriteria": {
      "States": ["ON", "SUSPENDED"],
      "Types": ["TEXT_CAMPAIGN", "UNIFIED_CAMPAIGN"]
    },
    "FieldNames": ["Id", "Name", "State", "Status", "Type", "DailyBudget"],
    "Page": { "Limit": 100 }
  }
}
```

### `Campaigns.add` — TextCampaign

```json
{
  "method": "add",
  "params": {
    "Campaigns": [{
      "Name": "Test campaign",
      "StartDate": "2026-01-01",
      "ClientInfo": "Client info",
      "TextCampaign": {
        "BiddingStrategy": {
          "Search": { "BiddingStrategyType": "HIGHEST_POSITION" },
          "Network": { "BiddingStrategyType": "SERVING_OFF" }
        }
      }
    }]
  }
}
```

### `Campaigns.suspend`

```json
{
  "method": "suspend",
  "params": { "SelectionCriteria": { "Ids": [12345, 12346] } }
}
```

Response:

```json
{ "result": { "SuspendResults": [{ "Id": 12345 }, { "Id": 12346 }] } }
```

## Client hygiene

- Always send `Accept-Encoding: gzip`.
- Keep-alive connection pool — reuse TCP/TLS.
- Timeout: 60–120 seconds for normal methods, 5+ minutes for Reports.
- Never send the token in URLs, logs, or breadcrumbs.
- User-Agent should carry the app name and contact: `MyApp/1.0 (ops@example.com)` — speeds up support.
