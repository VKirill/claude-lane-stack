# Yandex.Webmaster — OAuth setup and authentication

## Endpoints

| Service | URL |
|---|---|
| Webmaster API base | `https://api.webmaster.yandex.net/v4/` |
| OAuth authorize | `https://oauth.yandex.com/authorize` |
| OAuth token | `https://oauth.yandex.com/token` |
| OAuth dashboard | `https://oauth.yandex.com` |

HTTPS only. JSON by default (XML via `Accept: application/xml`), UTF-8.

## Step 1. Register an app

1. Open [oauth.yandex.com](https://oauth.yandex.com) → "Create new application".
2. Name, icon (optional), description.
3. **Platform**: "Web services" → set `Redirect URI` (e.g. `https://yourapp.com/oauth/callback`).
4. **Scopes** for Webmaster:
   - `webmaster:hostinfo` — read site info, analytics
   - `webmaster:verify` — manage verification, add/remove sites
5. Save → receive `client_id` and `client_secret`.

> Verify against current docs: exact scope strings — the dashboard may label them in localized form; the OAuth scope values themselves should be cross-checked there.

## Step 2. Authorization Code Flow

### 2.1. Redirect the user to authorize

```
https://oauth.yandex.com/authorize?
  response_type=code
  &client_id=<CLIENT_ID>
  &redirect_uri=<URL_ENCODED_REDIRECT_URI>
  &state=<CSRF_TOKEN>
```

After login + consent Yandex redirects to `redirect_uri?code=<AUTHORIZATION_CODE>&state=<CSRF_TOKEN>`.

**CSRF**: always pass `state` and verify on return.

### 2.2. Exchange code for access_token

```http
POST https://oauth.yandex.com/token HTTP/1.1
Host: oauth.yandex.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=<AUTHORIZATION_CODE>
&client_id=<CLIENT_ID>
&client_secret=<CLIENT_SECRET>
```

Alternative (RFC 6749): credentials via `Authorization: Basic <base64(client_id:client_secret)>`.

**Response 200**:

```json
{
  "access_token": "y0_AgAAAAA...",
  "expires_in": 31536000,
  "refresh_token": "1:1234567890:abc...",
  "token_type": "bearer"
}
```

- `expires_in` — seconds until expiry (often ~1 year for long-lived tokens, **less** for restricted scopes).
- `refresh_token` — for renewal; **persist it**.
- `token_type` is formally `bearer`, but Yandex expects the literal prefix `OAuth ` in the Authorization header (see below).

## Step 3. Using the token

```http
GET /v4/user HTTP/1.1
Host: api.webmaster.yandex.net
Authorization: OAuth y0_AgAAAAA...
Accept: application/json
```

**CRITICAL**: prefix is `OAuth`, **not** `Bearer`. `Bearer` returns 401 `INVALID_OAUTH_TOKEN`.

## Step 4. Refresh token

```http
POST https://oauth.yandex.com/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=<REFRESH_TOKEN>
&client_id=<CLIENT_ID>
&client_secret=<CLIENT_SECRET>
```

Response: new `access_token` plus new `refresh_token` (Yandex rotates refresh tokens — the old one stops working). Persist the new pair transactionally immediately.

## When to refresh

- **Reactively**: on 401 `INVALID_OAUTH_TOKEN` try refresh, then retry the request.
- **Proactively**: a cron job that refreshes 7 days before `expires_at = issued_at + expires_in`. Reduces the chance of 401 mid-batch.

## Fetching user_id

After getting the token — first call:

```http
GET /v4/user HTTP/1.1
Authorization: OAuth <token>
```

```json
{ "user_id": 1234567 }
```

Persist `user_id`, use in every `/v4/user/{user-id}/...` path.

## Credential storage

| What | Where | Note |
|---|---|---|
| `client_id` | env var / config | public-ish but do not ship in JS bundles |
| `client_secret` | env var / secrets manager | **NEVER** in code / git |
| `access_token` | secrets manager / encrypted DB | refresh on 401 |
| `refresh_token` | secrets manager / encrypted DB | persist on every refresh |
| `user_id` | DB | one per token, stable |
| `expires_at` | DB | `issued_at + expires_in` (UTC) |

## Multi-tenant scenario

Each end-user of your service runs their own OAuth flow with their own `(access_token, refresh_token, user_id)`. Hosts of different users do not intersect by `user_id`, but the same physical site can be verified by several users — `host_id` will be identical.

## Token revocation

The user can revoke the token at [yandex.com/id/profile](https://yandex.com/id/profile). After that every API request → 401. Detect, wipe the token, prompt re-authorization. Refresh against a revoked token returns 400 `invalid_grant`.

## Verify against current docs

- Exact scope strings (`webmaster:hostinfo` vs `webmaster:verify` — may be renamed in dashboard)
- Maximum `expires_in` for long-lived tokens (historically up to 1 year)
- Refresh-token rotation behavior (old token revoked vs kept alive)
