# GTM API v2 — Workspaces

A Workspace is the mutable edit surface within a Container. Changes made in a workspace (creating/updating/deleting tags, triggers, variables) are staged and do not affect the live container until a Version is created and published.

Base path: `accounts/{accountId}/containers/{containerId}/workspaces`

## Default Workspace vs custom workspaces

| | Default Workspace | Custom Workspace |
|---|---|---|
| Always exists | Yes | No — must be created |
| Can be deleted | No | Yes |
| Typical ID | `1` (verify via list) | Auto-assigned numeric ID |
| Typical name | "Default Workspace" | User-defined |
| Use case | Single-track editing | Parallel development tracks (A/B, staging, feature branches) |

Best practice: use one custom workspace per feature / change set. This keeps the diff (getStatus) clean and makes version descriptions meaningful.

## Lifecycle: workspace → version → live

```
[Workspace with staged edits]
        ↓
 POST workspaces/{id}:create_version
        ↓
[Immutable Version (versionId assigned)]
        ↓
 POST versions/{versionId}:publish
        ↓
[Live container updated; users see changes]
```

There is no path to publish that skips create_version. Always checkpoint before pushing to live.

## API operations

### List workspaces

```bash
GET accounts/{accountId}/containers/{containerId}/workspaces
```

```python
result = service.accounts().containers().workspaces().list(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()
for ws in result.get('workspace', []):
    print(ws['workspaceId'], ws['name'])
```

### Create a custom workspace

```json
POST accounts/{accountId}/containers/{containerId}/workspaces

{
  "name": "feature/consent-mode-v2",
  "description": "Implement Consent Mode v2 triggers and tag updates"
}
```

Response includes `workspaceId`, `fingerprint`, `tagManagerUrl` (link to the GTM UI for this workspace).

### getStatus — diff vs live version

Returns all changes in this workspace that are not yet in the published version. Use this before creating a version to confirm what's included.

```bash
GET accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}:getStatus
```

Response shape:
```json
{
  "containerVersion": { ... },
  "workspaceChange": [
    {
      "tag": { "name": "GA4 - purchase event", "tagId": "99" },
      "changeStatus": "ADDED"
    },
    {
      "trigger": { "name": "CE - form_submit", "triggerId": "77" },
      "changeStatus": "MODIFIED"
    }
  ]
}
```

`changeStatus` values: `ADDED`, `DELETED`, `MODIFIED`, `UNMODIFIED`, `NOT_IN_WORKSPACE`.

### sync — pull latest published changes into workspace

If another workspace was published while you were editing, your workspace may be behind. Sync pulls the latest published version into your workspace and surfaces conflicts.

```bash
POST accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}:sync
```

Response:
```json
{
  "syncStatus": {
    "mergeConflict": [
      {
        "entityInBaseVersion": { "tag": { "name": "Legacy Tag", "tagId": "55" } },
        "entityInWorkspace": { "tag": { "name": "Legacy Tag (modified)", "tagId": "55" } }
      }
    ]
  }
}
```

### Conflict resolution

When `mergeConflict` is non-empty: decide per entity whether to keep the workspace version or the base version. Conflicts must be resolved before `create_version` will succeed.

Resolution strategy:
1. For each conflict, compare `entityInBaseVersion` vs `entityInWorkspace`.
2. If workspace version should win: update the entity in the workspace (PUT) with the intended content — this overwrites the conflict marker.
3. If base version should win: delete the workspace's version of the entity (DELETE), then sync again.
4. When `mergeConflict` is empty, proceed to `create_version`.

### quick_preview — debug URL

Returns a URL that previews the workspace on a real site without publishing. The URL contains an embedded GTM snippet that loads the workspace state instead of the live version.

```bash
GET accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}:quick_preview
```

Response:
```json
{
  "compiledTag": {
    "name": "workspace_preview",
    "content": "..."
  },
  "containerVersion": { ... }
}
```

The `tagManagerUrl` field in the workspace object also points to the GTM UI Preview mode.

### create_version — checkpoint a workspace

Creates an immutable Version from the current state of the workspace. All staged edits are frozen. The workspace remains open for further edits.

```json
POST accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}:create_version

{
  "name": "v42 — consent mode v2 rollout",
  "notes": "Adds Consent Mode v2 triggers and updates all Google tags to consent-aware variants."
}
```

Response:
```json
{
  "containerVersion": {
    "versionId": "42",
    "name": "v42 — consent mode v2 rollout",
    "fingerprint": "...",
    "tag": [...],
    "trigger": [...],
    "variable": [...]
  },
  "syncStatus": { ... },
  "compilerError": false
}
```

Capture `versionId` from the response — you need it for the subsequent `publish` call and for rollback reference.

### Delete a workspace

Only non-default workspaces can be deleted.

```bash
DELETE accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}
```

Returns 204 on success. Staged edits in the workspace are discarded permanently.

## Workspace-based parallel development pattern

```
main branch → Default Workspace (always synced, low-risk changes)
feature branch → custom workspace (isolated; sync before create_version)
hotfix branch → custom workspace (minimal change; publish immediately after create_version)
```

Before merging any custom workspace to "live":
1. Call `getStatus` — review every change
2. Call `sync` — resolve any merge conflicts
3. Call `create_version` with a descriptive name and notes
4. Call `versions/{versionId}:publish`
5. Optionally delete the custom workspace

## Common mistakes

- **Hard-coding workspaceId = "1".** Correct for most containers but not guaranteed. Always call `workspaces.list` to discover IDs.
- **Calling `publish` directly on a workspace.** No such endpoint exists. The only publish path is `versions/{versionId}:publish` after `create_version`.
- **Skipping `getStatus` before create_version.** You may accidentally freeze unintended changes. Always verify the diff first.
- **Ignoring `mergeConflict` in sync response.** `create_version` will reject the request if unresolved conflicts exist.
- **Deleting the Default Workspace.** Returns 400. The Default Workspace is protected.
