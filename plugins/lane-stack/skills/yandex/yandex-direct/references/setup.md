# Setup — OAuth, sandbox, Client-Login

## 1. Register the application

1. Sign in at `https://oauth.yandex.ru/client/new` with the account that owns the integration.
2. Platform: "Web service" with a `Callback URI`, or "Desktop app" for manual token issuance.
3. In "Permissions", enable:
   - `direct:api` — main scope for Direct API v5 (ad management).
   - `direct:agency` — needed by agencies operating on client accounts.
4. Save `Client ID` and `Client Secret` to `.env` / secret manager. **Never commit them.**

## 2. OAuth flow

### Production: Authorization Code

```
GET https://oauth.yandex.ru/authorize?
    response_type=code&
    client_id=<CLIENT_ID>&
    state=<csrf_token>&
    force_confirm=yes
```

The user signs in with the Yandex.Direct account, presses "Allow", is redirected to `redirect_uri?code=...`.

```
POST https://oauth.yandex.ru/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=<code>&
client_id=<CLIENT_ID>&
client_secret=<CLIENT_SECRET>
```

Response:
```json
{
  "access_token": "y0_AgAAAA...",
  "refresh_token": "1:...",
  "expires_in": 31536000,
  "token_type": "bearer"
}
```

Token lifetime is up to one year. Refresh via the same endpoint with `grant_type=refresh_token`. After revocation any request returns `error_code` 1002 / 506.

### Dev: manual debug token

`https://oauth.yandex.ru/authorize?response_type=token&client_id=<CLIENT_ID>` — the token arrives in the URL fragment after redirect. Good only for prototypes / single-account work, not multi-tenant.

## 3. Client-Login for agencies

An agency account holds a token with scope `direct:agency`. By default the token operates "as agency". To target a **client** account, add:

```
Client-Login: example-client-login
```

The login is the one the client would use on `direct.yandex.ru`. To list the agency's clients call `AgencyClientsService.get` (without `Client-Login`).

### Use-Operator-Units

```
Use-Operator-Units: true
```

Charge **agency** units instead of the client's. Useful when the client has a small unit limit but the agency one is large. Works **only** from an agency context.

## 4. Sandbox

| Parameter | Production | Sandbox |
|---|---|---|
| Host | `api.direct.yandex.com` | `api-sandbox.direct.yandex.com` |
| Endpoint pattern | `/json/v5/{service}` | `/json/v5/{service}` |
| Reports | `/json/v5/reports` | `/json/v5/reports` |
| OAuth | same Yandex ID | same Yandex ID |
| UI | `direct.yandex.ru` | **none** |
| Real spend | yes | no (synthetic stats) |
| Moderation | real | synthetic / skipped |
| Data TTL | persistent | **deleted after 1 month of inactivity** |
| Reports | unlimited | **one campaign per report** |

### Creating the sandbox account

The sandbox is created **automatically** on the first call with a valid OAuth token to `api-sandbox.direct.yandex.com`. There is no separate registration — it is a mirrored virtual tier for the same Yandex ID.

First call: `Clients.get` or `Campaigns.get` (an empty list is normal). Then create a test campaign.

### Sandbox testing checklist

- [ ] OAuth token works against the sandbox host
- [ ] `Campaigns.add` creates a campaign; `Campaigns.get` returns it
- [ ] `Ads.add` → `Ads.moderate` → state moves to `ACCEPTED` within seconds
- [ ] `Reports` with `processingMode: online` returns TSV
- [ ] `Reports` with `processingMode: offline` returns `201 Created` → polling 202 → 200
- [ ] `error 153` (units exhausted) can be simulated with a large batch

## 5. Environment variables (recommended layout)

```bash
# Production
YANDEX_DIRECT_BASE_URL=https://api.direct.yandex.com
YANDEX_DIRECT_OAUTH_TOKEN=y0_AgAAAA...
YANDEX_DIRECT_CLIENT_LOGIN=example-client  # empty when operating on the own account

# Sandbox (separate config)
YANDEX_DIRECT_SANDBOX_BASE_URL=https://api-sandbox.direct.yandex.com

# Optional
YANDEX_DIRECT_USE_OPERATOR_UNITS=false
YANDEX_DIRECT_ACCEPT_LANGUAGE=en
YANDEX_DIRECT_LOCALE=RUB
YANDEX_DIRECT_TIMEOUT_SEC=120
YANDEX_DIRECT_REPORTS_MAX_PARALLEL=5
```

## 6. Minimal smoke test

```bash
curl -sS -X POST https://api-sandbox.direct.yandex.com/json/v5/campaigns \
  -H "Authorization: Bearer $YANDEX_DIRECT_OAUTH_TOKEN" \
  -H "Accept-Language: en" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "method": "get",
    "params": {
      "SelectionCriteria": {},
      "FieldNames": ["Id", "Name", "State", "Status", "Type"]
    }
  }' | jq
```

Expected: `{"result": {"Campaigns": [...]}}` or empty array for a new sandbox.

## 7. Production rollout checklist

- [ ] Sandbox smoke passed with identical request bodies
- [ ] OAuth refresh is implemented and tested
- [ ] `Client-Login` is set by middleware, never by business logic
- [ ] Logging redacts `Authorization` and `Client-Login`
- [ ] `Units` header parsed every response; alert at `remaining / daily_limit < 0.2`
- [ ] Partial errors handled (iterate over `AddResults` / `UpdateResults`)
- [ ] Reports polling honors `Retry-After`, max 5 parallel jobs
- [ ] `add` duplicates are blocked by a client-side idempotency key
- [ ] Money fields convert micro ↔ rubles at exactly one boundary
- [ ] Kill switch — a global "stop all writes" flag is wired
