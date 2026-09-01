# GTM API v2 — Errors, Etag Conflicts, and Retry Policy

## Error response shape

All GTM API errors follow the standard Google error envelope:

```json
{
  "error": {
    "code": 409,
    "message": "Request body fingerprint does not match current fingerprint.",
    "status": "ABORTED",
    "errors": [
      {
        "message": "Request body fingerprint does not match current fingerprint.",
        "domain": "tagmanager.googleapis.com",
        "reason": "conflictingOperation"
      }
    ]
  }
}
```

The `error.errors[].reason` field is the machine-readable discriminator for handling logic.

## HTTP status codes

### 400 Bad Request

Malformed request: missing required fields, invalid parameter type, invalid resource path, `create_version` on a workspace with unresolved merge conflicts, or attempting to publish an already-published version.

```json
{ "error": { "code": 400, "status": "INVALID_ARGUMENT", "message": "..." } }
```

**Action:** Fix the request. Do not retry without changes.

Common causes:
- Workspace has `mergeConflict` → resolve conflicts, then create_version
- Invalid `parameter.type` value in tag/trigger/variable body
- Attempting `DELETE` on the Default Workspace (protected)
- `name` field missing on create

### 401 Unauthorized

Access token expired or missing.

```json
{ "error": { "code": 401, "status": "UNAUTHENTICATED" } }
```

**Action:** Refresh the access token using the refresh token. If using ADC/service account, the library auto-refreshes. If using raw HTTP, exchange the refresh token. See `google-cloud-auth` → `references/refresh-tokens.md`.

### 403 Forbidden

Two distinct sub-cases:

**a) Missing scope (`insufficientPermissions`):**
```json
{ "error": { "errors": [{ "reason": "insufficientPermissions" }] } }
```
The token was minted with `tagmanager.readonly` but a write operation was attempted. Re-mint the token with `tagmanager.edit.containers` and/or `tagmanager.publish`.

**b) User not granted access in GTM (`forbidden`):**
```json
{ "error": { "errors": [{ "reason": "forbidden" }] } }
```
The authenticated identity (user or service account) has not been added in the GTM Account/Container User Management. Adding IAM roles in Google Cloud Console is not sufficient. A human with GTM Administrator access must add the identity in the GTM UI.

**c) Tag Manager API not enabled in Cloud project (`accessNotConfigured`):**
```json
{ "error": { "errors": [{ "reason": "accessNotConfigured" }] } }
```
Go to Google Cloud Console → APIs & Services → Library → search "Tag Manager API" → Enable.

### 404 Not Found

The requested resource path does not exist: wrong account ID, container ID, workspace ID, or version ID; or the resource was deleted.

**Action:** Verify IDs by listing parent resources. Soft-deleted versions return 404 unless `include_deleted=true` is set.

### 409 Conflict — Etag / Fingerprint Mismatch

The most important GTM-specific error. Occurs when:
- Two agents (or two API calls) update the same resource concurrently
- The `fingerprint` in the PUT body does not match the server's current fingerprint for that resource
- A `publish` is attempted on a version whose underlying resource state changed

```json
{
  "error": {
    "code": 409,
    "status": "ABORTED",
    "errors": [{ "reason": "conflictingOperation" }]
  }
}
```

**Action:** Re-GET the resource, read the updated `fingerprint`, merge your changes, and retry the PUT.

```python
import time

def update_tag_with_retry(service, tag_path, updates, max_retries=3):
    for attempt in range(max_retries):
        tag = service.accounts().containers().workspaces().tags().get(
            path=tag_path
        ).execute()
        tag.update(updates)
        # fingerprint is already in the fetched tag object — pass it through
        try:
            return service.accounts().containers().workspaces().tags().update(
                path=tag_path, body=tag
            ).execute()
        except Exception as e:
            if '409' in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            raise
```

### 429 Too Many Requests — Write Quota

GTM imposes a write quota of approximately **25 write operations per minute per container**. This covers create, update, delete operations on tags, triggers, variables, folders, workspaces, and versions.

```json
{ "error": { "code": 429, "status": "RESOURCE_EXHAUSTED" } }
```

**Action:** Exponential backoff with jitter. The `Retry-After` header may be present with the number of seconds to wait.

Read-only operations (GET, LIST) are not subject to the write quota but may hit read-rate limits under very high request volume.

### 500 / 503 Internal Server Error

Transient server errors. Retry with exponential backoff.

## Retry policy

```python
import time
import random

def api_call_with_backoff(fn, max_retries=5, base_delay=1.0):
    """
    Retry wrapper for GTM API calls.
    Retries on 429, 500, 503.
    Raises immediately on 400, 403, 404.
    Re-fetches and retries on 409.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            error_str = str(e)
            code = None
            if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                code = int(e.resp.status)

            if code == 429 or code in (500, 503):
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                print(f'Rate limit / transient error (attempt {attempt+1}), retrying in {delay:.1f}s')
                time.sleep(delay)
            elif code == 409:
                # Caller should re-fetch fingerprint — surface immediately
                raise RuntimeError(f'Etag conflict (409). Re-fetch the resource and retry.') from e
            else:
                raise  # 400, 401, 403, 404 — do not retry
    raise RuntimeError('Max retries exceeded')
```

## Node.js retry with googleapis

The `googleapis` library does not retry automatically. Wrap calls:

```javascript
async function withRetry(fn, maxRetries = 5) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      const code = err?.code || err?.response?.status;
      if ((code === 429 || code === 500 || code === 503) && attempt < maxRetries - 1) {
        const delay = Math.pow(2, attempt) * 1000 + Math.random() * 500;
        console.warn(`GTM API error ${code}, retrying in ${Math.round(delay)}ms`);
        await new Promise(r => setTimeout(r, delay));
      } else {
        throw err;
      }
    }
  }
}

// Usage
const tags = await withRetry(() =>
  tagmanager.accounts.containers.workspaces.tags.list({ parent: workspacePath })
);
```

## Backoff parameters

| Error | Initial delay | Multiplier | Max retries | Notes |
|---|---|---|---|---|
| 429 | 2s | 2x | 5 | Add jitter (±0.5s) |
| 500 / 503 | 1s | 2x | 5 | Add jitter |
| 409 | Re-GET immediately | — | 3 | Must re-fetch fingerprint first |
| 401 | Refresh token once | — | 1 | Do not loop refresh |
| 400 / 403 / 404 | — | — | 0 | Fix request; no retry |

## Etag / fingerprint: how it works

Every resource (tag, trigger, variable, workspace, version, container, account) has a `fingerprint` field. It is an opaque string that changes every time the resource is modified on the server.

Rules:
1. **GET → read fingerprint** before every PUT or DELETE.
2. **Include fingerprint in PUT body.** The `fingerprint` field in the body is the optimistic lock.
3. **If fingerprint mismatch → 409.** Re-GET, re-read fingerprint, retry.
4. **Never cache fingerprints for more than one operation.** They expire immediately on any modification.

The `fingerprint` is also available on Version objects and is used when publishing. Include it as a query parameter for belt-and-suspenders safety:

```bash
POST .../versions/{versionId}:publish?fingerprint={fingerprint_value}
```
