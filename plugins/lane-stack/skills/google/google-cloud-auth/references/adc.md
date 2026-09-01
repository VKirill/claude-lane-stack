# Application Default Credentials (ADC)

ADC is Google's zero-config credential discovery chain. When client libraries call `google.auth.default()` (Python) or `new GoogleAuth()` (Node.js), they walk a well-defined chain until they find credentials. This eliminates key file management on GCP infrastructure.

---

## Discovery chain (in order)

```
1. GOOGLE_APPLICATION_CREDENTIALS env var
   └── points to a key.json file (SA) or user credentials JSON
       If set and valid → use these credentials. STOP.

2. gcloud Application Default Credentials
   └── ~/.config/gcloud/application_default_credentials.json
       Created by: gcloud auth application-default login
       If file exists → use it. STOP.

3. Attached Service Account (GCP workload identity)
   └── Metadata server at http://169.254.169.254/computeMetadata/v1/
       Available on: Cloud Run, GKE, Compute Engine, Cloud Functions, App Engine
       If metadata server responds → use attached SA. STOP.

4. Error: could not find default credentials
```

The library tries each step in order and stops at the first successful source. Step 3 never fails on GCP (every GCP resource has an attached SA, at minimum the default Compute SA).

---

## Step 1 — GOOGLE_APPLICATION_CREDENTIALS

Set this env var to the absolute path of a key.json file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/home/user/keys/my-sa-key.json"
```

In Docker:

```dockerfile
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/key.json
```

Or inject at runtime (preferred — avoids baking secrets into images):

```bash
docker run \
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/key.json \
  -v /host/path/key.json:/run/secrets/key.json:ro \
  my-image
```

Python — explicitly load via `GOOGLE_APPLICATION_CREDENTIALS`:

```python
import os
from google.auth import default

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/key.json"

credentials, project = default(
    scopes=["https://www.googleapis.com/auth/analytics.readonly"]
)
```

Node.js:

```js
import { google } from 'googleapis';

// googleapis automatically reads GOOGLE_APPLICATION_CREDENTIALS
const auth = new google.auth.GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/analytics.readonly'],
});

const client = await auth.getClient();
// client is now authorized using whatever ADC resolved
```

---

## Step 2 — gcloud ADC (developer machine setup)

On a developer machine, run once to authorize ADC:

```bash
# Login as yourself (user credentials, not SA)
gcloud auth application-default login
```

This opens a browser, asks you to log in with your Google account, and writes credentials to `~/.config/gcloud/application_default_credentials.json`.

**Scopes with gcloud ADC:**

By default, `gcloud auth application-default login` requests basic scopes. For API-specific scopes, add `--scopes`:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/analytics.readonly,\
https://www.googleapis.com/auth/webmasters.readonly
```

**To use a specific project:**

```bash
gcloud auth application-default set-quota-project MY_PROJECT_ID
```

**To revoke:**

```bash
gcloud auth application-default revoke
```

**To inspect what ADC currently resolves to:**

```bash
gcloud auth application-default print-access-token
```

---

## Step 3 — Workload identity / metadata server (GCP)

On GCP infrastructure (Cloud Run, GKE, Compute Engine, Cloud Functions), every resource has an attached service account. The metadata server at `http://169.254.169.254/computeMetadata/v1/` serves tokens for that SA without any key file.

```bash
# Direct metadata server call (works from inside a GCP VM/container)
curl -s -H "Metadata-Flavor: Google" \
  "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
```

Response:
```json
{
  "access_token": "ya29.c...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

Client libraries call this automatically. No env vars, no files, no config needed.

**Setting the attached SA for Cloud Run:**

```bash
gcloud run deploy my-service \
  --image=gcr.io/my-project/my-image \
  --service-account=my-sa@my-project.iam.gserviceaccount.com
```

**Setting the attached SA for a GCE VM:**

```bash
gcloud compute instances set-service-account my-vm \
  --service-account=my-sa@my-project.iam.gserviceaccount.com \
  --scopes=cloud-platform
```

---

## Explicit credential construction (bypassing ADC)

When ADC resolution order is inconvenient, construct credentials explicitly:

**Python — SA from file:**

```python
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    "key.json",
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
```

**Python — SA from environment variable (JSON string):**

```python
import json, os
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SA_KEY_JSON"]),
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
```

**Python — user OAuth credentials from stored token:**

```python
from google.oauth2.credentials import Credentials

creds = Credentials(
    token=stored_access_token,
    refresh_token=stored_refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
```

---

## Verifying what ADC resolves to

**Python:**

```python
import google.auth

credentials, project = google.auth.default()
print(type(credentials).__name__)  # ServiceAccountCredentials, UserCredentials, etc.
print("project:", project)
print("SA email:", getattr(credentials, "service_account_email", "N/A"))
```

**Node.js:**

```js
import { GoogleAuth } from 'google-auth-library';

const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});
const client = await auth.getClient();
console.log('credential type:', client.constructor.name);
// Compute, JWT, UserRefreshClient, etc.
```

---

## ADC in different environments

| Environment | Credential source | Setup |
|---|---|---|
| Developer laptop | `gcloud auth application-default login` | Run once |
| Docker (local) | `GOOGLE_APPLICATION_CREDENTIALS` + mounted key | `docker run -e ...` |
| Cloud Run | Attached SA via metadata server | `gcloud run deploy --service-account=...` |
| GKE | Workload Identity Federation or node SA | Configure Workload Identity on the pod |
| Compute Engine | Instance SA via metadata server | `gcloud compute instances set-service-account ...` |
| Cloud Functions | Default Compute SA or specified SA | Function config |
| GitHub Actions | Workload Identity Federation (keyless) | `google-github-actions/auth` action |

---

## Workload Identity Federation (keyless from GitHub Actions)

Avoids downloading key files entirely. GCP trusts GitHub's OIDC tokens.

```yaml
# .github/workflows/deploy.yml
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/my-pool/providers/github'
    service_account: 'my-sa@my-project.iam.gserviceaccount.com'
```

After this step, `GOOGLE_APPLICATION_CREDENTIALS` is set automatically for subsequent steps.

---

## Common mistakes

- **`GOOGLE_APPLICATION_CREDENTIALS` set to a relative path** — client libraries require an absolute path; relative paths are not expanded.
- **Forgetting `gcloud auth application-default login` after switching GCP projects** — the old project's SA may not have access to the new resource.
- **Confusing `gcloud auth login` with `gcloud auth application-default login`** — the first sets credentials for gcloud CLI itself; the second sets ADC used by client libraries.
- **Expecting ADC to work outside GCP** — step 3 (metadata server) only works from within a GCP VM/container. On a non-GCP server, provide explicit credentials via step 1 or 2.
- **Running Cloud Run without specifying a SA** — the default Compute SA is used, which usually lacks the required resource-level grants.
- **Setting scopes at the compute instance level but not in the client** — scopes on a GCE instance are a ceiling, but the client library must also request the scope.
