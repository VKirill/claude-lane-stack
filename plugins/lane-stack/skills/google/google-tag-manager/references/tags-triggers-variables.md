# GTM API v2 — Tags, Triggers, Variables CRUD

Base path prefix: `accounts/{accountId}/containers/{containerId}/workspaces/{workspaceId}`

All three resource types follow the same REST pattern. Every mutating request must include the current `fingerprint` in the body to prevent concurrent-edit conflicts (409).

## Tags

### Tag type catalog

| Type code | Description |
|---|---|
| `gaawc` | Google Analytics: GA4 (recommended for GA4 events) |
| `gtag` | Google Tag (Global Site Tag — base tag for GA4/Ads) |
| `html` | Custom HTML (arbitrary `<script>`) |
| `img` | Custom Image (1x1 pixel beacon) |
| `ua` | Universal Analytics (legacy, UA-XXXXX) |
| `awct` | Google Ads Conversion Tracking |
| `sp` | Scroll Depth listener |
| `fls` | Floodlight Counter / Sales |
| `bzi` | LinkedIn Insight Tag |
| `twitter_website_tag` | Twitter / X pixel |
| `fbq` | Meta Pixel (Facebook) |

### List tags

```bash
GET .../workspaces/{workspaceId}/tags
```

Response: `{ "tag": [ {...}, {...} ] }`

```python
tags = service.accounts().containers().workspaces().tags().list(
    parent=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}'
).execute()
for tag in tags.get('tag', []):
    print(tag['name'], tag['type'], tag.get('tagId'))
```

### Get one tag

```bash
GET .../workspaces/{workspaceId}/tags/{tagId}
```

### Create a GA4 event tag

```json
POST .../workspaces/{workspaceId}/tags

{
  "name": "GA4 - purchase event",
  "type": "gaawc",
  "parameter": [
    { "type": "TEMPLATE", "key": "measurementId", "value": "G-XXXXXXXXXXXXXXX" },
    { "type": "TEMPLATE", "key": "eventName", "value": "purchase" },
    {
      "type": "LIST",
      "key": "eventParameters",
      "list": [
        {
          "type": "MAP",
          "map": [
            { "type": "TEMPLATE", "key": "name",  "value": "transaction_id" },
            { "type": "TEMPLATE", "key": "value", "value": "{{DL - transaction_id}}" }
          ]
        }
      ]
    }
  ],
  "firingTriggerId": ["12345678"],
  "tagFiringOption": "oncePerEvent"
}
```

Response contains the created tag with assigned `tagId` and `fingerprint`.

### Update a tag (fingerprint required)

```python
# Step 1: GET current fingerprint
tag = service.accounts().containers().workspaces().tags().get(
    path=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/tags/{tag_id}'
).execute()
fingerprint = tag['fingerprint']

# Step 2: PUT with updated fields + fingerprint
tag['name'] = 'GA4 - purchase event v2'
tag['fingerprint'] = fingerprint
service.accounts().containers().workspaces().tags().update(
    path=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/tags/{tag_id}',
    body=tag
).execute()
```

### Delete a tag

```bash
DELETE .../workspaces/{workspaceId}/tags/{tagId}
```

No body required. Returns empty 204.

## Triggers

### Trigger type catalog

| Type | Fires when |
|---|---|
| `pageview` | Immediately on page load |
| `domReady` | DOM is fully parsed (DOMContentLoaded) |
| `windowLoaded` | Full page including images loaded (window.onload) |
| `click` | Any element clicked (CSS selector filter optional) |
| `linkClick` | `<a>` element clicked |
| `formSubmission` | `<form>` submit event |
| `customEvent` | `dataLayer.push({ event: 'eventName' })` |
| `scrollDepth` | User scrolls to configured % |
| `elementVisibility` | Element enters viewport |
| `historyChange` | URL fragment or pushState change (SPA nav) |
| `jsError` | Uncaught JavaScript exception |
| `timerListener` | Fires every N milliseconds |

### Create a custom event trigger

```json
POST .../workspaces/{workspaceId}/triggers

{
  "name": "CE - form_submit",
  "type": "customEvent",
  "customEventFilter": [
    {
      "type": "EQUALS",
      "parameter": [
        { "type": "TEMPLATE", "key": "arg0", "value": "{{_event}}" },
        { "type": "TEMPLATE", "key": "arg1", "value": "form_submit" }
      ]
    }
  ]
}
```

