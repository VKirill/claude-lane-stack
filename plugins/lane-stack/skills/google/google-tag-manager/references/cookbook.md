# GTM API v2 — Cookbook

Seven end-to-end automation recipes using Python (`google-api-python-client`) or Node.js (`googleapis`).

## Setup shared across recipes

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json, time, random

SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/tagmanager.publish',
]

def build_service(key_file):
    creds = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return build('tagmanager', 'v2', credentials=creds)

ACCOUNT_ID = '123456'
CONTAINER_ID = '7890123'
WORKSPACE_ID = '1'  # verify via workspaces.list
WS_PATH = f'accounts/{ACCOUNT_ID}/containers/{CONTAINER_ID}/workspaces/{WORKSPACE_ID}'
CONTAINER_PATH = f'accounts/{ACCOUNT_ID}/containers/{CONTAINER_ID}'

service = build_service('/path/to/key.json')
```

---

## Recipe 1: Create a GA4 event tag + fire on custom event

Goal: Fire a GA4 purchase event when the `purchase` data layer event fires.

```python
def create_consent_trigger(service, ws_path, event_name):
    """Create a custom event trigger for a data layer event."""
    trigger_body = {
        'name': f'CE - {event_name}',
        'type': 'customEvent',
        'customEventFilter': [{
            'type': 'EQUALS',
            'parameter': [
                {'type': 'TEMPLATE', 'key': 'arg0', 'value': '{{_event}}'},
                {'type': 'TEMPLATE', 'key': 'arg1', 'value': event_name},
            ]
        }]
    }
    return service.accounts().containers().workspaces().triggers().create(
        parent=ws_path, body=trigger_body
    ).execute()

def create_ga4_event_tag(service, ws_path, tag_name, measurement_id, event_name, trigger_id):
    """Create a GA4 event tag firing on the given trigger."""
    tag_body = {
        'name': tag_name,
        'type': 'gaawc',
        'parameter': [
            {'type': 'TEMPLATE', 'key': 'measurementId', 'value': measurement_id},
            {'type': 'TEMPLATE', 'key': 'eventName', 'value': event_name},
        ],
        'firingTriggerId': [str(trigger_id)],
        'tagFiringOption': 'oncePerEvent',
    }
    return service.accounts().containers().workspaces().tags().create(
        parent=ws_path, body=tag_body
    ).execute()

# Execution
trigger = create_consent_trigger(service, WS_PATH, 'purchase')
trigger_id = trigger['triggerId']

tag = create_ga4_event_tag(
    service, WS_PATH,
    tag_name='GA4 - purchase event',
    measurement_id='G-XXXXXXXXXXXXXXX',
    event_name='purchase',
    trigger_id=trigger_id
)
print(f"Created trigger {trigger_id}, tag {tag['tagId']}")
```

---

## Recipe 2: Add a consent-aware pageview trigger

Goal: Fire tags only when `consentGranted` data layer variable is `true`.

```python
def create_consent_pageview_trigger(service, ws_path):
    """Pageview trigger with consent filter."""
    body = {
        'name': 'PV - consent granted only',
        'type': 'pageview',
        'filter': [{
            'type': 'EQUALS',
            'parameter': [
                {'type': 'TEMPLATE', 'key': 'arg0', 'value': '{{DL - consentGranted}}'},
                {'type': 'TEMPLATE', 'key': 'arg1', 'value': 'true'},
            ]
        }]
    }
    return service.accounts().containers().workspaces().triggers().create(
        parent=ws_path, body=body
    ).execute()

trigger = create_consent_pageview_trigger(service, WS_PATH)
print(f"Consent pageview trigger ID: {trigger['triggerId']}")
```

---

## Recipe 3: Bulk-rename variables via export-edit-import

Goal: Rename all variables matching a prefix (e.g., `OLD_` → `NEW_`).

```python
def bulk_rename_variables(service, ws_path, old_prefix, new_prefix):
    """Rename all variables whose name starts with old_prefix."""
    variables = service.accounts().containers().workspaces().variables().list(
        parent=ws_path
    ).execute().get('variable', [])

    renamed = []
    for var in variables:
        if var['name'].startswith(old_prefix):
            new_name = new_prefix + var['name'][len(old_prefix):]
            print(f'Renaming: "{var["name"]}" → "{new_name}"')
            var['name'] = new_name
            var_path = f'{ws_path}/variables/{var["variableId"]}'
            updated = service.accounts().containers().workspaces().variables().update(
                path=var_path, body=var
            ).execute()
            renamed.append(updated)
            time.sleep(0.5)  # respect write quota: ~25 ops/min
    print(f'Renamed {len(renamed)} variables')
    return renamed

