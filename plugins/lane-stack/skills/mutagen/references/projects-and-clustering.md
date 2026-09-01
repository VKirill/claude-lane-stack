# Projects (Избранное) and `claster_id`

Mutagen.ru has a UI feature called «Избранное» — user-created projects holding curated keyword lists. The API exposes them read-only via two free methods.

## Methods

### `mutagen.progects()`

Lists all user projects.

Response:

```json
[
  { "progect_id": 123, "name": "ecommerce-core" },
  { "progect_id": 456, "name": "blog-content" }
]
```

Note: the provider's spelling is `progects` (typo). Preserved verbatim in URL path and field names.

### `mutagen.progect.keywords(progect_id)`

Returns the keywords saved inside a project, each with its `claster_id`.

Response:

```json
[
  { "keyword": "купить квадроцикл",      "claster_id": 42 },
  { "keyword": "квадроцикл цена",        "claster_id": 42 },
  { "keyword": "электроквадроцикл",      "claster_id": 51 },
  { "keyword": "квадроцикл для ребёнка", "claster_id": 78 }
]
```

Both methods are **free** (no balance debit).

## What is `claster_id`?

`claster_id` is the cluster identifier from Mutagen's кластеризация tool (web UI at `https://mutagen.ru/?p=clasterization`). Keywords with the same `claster_id` were grouped by Mutagen's clustering algorithm into a single semantic cluster — implying:

- They share enough SERP overlap to be reasonably targeted by ONE landing page.
- Or they share enough topical overlap to belong in one content brief.

The API doesn't expose:

- Cluster names / descriptions — only numeric IDs.
- Cluster creation / update endpoints — projects and clusters are managed via the Mutagen web UI.
- The clustering threshold / algorithm parameters used.

For details on the underlying tool, the docs reference the кластеризация product page; this skill does not cover the UI workflow.

## What projects are useful for

The API surface is intentionally narrow — projects are primarily a UI affordance. From an API consumer's perspective:

1. **Ops tracking** — humans curate a project list in the UI; your pipeline reads the project as a source of seed keywords.
2. **Cluster propagation** — if Mutagen's clustering produced useful groups, mirror `claster_id` into your downstream system to keep cluster cohesion intact across processing steps.
3. **Cross-checking** — verify your own clustering algorithm against Mutagen's output for the same keyword set.

What projects are NOT useful for:

- Pipeline state (use your own DB).
- Batch state for `parser.mass` (use `mass_id` and your own DB).
- A search / filter primitive — `mutagen.progect.keywords` returns ALL keywords; filter / split client-side.

## Reading a project — typical flow

```python
# Pseudo
async def fetch_project(client, progect_id: int) -> list[dict]:
    rows = await client.progect_keywords(progect_id)
    # Persist locally
    await db.upsert_project_keywords(progect_id, rows)
    return rows

async def fetch_all_projects(client) -> None:
    projects = await client.progects()
    for p in projects:
        await fetch_project(client, p["progect_id"])
```

## Group by `claster_id`

```python
from collections import defaultdict

clusters: dict[int, list[str]] = defaultdict(list)
for row in rows:
    clusters[row["claster_id"]].append(row["keyword"])

# clusters[42] = ["купить квадроцикл", "квадроцикл цена", ...]
```

This grouping is useful for:

- Generating per-cluster content briefs (one landing per cluster).
- Per-cluster SERP analysis (run `serp.report` once per cluster).
- Producing exports / dashboards organized by cluster rather than by keyword.

## Cross-skill usage

If you need to map cluster IDs to human-readable names, store the mapping in your own DB (e.g., a `mutagen_cluster_name` table you populate manually). Mutagen's API doesn't return cluster names.

For storing the project / cluster / keyword structure long-term, see [postgresql](../../postgresql) for schema patterns.

## What if `progects()` returns empty

If the user hasn't created any projects in the UI, `mutagen.progects()` returns `[]`. This is expected, not an error.

## What if `claster_id` is null or absent

Keywords added to a project but not yet clustered in the кластеризация tool may have `claster_id = 0` or `null`. Treat as "uncategorised" and surface in your downstream system accordingly.

## Privacy / access

Projects are tied to the account whose API key is used. There's no shared / team primitive in the API — if multiple ops need to collaborate, they share the account (and its API key — see [setup.md](setup.md) for key handling).
