---
name: google-cloud-auth
description: "[RU: oauth google, авторизация гугл, service account, sa key, refresh token, invalid_grant, adc, google cloud auth] Google auth for all Google APIs — OAuth 2.0, Service Account JWT, ADC. Use when: auth setup, invalid_grant, SA key, refresh token, PKCE, gcloud ADC. SKIP: GA4 (→ga4-data-api); GSC (→google-search-console); GTM (→google-tag-manager)."
stacks:
  - google-cloud-auth
  - oauth2
  - python
  - nodejs
tags:
  - google
  - oauth
  - auth
  - service-account
  - adc
  - refresh-token
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (June 2026)

**Primary pins:**
- google-auth-library (Node): `9.x`
- google-auth (Python): `2.x`
- Node.js: `24.x (Active LTS)`
- Python: `3.14.x`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-06-11

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. This is the single source of truth for all Google API authentication patterns. Read the section you need, then follow the link to the relevant reference file.

## Use this skill when

- Setting up OAuth 2.0 Authorization Code flow (installed app or web app) for any Google API — GSC, GA4, GTM, YouTube, Drive
- Configuring a Service Account for server-to-server (backend) access: creating SA, downloading key.json, granting access
- Understanding Application Default Credentials (ADC) and `GOOGLE_APPLICATION_CREDENTIALS` env var discovery chain
- Diagnosing `invalid_grant`, `token_has_been_expired_or_revoked`, or `401 Unauthorized` on a previously working token
- Choosing between OAuth user flow and Service Account for a given use case
- Implementing offline access (`access_type=offline`) and `prompt=consent` to force a new refresh token
- Configuring PKCE for installed apps or web apps that cannot store a client secret securely
- Setting up domain-wide delegation (DWD) — impersonating G Suite users via a Service Account
- Reviewing minimum scopes needed for a specific Google API (GSC readonly, GA4 readonly, GTM publish, YouTube, etc.)
- Auditing OAuth consent screen configuration (redirect URIs, app verification, testing vs production mode)

## Do not use this skill when

- You need to make GA4 Data API calls — auth is covered in context; load `ga4-data-api` for request shape, quotas, and FilterExpression DSL
- You need to query Google Search Console data — load `google-search-console` for dimensions, filters, and URL Inspection
- You need GTM container / tag management — load `google-tag-manager` for resource hierarchy and CRUD operations
- You need Yandex OAuth (Yandex Metrika, Direct, Webmaster) — different provider; load `yandex-metrica`, `yandex-direct`, or `yandex-webmaster`
- You need general HTTP transport patterns (retries, backoff, connection pooling) — load `httpx` (Python) or `nodejs`

## Purpose

Google Cloud Authentication provides the credential foundation for every Google API call. Three patterns cover all use cases: OAuth 2.0 Authorization Code flow for end-user consent (installed apps, web apps), Service Account JWT bearer for backend scripts with no user interaction, and Application Default Credentials (ADC) for environments where credentials are pre-injected (Cloud Run, GKE, Compute Engine, gcloud CLI).

This skill is **high-stakes** because a wrong auth choice or misconfiguration fails silently — the API returns 401 or 403 with a reason that can be mistaken for a permission issue when it is actually a stale token, missing scope, or a refresh token rotation that was not handled. Every downstream Google skill (GA4, GSC, GTM, YouTube) depends on this skill for its credential bootstrap; errors here block all of them.

## Capabilities

### OAuth 2.0 Authorization Code flow

OAuth 2.0 is the right choice whenever a real Google user must grant consent — for example, when you need to access a Search Console property that the user owns, or read GA4 data on behalf of a paying customer. The flow has two sub-variants: **web application** (client secret stored server-side, redirect URI is an `https://` URL) and **installed application** (client secret is embedded in the app binary and treated as non-confidential; redirect URI is `urn:ietf:wg:oauth:2.0:oob` or `http://localhost:PORT`). Both variants produce the same token pair — `access_token` (1-hour TTL) and `refresh_token` (long-lived). PKCE (`code_challenge` + `code_verifier`) is mandatory for public clients (installed apps, SPAs) and recommended for web apps. Redirect URIs must be registered in the Cloud Console OAuth client; unregistered URIs return `redirect_uri_mismatch` immediately.

> Full reference: [references/oauth2-user-flow.md](references/oauth2-user-flow.md)

### Service Account JWT bearer

A Service Account (SA) is a Google-managed identity that authenticates with a key file rather than a user password. The auth library creates a signed JWT assertion, exchanges it for an access token at `https://oauth2.googleapis.com/token`, and re-exchanges automatically on expiry. This pattern requires: (1) the SA created in Cloud Console + key.json downloaded, (2) the relevant API enabled in the Cloud project, and (3) the SA email granted access on the target resource — for GA4 via Property Access Management, for GSC via the Search Console UI, for GTM via the GTM account/container settings. Domain-wide delegation (DWD) extends this by allowing the SA to impersonate any user in a G Suite domain; it requires a Super Admin to authorize the SA's client ID in the Admin Console.

> Full reference: [references/service-account.md](references/service-account.md)

### Application Default Credentials (ADC)

