# Auth Error Patterns

Taxonomy of errors from Google OAuth and Google API endpoints, with error JSON shapes, root causes, and retry / recovery policies.

---

## Error JSON shapes

### Token endpoint errors (`https://oauth2.googleapis.com/token`)

```json
{
  "error": "invalid_grant",
  "error_description": "Token has been expired or revoked."
}
```

```json
{
  "error": "invalid_client",
  "error_description": "The OAuth client was not found."
}
```

```json
{
  "error": "access_denied",
  "error_description": "The caller does not have permission"
}
```

### Google API endpoint errors

```json
{
  "error": {
    "code": 401,
    "message": "Request had invalid authentication credentials. Expected OAuth 2 access token, login cookie or other valid authentication credential.",
    "status": "UNAUTHENTICATED",
    "errors": [
      {
        "message": "Invalid Credentials",
        "domain": "googleapis.com",
        "reason": "authError",
        "location": "Authorization",
        "locationType": "header"
      }
    ]
  }
}
```

```json
{
  "error": {
    "code": 403,
    "message": "The caller does not have permission",
    "status": "PERMISSION_DENIED",
    "errors": [
      {
        "message": "User does not have sufficient permission for site 'https://example.com/'",
        "domain": "googleapis.com",
        "reason": "forbidden"
      }
    ]
  }
}
```

```json
{
  "error": {
    "code": 429,
    "message": "Quota exceeded for quota metric",
    "status": "RESOURCE_EXHAUSTED",
    "errors": [
      {
        "domain": "usageLimits",
        "reason": "quotaExceeded"
      }
    ]
  }
}
```

---

## 401 Unauthorized — authentication failure

**What it means:** The access token is absent, expired, or malformed. The request did not authenticate.

| `reason` | Root cause | Fix |
|---|---|---|
| `authError` | Access token expired or invalid | Refresh via `refresh_token` grant |
| `invalid_credentials` | Wrong or missing `Authorization` header | Check header format: `Bearer <access_token>` |
| (no reason) | Token endpoint returned an opaque 401 | Retry once; if repeats, re-authorize |

**Retry policy:** Always attempt a single token refresh before surfacing the error. If refresh succeeds, replay the original request. If refresh returns `invalid_grant`, do not retry — require re-authorization.

**Python recovery:**
```python
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

def call_with_refresh(service_fn, creds):
    try:
        return service_fn()
    except HttpError as e:
        if e.status_code == 401:
            try:
                creds.refresh(Request())
                return service_fn()  # one retry after refresh
            except RefreshError:
                raise NeedsReauthorization()
        raise
```

---

## 403 Forbidden — authorization failure

**What it means:** The token is valid and authenticated, but the identity lacks permission. A 403 always means "identity known, access denied" — not an auth token problem.

| `reason` | Root cause | Fix |
|---|---|---|
| `forbidden` | Service account / user not added to resource | Add SA email to GA4/GSC/GTM resource; add user to property |
| `insufficientPermissions` | Token scope too narrow for the operation | Re-authorize with the required scope; use `prompt=consent` |
| `accessNotConfigured` | API not enabled in Cloud project | `gcloud services enable APINAME.googleapis.com` |
| `SERVICE_DISABLED` | Same as above, different error shape | Enable the API in Cloud Console |
| `admin_policy_enforced` | Workspace admin blocked external apps | User's org admin must allow the app |
| `org_internal` | App limited to internal Workspace users | Change OAuth consent screen audience, or use an internal account |

**Do not retry a 403.** It is a permissions issue — retrying with the same credentials will not succeed. Fix the underlying permission first.

**Checklist when you see 403:**
1. Is the correct API enabled in the Cloud Console project?
2. Is the SA email (or OAuth user) added at the resource level (GA4 Property Access Management, GSC UI, GTM account)?
3. Does the scope in the token match what the operation requires?
4. Is `status: PERMISSION_DENIED` — that is a resource-level issue. Is it `accessNotConfigured` — that is API enablement.

---

## 429 Too Many Requests — quota exhausted

**What it means:** Rate limit or quota exceeded. Two sub-types require different handling.

| `reason` | Scope | Reset window | Action |
|---|---|---|---|
| `quotaExceeded` | Per-project or per-property daily quota | Daily (usually Pacific midnight) | Stop; wait for reset; reduce request volume |
| `userRateLimitExceeded` | Per-user QPM | 1 minute | Exponential backoff |
| `rateLimitExceeded` | Global QPM | Seconds | Exponential backoff |
| `dailyLimitExceeded` | Per-day cap (e.g. URL Inspection 2000/day) | Daily | Stop all requests until next day |

