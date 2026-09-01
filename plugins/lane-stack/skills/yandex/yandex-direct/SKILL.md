---
name: yandex-direct
description: "[RU: интеграция Яндекс.Директ API v5 — кампании, ставки, отчёты, автостратегии, песочница] Yandex.Direct API v5 — JSON over HTTPS, OAuth Bearer + Client-Login for agencies, Campaigns/AdGroups/Ads/Keywords/Bids/KeywordBids/BidModifiers/Reports services, units-based daily quota, sandbox at api-sandbox.direct.yandex.com, TSV reports with processingMode online/offline/auto and 201/202 polling via Retry-After. Use when: yandex direct, яндекс директ, direct api v5, JSON-RPC, CampaignsService, AdsService, BidsService, Reports TSV, units, sandbox, песочница, Client-Login, agency, агентский кабинет, auto bidding, автостратегии, WB_MAXIMUM_CLICKS, PAY_FOR_CONVERSION, поисковые/РСЯ, micro-currency. SKIP: web analytics (→yandex-metrica); SERP scraping (→xmlstock); Wordstat (→mutagen); Google Ads (→google-ads); myTarget/VK Ads (→vk-ads)."
stacks:
  - yandex-direct
  - ru-ads
  - python
  - nodejs
tags:
  - ads
  - ppc
  - ru
  - yandex
  - direct
  - json-rpc
  - oauth
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## Version Requirements

**Primary pins:**
- Yandex Direct API: `v5 (stable, JSON over HTTPS; api.direct.yandex.com/json/v5/{service})`
- Sandbox: `api-sandbox.direct.yandex.com/json/v5/{service}`
- Python: `3.14.x`
- Node.js: `24.x (Active LTS)`

> Verify against current Yandex Direct release notes before production use.

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. Read the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Programmatic campaign management in Yandex.Direct: create, update, suspend, archive via `CampaignsService`
- Bulk bid updates and strategy switching via `BidsService` / `KeywordBidsService`
- Loading keywords with negatives and operators via `KeywordsService`; tracking `Status` / `State` transitions (DRAFT/MODERATION/ACCEPTED/REJECTED)
- Creating and moderating ads (`AdsService`): TextAd, DynamicTextAd, MobileAppAd, ImageAd, CpcVideoAd, SmartAdBuilderAd
- Pulling statistics through the **Reports API** (TSV) with `processingMode` (online/offline/auto), 201/202 polling honoring `Retry-After`
- Working from an agency account: passing `Client-Login` per client, spending agency units via `Use-Operator-Units: true`
- Testing integration in the **sandbox** at `api-sandbox.direct.yandex.com` without burning real budgets
- Building your own client / connector (Python httpx, Node.js fetch) with units accounting, retry on 5xx/transient codes, manual idempotency
- Integrating into CRM/dashboard: pull account structure, adjust CPC from conversion signals, sync negative keywords

## Do not use this skill when

- Web traffic analytics and goals from the site → `yandex-metrica` (cascade marker)
- SERP scraping, position tracking, snippet parsing → `xmlstock` (cascade marker)
- Wordstat frequency and keyword competition → `mutagen` (cascade marker)
- Google Ads / Google Ads API (different platform, different auction model) → `google-ads` cascade
- myTarget / VK Ads / VKontakte advertising → `vk-ads` / `mytarget` cascade
- Static on-site ad blocks, direct sales without auction
- Plain stats viewing through UI — Direct API is only needed for automation and scale

## Purpose

Yandex.Direct API v5 is the official programmatic interface to Yandex's paid search and display platform. It manages campaigns (Search / Network / Master of Campaigns / Unified Performance / Dynamic / Smart banners / Mobile app / CPC Video / CPM Banner), ad groups, ads of all types, keywords and targetings, bids (manual and auto-strategies), reports (TSV), dictionaries, budget forecasts, and XML import/export.

This skill is **high-stakes** because:

