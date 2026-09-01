# GTM API v2 — Setup: Auth, IDs, and Clients

Base URL: `https://tagmanager.googleapis.com/tagmanager/v2/`

## Required scopes

| Scope | Use |
|---|---|
| `tagmanager.readonly` | Read all resources (accounts, containers, workspaces, tags, triggers, variables, versions) |
| `tagmanager.edit.containers` | Create, update, delete tags/triggers/variables/workspaces; create versions |
| `tagmanager.publish` | Publish a version to live; required in addition to `edit.containers` |
| `tagmanager.manage.accounts` | Manage account-level users and permissions |
| `tagmanager.manage.users` | Create/delete container-level user permissions |

For a typical automation that reads and publishes:
```
https://www.googleapis.com/auth/tagmanager.edit.containers
https://www.googleapis.com/auth/tagmanager.publish
```

## Service account setup

1. Create a service account in Google Cloud Console (`IAM & Admin → Service Accounts`).
2. Enable the **Tag Manager API** in the Cloud project (`APIs & Services → Library → search "Tag Manager API"`).
3. Download the JSON key file.
4. In the GTM UI: `Admin → Container → User Management` (or Account-level: `Admin → Account → User Management`). Add the service account email (`xxx@project.iam.gserviceaccount.com`) with the appropriate permission:
   - **Read** — list, get operations
   - **Edit** — create, update, delete, create_version
   - **Publish** — additionally publish versions
5. `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`

> Auth patterns (OAuth user flow, ADC, refresh token lifecycle) are covered in `google-cloud-auth`.

## Discover Account ID and Container ID

```bash
# List accounts
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://tagmanager.googleapis.com/tagmanager/v2/accounts"

# List containers in an account
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://tagmanager.googleapis.com/tagmanager/v2/accounts/{accountId}/containers"
```

Account ID is a numeric string (e.g., `123456`). Container ID is also numeric (e.g., `7890123`). Both appear in the GTM UI URL: `tagmanager.google.com/...#/container/{containerId}/...`

## Node.js client (googleapis)

```bash
npm install googleapis
```

```javascript
const { google } = require('googleapis');
const tagmanager = google.tagmanager('v2');

async function getClient() {
  const auth = new google.auth.GoogleAuth({
    keyFile: process.env.GOOGLE_APPLICATION_CREDENTIALS,
    scopes: [
      'https://www.googleapis.com/auth/tagmanager.edit.containers',
      'https://www.googleapis.com/auth/tagmanager.publish',
    ],
  });
  google.options({ auth });
  return tagmanager;
}

// List all containers in an account
async function listContainers(accountId) {
  const client = await getClient();
  const res = await client.accounts.containers.list({
    parent: `accounts/${accountId}`,
  });
  return res.data.container || [];
}
```

## Python client (google-api-python-client)

```bash
pip install google-api-python-client google-auth
```

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/tagmanager.publish',
]

def build_gtm_service(key_file: str):
    creds = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    return build('tagmanager', 'v2', credentials=creds)

# Usage
service = build_gtm_service('/path/to/key.json')

# List accounts
accounts = service.accounts().list().execute()
print(accounts.get('account', []))

# List containers
containers = service.accounts().containers().list(
    parent='accounts/123456'
).execute()
print(containers.get('container', []))
```

## Raw curl pattern

```bash
TOKEN=$(gcloud auth application-default print-access-token)
ACCOUNT_ID="123456"
CONTAINER_ID="7890123"
WORKSPACE_ID="5"

# GET tags in a workspace
curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "https://tagmanager.googleapis.com/tagmanager/v2/accounts/${ACCOUNT_ID}/containers/${CONTAINER_ID}/workspaces/${WORKSPACE_ID}/tags" \
  | jq '.tag[] | {name, tagId, type}'

# POST: create a tag (see tags-triggers-variables.md for body shape)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @tag_body.json \
  "https://tagmanager.googleapis.com/tagmanager/v2/accounts/${ACCOUNT_ID}/containers/${CONTAINER_ID}/workspaces/${WORKSPACE_ID}/tags"
```

## Resource path patterns

| Resource | Path |
|---|---|
| Account | `accounts/{accountId}` |
| Container | `accounts/{accountId}/containers/{containerId}` |
| Workspace | `accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}` |
| Tag | `.../workspaces/{workspaceId}/tags/{tagId}` |
| Trigger | `.../workspaces/{workspaceId}/triggers/{triggerId}` |
| Variable | `.../workspaces/{workspaceId}/variables/{variableId}` |
| Folder | `.../workspaces/{workspaceId}/folders/{folderId}` |
| Version | `accounts/{accountId}/containers/{containerId}/versions/{versionId}` |

## Common setup mistakes

- **Service account has IAM role but not GTM User Management access.** IAM (Google Cloud) and GTM's own user management are separate. The SA must be added in the GTM UI.
- **Tag Manager API not enabled.** Even with a valid key file, `403 accessNotConfigured` means the API is disabled. Enable it at `console.cloud.google.com/apis/library`.
- **Using `tagmanager.readonly` scope for write operations.** The response is 403 with `"insufficientPermissions"`. Add `edit.containers` and/or `publish` to the scope list.
- **Workspace ID "0" or "1".** The Default Workspace ID is `1` in most containers but may vary. Always look it up via `workspaces.list` rather than hard-coding.