### Create a pageview trigger with filter

```json
{
  "name": "PV - /checkout only",
  "type": "pageview",
  "filter": [
    {
      "type": "CONTAINS",
      "parameter": [
        { "type": "TEMPLATE", "key": "arg0", "value": "{{Page Path}}" },
        { "type": "TEMPLATE", "key": "arg1", "value": "/checkout" }
      ]
    }
  ]
}
```

Filter types: `EQUALS`, `CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `MATCHES_REGEX`, `LESS_THAN`, `GREATER_THAN`.

## Variables

### Built-in variable types (enable via container settings)

Built-in variables are referenced using `{{Variable Name}}` and do not have a `variableId`. Enable them via `PUT .../built_in_variables?type=PAGE_URL&type=CLICK_ID&...`.

Common built-in variable types: `PAGE_URL`, `PAGE_PATH`, `PAGE_HOSTNAME`, `PAGE_REFERRER`, `CLICK_ELEMENT`, `CLICK_CLASSES`, `CLICK_ID`, `CLICK_TEXT`, `CLICK_URL`, `FORM_ELEMENT`, `FORM_ID`, `FORM_CLASSES`, `FORM_TEXT`, `SCROLL_DEPTH_THRESHOLD`, `SCROLL_DEPTH_UNITS`, `HISTORY_SOURCE`, `HISTORY_NEW_URL_FRAGMENT`.

### User-defined variable types

| Type code | Description |
|---|---|
| `v` | 1st-party cookie |
| `jsm` | Custom JavaScript function |
| `d` | Data Layer variable |
| `k` | URL query parameter |
| `r` | Regex table (value mapping via regex) |
| `smm` | Lookup table (exact value mapping) |
| `c` | Constant string |
| `f` | HTTP Referrer |
| `cid` | GA Client ID |
| `vis` | Visibility |
| `k` | URL |

### Create a Data Layer variable

```json
POST .../workspaces/{workspaceId}/variables

{
  "name": "DL - transaction_id",
  "type": "d",
  "parameter": [
    { "type": "INTEGER", "key": "dataLayerVersion", "value": "2" },
    { "type": "BOOLEAN", "key": "setDefaultValue", "value": "false" },
    { "type": "TEMPLATE", "key": "name", "value": "ecommerce.transaction_id" }
  ]
}
```

### Create a Custom JavaScript variable

```json
{
  "name": "JS - page category",
  "type": "jsm",
  "parameter": [
    {
      "type": "TEMPLATE",
      "key": "javascript",
      "value": "function() {\n  return document.body.dataset.category || 'unknown';\n}"
    }
  ]
}
```

### Create a Constant variable

```json
{
  "name": "Const - GA4 Measurement ID",
  "type": "c",
  "parameter": [
    { "type": "TEMPLATE", "key": "value", "value": "G-XXXXXXXXXXXXXXX" }
  ]
}
```

## Parameter type codes

| Code | Meaning |
|---|---|
| `TEMPLATE` | String value (may contain `{{variable}}` references) |
| `INTEGER` | Integer as string |
| `BOOLEAN` | `"true"` or `"false"` as string |
| `LIST` | Array of parameter objects |
| `MAP` | Key-value map (array of `{ key, value }` pairs) |

## Common CRUD mistakes

- **Omitting `fingerprint` on update.** PUT without fingerprint returns 400 or silently uses the wrong version. Always GET → read `fingerprint` → include in PUT body.
- **Referencing a trigger by name instead of ID.** `firingTriggerId` is the numeric `triggerId` string, not the human-readable name.
- **Using `{{Variable Name}}` syntax in API calls.** The API accepts template-type parameters with `{{...}}` interpolation only inside `"value"` fields of `TEMPLATE` parameters — not as raw JSON values.
- **Creating a tag without any `firingTriggerId`.** The tag will never fire. Include at least one trigger ID (the "All Pages" trigger ID is typically `2147479553`).
- **Modifying tags/triggers in a workspace but forgetting to create a version before publish.** The workspace changes are invisible until a version is created and published.