1. **Every write call spends real budget.** `AdsService.add` and `BidsService.set` start serving and consume client money. A misplaced zero in `MaxCpc` = hundreds of thousands of rubles burned in an hour. Every write requires a sandbox dry-run plus explicit confirmation of magnitudes.
2. **Units economy.** Each method costs units from a per-account daily limit. Overrun → `error 153` (UnitsLimitExceeded) and the batch ends up in an inconsistent state. Estimate cost before each batch; parse `Units: consumed/remaining/daily-limit` from every response.
3. **`Client-Login` is mandatory for agencies.** Forget it and the call runs against the agency's own account instead of the client's → auth error or, worse, silent change to the wrong account. Enforce in middleware and assert on `Units-Used-Login` in responses.
4. **Partial errors in batch operations.** `AddResults` / `UpdateResults` may contain a mix of `Id` and `Errors` per item. A 200 OK does not mean the batch fully succeeded — iterate per element.
5. **Reports API has its own lifecycle.** `processingMode=offline` returns HTTP 201 (queued) or 202 (forming); polling must respect `Retry-After`. Ignoring it → 429 / IP or account throttling. Maximum 5 parallel reports.
6. **Sandbox ≠ production data.** Sandbox campaigns are not shown to real users; stats are synthetic. Sandbox is still the right place to validate request structure and error handling without spending money.
7. **No built-in idempotency.** Repeating `add` with the same body creates a duplicate. Maintain client-side dedup by business key (name + parent id) or a unique external index on returned `Id`.
8. **Token revocation.** OAuth tokens can be revoked by the user — every request then fails with `error_code 1002` / `506`. Refresh logic and an "auth degraded" sentinel are required.
9. **10 000 IDs per selection.** `SelectionCriteria.Ids` accepts up to 10 000; more → `error 17`. Chunk client-side.
10. **`suspend` ≠ `archive`.** Suspend pauses (reversible); archive is terminal and locks editing. Confusing them = losing the ability to mutate the object.

This skill owns Direct-domain knowledge: endpoints, headers, units economy, Reports lifecycle, agency access modeling, error semantics, sandbox testing. HTTP plumbing lives in `httpx` / `nodejs`; storage in `postgresql`.

## Capabilities

### OAuth 2.0 and Client-Login for agencies

Yandex Direct requires a Yandex ID OAuth token per user (advertiser or agency). Tokens are issued via the standard OAuth flow on `oauth.yandex.ru` or a manual debug token from the app page. For agencies: one token per agency + the `Client-Login: <client-login>` header selects the target account. `Use-Operator-Units: true` charges the agency's units rather than the client's. Without `Client-Login`, an agency token operates only on the agency account itself.

> Full reference: [references/setup.md](references/setup.md)

### JSON envelope and required headers

Body is JSON: `{"method": "<action>", "params": {...}}`. Endpoint: `POST https://api.direct.yandex.com/json/v5/<service>` (or the sandbox host). Required headers: `Authorization: Bearer <token>`, `Client-Login` (agencies), `Content-Type: application/json; charset=utf-8`. Optional: `Accept-Language: ru|en` (message language), `Use-Operator-Units: true`, `Accept-Encoding: gzip`. Response headers: `RequestId` (for support), `Units: <consumed>/<remaining>/<daily-limit>`, `Units-Used-Login` (which account paid). `Accept-Encoding: gzip` is critical for large `get` responses and TSV reports.

> Full reference: [references/envelope-and-headers.md](references/envelope-and-headers.md)

### Campaign and ad-group lifecycle — states, archive, suspend/resume

`CampaignsService` exposes `get`, `add`, `update`, `delete`, `suspend`, `resume`, `archive`, `unarchive`. `Status` (DRAFT, MODERATION, ACCEPTED, REJECTED) is moderation state; `State` (CONVERTED, ARCHIVED, SUSPENDED, ENDED, OFF, ON) is operational state. Types: `TEXT_CAMPAIGN`, `UNIFIED_CAMPAIGN`, `DYNAMIC_TEXT_CAMPAIGN`, `MOBILE_APP_CAMPAIGN`, `CPM_BANNER_CAMPAIGN`, `SMART_CAMPAIGN`, `CPM_VIDEO_CAMPAIGN`. `AdGroupsService`: `get`/`add`/`update`/`delete` with `RegionIds`, `NegativeKeywords`, `TrackingParams`. Prefer `archive` over `delete` for objects with stats.

