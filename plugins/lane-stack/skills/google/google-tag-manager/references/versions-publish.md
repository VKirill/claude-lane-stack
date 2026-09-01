# GTM API v2 — Versions and Publish

Versions are immutable snapshots of a Container's configuration. They serve as both the publish mechanism and the audit trail. The only way to update a live container is to publish a Version.

Base path: `accounts/{accountId}/containers/{containerId}/versions`

## Version lifecycle

```
Workspace (mutable edits)
    ↓  create_version
Version N (immutable snapshot, status: CREATED)
    ↓  publish
Version N (status: PUBLISHED → becomes "live")
    ↓  (next publish)
Version N+1 published; Version N becomes previous version (still accessible for rollback)
```

All versions are retained unless explicitly (soft-)deleted. They form an audit trail: who published what and when.

## create_version — freeze a workspace

```json
POST accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}:create_version

{
  "name": "v42 — GA4 e-commerce events",
  "notes": "Adds purchase, add_to_cart, begin_checkout events with data layer variables."
}
```

Fields:
- `name` — human-readable label (appears in GTM UI version list)
- `notes` — changelog note visible in GTM UI; use it

Response body: `containerVersion` object with the new `versionId`, plus `syncStatus` and `compilerError` flag.

```python
ws_path = f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}'
result = service.accounts().containers().workspaces().create_version(
    path=ws_path,
    body={
        'name': 'v42 — GA4 e-commerce events',
        'notes': 'purchase + add_to_cart + begin_checkout events'
    }
).execute()

version_id = result['containerVersion']['versionId']
print(f'Created version {version_id}')
```

**Always capture `versionId` immediately.** You need it for publish and rollback.

## get_live — read the currently published version

```bash
GET accounts/{accountId}/containers/{containerId}/versions:live
```

Returns the full Version object of whatever is currently live on the container. Key fields to capture before any publish:

```python
live = service.accounts().containers().versions().live(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()

current_live_version_id = live['versionId']
print(f'Currently live: version {current_live_version_id} "{live.get("name", "")}"')
```

**Always call `get_live` before publishing** to record `current_live_version_id`. This is your rollback target if the new publish goes wrong.

## publish — push a version to live

```bash
POST accounts/{accountId}/containers/{containerId}/versions/{versionId}:publish
```

Optional query parameter: `fingerprint` (etag of the version object) — include for extra safety.

```python
version_path = f'accounts/{account_id}/containers/{container_id}/versions/{version_id}'
result = service.accounts().containers().versions().publish(
    path=version_path
).execute()

print(f'Published: {result.get("containerVersion", {}).get("versionId")}')
```

What happens on publish:
1. The target Version is marked as the live version.
2. The GTM snippet served to browsers is regenerated to reflect the Version content.
3. All new page loads on the site will run the new tag/trigger/variable configuration.
4. The previous live Version is retained in history.

**There is no "draft" publish or "preview-only" publish.** When you call `:publish`, the change is immediately live for all visitors. Use `quick_preview` (workspaces) for pre-publish verification.

## get — read any version

```bash
GET accounts/{accountId}/containers/{containerId}/versions/{versionId}
```

Returns the full frozen snapshot including all tags, triggers, variables, and folders at the time the version was created.

## list — list all versions

```bash
GET accounts/{accountId}/containers/{containerId}/versions
```

Response: `{ "containerVersion": [ { versionId, name, description, deleted, fingerprint }, ... ] }`

Only summary fields are returned (not the full tag/trigger/variable arrays). Use `get` for full content.

```python
versions = service.accounts().containers().versions().list(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()
for v in versions.get('containerVersion', []):
    print(v['versionId'], v.get('name', '(unnamed)'), 'deleted:', v.get('deleted', False))
```

## undelete — restore a soft-deleted version

```bash
POST accounts/{accountId}/containers/{containerId}/versions/{versionId}:undelete
```

Returns the restored Version. Soft-deleted versions remain in the API response from `list` with `"deleted": true`; they just cannot be published until undeleted.

## delete (soft) — archive a version

```bash
DELETE accounts/{accountId}/containers/{containerId}/versions/{versionId}
```

Sets `deleted: true`. Does not permanently remove the version. Use `undelete` to restore. The live version cannot be deleted.

## Safe publish checklist

Before every publish:

1. `getStatus` on the workspace — review every change included
2. `sync` on the workspace — resolve any merge conflicts
3. `get_live` — capture `current_live_version_id` and store it
4. `create_version` — create the checkpoint with a descriptive name and notes
5. Capture `new_version_id` from the response
6. `quick_preview` — verify on a staging/test URL if available
7. Confirm with stakeholder if changes affect core analytics or consent
8. `publish` with `new_version_id`
9. Verify: `get_live` — confirm the live version ID matches `new_version_id`

If anything goes wrong after step 8, proceed to `rollback.md`.

## Versions as audit trail

GTM Versions record:
- Which tags, triggers, and variables were live at each point in time
- The version name and notes (your changelog)
- When the version was created (via `fingerprint` timestamp)

Use `versions.list` + `versions.get` to answer questions like:
- "What was live on the site two weeks ago?"
- "When was this variable last changed?"
- "Which version introduced this tag?"

## Common mistakes

- **Publishing without first calling `create_version`.** There is no direct publish-from-workspace endpoint. You will get an error or publish an unintended state.
- **Not capturing `liveVersionId` before publish.** If you need to roll back, you have to search the version list. Capture it upfront.
- **Publishing to the wrong container.** Verify `containerId` matches the target site. GTM containers are not namespaced — a publish immediately updates production.
- **Treating publish as reversible without rollback preparation.** Rollback is possible but requires the two-step process. "Just unpublish" is not a button that exists.
- **Skipping `quick_preview`.** Preview mode runs the workspace state on your browser without affecting other visitors — use it.
