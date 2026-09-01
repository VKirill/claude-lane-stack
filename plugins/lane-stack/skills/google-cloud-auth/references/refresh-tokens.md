# Refresh Token Lifecycle

Refresh tokens are the persistent credential in OAuth 2.0. This reference covers their lifecycle, when they rotate or expire, `invalid_grant` recovery, offline access configuration, and forcing a new refresh token with `prompt=consent`.

---

## Token pair overview

| Token | Lifetime | Purpose |
|---|---|---|
| `access_token` | ~3600 seconds (1 hour) | Bearer token sent in `Authorization` header |
| `refresh_token` | Long-lived (see below) | Exchanges for new `access_token` via `/token` endpoint |
| `id_token` | ~3600 seconds | JWT with user identity (OpenID Connect; not needed for API auth) |

Access tokens cannot be refreshed — only replaced via the `refresh_token` grant. Refresh tokens do not expire on a fixed schedule but are invalidated by specific events (see below).

---

## Obtaining a refresh token

A `refresh_token` is only returned when **both** conditions are true:

1. `access_type=offline` is included in the authorization URL
2. The authorization URL results in a new consent (first-time or `prompt=consent`)

If `access_type` is omitted (or set to `online`), the token endpoint never returns `refresh_token`. This is the most common cause of "I got an `access_token` but no `refresh_token`".

**Authorization URL with offline access:**
```
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=CLIENT_ID
  &redirect_uri=https://yourapp.com/callback
  &response_type=code
  &scope=SCOPES
  &access_type=offline
  &prompt=consent
```

`prompt=consent` is required the second time you authorize the same user for the same client — Google does not return a second refresh token unless consent is re-shown.

---

## When refresh tokens are invalidated

| Event | What happens | Recovery |
|---|---|---|
| User revokes access | Google immediately invalidates the RT | Re-authorize the user |
| `prompt=consent` mints a new RT | The old RT from the same authorization is invalidated | Store only the latest RT |
| App is in "Testing" mode | RT expires after **7 days** | Publish the app or add test user, then re-authorize |
| RT unused for 6 months | Google invalidates it | Re-authorize the user |
| Google detects suspicious activity | RT may be invalidated proactively | User receives email; re-authorize |
| User changes password | May invalidate dependent RTs | Re-authorize |
| RT rotation enabled (project setting) | Each use returns a new RT; old RT invalidated after use | Always store the latest RT from every token response |
| Service Account key deleted | Tokens signed by that key stop working | Create new key + re-authorize |

---

## Using a refresh token to get a new access token

**curl:**
```bash
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=CLIENT_ID" \
  -d "client_secret=CLIENT_SECRET" \
  -d "refresh_token=1//0gSTORED_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

Response:
```json
{
  "access_token": "ya29.a0...",
  "expires_in": 3599,
  "scope": "https://www.googleapis.com/auth/analytics.readonly",
  "token_type": "Bearer"
}
```

**Note:** The token endpoint may also return a new `refresh_token` in this response (when rotation is enabled). Always check for `refresh_token` in the response and update your stored value if present.

---

## Python — automatic refresh with google-auth

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import time

def get_valid_credentials(stored: dict) -> Credentials:
    """Return valid credentials, refreshing if expired."""
    creds = Credentials(
        token=stored.get("access_token"),
        refresh_token=stored["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=stored["client_id"],
        client_secret=stored["client_secret"],
        scopes=stored["scopes"],
    )
    if not creds.valid:
        creds.refresh(Request())
        # Persist updated access_token (and possibly new refresh_token)
        stored["access_token"] = creds.token
        if creds.refresh_token:
            stored["refresh_token"] = creds.refresh_token
        save_to_db(stored)
    return creds
```

`creds.valid` is `False` when the token is expired or absent. `.refresh(Request())` exchanges the stored `refresh_token` for a new `access_token`.

---

## Node.js — automatic refresh with googleapis