> Full reference: [references/campaigns-and-adgroups.md](references/campaigns-and-adgroups.md)

### Ads and keywords — moderation and states

`AdsService`: `get`, `add`, `update`, `delete`, `archive`, `unarchive`, `moderate`, `resume`, `suspend`. Ad types live under exactly one of `TextAd`, `MobileAppAd`, `DynamicTextAd`, `ImageAd`, `CpcVideoAdBuilderAd`, `SmartAdBuilderAd`, `CpmBannerAdBuilderAd`. After `add` an ad is `Status=DRAFT` — `moderate` pushes it to `MODERATION` → `ACCEPTED` / `REJECTED` / `PREACCEPTED`. `KeywordsService`: `get`/`add`/`update`/`delete`/`resume`/`suspend`. Negative keywords apply at Campaign (`NegativeKeywords`), AdGroup, and Keyword level. Operators: `!`, `+`, `[]`, `""`, `-`, `(a|b)`.

> Full reference: [references/ads-and-keywords.md](references/ads-and-keywords.md)

### Bids — manual, auto-strategies, search vs network split

`BidsService`: `set`, `get`, `setAuto`. `KeywordBidsService` is the current entry point for per-keyword bids. Auto-strategies: `WB_MAXIMUM_CLICKS`, `WB_MAXIMUM_CONVERSION_RATE`, `AVERAGE_CPC`, `AVERAGE_CPA`, `WEEKLY_CLICK_PACKAGE`, `AVERAGE_ROI`, `PAY_FOR_CONVERSION`, `HIGHEST_POSITION`, `SERVING_OFF`. Manual bids: `SearchBid` (search), `NetworkBid` (Network / RSYA), `ContextCoverage` (% of network reach). `BidModifiersService` adjusts by audience, geo, demographics, devices, time. All money fields are in **micro-currency** (divide by 1 000 000 for rubles).

> Full reference: [references/bids.md](references/bids.md)

### Reports API — TSV lifecycle with polling

Dedicated endpoint: `POST /json/v5/reports`. Body: `{"params": {"SelectionCriteria": {...}, "FieldNames": [...], "ReportName": "...", "ReportType": "CAMPAIGN_PERFORMANCE_REPORT|AD_PERFORMANCE_REPORT|...", "DateRangeType": "LAST_WEEK|CUSTOM_DATE|...", "Format": "TSV", "IncludeVAT": "YES|NO"}}`. The `processingMode` header chooses `online` (sync up to 5 minutes), `offline` (queued, HTTP 201/202 + `Retry-After`), or `auto`. Set `returnMoneyInMicros: false` for rubles; `skipReportHeader / skipColumnHeader / skipReportSummary: true` for clean parsing. Polling: on 201/202, sleep `Retry-After`, repeat the **identical** POST until 200/error. Maximum 5 parallel reports.

> Full reference: [references/stats-tsv.md](references/stats-tsv.md)

### Error codes — billing semantics, retry, partial errors

Common codes: `1` (InternalError), `2` (InvalidArgument), `8` (Forbidden), `9` (NotAllowedYet), `12` (ServiceTemporarilyUnavailable → retry), `17` (BadRequest), `52` (NoRights), `53` (AuthenticationError), `54` (InvalidLogin), `56` (NotFound), `58` (LimitReached), `152` (PreconditionFailed), `153` (UnitsLimitExceeded), `506` (TokenRevoked), `1000–1003` (auth-domain), `5000–9999` (service-specific). Partial errors in batches: HTTP 200 but `result.AddResults[i].Errors[]` per item. `Warnings[]` are non-blocking but must be logged.

> Full reference: [references/errors.md](references/errors.md)

### Units economy — what costs what

Each method consumes units from a per-account daily limit. New apps start around 3 000–5 000 units/day; the limit grows with sustained usage. `get` is cheap (~1–40 units); `add` / `update` / `delete` is more expensive (~10–30 per call plus per-element cost). `Reports` enqueue costs ~10–20 units; polling and final download are free. Sandbox units are a separate wallet. Read the `Units` header after every response; throttle writes when `remaining / daily_limit < 0.2`.

