# GTM API v2 — Rollback

Rolling back a GTM container to a previous version is a two-step process. There is no single "revert" endpoint.

**Critical:** A rollback immediately updates the live container. It is not a staged operation. Always confirm with the responsible stakeholder before executing.

## Why two steps?

GTM does not allow republishing an existing Version directly. Versions are immutable records. The rollback path is:

1. Duplicate the target old Version → this creates a **new** Version that is a copy of the old one.
2. Publish the new Version → the container goes live with the old configuration.

This design ensures every publish has a new, traceable Version entry in the audit trail.

## Full rollback recipe

### Step 0: confirm the decision

Before any API call, present the target version details to the user and get explicit confirmation.

```python
def get_version_summary(service, account_id, container_id, version_id):
    """Fetch and display summary of the target rollback version."""
    version = service.accounts().containers().versions().get(
        path=f'accounts/{account_id}/containers/{container_id}/versions/{version_id}'
    ).execute()
    return {
        'versionId': version['versionId'],
        'name': version.get('name', '(unnamed)'),
        'notes': version.get('description', ''),
        'tagCount': len(version.get('tag', [])),
        'triggerCount': len(version.get('trigger', [])),
        'variableCount': len(version.get('variable', [])),
    }

summary = get_version_summary(service, account_id, container_id, target_version_id)
print(f"""
Rollback target:
  Version:   {summary['versionId']} — "{summary['name']}"
  Notes:     {summary['notes']}
  Content:   {summary['tagCount']} tags, {summary['triggerCount']} triggers, {summary['variableCount']} variables

This will immediately replace the live container. Continue? [yes/no]
""")
if input().strip().lower() != 'yes':
    print('Rollback cancelled.')
    exit(0)
```

**Never auto-rollback.** Always require explicit human confirmation.

### Step 1: find the target old_version_id

```python
# List all versions to find the one you want to roll back to
versions = service.accounts().containers().versions().list(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()

print("Available versions:")
for v in sorted(versions.get('containerVersion', []), key=lambda x: int(x['versionId']), reverse=True):
    if not v.get('deleted'):
        print(f"  {v['versionId']:>6} — {v.get('name', '(unnamed)')}")
```

Or, if you captured `liveVersionId` before the problematic publish:

```python
target_version_id = previously_captured_live_version_id  # e.g., "41"
```

### Step 2: capture the current live version (safety record)

```python
live = service.accounts().containers().versions().live(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()
current_live_version_id = live['versionId']
print(f'Current live version: {current_live_version_id} — will be superseded by rollback')
```

### Step 3: create_version_from_old

```bash
POST accounts/{accountId}/containers/{containerId}/versions/{old_version_id}:create_version_from_old
```

No body required. Returns a new Version object that is a full copy of `old_version_id`.

```python
old_version_path = f'accounts/{account_id}/containers/{container_id}/versions/{target_version_id}'
result = service.accounts().containers().versions().create_version_from_old(
    path=old_version_path
).execute()

new_version_id = result['containerVersion']['versionId']
new_version_name = result['containerVersion'].get('name', '')
print(f'Created rollback version: {new_version_id} (copy of {target_version_id})')
```

### Step 4: publish the new version

```python
new_version_path = f'accounts/{account_id}/containers/{container_id}/versions/{new_version_id}'
pub_result = service.accounts().containers().versions().publish(
    path=new_version_path
).execute()
print(f'Published rollback version: {pub_result["containerVersion"]["versionId"]}')
```

### Step 5: verify

```python
live_after = service.accounts().containers().versions().live(
    parent=f'accounts/{account_id}/containers/{container_id}'
).execute()
assert live_after['versionId'] == new_version_id, 'Rollback verification failed!'
print(f'Rollback complete. Live version is now: {live_after["versionId"]}')
```

## Full Python rollback function

```python
def rollback_gtm_container(service, account_id, container_id, target_version_id):
    """
    Two-step GTM rollback: create_version_from_old → publish.
    Requires explicit confirmation before proceeding.
    Returns the new version ID published.
    """
    # Show target version summary and get confirmation
    summary = get_version_summary(service, account_id, container_id, target_version_id)
    print(f'\nRollback target: version {summary["versionId"]} — "{summary["name"]}"')
    print(f'Content: {summary["tagCount"]} tags, {summary["triggerCount"]} triggers')
    if input('Confirm rollback? [yes/no]: ').strip().lower() != 'yes':
        raise RuntimeError('Rollback cancelled by user')

    # Record current live version
    live = service.accounts().containers().versions().live(
        parent=f'accounts/{account_id}/containers/{container_id}'
    ).execute()
    print(f'Current live: {live["versionId"]}')

    # Step 1: create_version_from_old
    old_path = f'accounts/{account_id}/containers/{container_id}/versions/{target_version_id}'
    copy = service.accounts().containers().versions().create_version_from_old(
        path=old_path
    ).execute()
    new_version_id = copy['containerVersion']['versionId']
    print(f'Created rollback version: {new_version_id}')

    # Step 2: publish
    new_path = f'accounts/{account_id}/containers/{container_id}/versions/{new_version_id}'
    service.accounts().containers().versions().publish(path=new_path).execute()
    print(f'Rollback complete. Live version: {new_version_id}')

    return new_version_id
```

## Risks and side effects

### Traffic in flight

GTM snippet is served as a cached JavaScript file. After publish, CDN edge caches may serve the old snippet for 30–120 seconds. Sessions already in progress on the user's browser will continue with the old tag configuration until the next page load.

### Workspace edits are not affected

Rollback does not modify any Workspace. If team members have edits staged in a workspace that were based on the now-rolled-back state, those edits still exist. When they next call `sync`, they will see the rolled-back version as the new base and may encounter merge conflicts.

### The rolled-back version is a new version

`create_version_from_old` creates version N+2 (a copy of N). Version N+1 (the bad publish) remains in the audit trail — it is not deleted. If you want to archive it: `DELETE .../versions/{bad_version_id}` (soft-delete).

### Analytics data loss during rollback

If the bad publish fired analytics events for X minutes, those events are already recorded in GA4 / GTM. Rolling back the container does not erase already-sent hits. You may need to filter those minutes out in reporting.

### Partial state risk

If the bad version introduced new workspace entities (e.g., new triggers used by new tags) that do not exist in the rollback target version, those entities will be absent from the container after rollback. Verify the rollback target's content with `get_version_summary` before proceeding.

## Decision tree

```
Something is wrong after a publish
    ↓
Is it a data quality issue (wrong values being sent)?
    → Yes → Rollback immediately if in the first hour; otherwise investigate first
    → No  → Continue
        ↓
Is it a broken page / JS error caused by a Custom HTML tag?
    → Yes → Rollback (fastest fix)
    → No  → Continue
        ↓
Is it a consent / legal compliance issue (wrong consent signals)?
    → Yes → Rollback immediately; notify DPO
    → No  → Fix forward in a new workspace, create_version, publish
```

## Common mistakes

- **Calling `publish` on the old version directly.** The API does not allow republishing an existing version. You will receive `400 Bad Request`. The endpoint is `create_version_from_old`, not `publish` on the old version.
- **Skipping the confirmation prompt.** Auto-rollback scripts that execute without user confirmation have caused outages when invoked by mistake or by a CI job in the wrong environment.
- **Not verifying after publish.** Call `get_live` and assert the version ID. A 200 response from `publish` is not enough — verify the state independently.
- **Assuming rollback fixes GA4 data.** It does not. Data already sent to GA4 is permanent. Rollback only stops future incorrect data collection.