ADC is the zero-config credential discovery chain used by all Google client libraries (`google-auth`, `googleapis`, `google-auth-library`). When code calls `google.auth.default()` or `new GoogleAuth()`, the library walks a discovery chain: (1) `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a key.json, (2) `gcloud auth application-default login` credentials at `~/.config/gcloud/application_default_credentials.json`, (3) the workload identity / metadata server on GCP (Cloud Run, GKE, Compute Engine). ADC is the right pattern for cloud-native services — avoids key file management entirely on GCP. On developer machines, `gcloud auth application-default login` bootstraps the chain in one command.

> Full reference: [references/adc.md](references/adc.md)

### Scopes catalog

Google APIs use OAuth scopes to limit what a token can do. Always request minimum scopes — over-requesting triggers a broader OAuth consent screen that users are more likely to reject. The scope is set at the time the `refresh_token` is minted; changing scope requires a new authorization cycle (or `prompt=consent` to force re-consent on the same redirect). Different APIs use disjoint scope namespaces: `webmasters.*` for GSC, `analytics.*` for GA4, `tagmanager.*` for GTM, `youtube.*` / `yt-analytics.*` for YouTube.

> Full reference: [references/scopes-catalog.md](references/scopes-catalog.md)

### Refresh token lifecycle

An `access_token` expires after 3600 seconds. The `refresh_token` is long-lived but not eternal — it can be revoked by the user, expire if the app stays in "Testing" mode (7-day refresh token expiry), rotate if the project has enabled refresh token rotation, or be invalidated when `prompt=consent` mints a new one. The canonical error is `invalid_grant`. Recovery path: detect `invalid_grant` in the error response, delete the stored token, and redirect the user to the authorization URL with `access_type=offline&prompt=consent` to get a fresh pair. Tokens must be persisted in a database or secrets manager, never in files committed to git.

> Full reference: [references/refresh-tokens.md](references/refresh-tokens.md)

### Error patterns

Google API auth errors follow a predictable taxonomy. **401 Unauthorized** means the access token is absent, expired, or malformed — always attempt a token refresh before surfacing an error to the user. **403 Forbidden** means the token is valid but the identity lacks permission — check scopes first, then check resource-level grants (SA not added to GA4/GSC, wrong GTM role). **429 Too Many Requests** on the token endpoint means the refresh loop is running too fast — add exponential backoff with jitter. **500/503** on the token endpoint are transient — retry with backoff. The error body JSON distinguishes reasons (`invalid_grant`, `access_denied`, `admin_policy_enforced`, `org_internal`) that map to different recovery actions.

> Full reference: [references/errors.md](references/errors.md)

## Behavioral Traits

- Always choose the minimum scope set — one scope per API, `readonly` unless writes are confirmed required
- Always persist refresh tokens in a database or secrets manager; never in `.env` files committed to git
- Always handle `invalid_grant` with a re-authorization redirect, not a retry loop — retrying does not fix a revoked token
- Always set `access_type=offline` and `prompt=consent` when the intent is to get a refresh token that survives beyond the browser session
- Always verify the `GOOGLE_APPLICATION_CREDENTIALS` path resolves before running a service in production
- Always enable the specific API (e.g., Google Analytics Data API, Tag Manager API) in the Cloud Console project — having a valid key file is necessary but not sufficient
- For Service Accounts, always confirm the SA email has been granted access at the resource level (not just IAM project level) before debugging API calls

## Important Constraints

- NEVER store key.json files in git repositories — use Secret Manager, Vault, or environment variables injected at runtime
- NEVER request scopes beyond what the current feature requires — re-request with a new `prompt=consent` when scope expands
- NEVER reuse a refresh token after receiving `invalid_grant` — the token is permanently invalidated; the only recovery is re-authorization
- NEVER implement domain-wide delegation without a Super Admin reviewing and approving the SA client ID in the Admin Console
- NEVER call `prompt=consent` unconditionally on every auth request — only when a refresh token is missing or `invalid_grant` is received
- ALWAYS use PKCE for installed apps and SPAs — omitting it on public clients is a security vulnerability
- ALWAYS rotate SA keys on a schedule (recommended: every 90 days) and immediately on suspected compromise
- ALWAYS check that the correct API is enabled in the Cloud Console project — a missing API enablement produces a misleading 403 or "API not enabled" error

## Related Skills

- `ga4-data-api` — GA4 Data API reporting (auth bootstrap is covered there; load this skill for request shape, quotas, FilterExpression)
- `google-search-console` — GSC search analytics, URL Inspection, Sitemaps (depends on this skill for credential setup)
- `google-tag-manager` — GTM container / tag management (depends on this skill for credential bootstrap)
- `yandex-metrica` — Russian analytics analogue; separate Yandex OAuth, not Google OAuth
- `yandex-webmaster` — Yandex Webmaster API; separate Yandex OAuth
- `httpx` — Python HTTP transport for raw REST calls with bearer tokens
- `nodejs` — Node.js runtime patterns for googleapis library and raw fetch with auth headers
- `postgresql` — persistence layer for refresh tokens, token expiry, and audit logs
- `redis` — short-lived token caching and rate-limit counters for auth endpoints

## API Reference

| Topic | File |
|---|---|
| OAuth 2.0 Authorization Code flow — installed app, web app, PKCE, code exchange | [references/oauth2-user-flow.md](references/oauth2-user-flow.md) |
| Service Account JWT bearer — key.json, domain-wide delegation, when to prefer SA | [references/service-account.md](references/service-account.md) |
| Application Default Credentials — discovery chain, gcloud, metadata server | [references/adc.md](references/adc.md) |
| Scopes catalog — minimum scopes for GSC, GA4, GTM, YouTube, Drive | [references/scopes-catalog.md](references/scopes-catalog.md) |
| Refresh token lifecycle — rotation, invalid_grant, offline access, prompt=consent | [references/refresh-tokens.md](references/refresh-tokens.md) |
| Error patterns — 401/403/429/500 shapes, retry policy, backoff windows | [references/errors.md](references/errors.md) |