> Full reference: [references/limits-and-units.md](references/limits-and-units.md)

### Sandbox vs production

Sandbox host: `api-sandbox.direct.yandex.com`. Same OAuth token (Yandex ID is unified) but a separated, isolated tier. No UI — API only. Data is deleted after 1 month of inactivity. Reports in sandbox: one campaign per report; stats are synthetic. Use it for: request/response shape validation, error-path drills, polling behavior. Production-only checks: real moderation, real spend, bid adjustments against live audiences.

> Full reference: [references/setup.md](references/setup.md)

### End-to-end workflow (bootstrap → ETL)

Bootstrap OAuth → sandbox smoke → JSON envelope → Campaigns lifecycle → AdGroups / Ads / Keywords flow → Bids (manual / auto) → Reports submit + poll + persist → idempotent daily ETL.

> Full reference: [references/workflow.md](references/workflow.md)

### Cookbook — 28 ready-to-use recipes

Auth, campaigns, ad groups, ads, keywords, bids, reports polling lifecycle, wordstat via Direct, agency clients, error handling, and migration from v0.4 (`wordstat_keywords` replacement).

> Full reference: [references/cookbook.md](references/cookbook.md)

## Quick reference

### Services

| Service | Endpoint suffix | Common methods |
|---|---|---|
| `agencyclients` | `/json/v5/agencyclients` | get, add, update |
| `campaigns` | `/json/v5/campaigns` | get, add, update, delete, suspend, resume, archive, unarchive |
| `adgroups` | `/json/v5/adgroups` | get, add, update, delete |
| `ads` | `/json/v5/ads` | get, add, update, delete, archive, unarchive, moderate, resume, suspend |
| `keywords` | `/json/v5/keywords` | get, add, update, delete, resume, suspend |
| `bids` | `/json/v5/bids` | set, setAuto, get |
| `bidmodifiers` | `/json/v5/bidmodifiers` | set, get, delete |
| `keywordbids` | `/json/v5/keywordbids` | get, set, setAuto |
| `audiencetargets` | `/json/v5/audiencetargets` | get, add, delete, resume, suspend |
| `retargetinglists` | `/json/v5/retargetinglists` | get, add, update, delete |
| `sitelinks` | `/json/v5/sitelinks` | get, add, delete |
| `vcards` | `/json/v5/vcards` | get, add, delete |
| `dictionaries` | `/json/v5/dictionaries` | get (regions, currencies, metrics) |
| `changes` | `/json/v5/changes` | check, checkDictionaries, checkCampaigns |
| `reports` | `/json/v5/reports` | TSV reports with processingMode |
| `clients` | `/json/v5/clients` | get, update |
| `dynamictextadtargets` | `/json/v5/dynamictextadtargets` | get, add, delete, suspend, resume |
| `feeds` | `/json/v5/feeds` | get, add, update, delete |
| `negativekeywordsharedsets` | `/json/v5/negativekeywordsharedsets` | get, add, update, delete |

### HTTP headers

| Header | Required | Purpose |
|---|---|---|
| `Authorization: Bearer <token>` | always | Yandex ID OAuth token |
| `Client-Login: <login>` | agencies | Target client account |
| `Accept-Language: ru\|en` | optional | Language of messages and errors |
| `Use-Operator-Units: true` | optional, agency only | Charge agency units, not client |
| `Content-Type: application/json; charset=utf-8` | POST | Required for JSON body |
| `Accept-Encoding: gzip` | optional | Compression — critical for large reads |

### Response headers

| Header | Meaning |
|---|---|
| `RequestId` | Unique request id, log for support |
| `Units` | `<consumed>/<remaining>/<daily-limit>` |
| `Units-Used-Login` | Account whose balance was charged |
| `Retry-After` | (Reports) seconds before next poll on 201/202 |

### Result codes (key subset)

