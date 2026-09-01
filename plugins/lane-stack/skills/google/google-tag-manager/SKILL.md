---
name: google-tag-manager
description: "[RU: gtm, тег менеджер, google tag manager, контейнер, теги, триггеры, переменные, публикация версии, откат] GTM API v2 full read + write — Account/Container/Workspace hierarchy, Tag/Trigger/Variable CRUD, version create + publish + rollback (two-step). Use when: gtm, tag manager, containers, workspaces, publish, rollback, etag concurrency, write quotas. SKIP: gtm server-side container code (→gtm-server-side if it exists, else omit); GA4 measurement protocol (→google-analytics); legacy ga.js."
stacks:
  - google-tag-manager
  - marketing-tech
  - nodejs
  - python
tags:
  - google
  - gtm
  - tag-manager
  - containers
  - workspaces
  - publish
  - rollback
  - marketing
source: vechkasov-global-skills
risk: high-stakes
---

<!-- versions:start -->

## 🎯 Version Requirements (June 2026)

**Primary pins:**
- GTM API: `v2 (stable)`
- googleapis (Node): `144.x`
- google-api-python-client: `2.x`
- Node.js: `24.x (Active LTS)`
- Python: `3.14.x`

> Source of truth: [STACK_VERSIONS.md](../../STACK_VERSIONS.md) — verified 2026-06-11

<!-- versions:end -->

## Usage

Loaded automatically when its description matches the active task. This is the single source of truth for Google Tag Manager API v2 operations: reading container state, making writes, publishing versions, and rolling back. Read the section you need, then follow the link to the relevant reference file for full detail.

## Use this skill when

- Listing, creating, or updating GTM containers, workspaces, tags, triggers, or variables programmatically
- Publishing a workspace to live — requires the two-step create_version + publish flow
- Rolling back a GTM container to a previous version (two-step: `create_version_from_old` → publish)
- Auditing all tags in a container: list tags referencing a specific variable, find unused triggers
- Bulk-renaming or migrating variables via export-edit-import pattern
- Cloning a workspace for staging / QA before publish
- Diagnosing etag conflicts (409) on concurrent container edits
- Managing write quota (~25 write ops/min/container) and planning batch operations
- Setting up a service account or OAuth flow for GTM API access
- Finding account IDs and container IDs via API (accounts.list, containers.list)

## Do not use this skill when

- You need GA4 event analytics (sessions, conversions, reports) — use `google-analytics`
- You need Google OAuth / Service Account credential setup — use `google-cloud-auth`
- You need to write data into GA4 via Measurement Protocol — use `google-analytics`
- You need Yandex.Metrica tag management — different provider; load `yandex-metrica`
- You need generic HTTP transport patterns (retries, backoff) — use `httpx` or `nodejs`
- You need GTM server-side container code (sGTM custom templates in JavaScript) — different domain; check `gtm-server-side` if that skill exists

## Purpose

Google Tag Manager API v2 (`https://tagmanager.googleapis.com/tagmanager/v2/`) is the programmatic surface for managing GTM containers. It exposes a full hierarchy — Account → Container → Workspace → Tag/Trigger/Variable/Folder — with CRUD at every level, plus a publish workflow based on immutable, numbered Versions. Every write that modifies a live container must go through the two-step path: create an immutable Version checkpoint from the Workspace, then publish that Version; direct publish-without-checkpoint is not supported.

This skill is **high-stakes** because publishing incorrect tags to a live GTM container can instantly break analytics collection, fire unwanted pixels, or block consent flows for every visitor of the site. Rollback is possible but requires the two-step sequence described in `references/rollback.md`. Write operations consume a conservative per-container quota; exceeding it silently queues or drops changes. Etag-based optimistic concurrency is mandatory on updates to prevent one agent from stomping another's edits.

## Capabilities

### Authentication

GTM API uses standard Google OAuth 2.0 or a Service Account. The required scope for read-only access is `https://www.googleapis.com/auth/tagmanager.readonly`. For write operations (create, update, delete, publish) the scope is `https://www.googleapis.com/auth/tagmanager.edit.containers`. For publishing specifically the scope is `https://www.googleapis.com/auth/tagmanager.publish`. Service accounts must be granted access in the GTM Account/Container settings (not just IAM). Auth bootstrap is owned by `google-cloud-auth`.

> Full reference: [references/setup.md](references/setup.md)

### Resource hierarchy

GTM resources form a strict parent-child tree: **Account** (one per Google account or organization) → **Container** (one per site/app) → **Workspace** (edit sandbox; default workspace always exists) → **Tag/Trigger/Variable/Folder** (leaf resources within a Workspace). Versions sit alongside Workspaces at the Container level and are immutable snapshots. Permissions are granted at the Account or Container level; a user with container-level access cannot see other containers in the same account.

> Full reference: [references/resources-hierarchy.md](references/resources-hierarchy.md)

### Tags, Triggers, Variables CRUD

All three resource types follow the same REST pattern under a workspace path: list, get, create, update, delete. Tags reference trigger IDs in `firingTriggerIds` and `blockingTriggerIds`. Triggers evaluate conditions and fire tags. Variables resolve values (page URL, data layer values, cookie contents, etc.) that tags and triggers use. Updates require the current `fingerprint` (etag) in the request body to prevent concurrent-edit conflicts.

> Full reference: [references/tags-triggers-variables.md](references/tags-triggers-variables.md)

### Workspaces

A Workspace is the mutable edit surface inside a Container. The **Default Workspace** always exists; custom workspaces enable parallel development tracks. A Workspace stays in sync with the published version via the sync endpoint; conflicts (when the live version changed since the workspace was created) are surfaced as a `mergeConflict` list. `getStatus` shows all changes not yet in the live version.

