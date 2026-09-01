# Management API — counters, goals, filters CRUD

Host: `https://api-metrika.yandex.net`. Header: `Authorization: OAuth <token>`. Scope: read — `metrika:read`, write — `metrika:write`.

## Counters

### List

```
GET /management/v1/counters?per_page=100&offset=1&type=simple
```

| Query | Description |
|---|---|
| `per_page` | up to 100 |
| `offset` | 1-based |
| `permission` | `own` / `view` / `edit` filter |
| `type` | `simple` / `partner` |
| `search_string` | substring match on name/site |
| `favorite` | `1` — only favorites |

Counter fields: `id`, `name`, `site` (domain), `status` (`Active`/`Deleted`), `owner_login`, `permission`, `pro`, `time_zone_name`, `webvisor`, `code_options`, `goal_count`, `filter_count`, `representative_count`, `gdpr_agreement_accepted`.

### Single

```
GET /management/v1/counter/{counter_id}?field=time_zone,goals,filters,operations,grants
```

`field=` — which related collections to return inline.

### Create

```
POST /management/v1/counters
Content-Type: application/json

{
  "counter": {
    "name": "Site name",
    "site": "example.com",
    "mirrors": ["www.example.com","m.example.com"],
    "time_zone_name": "Europe/Moscow",
    "code_options": {
      "async": 1,
      "informer": {"enabled": 0},
      "visor": 1,
      "clickmap": 1,
      "track_hash": 0,
      "ecommerce": 1
    }
  }
}
```

Scope: `metrika:write`. Returns the created counter with its `id`.

### Update / Delete

```
PUT    /management/v1/counter/{id}
DELETE /management/v1/counter/{id}
POST   /management/v1/counter/{id}/undelete
```

## Goals

### Goal types

| Type | Description |
|---|---|
| `url` | URL goal (visit to a specific page) |
| `number` | N page views per visit |
| `step` | Multi-step URL sequence |
| `composite` | OR-union of several goals |
| `action` | JS event via `reachGoal()` |
| `phone` | Phone call (requires call-tracking integration) |
| `email` | Email click |
| `messenger` | Messenger-link click |
| `file` | File download |
| `search` | On-site search |
| `payment_system` | Revenue (e-commerce) |

### List & CRUD

```
GET  /management/v1/counter/{id}/goals
GET  /management/v1/counter/{id}/goal/{goal_id}
POST /management/v1/counter/{id}/goals
PUT  /management/v1/counter/{id}/goal/{goal_id}
DELETE /management/v1/counter/{id}/goal/{goal_id}
```

### Create a URL goal

```
POST /management/v1/counter/{id}/goals
{
  "goal": {
    "name": "Thank you page",
    "type": "url",
    "is_retargeting": false,
    "conditions": [
      {"type": "exact", "url": "https://example.com/thank-you"}
    ]
  }
}
```

`conditions[].type`: `exact` / `contain` / `start` / `regexp`.

### Create a composite goal

```
{
  "goal": {
    "name": "Purchase OR Lead",
    "type": "composite",
    "depth": 2,
    "steps": [
      {"name": "Step 1", "type": "url", "conditions": [{"type": "exact", "url": "..."}]},
      {"name": "Step 2", "type": "action", "conditions": [{"type": "exact", "url": "leadFormSubmit"}]}
    ]
  }
}
```

## Filters

Applied at data-collection time (bots, IPs, domains).

```
GET  /management/v1/counter/{id}/filters
POST /management/v1/counter/{id}/filters
PUT  /management/v1/counter/{id}/filter/{filter_id}
DELETE /management/v1/counter/{id}/filter/{filter_id}
```

```json
{
  "filter": {
    "attr": "client_ip",
    "type": "interval",
    "value": "192.168.0.0",
    "value2": "192.168.255.255",
    "action": "exclude",
    "status": "active"
  }
}
```

`attr`: `client_ip` / `referer` / `url` / `title` / `uniq_id`. `type`: `equal` / `me` (own traffic) / `contain` / `start` / `regexp` / `interval`. `action`: `include` / `exclude` / `only_mirrors`.

## Operations

URL transformations applied before the data is stored (e.g. stripping query parameters).

```
GET  /management/v1/counter/{id}/operations
POST /management/v1/counter/{id}/operations
```

```json
{
  "operation": {
    "action": "merge_https_and_http",
    "attr": "url",
    "value": ""
  }
}
```

`action`: `cut_parameter` / `replace` / `to_lower` / `cut_fragment` / `merge_https_and_http` / `merge_www_and_without_www` / `replace_domain`.

Example — strip `?utm_*`:
```json
{"operation": {"action": "cut_parameter", "attr": "url", "value": "utm_source"}}
```

## Representatives

Delegated access to another user.

```
GET  /management/v1/counter/{id}/representatives
POST /management/v1/counter/{id}/representatives
DELETE /management/v1/counter/{id}/representative/{user_login}
```

```json
{
  "representative": {
    "user_login": "partner-login",
    "perm": "view",
    "comment": "Partner — read-only"
  }
}
```

`perm`: `view` (read) / `edit` (write). The recipient must confirm in their Yandex ID account.

## Segments

Persistent segments referenced from the Reporting API.

```
GET  /management/v1/counter/{id}/apps_segments
POST /management/v1/counter/{id}/segments
PUT  /management/v1/counter/{id}/segment/{segment_id}
DELETE /management/v1/counter/{id}/segment/{segment_id}
```

```json
{
  "segment": {
    "name": "Mobile buyers from Moscow",
    "expression": "ym:s:deviceCategory=='mobile' AND ym:s:regionCity=='Moscow' AND EXISTS(ym:ev:eventType=='purchase')"
  }
}
```

`expression` uses the same DSL as the Reporting API `filters` param.

## Bulk goals / filters / operations

To migrate between counters:

1. `GET /management/v1/counter/{src}/goals`
2. Strip `id` / `flag` / `default_price` etc. — keep only business fields
3. `POST /management/v1/counter/{dst}/goals` for each

There are no built-in "copy" endpoints — migrate via API by hand or with a script.

## Permissions

`GET /management/v1/counter/{id}/permissions` — who has access to the counter. Useful for audit.

## Data Import API (upload)

Expenses / CRM / user_params imports — a sub-group of the Management API:

```
POST /management/v1/counter/{id}/expenses/upload?...                              # CSV expenses
POST /management/v1/counter/{id}/offline_conversions/upload?client_id_type=USER_ID  # offline conversions
POST /management/v1/counter/{id}/offline_conversions/calls/upload                 # phone calls
POST /management/v1/counter/{id}/user_params/upload                               # user params (CSV multipart/form-data)
```

The CSV must follow the Metrika format (see `/data-import/`). Each upload returns an `upload_id`; poll status via `GET /management/v1/counter/{id}/expenses/uploadings`.

Requires `metrika:write` plus the specific scope (`metrika:expenses`, `metrika:offline_data`, `metrika:user_params`).