**Exponential backoff with jitter:**

```python
import time
import random
from googleapiclient.errors import HttpError

def with_backoff(fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as e:
            if e.status_code != 429:
                raise
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"429 — waiting {wait:.1f}s (attempt {attempt + 1})")
            time.sleep(wait)
```

**Node.js with backoff:**

```js
async function withBackoff(fn, maxRetries = 5) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (err.code !== 429 || attempt === maxRetries - 1) throw err;
      const wait = (2 ** attempt + Math.random()) * 1000;
      console.log(`429 — waiting ${(wait / 1000).toFixed(1)}s`);
      await new Promise(resolve => setTimeout(resolve, wait));
    }
  }
}
```

**Backoff windows:**

| Quota type | Base wait | Max wait | Jitter |
|---|---|---|---|
| QPM (short-window) | 1s | 64s | ±1s |
| Daily quota | Until next UTC/PT midnight | — | None — just stop |

For `dailyLimitExceeded`, no amount of retries will help until the quota resets. Log the error, stop the worker, and alert.

---

## 500 / 503 — server errors

**What it means:** Google's servers encountered a transient error. These are not caused by the client.

| Code | Name | Retry? |
|---|---|---|
| 500 | Internal Server Error | Yes — up to 3 times with backoff |
| 502 | Bad Gateway | Yes — up to 3 times |
| 503 | Service Unavailable | Yes — up to 3 times with backoff |
| 504 | Gateway Timeout | Yes — once; if repeats, reduce request scope |

**Retry policy for 5xx:**

```python
RETRYABLE = {500, 502, 503, 504}

def with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as e:
            if e.status_code not in RETRYABLE or attempt == max_retries - 1:
                raise
            time.sleep((2 ** attempt) + random.uniform(0, 0.5))
```

Do not retry more than 3 times for 5xx — if Google's servers are consistently down, retrying indefinitely worsens the situation.

---

## Token endpoint errors

### `invalid_grant`

```json
{ "error": "invalid_grant", "error_description": "..." }
```

Causes:
- Refresh token expired (Testing mode, 7-day limit)
- Refresh token revoked by user
- Auth code already used (codes are single-use)
- System clock skew > 5 minutes (JWT `iat` validation fails)
- Refresh token rotation: old RT used after a new RT was issued

**Do not retry.** Delete the stored token and redirect the user to re-authorize.

### `invalid_client`

```json
{ "error": "invalid_client", "error_description": "The OAuth client was not found." }
```

Causes: wrong `client_id` or `client_secret`. Check that the downloaded `client_secret.json` matches the OAuth client in Cloud Console.

### `redirect_uri_mismatch`

```json
{ "error": "redirect_uri_mismatch" }
```

Cause: The `redirect_uri` in the request does not match any registered URI. Register the exact URI in Cloud Console (including trailing slash, protocol, and port).

### `access_denied`

```json
{ "error": "access_denied" }
```

Causes: User clicked "Cancel" on the consent screen, or the Workspace admin has blocked the app (`admin_policy_enforced`). Cannot be recovered by the application — requires user or admin action.

---

## Clock skew — JWT validation failure

Service Account JWT assertions have `iat` (issued at) and `exp` (expiry). If the server clock is more than 5 minutes off from Google's servers, the JWT is rejected with `invalid_grant` or `BadRequest`.

**Check clock sync:**
```bash
timedatectl status          # Linux
date -u                     # Compare with: curl -s https://timeapi.io/api/time/current/zone?timeZone=UTC | jq .dateTime
```

**Fix:**
```bash
# Ubuntu/Debian
sudo systemctl enable --now systemd-timesyncd
timedatectl set-ntp true
```

---

## Error decision tree

```
API call fails
│
├── 401? → refresh access_token
│         ├── refresh succeeds? → retry API call
│         └── refresh fails with invalid_grant? → delete RT, re-authorize user
│
├── 403? → check root cause (do NOT retry)
│         ├── insufficientPermissions → wrong scope; re-authorize with correct scope
│         ├── forbidden → SA/user not in resource permissions
│         └── accessNotConfigured → enable API in Cloud Console
│
├── 429? → check reason
│         ├── quotaExceeded / dailyLimitExceeded → stop; wait for reset
│         └── userRateLimitExceeded / rateLimitExceeded → exponential backoff
│
├── 500/502/503/504? → exponential backoff, max 3 retries
│
└── invalid_grant (token endpoint) → delete RT, re-authorize user (no retry)
```
