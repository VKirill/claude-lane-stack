# Yandex.Webmaster — Links analysis

## External (inbound) links

### Samples — example inbound links

```
GET /v4/user/{user-id}/hosts/{host-id}/links/external/samples
    ?offset=0&limit=10
```

- `offset`: min 0, default 0
- `limit`: 1-100, default 10

**Response**:

```json
{
  "count": 12345,
  "links": [
    {
      "source_url": "https://referrer.com/blog/post1",
      "destination_url": "https://example.com/landing",
      "discovery_date": "2024-01-10",
      "source_last_access_date": "2024-01-14"
    }
  ]
}
```

- `count` — total external links to the site (not the current page size)
- `source_url` — where the link sits
- `destination_url` — which page of your site it points to
- `discovery_date` — when the bot first saw the link
- `source_last_access_date` — last time the bot fetched the source page (freshness)

### History — inbound link dynamics

```
GET /v4/user/{user-id}/hosts/{host-id}/links/external/history?date_from=&date_to=
```

Time series of inbound-link count per day. Useful for tracking SEO campaigns or link-mass losses.

## Internal (broken) links

### Samples — examples of broken internal

```
GET /v4/user/{user-id}/hosts/{host-id}/links/internal/samples
    ?offset=0&limit=10
    [&indicator=BROKEN]
```

**Response**:

```json
{
  "count": 123,
  "links": [
    {
      "source_url": "https://example.com/page-a",
      "destination_url": "https://example.com/deleted-page",
      "discovery_date": "2024-01-10"
    }
  ]
}
```

Returns pages with broken internal links where `source` links to a `destination` returning 4xx/5xx.

### History

```
GET /v4/user/{user-id}/hosts/{host-id}/links/internal/history?date_from=&date_to=
```

Time series for broken internal link count. A "technical health" metric.

## Pagination for large volumes

For sites with many links (count >> 100) — paginate via `offset`:

```python
async def fetch_all_external_links(client, host_id, max_per_page=100):
    all_links = []
    offset = 0
    while True:
        page = await client.links_external_samples(host_id, offset=offset, limit=max_per_page)
        if not page["links"]:
            break
        all_links.extend(page["links"])
        offset += max_per_page
        if offset >= page["count"]:
            break
    return all_links
```

**Note**: Webmaster API does not promise `samples` covers all links — it is a sample. For full backlink analytics use external SEO tools or referrer data from Yandex.Metrica (`yandex-metrica`).

## Common mistakes

- **Treating `count` as the current response size** — it is the **total**; for pagination compare with `offset + limit`.
- **Using `samples` for a full backlink dump** — not designed for that. Use external services for full coverage.
- **Comparing `external/history` with Yandex.Metrica** — Webmaster reports **links discovered by bot**; Metrica reports **referral visits**. Different metrics.
- **Surprised by changing `count` between calls** — Yandex updates data incrementally; the value drifts hour to hour.

## Use cases

- **Backlink audit**: monthly snapshot to your DB for trend lines and detecting sudden drops (potential SEO incident).
- **Health check**: alert when `links/internal/history` grows — navigation regressed.
- **Migration validation**: after a domain change — monitor `links/external/samples` for leftover links to the old domain (set up redirects).
