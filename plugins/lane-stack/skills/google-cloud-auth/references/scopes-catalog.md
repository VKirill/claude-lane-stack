# Google API Scopes Catalog

Minimum required scopes for each API. Always request the smallest scope set that covers the use case — over-requesting broadens the consent screen and increases rejection risk.

**Rule:** Scopes are set at refresh-token mint time. Adding a new scope to an existing token requires re-authorization (`prompt=consent`).

---

## How to read this table

| Column | Meaning |
|---|---|
| Scope URL | Full scope string to include in the auth request |
| What it grants | Capabilities unlocked by this scope |
| API | Which Google API(s) use this scope |
| Min? | Is this the minimum for the most common task |

---

## Google Search Console (GSC / Webmasters)

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/webmasters.readonly` | Read all Search Analytics data, Sites list, Sitemaps list, URL Inspection | Webmasters v3, Search Console v1 | Yes — for read-only automation |
| `https://www.googleapis.com/auth/webmasters` | Full access: read + submit/delete sitemaps, add/remove sites | Webmasters v3 | Yes — when sitemap management is needed |
| `https://www.googleapis.com/auth/indexing` | Submit URL_UPDATED and URL_DELETED notifications to Indexing API | Indexing API v3 | Yes — for JobPosting/BroadcastEvent pages only |

**Common pattern:** Use `webmasters.readonly` unless you need sitemap submit. Add `indexing` only when working with structured data (JobPosting, BroadcastEvent).

---

## Google Analytics 4 (GA4 Data API + Admin API)

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/analytics.readonly` | Read GA4 reports, run queries, read Admin API (properties, custom dimensions) | Data API v1beta, Admin API v1beta | Yes — for reporting scripts |
| `https://www.googleapis.com/auth/analytics.edit` | Read + write Admin API (create/update custom dimensions, conversion events) | Admin API v1beta | When modifying GA4 config |
| `https://www.googleapis.com/auth/analytics.manage.users` | Manage user access at property level | Admin API v1beta | Only for user management automation |
| `https://www.googleapis.com/auth/analytics.manage.users.readonly` | Read user access lists | Admin API v1beta | For access audits |

**Note:** `analytics.readonly` is sufficient for all `runReport`, `runPivotReport`, `runRealtimeReport`, and `batchRunReports` calls. Admin API list operations (properties, customDimensions) also work with `readonly`.

---

## Google Tag Manager (GTM API v2)

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/tagmanager.readonly` | Read accounts, containers, workspaces, tags, triggers, variables, versions | Tag Manager v2 | Yes — for read-only automation |
| `https://www.googleapis.com/auth/tagmanager.edit.containers` | Read + create/update/delete tags, triggers, variables, workspaces, folders | Tag Manager v2 | For tag/trigger/variable CRUD |
| `https://www.googleapis.com/auth/tagmanager.edit.containerversions` | Read + create container versions | Tag Manager v2 | For version creation |
| `https://www.googleapis.com/auth/tagmanager.publish` | Read + publish container versions (make live) | Tag Manager v2 | For publishing/go-live |
| `https://www.googleapis.com/auth/tagmanager.delete.containers` | Delete containers | Tag Manager v2 | Only for container deletion |
| `https://www.googleapis.com/auth/tagmanager.manage.accounts` | Manage account-level settings | Tag Manager v2 | Rarely needed |
| `https://www.googleapis.com/auth/tagmanager.manage.users` | Manage account and container user permissions | Tag Manager v2 | For user management only |

**Common patterns:**
- Read-only audit: `tagmanager.readonly`
- Full automation (CRUD + publish): `tagmanager.edit.containers` + `tagmanager.edit.containerversions` + `tagmanager.publish`
- Do not request `tagmanager.delete.containers` unless deletion is explicitly in scope

---

## YouTube Data API

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/youtube.readonly` | Read YouTube channel data, videos, playlists, comments | YouTube Data API v3 | Yes — for read-only channel data |
| `https://www.googleapis.com/auth/youtube` | Manage YouTube account: upload, edit, delete videos, playlists | YouTube Data API v3 | When uploads/edits are needed |
| `https://www.googleapis.com/auth/youtube.force-ssl` | Perform all read/write operations over HTTPS (required for some comment operations) | YouTube Data API v3 | When writing comments or community posts |

**Note:** `youtube.force-ssl` is the scope required for comment management and some channel membership operations. Despite the name, it doesn't just enforce SSL — it unlocks write operations that `youtube.readonly` blocks.

---

## YouTube Analytics API

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/yt-analytics.readonly` | Read YouTube Analytics reports: views, watch time, traffic sources, demographics | YouTube Analytics API v2 | Yes — for analytics dashboards |
| `https://www.googleapis.com/auth/yt-analytics-monetary.readonly` | Read estimated revenue, ad performance, monetization metrics | YouTube Analytics API v2 | When revenue data is needed |

**Common pattern:** Use `yt-analytics.readonly` for view/engagement metrics. Add `yt-analytics-monetary.readonly` only when revenue/CPM data is explicitly required — it requires channel monetization to be enabled and triggers a broader consent screen.

---

## Google Drive (supplemental)

| Scope URL | What it grants | API | Min? |
|---|---|---|---|
| `https://www.googleapis.com/auth/drive.readonly` | Read files and file metadata | Drive API v3 | Yes — for reading exported GA4/GSC reports |
| `https://www.googleapis.com/auth/drive.file` | Create and modify only files created by this app | Drive API v3 | For creating spreadsheets/exports |
| `https://www.googleapis.com/auth/drive` | Full Drive access — read, write, delete any file | Drive API v3 | Avoid unless strictly necessary |
| `https://www.googleapis.com/auth/spreadsheets` | Read and write Google Sheets | Sheets API v4 | For Sheets integration |
| `https://www.googleapis.com/auth/spreadsheets.readonly` | Read Google Sheets | Sheets API v4 | For Sheets read-only access |

**Warning:** `drive` (full access) requires a Google security assessment for External apps. Prefer `drive.file` (app-created files only) or `drive.readonly`.

---

## Combining scopes

Pass multiple scopes as a space-separated string or an array. Google will show a combined consent screen.

**curl / authorization URL:**
```
scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fanalytics.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fwebmasters.readonly
```

**Python:**
```python
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]
```

**Node.js:**
```js
const SCOPES = [
  'https://www.googleapis.com/auth/analytics.readonly',
  'https://www.googleapis.com/auth/webmasters.readonly',
];
const auth = new google.auth.GoogleAuth({ scopes: SCOPES });
```

---

## Scope verification — check what a token covers

**Introspection endpoint:**
```bash
curl "https://oauth2.googleapis.com/tokeninfo?access_token=ya29.YOUR_ACCESS_TOKEN"
```

Response includes `scope` field — space-separated list of scopes granted. If a scope you expected is missing, the refresh token was minted without it; re-authorize with `prompt=consent`.

**Python — check granted scopes:**
```python
from google.auth.transport.requests import Request

creds.refresh(Request())
print("granted scopes:", creds.scopes)
```

---

## Scope expansion rule

When you add a new scope to an existing OAuth client, users who previously authorized must re-consent. To trigger re-consent programmatically:

```
https://accounts.google.com/o/oauth2/v2/auth
  ?...existing params...
  &scope=OLD_SCOPES%20NEW_SCOPE
  &prompt=consent
  &access_type=offline
```

This mints a new refresh token covering all scopes. Invalidate the old token after storing the new one.
