# Methods — full surface

Every method with signature, parameters, response shape. URL pattern for all calls:

```
http://api.mutagen.ru/json/{api_key}/{method}/?{params}
```

Where `{method}` is the dotted name with `/` instead of `.` (e.g. `mutagen.check_key.new` → `mutagen.check_key.new/`).

---

## Account

### `mutagen.balance()`

Returns current account balance in rubles.

**Params:** none.

**Response:**

```json
{ "balance": 1234.56 }
```

Type: `float`. Use to gate paid operations — see [pricing-and-balance.md](pricing-and-balance.md).

---

## Projects / Избранное

### `mutagen.progects()`

Lists the user's favorite-projects (built in the web UI).

**Params:** none.

**Response:**

```json
[
  { "progect_id": 123, "name": "ecommerce-core" },
  { "progect_id": 456, "name": "blog-content" }
]
```

Note: the documentation spells it `progects` (typo by the provider, preserved verbatim).

### `mutagen.progect.keywords(progect_id)`

Returns all keywords saved inside a project, each with its `claster_id` (cluster id from the кластеризация tool).

**Params:**
- `progect_id` (int, required)

**Response:**

```json
[
  { "keyword": "купить квадроцикл", "claster_id": 42 },
  { "keyword": "квадроцикл цена",  "claster_id": 42 },
  { "keyword": "электроквадроцикл", "claster_id": 51 }
]
```

See [projects-and-clustering.md](projects-and-clustering.md).

---

## Competition check — async (`check_key`)

PAID. Pay-per-call. See [pricing-and-balance.md](pricing-and-balance.md).

### check_key (асинхронный)
- **Submit:** `check_key.new` → возвращает `task_id`
- **Poll:** `check_key.get?task_id=N` ← method ends with `.get`, ID field `task_id`

### `mutagen.check_key.new(key)`

Submits a keyword for competition analysis. Returns a `task_id` immediately; result comes via `check_key.get`.

**Params:**
- `key` (string, required) — the search phrase to check

**Response:**

```json
{ "task_id": 9731540, "status": "created" }
```

Possible `status` values immediately after submit: `created` or `processed` (rare — if the worker grabbed it instantly).

### `mutagen.check_key.get(task_id)`

Fetches the result of a previously submitted task.

**Params:**
- `task_id` (int, required)

**Response — not yet ready** (mirrors `check_key.new`):

```json
{ "task_id": 9731540, "status": "processed" }
```

**Response — completed:**

```json
{
  "status": "completed",
  "key": "mp3",
  "strong": 25,
  "wordstat": 31460,
  "tails": 5174841,
  "direct": { "spec": 129.3, "first": 6.6, "garant": 6.6 },
  "vital": "",
  "vital_site": ""
}
```

Field meanings (from official docs, RU verbatim):

| Field | Type | Meaning (RU verbatim where present) |
|---|---|---|
| `status` | string | Lifecycle state — see below |
| `key` | string | The checked keyword |
| `strong` | int | Уровень конкуренции (competition score, scale ~1-25+) |
| `wordstat` | int | «количество просмотров по фразе в кавычках» — exact-match Wordstat impressions |
| `tails` | int | «количество просмотров хвостов» — long-tail impressions volume |
| `direct.spec` | float | «ставка спецразмещения» — premium Yandex.Direct placement bid (RUB) |
| `direct.first` | float | «ставка первого места» — first-position bid (RUB) |
| `direct.garant` | float | «ставка гарантированных показов» — guaranteed-impressions bid (RUB) |
| `vital` | string/bool | Flag indicating a vital ("тематический") site is present |
| `vital_site` | string | URL of the vital site, if present |

**Status lifecycle:**

| Status | Meaning |
|---|---|
| `created` | task just created, processing not started |
| `processed` | actively executing |
| `completed` | result is ready — all data fields populated |
| `rejected` | API refused to process the task (terminal) |
| `error` | parsing / query failure (terminal) |

See [check-key-async-pattern.md](check-key-async-pattern.md) for polling and idempotency.

---

## Parser — single keyword

### `mutagen.parser.get(key, parser, region_id="0")`

Single-keyword parse. Returns either an in-progress envelope or the completed data, depending on whether prior cached results exist.

**Params:**
- `key` (string, required)
- `parser` (string, required) — one of the parser types in [parser-types.md](parser-types.md)
- `region_id` (string, optional, default `"0"`) — region code(s); see [regions.md](regions.md)

**Response — in progress:**

