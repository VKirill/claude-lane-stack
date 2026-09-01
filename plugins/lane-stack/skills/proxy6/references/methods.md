# Methods — full reference for all 10

Every call follows `GET https://px6.link/api/{api_key}/{method}/?{params}`. Envelope rules in [setup.md](setup.md).

All success envelopes carry `status`, `user_id`, `balance`, `currency`. Examples below show only the method-specific extras.

---

## 1. `getprice` — order price calculation

**Params**

| Name | Required | Notes |
|---|---|---|
| `count` | optional | Integer. Number of proxies. |
| `period` | optional | Integer. Days. |
| `version` | optional | `3` IPv4 Shared · `4` IPv4 · `5` MTproto · `6` IPv6. |

When all three are given → returns a single quote. When none are given → returns the full price matrix in a nested `data` object keyed by version → period.

**Success extras**

```json
{
  "price": "12.50",
  "price_single": "0.0625",
  "period": 20,
  "count": 10
}
```

Field semantics:
- `price` — total order price (string, major units of `currency`).
- `price_single` — price per proxy per day.
- `period` — echoed period in days.
- `count` — echoed count.

**Errors**: `200` (bad count), `210` (bad period), `240` (bad version), `410` (computed price ≤ 0 — combination not sold).

---

## 2. `getcount` — available stock by country + version

**Params**

| Name | Required | Notes |
|---|---|---|
| `country` | required | ISO-2 (e.g. `ru`, `us`, `de`). |
| `version` | required | `3` / `4` / `5` / `6`. |

**Success extras**

```json
{ "count": "971" }
```

`count` — number of proxies available for purchase right now. String, but parses as int.

**Errors**: `220` (bad/missing country), `240` (bad version).

**Use**: always call before `buy` to avoid `error_id 300` (insufficient stock).

---

## 3. `getcountry` — country list

**Params**

| Name | Required | Notes |
|---|---|---|
| `version` | required | `3` / `4` / `5` / `6`. |

**Success extras**

```json
{ "list": ["ru", "ua", "us", "de", "fr", "..."] }
```

`list` is an array of lowercase ISO-2 codes. Use to populate dropdowns or sanity-check a country code before `getcount` / `buy`.

**Errors**: `240`.

---

## 4. `getproxy` — list user's proxies

**Params**

| Name | Required | Notes |
|---|---|---|
| `state` | optional | `active` · `expired` · `expiring` · `all` (default `all`). |
| `descr` | optional | Filter by exact `descr` value. |
| `nokey` | optional flag | Skip extra envelope fields. |
| `page` | optional | Default `1`. |
| `limit` | optional | Default `1000`, max `1000`. |

**Success extras**

```json
{
  "list_count": 7,
  "list": {
    "11": {
      "id": "11",
      "version": "6",
      "ip": "2a00:1838:32:19f:45fb:2640::330",
      "host": "185.22.134.250",
      "port": "7330",
      "user": "5svBNGSn",
      "pass": "9WJpHKf",
      "type": "http",
      "country": "ru",
      "date": "2024-09-10 15:35:01",
      "date_end": "2024-10-11 12:31:01",
      "unixtime": 1726000501,
      "unixtime_end": 1728646261,
      "descr": "scraper-A",
      "active": "1"
    }
  }
}
```

Field semantics (verbatim from spec):
- `id` — proxy6 internal id (string).
- `version` — `3`/`4`/`5`/`6`.
- `ip` — for IPv6 the actual IPv6 address; for IPv4 same as `host`.
- `host` — IPv4 endpoint to connect to.
- `port` — port (string).
- `user` / `pass` — credentials for user/pass auth (ignored if you use `ipauth`).
- `type` — `http` · `socks` · `auto`.
- `country` — ISO-2.
- `date`, `date_end` — human strings; `unixtime`, `unixtime_end` — epoch seconds.
- `descr` — your tag (max 50 chars).
- `active` — `1` if currently usable, `0` if expired / disabled.

**Errors**: `230` (bad ids — irrelevant here since none accepted).

**Pagination**: with > 1000 proxies use `page` to walk. `list` is a JSON object, not array — keys are proxy ids as strings.

---

## 5. `setdescr` — update technical comment

**Params**

| Name | Required | Notes |
|---|---|---|
| `new` | required | New comment value. Max 50 chars. |
| `old` | one of `old`/`ids` | Filter: change only proxies whose current `descr` matches `old`. |
| `ids` | one of `old`/`ids` | CSV list of proxy ids to update. |

Must supply **either** `old` or `ids`, not neither. Spec allows providing both (filters AND-combine: ids matching AND with that old descr).

**Success extras**

```json
{ "count": 3 }
```

`count` — number of proxies updated.

**Errors**: `230` (bad ids format), `250` (bad descr — over 50 chars or empty), `404` (no matching proxies).

---

## 6. `buy` — purchase proxies  ⚠️ MONEY

**Params**

| Name | Required | Notes |
|---|---|---|
| `count` | required | How many to buy. |
| `period` | required | Days. |
| `country` | required | ISO-2. |
| `version` | required | `3`/`4`/`5`/`6`. |
| `descr` | optional | Operational tag. Max 50 chars. Recommended ALWAYS to set. |
| `auto_prolong` | optional **flag** | Presence enables auto-renewal. Default: OFF (omit). |
| `nokey` | optional flag | Skip extra envelope fields. |
| `type` | optional | `http` · `socks` (`auto` default depends on dashboard). |

