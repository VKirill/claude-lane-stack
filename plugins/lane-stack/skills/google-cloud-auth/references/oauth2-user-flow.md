# OAuth 2.0 Authorization Code Flow

Google OAuth 2.0 Authorization Code flow for user-facing applications. Covers both **installed app** (desktop, CLI, mobile) and **web app** variants, PKCE requirement, the full code → tokens exchange, and callback URL registration.

---

## Prerequisites

1. Create a project in [Google Cloud Console](https://console.cloud.google.com).
2. Enable the API(s) you need (e.g., "Google Analytics Data API", "Search Console API").
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
4. Configure the **OAuth consent screen** (App name, support email, scopes).
5. Choose application type:
   - **Web application** → register `https://` redirect URIs
   - **Desktop app** → redirect URI is `http://localhost:PORT` or `urn:ietf:wg:oauth:2.0:oob` (deprecated)
6. Download `client_secret_XXX.json`.

---

## Application types

### Web application flow

```
Browser                   Your Server                 Google
  |                           |                           |
  |--- GET /login ----------->|                           |
  |                           |-- redirect_uri ---------->|  Authorization URL
  |<-- redirect to Google ----|                           |
  |                                                       |
  |--- user consents ---------------------------------------->|
  |                                                       |
  |<--- redirect to your /callback?code=XXX --------------|
  |                           |                           |
  |--- GET /callback?code=XXX->|                          |
  |                           |-- POST /token (code) ---->|
  |                           |<-- {access_token,         |
  |                           |     refresh_token,        |
  |                           |     expires_in} ----------|
  |                           |                           |
  |<-- session / cookie ------|                           |
```

**Authorization URL** (redirect the user here):

```
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=YOUR_CLIENT_ID
  &redirect_uri=https%3A%2F%2Fyourapp.com%2Fcallback
  &response_type=code
  &scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fwebmasters.readonly
  &access_type=offline
  &prompt=consent
  &state=RANDOM_CSRF_TOKEN
```

`access_type=offline` → server returns a `refresh_token`.  
`prompt=consent` → forces Google to re-show the consent screen and issue a new `refresh_token` (use only when you need a fresh RT).

**Token exchange** (POST from your server):

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=AUTH_CODE_FROM_CALLBACK" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://yourapp.com/callback" \
  -d "grant_type=authorization_code"
```

Response:

```json
{
  "access_token": "ya29.a0...",
  "expires_in": 3599,
  "refresh_token": "1//0gXXXX...",
  "scope": "https://www.googleapis.com/auth/webmasters.readonly",
  "token_type": "Bearer"
}
```

Store `refresh_token` in your database. `access_token` is ephemeral — regenerate from `refresh_token`.

---

### Installed application flow (Desktop / CLI)

For CLI tools, local scripts, and desktop apps where a browser can be opened but the callback goes to localhost.

**Node.js example using `googleapis`:**

```js
import { google } from 'googleapis';
import http from 'http';
import url from 'url';
import open from 'open'; // npm install open

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  'http://localhost:3000/oauth2callback'
);

const SCOPES = [
  'https://www.googleapis.com/auth/webmasters.readonly',
  'https://www.googleapis.com/auth/analytics.readonly',
];

// Step 1: Build auth URL
const authUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  prompt: 'consent',
  scope: SCOPES,
});

console.log('Opening browser:', authUrl);
open(authUrl);

// Step 2: Temporary localhost server to capture the code
const server = http.createServer(async (req, res) => {
  const qs = new url.URL(req.url, 'http://localhost:3000').searchParams;
  const code = qs.get('code');
  if (!code) { res.end('No code'); return; }
  res.end('Auth complete. You can close this tab.');
  server.close();

  // Step 3: Exchange code for tokens
  const { tokens } = await oauth2Client.getToken(code);
  oauth2Client.setCredentials(tokens);

  // tokens.refresh_token — persist this
  console.log('refresh_token:', tokens.refresh_token);
});