```json
{ "status": "create" }
```

or `{ "status": "process" }`.

**Response — finished:**

```json
{ "status": "finish", "data": { ... } }
```

`data` shape depends on the `parser` type — see [parser-types.md](parser-types.md).

**Response — error:** `{ "status": "error" }`.

---

## Parser — batch (`parser.mass`)

### parser.mass (асинхронный)
- **Submit:** `parser.mass.new` → возвращает `id` (НЕ task_id!)
- **Poll:** `parser.mass.id?mass_id=N` ← method ends with `.id`, ID field `mass_id`

> **Не путать:** parser.mass поллится через `.id`, а не через `.get`.

### `mutagen.parser.mass.new(keys_list, name, parser, region_id="0")`

Creates a batch parsing job.

**Params:**
- `keys_list` (array OR comma-separated string, required) — list of keys
- `name` (string, required) — your label for the job
- `parser` (string, required) — see [parser-types.md](parser-types.md)
- `region_id` (string, optional, default `"0"`)

**Response:**

```json
{ "status": "stop", "id": 84321 }
```

or `{ "status": "process", "id": 84321 }`.

The `id` is the `mass_id` used by `parser.mass.id`.

POST is strongly recommended — see [setup.md](setup.md) GET/POST 128KB limit.

### `mutagen.parser.mass.list()`

Lists all batch jobs for the account.

**Response:**

```json
[
  {
    "id": 84321,
    "name": "semantics-2026-05",
    "parser": "wordstat_qso",
    "region_id": "0",
    "count": 1500,
    "time": 1715000000,
    "status": "finish"
  },
  ...
]
```

### `mutagen.parser.mass.id(mass_id)`

Retrieves the results of a specific batch job.

**Params:**
- `mass_id` (int, required) — the `id` returned by `parser.mass.new`

**Response — not yet ready:**

```json
{
  "id": 84321,
  "name": "semantics-2026-05",
  "parser": "wordstat_qso",
  "region_id": "0",
  "count": 1500,
  "time": 1715000000,
  "status": "process"
}
```

**Response — finished:**

```json
{
  "id": 84321,
  "name": "semantics-2026-05",
  "parser": "wordstat_qso",
  "region_id": "0",
  "count": 1500,
  "time": 1715000000,
  "status": "finish",
  "data": { ... per-parser shape ... }
}
```

Batch-job status values: `stop`, `process`, `finish`. (Note: differs from `check_key` lifecycle.)

See [batch-strategy.md](batch-strategy.md) and [parser-types.md](parser-types.md).

---

## SERP mega-tool

### `mutagen.serp.report(region, <element>, report, filter?, sort?, limit?, count?)`

Single endpoint switching on the `report` parameter. 22+ report types — see [serp-report.md](serp-report.md).

**Required:**
- `region` (string) — `yandex_ru` | `yandex_msk` | `yandex_spb` | `yandex_minsk` | `yandex_nsk` | `yandex_ekb` | `yandex_rostov` | `yandex_kazan` | `yandex_nn`. See [regions.md](regions.md).
- `<element>` (one of):
  - `keyword` (string) — single phrase
  - `keywords` (string, comma-separated, max 1000) — for batch keyword stats
  - `domain` (string)
  - `domain_with_subdomains` (string)
  - `page` (string) — full URL
- `report` (string) — one of the 22+ report types

**Optional:**
- `filter` (array of filter-object) — see [filtering.md](filtering.md)
- `sort` (string) — `"column_name"` or `"-column_name"` (desc)
- `limit` (int) — max rows
- `count` (1 / `true`) — return only `{"count": N}` row-count probe

**Response — data:**

```json
[ { col1: ..., col2: ..., ... }, ... ]
```

**Response — count probe:**

```json
{ "count": 5847 }
```

POST is strongly recommended when `keywords` is long or `filter` chain is large — see [setup.md](setup.md).

---

## Status fields summary

| Method family | Status values |
|---|---|
| `check_key.new` / `check_key.get` | `created`, `processed`, `completed`, `rejected`, `error` |
| `parser.get` | `create`, `process`, `finish`, `error` |
| `parser.mass.new` / `parser.mass.id` / `parser.mass.list` | `stop`, `process`, `finish`, `error` |

Note the inconsistency — `check_key` uses `created/processed/completed` while `parser` uses `create/process/finish`. Validate per-method. Both `rejected` (check_key only) and `error` (all) are **terminal** — do not auto-resubmit; see [troubleshooting.md](troubleshooting.md).