```js
import { google } from 'googleapis';

async function getAuthClient(stored) {
  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.GOOGLE_REDIRECT_URI,
  );

  oauth2Client.setCredentials({
    access_token: stored.accessToken,
    refresh_token: stored.refreshToken,
  });

  // googleapis refreshes automatically when access_token expires
  // Listen for token updates to persist them
  oauth2Client.on('tokens', (tokens) => {
    if (tokens.refresh_token) {
      // Rotation: save new refresh token
      stored.refreshToken = tokens.refresh_token;
    }
    stored.accessToken = tokens.access_token;
    saveToDb(stored);
  });

  return oauth2Client;
}
```

---

## Handling `invalid_grant`

`invalid_grant` is the canonical error for an invalidated or expired refresh token.

**Error response:**
```json
{
  "error": "invalid_grant",
  "error_description": "Token has been expired or revoked."
}
```

Or:
```json
{
  "error": "invalid_grant",
  "error_description": "Bad Request"
}
```

**Recovery flow:**

```python
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request

def safe_refresh(creds, db, user_id):
    try:
        creds.refresh(Request())
        db.update_token(user_id, access_token=creds.token,
                        refresh_token=creds.refresh_token)
        return creds
    except RefreshError as e:
        if "invalid_grant" in str(e):
            # Token permanently invalidated — cannot retry
            db.delete_token(user_id)
            raise NeedsReauthorization(user_id) from e
        raise  # Other errors (network, 500) — let caller handle
```

**Do not retry `invalid_grant`** — retrying does not un-revoke a token. The only fix is re-authorization via the full OAuth flow with `prompt=consent`.

---

## Preventing `invalid_grant` issues

1. **Publish the app.** Testing mode = 7-day RT expiry. Fix: OAuth consent screen → Publish App.
2. **Avoid multiple simultaneous refresh calls.** If two threads refresh at the same time and rotation is enabled, one will get `invalid_grant` from the rotated-away token. Use a mutex or distributed lock.
3. **Persist the latest RT after every refresh.** When rotation is enabled, the old RT is immediately invalidated after the first use.
4. **Do not call `prompt=consent` unless needed.** Every call mints a new RT and invalidates the old one — if you don't save the new RT, you lose the user's access.
5. **Store RT in the database with created_at timestamp.** When `invalid_grant` fires, check age — if > 6 months unused, expected.

---

## Token storage patterns

**Correct: PostgreSQL with encryption**

```sql
CREATE TABLE oauth_tokens (
  user_id        BIGINT PRIMARY KEY,
  access_token   TEXT,              -- short-lived, ok to store plaintext
  refresh_token  TEXT NOT NULL,     -- encrypt at rest (pgcrypto or app-level)
  scopes         TEXT[],
  expires_at     TIMESTAMPTZ,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
```

**Correct: environment variable for single-user scripts**

```bash
export GOOGLE_REFRESH_TOKEN="1//0gXXXX..."
```

**Never:**
- `.env` files committed to git
- `tokens.json` in the project root
- Hardcoded in source code
- Shared across users (each user needs their own RT)

---

## Refresh token rotation

Some Google Workspace / Cloud projects enable refresh token rotation (one-time use). When enabled:

- Each `refresh_token` grant returns a new `refresh_token` in the response
- The old `refresh_token` is immediately invalidated
- If you don't save the new RT, you permanently lose access

Check if rotation is enabled: test the token endpoint — if the response includes `refresh_token`, rotation is active for this project.

**Always store the `refresh_token` from every token response, even on refresh calls.**

---

## `prompt=consent` — force new refresh token

Use `prompt=consent` only when:

1. The stored refresh token was lost and you need a fresh one
2. You are expanding the scope set and need re-consent
3. Switching to a new OAuth client (changed `client_id`)

Do not use it on every auth — it invalidates the previous refresh token and creates orphan tokens if the new one is not captured.

```
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=CLIENT_ID
  &redirect_uri=REDIRECT_URI
  &response_type=code
  &scope=SCOPES
  &access_type=offline
  &prompt=consent   ← forces re-consent + new refresh token
```
