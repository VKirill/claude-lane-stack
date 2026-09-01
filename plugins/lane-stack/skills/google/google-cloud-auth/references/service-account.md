# Service Account JWT Bearer Flow

Service Accounts (SA) enable server-to-server Google API access with no user interaction. The auth library signs a JWT assertion and exchanges it for a short-lived access token. This reference covers key.json setup, the JWT bearer flow, domain-wide delegation, and guidance on when to prefer SA over OAuth.

---

## When to prefer Service Account over OAuth

| Scenario | Prefer |
|---|---|
| Backend script, cron job, CI/CD pipeline | Service Account |
| Cloud function / Cloud Run with no user session | Service Account (+ ADC) |
| User-owned resource requiring consent (user's GSC property) | OAuth user flow |
| Data access for your own GA4/GSC/GTM properties | Service Account |
| Acting on behalf of a G Suite user | Service Account + DWD |
| OAuth app where refresh tokens already exist | OAuth (keep existing) |

The key rule: if a human must grant ongoing consent, OAuth. If a machine owns the resource or is granted access by an admin, Service Account.

---

## Setting up a Service Account

### Step 1 — Create the SA in Cloud Console

```bash
# Using gcloud CLI
gcloud iam service-accounts create my-seo-sa \
  --description="SEO automation SA" \
  --display-name="SEO Automation"

# List SAs in the project
gcloud iam service-accounts list
```

Or: **Cloud Console → IAM & Admin → Service Accounts → Create Service Account**.

### Step 2 — Download key.json

```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=my-seo-sa@MY_PROJECT.iam.gserviceaccount.com
```

`key.json` structure:

```json
{
  "type": "service_account",
  "project_id": "my-project",
  "private_key_id": "abc123",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "client_email": "my-seo-sa@my-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

**Never commit this file to git.** Store it in Secret Manager or as an env var.

### Step 3 — Enable APIs in the Cloud project

```bash
gcloud services enable analyticsdata.googleapis.com
gcloud services enable webmasters.googleapis.com
gcloud services enable tagmanager.googleapis.com
gcloud services enable analytics.googleapis.com
```

Without enabling, the SA gets `403 SERVICE_DISABLED`.

### Step 4 — Grant SA access at the resource level

| API | Where to grant | Steps |
|---|---|---|
| GA4 | GA4 Admin → Property → Property Access Management | Add SA email, role = Viewer (read) or Analyst (write/annotate) |
| GSC | Search Console → Settings → Users and permissions | Add SA email, role = Restricted or Full |
| GTM | Tag Manager → Admin → Account → User Management | Add SA email, choose permission level |
| YouTube | Channel-level — YouTube Analytics only | SA must be granted via the analytics service |
| Drive | Share folder/file with SA email | Like sharing with a normal user |

A key file is necessary but not sufficient — the SA email must have explicit resource-level access.

---

## JWT bearer flow (how it works under the hood)

The auth library creates a signed JWT assertion and exchanges it for an access token. You rarely need to do this manually, but understanding it helps debug.

### JWT assertion structure

**Header:**
```json
{ "alg": "RS256", "typ": "JWT", "kid": "KEY_ID_FROM_KEY_JSON" }
```

**Payload:**
```json
{
  "iss": "sa-email@project.iam.gserviceaccount.com",
  "scope": "https://www.googleapis.com/auth/analytics.readonly",
  "aud": "https://oauth2.googleapis.com/token",
  "iat": 1716000000,
  "exp": 1716003600
}
```

**Token exchange:**

```bash
# Build and sign the JWT (example shows structure, use a library in practice)
curl -X POST https://oauth2.googleapis.com/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
  -d "assertion=SIGNED_JWT"
```

Response:
```json
{ "access_token": "ya29.c...", "expires_in": 3599, "token_type": "Bearer" }
```

Access tokens expire in 3600s. The library refreshes automatically.

---

## Python — service account auth

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

# From a key.json file
creds = service_account.Credentials.from_service_account_file(
    "key.json",
    scopes=SCOPES,
)

# Build a GA4 Analytics Data client
from google.analytics.data_v1beta import BetaAnalyticsDataClient
client = BetaAnalyticsDataClient(credentials=creds)

# Build a GSC client
gsc = build("webmasters", "v3", credentials=creds)
```

**From an environment variable (recommended for production):**

```python
import json, os
from google.oauth2 import service_account

key_data = json.loads(os.environ["GOOGLE_SA_KEY_JSON"])
creds = service_account.Credentials.from_service_account_info(
    key_data,
    scopes=SCOPES,
)
```

---

## Node.js — service account auth

```js
import { google } from 'googleapis';
import { readFileSync } from 'fs';

const key = JSON.parse(readFileSync('key.json', 'utf8'));

const auth = new google.auth.GoogleAuth({
  credentials: key,
  scopes: [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly',
  ],
});

// For googleapis library services
const webmasters = google.webmasters({ version: 'v3', auth });
const res = await webmasters.sites.list();

// For raw fetch with bearer token
const client = await auth.getClient();
const token = await client.getAccessToken();
const bearerToken = token.token; // use in Authorization header
```

**From environment variable:**

```js
const auth = new google.auth.GoogleAuth({
  credentials: JSON.parse(process.env.GOOGLE_SA_KEY_JSON),
  scopes: ['https://www.googleapis.com/auth/analytics.readonly'],
});
```

---

## Domain-wide delegation (DWD)

DWD allows a Service Account to impersonate any user in a Google Workspace (G Suite) domain. Required for: Google Workspace Admin SDK, Calendar API on behalf of users, Drive on behalf of users.

### Setup steps

1. **Enable DWD on the SA:**
   - Cloud Console → IAM → Service Accounts → select SA → **Enable G Suite Domain-wide Delegation**.
   - Note the **OAuth2 Client ID** (numeric, displayed after enabling).

2. **Authorize in Workspace Admin Console:**
   - Go to `admin.google.com` → Security → API Controls → Domain-wide delegation → **Add new**.
   - Paste the SA Client ID.
   - Add scopes the SA needs.
   - Must be done by a Workspace Super Admin.

3. **Impersonate in code (Python):**

```python
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SA_FILE = "key.json"
USER_TO_IMPERSONATE = "alice@yourdomain.com"

creds = service_account.Credentials.from_service_account_file(
    SA_FILE,
    scopes=SCOPES,
)
delegated_creds = creds.with_subject(USER_TO_IMPERSONATE)

from googleapiclient.discovery import build
gmail = build("gmail", "v1", credentials=delegated_creds)
```

4. **Impersonate in code (Node.js):**

```js
import { google } from 'googleapis';
import { readFileSync } from 'fs';

const key = JSON.parse(readFileSync('key.json', 'utf8'));
const auth = new google.auth.JWT({
  email: key.client_email,
  key: key.private_key,
  scopes: ['https://www.googleapis.com/auth/gmail.readonly'],
  subject: 'alice@yourdomain.com', // the user being impersonated
});
```

### DWD caveats

- `403 Unauthorized client` — the client ID is not authorized in the Admin Console, or the scope was not included
- `403 access_denied` — the user being impersonated does not exist or has no access to the resource
- DWD bypasses user consent — use it only when an admin has explicitly authorized the scope
- DWD does not work for non-Workspace Google accounts (personal Gmail)

---

## Key rotation policy

- List and delete old keys regularly:

```bash
# List keys for a SA
gcloud iam service-accounts keys list \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com

# Delete an old key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com
```

- Rotate every 90 days or immediately on suspected compromise.
- When rotating: create new key → deploy → verify → delete old key.

---

## Common mistakes

- **SA has IAM project role but no resource-level access** — Project `roles/viewer` does not grant access to GA4 data or GSC properties. Always add the SA email to the specific resource.
- **Key.json stored in git** — immediate revoke + create new key + audit access log.
- **Forgot to enable the API in the Cloud project** — 403 `SERVICE_DISABLED` error. Fix: `gcloud services enable APINAME`.
- **Wrong email format** — SA email format is `name@project-id.iam.gserviceaccount.com`; copying only the display name fails.
- **DWD without Admin Console approval** — gets `403 unauthorized_client`. A Super Admin must add the client ID, not just the project owner.
- **Single key used across many services** — if one service is compromised, all services are. Use separate SAs per service.
