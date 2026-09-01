# Setup — OAuth scopes, service account, property types

## OAuth 2.0 scopes

| Scope | Access |
|---|---|
| `https://www.googleapis.com/auth/webmasters.readonly` | read-only: searchanalytics.query, sites.list/get, sitemaps.list/get, urlInspection.index.inspect |
| `https://www.googleapis.com/auth/webmasters` | full: + sites.add/delete, sitemaps.submit/delete |
| `https://www.googleapis.com/auth/indexing` | Indexing API — separate scope, JobPosting / BroadcastEvent only |

Authorization endpoints:

- Authorization endpoint: `https://accounts.google.com/o/oauth2/v2/auth`
- Token endpoint: `https://oauth2.googleapis.com/token`
- Revoke endpoint: `https://oauth2.googleapis.com/revoke`

## Authentication paths

### Path A — User OAuth (Authorization Code + refresh_token)

Use when: the GSC owner logs into your app via Google. You receive an `access_token` plus a `refresh_token` (offline access).

1. Create an OAuth client ID in Google Cloud Console: Type = **Web application** or **Desktop**, add redirect URI.
2. Redirect the user to `accounts.google.com/o/oauth2/v2/auth` with:
   - `client_id`, `redirect_uri`
   - `scope=https://www.googleapis.com/auth/webmasters.readonly`
   - `access_type=offline` — mandatory, otherwise no `refresh_token`
   - `prompt=consent` — mandatory to re-issue refresh_token if the user already consented
   - `response_type=code`
3. From the callback, exchange `code` for tokens via `POST https://oauth2.googleapis.com/token` (form-encoded: `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type=authorization_code`).
4. Persist `refresh_token` forever (Redis/PG, encrypted). `access_token` lives ~1 hour — refresh before each call.

> Testing-mode quirk: if your OAuth app is stuck in "Testing" in Google Cloud, `refresh_token` expires after 7 days. Production needs OAuth verification (branding + privacy policy URL + Google review).

### Path B — Service Account (JWT)

Use when: server-to-server with no human; you own the property or the owner agrees to add the service account email.

1. In Google Cloud Console → IAM & Admin → Service Accounts → Create. Download the JSON key.
2. **Critical**: open Search Console → property → Settings → Users and permissions → Add user. Use the service account email (`xxx@<project>.iam.gserviceaccount.com`). Role: **Restricted** (read-only API) or **Full** (sitemap submit).
3. Without step 2 every API call returns `403 Forbidden` or `404 User does not have sufficient permission for site`. A service account cannot self-grant access.
4. In code: build a JWT assertion, sign with the private key, `aud=https://oauth2.googleapis.com/token`, `scope=...`, exchange for `access_token`. Cache `access_token` for ~50 minutes.

### Domain-wide delegation (optional)

For Google Workspace orgs acting on behalf of a specific user: enable DWD in Google Admin Console, add the service account client ID with scope `webmasters.readonly`, and include `sub: user@domain.com` in the JWT. Rarely needed — adding the service account directly in GSC UI is usually enough.

## Property types

GSC supports two property types; `siteUrl` formatting depends on the type.

### URL-prefix property

- Format: `https://www.example.com/` — **mandatory trailing slash**, exact protocol, exact subdomain.
- Verification: HTML file / HTML meta / Google Analytics / Google Tag Manager / DNS TXT.
- Sees only URLs under that exact prefix. `https://www.example.com/` and `https://example.com/` are **different** properties.
- For URL Inspection, `siteUrl` must match **exactly**.

### Domain property

- Format: `sc-domain:example.com` — no protocol, no slashes.
- Verification: **DNS TXT only**.
- Aggregates ALL protocols (http/https) and ALL subdomains (www, m, blog, ...).
- Sees more impressions than any URL-prefix → data will not match across types.
- In code: `siteUrl = "sc-domain:example.com"`; URL-encoding not required (colon is safe in path after `/sites/`).

> Best practice for serious analysis: keep both a Domain property AND URL-prefix properties per protocol+subdomain — different granularities.

## Token storage and refresh

- `refresh_token` — store encrypted (libsodium / KMS); in Redis / PG; never in logs.
- `access_token` — cache for 50 minutes (slightly under the 60-minute TTL).
- On 401 — refresh and retry once; if still 401 → require user re-consent.
- On revoke (user revoked in Google Account) — refresh returns `invalid_grant`; route the user back through the OAuth flow.

## Sanity check after setup

```bash
# user OAuth — token in env
curl -H "Authorization: Bearer $TOKEN" \
  https://www.googleapis.com/webmasters/v3/sites

# service account — after adding it in GSC UI, must return the property list
# with permissionLevel siteRestrictedUser / siteFullUser, NOT siteUnverifiedUser
```

If the response is `[]` or 403 — the service account was not added. If `permissionLevel: siteUnverifiedUser` — added without a role; API will return no data.
