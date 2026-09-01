# GTM API v2 — Resource Hierarchy

## Conceptual tree

```
Account
└── Container (one per site/app/brand)
    ├── Workspace (edit sandbox; Default always exists)
    │   ├── Tag
    │   ├── Trigger
    │   ├── Variable
    │   └── Folder
    └── Version (immutable snapshot; created from Workspace)
```

Versions sit at the Container level, not inside a Workspace. Each Version is a complete frozen copy of all tags, triggers, variables, and folders at a given point in time.

## Account

The top-level GTM entity. One Google account or Google Workspace org typically owns one GTM account. Account ID is numeric.

| Field | Type | Notes |
|---|---|---|
| `accountId` | string | Numeric. Appears in GTM URL. |
| `name` | string | Human-readable account name |
| `shareData` | bool | Whether data is shared with Google Benchmarking |
| `fingerprint` | string | Etag for optimistic concurrency |
| `path` | string | Resource path: `accounts/{accountId}` |

**Endpoints:**
- `GET accounts` — list all accounts the caller has access to
- `GET accounts/{accountId}` — get one account
- `PUT accounts/{accountId}` — update account (name, shareData)

## Container

One GTM container per site or app. A container holds the tag/trigger/variable configuration and publishes it as a script snippet embedded in the site.

| Field | Type | Notes |
|---|---|---|
| `containerId` | string | Numeric |
| `name` | string | Human label |
| `usageContext` | string[] | `WEB`, `ANDROID`, `IOS`, `AMP`, `SERVER` |
| `domainName` | string[] | Associated domains (informational) |
| `publicId` | string | The `GTM-XXXXXXX` ID used in the snippet |
| `fingerprint` | string | Etag |

**Endpoints:**
- `GET accounts/{accountId}/containers` — list containers
- `GET accounts/{accountId}/containers/{containerId}` — get one
- `POST accounts/{accountId}/containers` — create
- `PUT accounts/{accountId}/containers/{containerId}` — update
- `DELETE accounts/{accountId}/containers/{containerId}` — delete

## Workspace

The mutable edit surface. Changes made here do not affect the live container until a Version is created and published.

| Field | Type | Notes |
|---|---|---|
| `workspaceId` | string | Numeric; "1" is usually the Default Workspace |
| `name` | string | "Default Workspace" or custom name |
| `description` | string | Optional |
| `fingerprint` | string | Etag |

The Default Workspace (`workspaceId = 1` typically) always exists and cannot be deleted. You can create additional named workspaces for parallel development tracks.

**Endpoints:**
- `GET .../workspaces` — list workspaces
- `GET .../workspaces/{workspaceId}` — get one
- `POST .../workspaces` — create a custom workspace
- `PUT .../workspaces/{workspaceId}` — update name/description
- `DELETE .../workspaces/{workspaceId}` — delete (non-default only)
- `POST .../workspaces/{workspaceId}:create_version` — create a Version from this workspace
- `GET .../workspaces/{workspaceId}:getStatus` — diff vs live version
- `POST .../workspaces/{workspaceId}:sync` — pull latest published changes in
- `GET .../workspaces/{workspaceId}:quick_preview` — returns a debug container URL

> Full detail in `workspaces.md`.

## Tag

A tag is a script (pixel, event beacon, analytics snippet) that fires under specified conditions. Each tag belongs to one workspace.

Key fields: `tagId`, `name`, `type`, `parameter[]`, `firingTriggerId[]`, `blockingTriggerId[]`, `fingerprint`.

Tag types: `gaawc` (Google Analytics: GA4), `gtag` (Global Site Tag), `html` (Custom HTML), `img` (Custom Image), `ua` (Universal Analytics — legacy), `awct` (Google Ads Conversion Tracking), `sp` (Scroll Depth), `fls` (Floodlight), and many more.

## Trigger

A trigger determines when a tag fires or is blocked. Triggers evaluate against GTM's built-in or data layer variables.

Key fields: `triggerId`, `name`, `type`, `filter[]`, `autoEventFilter[]`, `parameter[]`, `fingerprint`.

Trigger types: `pageview`, `domReady`, `windowLoaded`, `click`, `linkClick`, `formSubmission`, `customEvent`, `scrollDepth`, `elementVisibility`, `historyChange`, `jsError`, `timerListener`.

## Variable

A variable resolves a dynamic value at runtime. Variables are referenced by tags and triggers using `{{Variable Name}}` syntax.

Key fields: `variableId`, `name`, `type`, `parameter[]`, `fingerprint`.

Built-in variables (enabled in container settings): `Page URL`, `Page Path`, `Page Hostname`, `Referrer`, `Click ID`, `Click Classes`, `Click Text`, `Click URL`, `Form ID`, etc.

User-defined variable types: `v` (1st-party cookie), `jsm` (JavaScript variable), `d` (data layer variable), `k` (URL parameter), `r` (regex table), `smm` (lookup table), `cid` (GA client ID), `vis` (visibility), `aev` (auto event variable), `c` (constant), `f` (HTTP Referrer), `gtcs` (Google Tag config settings), and others.

## Folder

Folders organize tags/triggers/variables within a workspace. Folder membership is tracked on the resource (`folderId` field), not in a separate relationship table.

**Endpoint:** `POST .../folders/{folderId}:move_entities_to_folder` to batch-assign resources to a folder.

## Version

An immutable snapshot of all workspace content. Versions are the only path to publishing and rolling back.

| Field | Type | Notes |
|---|---|---|
| `versionId` | string | Numeric; auto-assigned |
| `name` | string | Human label (auto-generated or custom) |
| `description` | string | Optional changelog note |
| `deleted` | bool | Soft-deleted versions |
| `fingerprint` | string | Etag of the version object |
| `container` | object | Snapshot of the container at publish time |
| `tag[]` | object[] | Frozen tags |
| `trigger[]` | object[] | Frozen triggers |
| `variable[]` | object[] | Frozen variables |

**Endpoints:**
- `GET accounts/{accountId}/containers/{containerId}/versions` — list versions (summary only)
- `GET .../versions/{versionId}` — get one version (full content)
- `GET .../versions:live` — get the currently published version
- `POST .../versions/{versionId}:publish` — publish a version
- `POST .../versions/{versionId}:undelete` — restore a soft-deleted version
- `POST .../versions/{versionId}:create_version_from_old` — duplicate an old version (for rollback)
- `DELETE .../versions/{versionId}` — soft-delete a version

## Permissions model

GTM has its own permission layer separate from Google Cloud IAM.

| GTM Role | Scope | Capabilities |
|---|---|---|
| `Read` | Account or Container | List and get all resources |
| `Edit` | Container | Create, update, delete resources within the container; create versions |
| `Approve` | Container | Approve version submissions (if workflow enabled) |
| `Publish` | Container | Publish a version to live |
| `Administrator` | Account | Full access to all containers in account + user management |

**User management endpoints:**
- `GET accounts/{accountId}/user_permissions` — list account-level user permissions
- `POST/PUT/DELETE accounts/{accountId}/user_permissions/{userPermissionId}` — manage account access
- Container-level: `accounts/{accountId}/containers/{containerId}/environments` (Environments are a separate feature for multi-environment publishing)

**Important:** A service account must be explicitly added as a user in the GTM UI. Holding a Cloud IAM role on the project is not sufficient. The SA email appears in the GTM UI user management exactly like a regular email.