**Success extras**

```json
{
  "order_id": "12345",
  "count": 10,
  "price": "12.50",
  "price_single": "0.0625",
  "period": 20,
  "country": "ru",
  "list": {
    "11": { "id": "11", "version": "6", "ip": "...", "...": "..." }
  }
}
```

`list` carries the same per-proxy shape as `getproxy`. Save it locally — that's your authoritative pool snapshot for this order.

**Errors**: `200`/`210`/`220`/`240`/`250`/`260`/`300` (not enough stock — call `getcount` first), `400` (insufficient balance — check envelope `balance` first), `410` (price ≤ 0 — bad combination).

**Money safety checklist** (full version in [purchase-and-billing.md](purchase-and-billing.md)):
1. `getprice(count, period, version)` → confirm price you expected.
2. `getcount(country, version)` → confirm stock ≥ count.
3. Any envelope `balance` ≥ price + safety margin.
4. `buy(...)` with explicit `descr`.

---

## 7. `prolong` — extend proxy lifetime  ⚠️ MONEY

**Params**

| Name | Required | Notes |
|---|---|---|
| `period` | required | Days. |
| `ids` | required | CSV list of proxy ids. |
| `nokey` | optional flag | Skip extra envelope fields. |

**Success extras**

```json
{
  "order_id": "12346",
  "price": "5.00",
  "price_single": "0.0625",
  "period": 20,
  "count": 4,
  "list": {
    "11": { "id": "11", "date_end": "2024-11-01 12:31:01", "unixtime_end": 1730475061 }
  }
}
```

⚠️ **Mixed-version gotcha**: if `ids` mixes versions (e.g. IPv4 + IPv6 in one call), `price_single` is **absent** because per-proxy cost varies. To verify costs in mixed batches, iterate `list` entries and sum.

**Errors**: `210`/`230`/`400` (insufficient balance), `404` (any id not found).

---

## 8. `delete` — irreversible removal  ⚠️ DESTRUCTIVE

**Params**

| Name | Required | Notes |
|---|---|---|
| `ids` | one of `ids`/`descr` | CSV list of proxy ids. |
| `descr` | one of `ids`/`descr` | Exact-match filter — deletes ALL proxies with this `descr`. |

Must supply **either** `ids` or `descr`. Per spec, `ids` takes precedence if both are passed.

**Success extras**

```json
{ "count": 4 }
```

`count` — number of proxies actually deleted.

**Errors**: `230`, `250`, `404`.

**Operational rule** — see [wrong-vs-right.md](wrong-vs-right.md) and [pool-management.md](pool-management.md):
1. Run `getproxy(descr=<tag>)` and print every id.
2. Confirm the count matches expectation.
3. Then `delete(ids=<csv of ids>)` — NEVER `delete(descr=<tag>)` blindly.

---

## 9. `check` — validate a single proxy

**Params**

| Name | Required | Notes |
|---|---|---|
| `ids` | one of | Internal proxy6 id. |
| `proxy` | one of | Full string `ip:port:user:pass`. |

**Success extras**

```json
{ "proxy_id": "11", "proxy_status": true }
```

`proxy_status` is a JSON boolean. `true` = reachable / valid on proxy6's side; `false` = unreachable or auth failure.

**Errors**: `230`, `280` (bad proxy string), `404`.

**Note**: this checks proxy6's view of the proxy. It does NOT guarantee the proxy works against your target site — that requires an end-to-end HEAD/GET through the proxy via your HTTP client.

---

## 10. `ipauth` — bind/unbind IP allowlist for proxy auth  ⚠️ FULL-REPLACE

**Params**

| Name | Required | Notes |
|---|---|---|
| `ip` | required | CSV list of IPs **OR** the literal string `delete`. |

**Success**: standard envelope only. No extra data.

⚠️ **Full-replace semantics**: this call REPLACES the entire allowlist. Sending one IP wipes any other previously bound IPs. Sending `delete` clears everything (proxies revert to user/pass auth).

**Errors**: `105` (one of the IPs is malformed).

**Use**: see [ipauth-strategy.md](ipauth-strategy.md) for dev/prod separation and the canonical "compose the full set every time" pattern.

---

## Method × HTTP method × Risk summary

| Method | Reads | Writes | Money | Destructive | Rate-budget weight |
|---|---|---|---|---|---|
| `getprice` | ✅ | — | — | — | 1 |
| `getcount` | ✅ | — | — | — | 1 |
| `getcountry` | ✅ | — | — | — | 1 |
| `getproxy` | ✅ | — | — | — | 1 (1 per page) |
| `setdescr` | — | ✅ | — | — | 1 |
| `buy` | — | ✅ | 💰 | — | 1 |
| `prolong` | — | ✅ | 💰 | — | 1 |
| `delete` | — | ✅ | — | 💀 | 1 |
| `check` | ✅ | — | — | — | 1 |
| `ipauth` | — | ✅ | — | ⚠️ replaces full list | 1 |

Every call consumes one rate-limit token — there is no special endpoint that is cheaper. Plan accordingly.
