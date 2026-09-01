# Sites + Sitemaps CRUD

Base: `https://www.googleapis.com/webmasters/v3`. All endpoints are JSON.

## Sites

### List

`GET /webmasters/v3/sites`

```jsonc
{
  "siteEntry": [
    { "siteUrl": "sc-domain:example.com",      "permissionLevel": "siteFullUser" },
    { "siteUrl": "https://www.example.com/",   "permissionLevel": "siteOwner" }
  ]
}
```

`permissionLevel`:

| Value | Capabilities |
|---|---|
| `siteOwner` | everything (including sitemap submit) |
| `siteFullUser` | read + sitemap manage; cannot manage users |
| `siteRestrictedUser` | read-only (search analytics, URL inspection, sitemaps list) |
| `siteUnverifiedUser` | **nothing useful** — added without a role; API returns empty data |

### Get

`GET /webmasters/v3/sites/{siteUrl}`

`siteUrl` URL-encoded entirely: `https%3A%2F%2Fwww.example.com%2F` or `sc-domain%3Aexample.com`.

### Add

`PUT /webmasters/v3/sites/{siteUrl}`

Attaches the URL to the user's property list. **Does not verify** — Domain still needs DNS TXT, URL-prefix needs HTML / DNS / GA / GTM. Empty request body.

### Delete

`DELETE /webmasters/v3/sites/{siteUrl}`

Detaches the property from the current user (service account uses its own identity). The property continues to exist in Google for other users.

## Sitemaps

### List

`GET /webmasters/v3/sites/{siteUrl}/sitemaps`

```jsonc
{
  "sitemap": [
    {
      "path": "https://example.com/sitemap.xml",
      "lastSubmitted": "2026-05-10T12:34:56Z",
      "lastDownloaded": "2026-05-12T03:11:42Z",
      "isPending": false,
      "isSitemapsIndex": true,
      "type": "sitemap",
      "errors": 0,
      "warnings": 2,
      "contents": [
        { "type": "web",   "submitted": 12345 },
        { "type": "image", "submitted":   980 }
      ]
    }
  ]
}
```

`type`: `sitemap` | `rssFeed` | `atomFeed` | `urlList` | `patternSitemap` | `notSitemap`.

`contents[].type`: `web` | `image` | `video` | `news` | `mobile` | `androidApp` | `iosApp` | `pattern`.

### Get

`GET /webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}`

`feedpath` — **URL-encoded** full sitemap URL: `https%3A%2F%2Fexample.com%2Fsitemap.xml`.

### Submit

`PUT /webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}`

Empty body. Idempotent — re-submitting the same feedpath refreshes `lastSubmitted`.

Requires `permissionLevel` in {siteOwner, siteFullUser} and OAuth scope `https://www.googleapis.com/auth/webmasters` (not `.readonly`).

### Delete (unsubmit)

`DELETE /webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}`

Removes the sitemap from the GSC list. Does not delete the file from your server and does not "deindex" URLs — Google still knows them from other sources.

## Important behaviors

- `isSitemapsIndex: true` — a sitemap-index file pointing to children. Children show up separately after the first `lastDownloaded`.
- `isPending: true` — submission accepted, not yet processed. Usually flips to false within minutes / hours.
- `errors > 0` — Google could not parse part of it. Not an API failure — see the UI for detail.
- `warnings` — soft issues (e.g. URLs in the sitemap that return 404).
- For a Domain property (`sc-domain:`) you can submit a sitemap for **any subdomain** within the domain.
- If the sitemap responds 404 or is robots.txt-blocked, `errors` accumulates; `submit` still returns 200 — visible only in the `errors` field.

## Sample — Python

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    "sa.json",
    scopes=["https://www.googleapis.com/auth/webmasters"],
)
svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

# List
res = svc.sitemaps().list(siteUrl="sc-domain:example.com").execute()
for sm in res.get("sitemap", []):
    print(sm["path"], sm.get("errors", 0), sm.get("warnings", 0))

# Submit
svc.sitemaps().submit(
    siteUrl="sc-domain:example.com",
    feedpath="https://example.com/sitemap-new.xml",
).execute()  # empty response on success
```

## Sample — Node.js

```js
import { google } from "googleapis";
const auth = new google.auth.GoogleAuth({
  keyFile: "./sa.json",
  scopes: ["https://www.googleapis.com/auth/webmasters"],
});
const sc = google.searchconsole({ version: "v1", auth });

const { data } = await sc.sitemaps.list({ siteUrl: "sc-domain:example.com" });
for (const sm of data.sitemap ?? []) console.log(sm.path, sm.errors, sm.warnings);

await sc.sitemaps.submit({
  siteUrl: "sc-domain:example.com",
  feedpath: "https://example.com/sitemap-new.xml",
});
```

## Common mistakes

- `feedpath` not URL-encoded → 400. Fix: `encodeURIComponent(...)`.
- Submitting a sitemap with `.readonly` scope → 403. Fix: use the full `webmasters` scope.
- Submitting a foreign domain on a Domain property → 400 "not under siteUrl". Fix: sitemap URL must be inside the property.
- Deleting a sitemap and expecting "deindexation" — will not happen. Google still knows the URLs from links / Discover.