bulk_rename_variables(service, WS_PATH, 'DL - ', 'DataLayer - ')
```

---

## Recipe 4: Rollback to version N-1

Goal: Roll back the container to the version before the current live version.

```python
def rollback_to_previous_version(service, container_path):
    """
    Two-step rollback: create_version_from_old → publish.
    Requires confirmation before proceeding.
    """
    # Get all versions sorted by ID descending
    versions = service.accounts().containers().versions().list(
        parent=container_path
    ).execute().get('containerVersion', [])
    active = [v for v in versions if not v.get('deleted')]
    active.sort(key=lambda v: int(v['versionId']), reverse=True)

    live_id = active[0]['versionId']
    if len(active) < 2:
        raise RuntimeError('No previous version available for rollback')

    target = active[1]
    target_id = target['versionId']
    target_name = target.get('name', '(unnamed)')

    print(f'\nCurrent live: {live_id}')
    print(f'Rollback to:  {target_id} — "{target_name}"')
    if input('Confirm? [yes/no]: ').strip().lower() != 'yes':
        print('Cancelled')
        return None

    # Step 1: create_version_from_old
    old_path = f'{container_path}/versions/{target_id}'
    copy = service.accounts().containers().versions().create_version_from_old(
        path=old_path
    ).execute()
    new_id = copy['containerVersion']['versionId']

    # Step 2: publish
    new_path = f'{container_path}/versions/{new_id}'
    service.accounts().containers().versions().publish(path=new_path).execute()
    print(f'Rollback complete. New live version: {new_id} (copy of {target_id})')
    return new_id

rollback_to_previous_version(service, CONTAINER_PATH)
```

---

## Recipe 5: List all tags referencing a specific variable

Goal: Find every tag that uses a given variable (by name).

```python
def find_tags_using_variable(service, ws_path, variable_name):
    """Find all tags that reference the given variable by {{variable_name}} syntax."""
    search_token = '{{' + variable_name + '}}'
    tags = service.accounts().containers().workspaces().tags().list(
        parent=ws_path
    ).execute().get('tag', [])

    matching = []
    for tag in tags:
        tag_json = json.dumps(tag)
        if search_token in tag_json:
            matching.append({'tagId': tag['tagId'], 'name': tag['name'], 'type': tag['type']})

    print(f'Tags referencing "{{{{ {variable_name} }}}}":')
    for t in matching:
        print(f"  [{t['tagId']}] {t['name']} ({t['type']})")
    return matching

find_tags_using_variable(service, WS_PATH, 'GA4 Measurement ID')
```

---

## Recipe 6: Find unused triggers

Goal: Find triggers that no tag fires on (orphaned triggers).

```python
def find_unused_triggers(service, ws_path):
    """Return triggers not referenced by any tag's firingTriggerId or blockingTriggerId."""
    tags = service.accounts().containers().workspaces().tags().list(
        parent=ws_path
    ).execute().get('tag', [])
    triggers = service.accounts().containers().workspaces().triggers().list(
        parent=ws_path
    ).execute().get('trigger', [])

    used_ids = set()
    for tag in tags:
        used_ids.update(tag.get('firingTriggerId', []))
        used_ids.update(tag.get('blockingTriggerId', []))

    unused = [t for t in triggers if t['triggerId'] not in used_ids]
    print(f'Unused triggers ({len(unused)}):')
    for t in unused:
        print(f"  [{t['triggerId']}] {t['name']} ({t['type']})")
    return unused

find_unused_triggers(service, WS_PATH)
```

---

## Recipe 7: Clone a workspace for staging

Goal: Create a parallel "staging" workspace that mirrors current workspace changes.

```python
def clone_workspace_to_staging(service, container_path, source_workspace_id):
    """
    Create a new workspace, then copy all tags/triggers/variables from the source.
    GTM has no native workspace-clone endpoint — this reimplements it.
    """
    # Create the staging workspace
    staging_ws = service.accounts().containers().workspaces().create(
        parent=container_path,
        body={'name': 'staging-clone', 'description': f'Clone of workspace {source_workspace_id}'}
    ).execute()
    staging_id = staging_ws['workspaceId']
    staging_path = f'{container_path}/workspaces/{staging_id}'
    print(f'Created staging workspace: {staging_id}')

    src_path = f'{container_path}/workspaces/{source_workspace_id}'

    # Copy variables first (tags/triggers may reference them)
    for var in service.accounts().containers().workspaces().variables().list(
        parent=src_path
    ).execute().get('variable', []):
        body = {k: v for k, v in var.items() if k not in ('variableId', 'fingerprint', 'path', 'accountId', 'containerId', 'workspaceId')}
        service.accounts().containers().workspaces().variables().create(
            parent=staging_path, body=body
        ).execute()
        time.sleep(0.3)

    # Copy triggers
    for trig in service.accounts().containers().workspaces().triggers().list(
        parent=src_path
    ).execute().get('trigger', []):
        body = {k: v for k, v in trig.items() if k not in ('triggerId', 'fingerprint', 'path', 'accountId', 'containerId', 'workspaceId')}
        service.accounts().containers().workspaces().triggers().create(
            parent=staging_path, body=body
        ).execute()
        time.sleep(0.3)

    print(f'Staging workspace {staging_id} ready. Trigger IDs will differ — review firingTriggerId references in tags manually.')
    return staging_id
```

**Warning:** Tag `firingTriggerId` references use the source workspace's numeric trigger IDs. After cloning triggers into the new workspace they receive new IDs. You must remap `firingTriggerId` arrays in each tag manually after cloning. Full tag copy with ID remapping is left as an exercise; the pattern above is the scaffold.