| Code | Name | Retry? | Action |
|---|---|---|---|
| 1 | InternalError | maybe (1–2x) | Backoff; if persistent, share `RequestId` with support |
| 2 | InvalidArgument | no | Inspect request body |
| 8 | Forbidden | no | Wrong rights, check OAuth scope and role |
| 9 | NotAllowedYet | maybe | Resource not ready; retry later |
| 12 | ServiceTemporarilyUnavailable | yes | Exponential backoff |
| 17 | BadRequest | no | Check >10 000 IDs / field format |
| 52 | NoRights | no | Insufficient OAuth scope |
| 53 | AuthenticationError | no | Token broken / expired |
| 54 | InvalidLogin | no | `Client-Login` invalid |
| 56 | NotFound | no | Object does not exist |
| 58 | LimitReached | no (until reset) | Account-level limit |
| 152 | PreconditionFailed | no | Object state forbids the action |
| 153 | UnitsLimitExceeded | no (until reset) | Suspend writes until daily reset |
| 506 | TokenRevoked | no | Refresh OAuth |
| 1000–1003 | Auth domain | no | Re-issue token |

### Reports HTTP codes

| HTTP | Meaning | Action |
|---|---|---|
| 200 OK | TSV body ready | Parse, persist |
| 201 Created | Queued | Wait `Retry-After`, repeat identical POST |
| 202 Accepted | Forming | Same as 201 |
| 400 Bad Request | Param error | Inspect JSON error, do not retry |
| 500 Internal | Server error | Backoff |
| 502/503/504 | Transient | Backoff |

## Common mistakes

- **Missing `Client-Login` in agency context** — the call mutates the agency account or returns `error 54`. Fix: middleware enforcement + assert on `Units-Used-Login`.
- **Not reading the `Units` header** — a 1 000-item update batch burns the daily limit and the second half fails with `153`. Fix: parse `Units` every response; pause writes when `remaining / daily_limit < 0.2`.
- **Treating HTTP 200 as full batch success** — `AddResults` / `UpdateResults` carry per-item errors. Fix: always iterate and log `Errors[]` per item, retry only failed ones.
- **Polling reports faster than `Retry-After`** — IP / account throttling. Fix: respect `Retry-After`, +10% jitter, max 5 parallel reports.
- **Changing the body between report polls** — every change is a new job, fresh units burned. Fix: dump and reuse the exact same payload.
- **`delete` instead of `archive`** on campaigns with stats — data is lost. Fix: archive-first policy; `delete` only for drafts.
- **Mixing sandbox and production endpoints** — the same OAuth token works on both, so it's easy to misconfigure `BASE_URL`. Fix: separate configs, explicit env prefix in logs.
- **`MaxCpc` in rubles instead of micro-currency** — `100` becomes 100 micro-rubles (no impressions) or `100_000_000` becomes 100 rubles × 1M (instant burn). Fix: convert at the boundary, never in business logic.
- **>10 000 IDs in `SelectionCriteria.Ids`** → `error 17`. Fix: chunk to 10 000.
- **Assuming `suspend` halts impressions instantly** — propagation can take minutes. Fix: combine with bid floor for critical stops.
- **Production token in sandbox calls** — works, but logs get muddled. Fix: explicit env flag on `DIRECT_HOST`.
- **Ignoring `error 506` (token revoked)** — all subsequent calls fail. Fix: catch + refresh + "auth degraded" sentinel.

## Red flags — STOP and verify

- "A campaign changed but I did not start anything" → agency token without `Client-Login` operated on the agency's own account. Check `Units-Used-Login` in logs.
- "Money is burning unexpectedly" → `MaxCpc` sent in wrong units (rubles vs. micro × 1M). Suspend the campaign immediately and re-read the last `Bids.set` payload.
- "Reports polling looped forever" → likely `processingMode: online` with a 5-minute server-side cutoff. Switch to `offline`.
- "`error 153` mid-batch" → units exhausted. Do not retry the rest of the batch; save the cursor and resume after 00:00 UTC reset.
- `Bids.get` returns shifting values between runs → someone is editing in the UI in parallel. Add audit log and a write lock on the app side.
- Mass `error 1002` / `506` → user revoked the token. Stop the loop before hitting rate limits.

## Behavioral traits