server.listen(3000);
```

**Python example using `google-auth-oauthlib`:**

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",  # downloaded from Cloud Console
    scopes=SCOPES,
)

# Opens browser, local server captures callback
creds = flow.run_local_server(port=0)  # port=0 picks a random free port

# Persist tokens
token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
}
with open("tokens.json", "w") as f:
    json.dump(token_data, f)
```

---

## PKCE (Proof Key for Code Exchange)

PKCE is mandatory for installed apps and SPAs, and recommended for web apps. It prevents auth code interception attacks.

**Generate verifier and challenge:**

```python
import secrets
import hashlib
import base64

# 1. Generate a random code_verifier (43-128 chars)
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()

# 2. Compute code_challenge = BASE64URL(SHA256(code_verifier))
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
```

**Authorization URL with PKCE:**

```
https://accounts.google.com/o/oauth2/v2/auth
  ?client_id=YOUR_CLIENT_ID
  &redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback
  &response_type=code
  &scope=...
  &access_type=offline
  &code_challenge=COMPUTED_CHALLENGE
  &code_challenge_method=S256
```

**Token exchange with PKCE:**

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=AUTH_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "redirect_uri=http://localhost:8080/callback" \
  -d "grant_type=authorization_code" \
  -d "code_verifier=YOUR_ORIGINAL_CODE_VERIFIER"
```

No `client_secret` needed for public clients using PKCE.

---

## Refreshing an access token

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=STORED_REFRESH_TOKEN" \
  -d "grant_type=refresh_token"
```

Response returns a new `access_token` (and sometimes a rotated `refresh_token` — always persist the latest one).

**Python (google-auth):**

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds = Credentials(
    token=None,
    refresh_token="1//0gXXXX...",
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=SCOPES,
)

if not creds.valid:
    creds.refresh(Request())  # uses refresh_token to get a new access_token
```

---

## Redirect URI rules

| Scenario | Allowed redirect URI |
|---|---|
| Web app (production) | `https://yourapp.com/callback` (must be `https://`, no wildcards) |
| Web app (dev) | `http://localhost:PORT/callback` |
| Installed app | `http://localhost:PORT/callback` |
| Legacy OOB (deprecated) | `urn:ietf:wg:oauth:2.0:oob` — do not use for new apps |
| Custom scheme (mobile) | `com.yourapp:/oauth2redirect` |

- Redirect URIs must be registered exactly (trailing slashes matter).
- Unregistered URI → `redirect_uri_mismatch` error immediately.
- Wildcard subdomains are not supported.

---

## Consent screen: Testing vs Production

- **Testing mode** (default for new apps): refresh tokens expire after **7 days**. Only test users added in the Cloud Console can authorize.
- **Production mode**: refresh tokens do not expire from age (but can be revoked or rotated). Requires OAuth verification for sensitive/restricted scopes.
- To publish: **APIs & Services → OAuth consent screen → Publish App**.

---

## OAuth consent screen scopes configuration

Go to **OAuth consent screen → Edit app → Scopes**. Add the scopes your app uses. Scopes are categorized:

- **Non-sensitive**: basic profile, email
- **Sensitive**: most analytics/webmaster scopes — require Google review if audience is External
- **Restricted**: Admin SDK, Drive full access — require security assessment

For internal-only apps (Workspace domain, audience = Internal), sensitive scopes do not require review.

---

## Common mistakes

- `redirect_uri_mismatch` — URI in the request does not match any registered URI, including trailing slash differences
- `invalid_client` — wrong `client_id` or `client_secret`; verify you are using the correct downloaded JSON
- `invalid_grant` on first use — the auth code was already used or expired (codes expire in ~10 minutes)
- Missing `access_type=offline` → no `refresh_token` returned; subsequent calls require re-auth every hour
- `prompt=consent` on every auth → mints a new RT each time, leaving orphan tokens; use only when RT is missing