> Full reference: [references/workspaces.md](references/workspaces.md)

### Versions and publish

A **Version** is an immutable snapshot of a Container. The workflow to push changes live: (1) call `workspaces:create_version` on your workspace — this produces a numbered Version; (2) call `versions/{versionId}:publish` on that Version. The API does not support publishing a workspace directly. After publish, `versions:live` reflects the newly live state. Versions serve as the audit trail and rollback source.

> Full reference: [references/versions-publish.md](references/versions-publish.md)

### Rollback

Rollback is a two-step process: you cannot "reset to version N" directly. Step 1: call `versions/{old_version_id}:create_version_from_old` — this creates a new Version that is a copy of the target old Version. Step 2: call `versions/{new_version_id}:publish` on the freshly created Version. The previous live Version is preserved in history. In-flight workspace edits are not affected but may conflict with the rolled-back state.

> Full reference: [references/rollback.md](references/rollback.md)

### Etag-based concurrency

Every mutable GTM resource carries a `fingerprint` field. When two agents edit the same resource concurrently, the second write will receive 409 Conflict if the fingerprint has changed. Always: (1) GET the resource to obtain the current `fingerprint`, (2) include that `fingerprint` in the UPDATE body, (3) handle 409 by re-fetching and retrying.

> Full reference: [references/errors.md](references/errors.md)

### Errors and quotas

GTM API returns standard Google error JSON. Key codes: 401 (token expired), 403 (missing scope or not granted access on container), 409 (etag/fingerprint conflict on concurrent edit), 429 (write quota ~25 ops/min/container), 500/503 (transient). Exponential backoff with jitter is required on 429 and 5xx.

> Full reference: [references/errors.md](references/errors.md)

### Real automation examples

Five-to-eight concrete automation recipes: create GA4 event tag, add consent-aware trigger, bulk-rename variables, rollback to version N-1, list tags referencing a specific variable, find unused triggers, clone workspace for staging.

> Full reference: [references/cookbook.md](references/cookbook.md)

## Behavioral Traits

- Always obtain the live `versionId` before any publish to enable rollback if needed
- Always read the resource `fingerprint` before an update — include it in the body to prevent 409
- Always create a Version (create_version) before publish — no workspace-direct publish path exists
- Treat write quota as a real constraint: batch related changes in one workspace, avoid per-item loops that fire 25+ writes/min
- For rollback: never auto-roll back. Present the target version summary to the user, get confirmation, then execute the two-step sequence
- Treat 409 as expected in multi-agent scenarios; re-GET, merge, retry
- For bulk operations: list all resources first, filter locally, then write — minimizes API calls and quota consumption

## Important Constraints

- **NEVER publish to live without calling `create_version` first** — create_version is the safety checkpoint; without it there is no version to roll back to
- **ALWAYS capture the current `liveVersionId` before publish** — store it so rollback can target the correct old version
- **Rollback requires a confirmation prompt — never auto-rollback** — show the user the target version (name, description, creation time) and ask for explicit approval before executing the two-step sequence
- NEVER send an UPDATE or DELETE without including the current `fingerprint` in the request body — omitting it risks stomping concurrent edits (409 is the best outcome; silent data loss is the worst)
- NEVER exceed the write quota (~25 ops/min/container) without exponential backoff — plan bulk operations with delays
- NEVER commit service account key files to git — use environment variables or a secrets manager
- ALWAYS verify the service account or OAuth user is granted access at the GTM Account or Container level in the GTM UI, not just at Google Cloud IAM level
- ALWAYS enable the Tag Manager API in the Google Cloud Console project — a valid key file alone is insufficient
- Rollback is a TWO-STEP operation: `create_version_from_old` → `publish` — there is no single "revert" endpoint

## Related Skills

- `google-cloud-auth` — OAuth 2.0 user flow, Service Account JWT, ADC, scopes catalog, invalid_grant recovery (required before any GTM API call)
- `google-analytics` — GA4 reporting; pair with GTM for the full analytics instrumentation story
- `google-search-console` — GSC search data; often used alongside GTM in the same site analytics stack
- `nodejs` — Node.js runtime patterns for `googleapis` library (`google.tagmanager('v2')`)
- `python` — Python runtime patterns for `google-api-python-client` (`build('tagmanager', 'v2', ...)`)
- `httpx` — Python HTTP transport for raw REST calls with bearer tokens
- `postgresql` — persistence for version snapshots, audit logs, rollback history

## API Reference

| Topic | File |
|---|---|
| Auth (OAuth + Service Account), discover Account/Container IDs, curl + Node + Python init | [references/setup.md](references/setup.md) |
| Account → Container → Workspace → Tag/Trigger/Variable/Folder hierarchy, permissions model | [references/resources-hierarchy.md](references/resources-hierarchy.md) |
| Tags, Triggers, Variables CRUD — types catalog, JSON examples | [references/tags-triggers-variables.md](references/tags-triggers-variables.md) |
| Workspace lifecycle — default/custom, sync, conflict resolution, getStatus diff | [references/workspaces.md](references/workspaces.md) |
| Version create, publish, get_live, undelete — audit trail | [references/versions-publish.md](references/versions-publish.md) |
| Rollback recipe (two-step) — risks, confirmation pattern, code walkthrough | [references/rollback.md](references/rollback.md) |
| Errors 401/403/409/429/500, etag conflicts, retry policy with exponential backoff | [references/errors.md](references/errors.md) |
| Cookbook — 7 real automations end-to-end | [references/cookbook.md](references/cookbook.md) |