- **Sandbox first.** Any new integration or large change passes through `api-sandbox.direct.yandex.com` before flipping to production.
- **Read-only first.** Always `get`, inspect shape, then `add`/`update`/`delete`. Never write blindly.
- **Manual idempotency.** Business key (Name + parent id, or hash) checked before `add`. Returned `Id` stored with a unique index.
- **Logs `RequestId` and `Units` per call.** Support cannot help without `RequestId`.
- **Money in micro-units.** All read/write of money fields multiplies/divides by 1 000 000 at one explicit boundary.
- **Partial errors are normal.** Loop over result arrays, split success/failed, retry only failed.
- **Reports off the main thread.** Polling in a background worker respecting `Retry-After`.

## Important constraints

### Money-side double-spend trap

Direct controls real ad spend; **idempotency by ClientID is non-negotiable**. When a write call fails on network or timeout, do **not** blindly resend `add` / `update`. The first request may have reached Direct and changed state already; a blind retry will:

- create a duplicate campaign (`add` retry);
- apply a bid change twice (`Bids.set` retry on an already-set value if relative semantics are used);
- re-submit moderation that already succeeded.

Resolution before retry:

1. Look up the business key in `direct_idempotency`. If `direct_id` is present, the previous call succeeded — skip.
2. Otherwise call `get` filtered by that business key. If the object exists in Direct, store the `Id` and skip.
3. Only when neither side has a record → safe to retry `add`.

For `update` / `set`, use **absolute values** (e.g. `SearchBid: 5_000_000`, never "+10%"). Absolute payloads are idempotent under repeated retries.

### Operational constraints

- **Production writes only after a sandbox dry-run** and explicit confirmation of magnitudes. Any `add` of dozens of campaigns or `Bids.set` over thousands of keywords first runs on 1–2 elements.
- **Never log tokens or logins.** Redact `Authorization` and `Client-Login` in every sink. Store in .env / secret manager.
- **Maximum 5 parallel reports** per account. Otherwise reports are blocked and the account hits rate limits.
- **Honor `Retry-After`.** Ignoring it → 429 / IP block.
- **`delete` requires explicit confirmation.** For campaigns / groups with statistics, `archive` is the default.
- **On `error 153` (units exhausted), suspend writes** until daily reset (00:00 UTC).
- **`Use-Operator-Units: true` only from agency accounts.** From an advertiser account → rights error.
- **Sandbox data expires after 1 month of inactivity.** Do not use it as a persistent test fixture.
- **OAuth scope `direct:api`** must be requested at app issuance. Without it every request fails 52 / 506.

## Related skills

- `yandex-metrica` — web analytics, goals, ecommerce reports (conversion source for bid optimization)
- `xmlstock` — SERP / position parsing (knowing where the site sits in results)
- `mutagen` — Wordstat frequency and competition (keyword sourcing)
- `google-ads` cascade — Google Ads API (cross-platform context)
- `vk-ads` / `mytarget` cascade — VKontakte targeted advertising
- `httpx`, `nodejs` — HTTP plumbing
- `postgresql`, `redis` — persistence (idempotency keys, reports archive, dedup)
- `bullmq` — queue for Reports polling and retry

## API reference

| Resource | URL |
|---|---|
| Production endpoint | `https://api.direct.yandex.com/json/v5/{service}` |
| Sandbox endpoint | `https://api-sandbox.direct.yandex.com/json/v5/{service}` |
| Reports endpoint | `https://api.direct.yandex.com/json/v5/reports` |
| OAuth authorize | `https://oauth.yandex.ru/authorize` |
| OAuth token | `https://oauth.yandex.ru/token` |
| Official docs (EN) | `https://yandex.com/dev/direct/doc/en/` |
| Official docs (RU) | `https://yandex.ru/dev/direct/doc/ru/` |
| Result codes (EN) | `https://yandex.com/dev/direct/doc/en/concepts/result-codes` |
| Sandbox docs | `https://yandex.com/dev/direct/doc/en/concepts/sandbox` |
| Reports spec | `https://yandex.com/dev/direct/doc/en/reports/spec` |
| Units / limits | `https://yandex.com/dev/direct/doc/en/concepts/limits` |
