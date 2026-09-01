# Cookbook — mutagen_api recipes for mcp-mutagen
Last verified: 2026-05-18 against https://mutagen.ru/?p=api

> Use these recipes via mcp-mutagen tool `mutagen_api({method, params})`.
> For competition check of phrases — convenience tool `mutagen_competition({phrases})`.

---

## Subscription requirements

> **SERP reports require a paid Mutagen subscription.**
> Without an active subscription every `serp.report` call returns `error_id=111`.
> Free-tier methods (accessible without a subscription): `balance`, `check_key`, `progects`.

If you see `error_id=111`, the account has no active SERP-report subscription. Purchase one at
https://mutagen.ru/?p=price or check active subscriptions at https://mutagen.ru/?api_config.

---

## Free tier methods

These methods work on any Mutagen account, regardless of subscription status.

### balance — current account balance

```js
mutagen_api({ method: 'balance' })
```

Returns: `{ balance: 142.50 }` (rubles remaining on account)

Use before any paid batch to gate execution.

---

### check_key — keyword competition (score 1-25 + Direct prices)

```js
mutagen_api({ method: 'check_key', params: { key: 'молитва' } })
```

Returns: `{ strong: 14, wordstat: 22000, direct: { spec: 4.20, first: 3.10, garant: 1.80 } }`

- `strong` — competition level 1 (low) to 25+ (extremely competitive)
- `wordstat` — broad-match Wordstat frequency
- `direct.spec` / `direct.first` / `direct.garant` — Yandex Direct bid estimates in RUB

> Note: for batch competition checks use `mutagen_competition({phrases: [...]})` tool instead — it
> handles async polling, deduplication, and 30-day caching automatically.

The `mutagen_api` tool also handles async polling for `check_key` automatically: it submits
`check_key.new`, then polls `check_key.get` until `status='completed'` or `poll_timeout_sec` is
reached (default 60 s).

---

### progects — list user projects

```js
mutagen_api({ method: 'progects' })
```

Returns: `[{ progect_id: 123, name: 'Treba Online' }, ...]`

To list keywords in a project (with cluster IDs):

```js
mutagen_api({ method: 'progect.keywords', params: { progect_id: 123 } })
```

Returns: `[{ keyword: 'молитва луке крымскому', claster_id: 45 }, ...]`

---

## Paid tier — SERP reports (mutagen.serp.report)

> Requires active subscription. Check balance and subscription status before running reports.

Generic call shape:

```js
mutagen_api({ method: 'serp.report', params: { report: '<type>', region: 213, ...args } })
```

Note: `region` accepts either the numeric Yandex region ID (213 = Moscow) or the Mutagen string
alias (`yandex_msk`). Both are accepted by the API.

---

## Top-4 most useful recipes (detailed)

### 1. report_keyword_positions_organic — organic SERP for a keyword (top-50)

**Use case:** see who ranks in the top 50 for a specific search phrase in Moscow.

```js
mutagen_api({
  method: 'serp.report',
  params: {
    report: 'report_keyword_positions_organic',
    keyword: 'молитва',
    region: 'yandex_msk',
  }
})
```

**Returns:** array of up to 50 rows, each containing:
- `position` — organic rank (1–50)
- `url` — ranking page URL
- `domain` — domain of the ranking page
- `title` — page title
- `snippet` — SERP snippet text
- `domain_organic_keywords` — total keywords the domain ranks for
- `domain_organic_wsqso` — estimated monthly organic traffic for the domain
- `visibility` — domain visibility index

**Estimated cost:** ~5 RUB per call.

**Tip:** use `count: 1` to probe row count before fetching; then paginate with `limit` + `offset`.

---

### 2. report_keywords_organic — all keywords a site ranks for in organic

**Use case:** full semantic core of a domain — every phrase it appears for in organic, with
positions and traffic data.

```js
mutagen_api({
  method: 'serp.report',
  params: {
    report: 'report_keywords_organic',
    domain: 'treba-online.ru',
    region: 'yandex_msk',
    sort: '-region_wsqso',
    limit: 100,
  }
})
```

**Returns:** array of rows, each containing:
- `keyword` — search phrase
- `position` — organic position for this phrase
- `region_wsqso` — точная частотность (regional)
- `domain_organic_wsqso` — estimated monthly traffic from organic
- `visibility` — visibility score

**Estimated cost:** ~10 RUB for a mid-sized domain. Large domains can be significantly more —
always probe with `count: 1` first.

**Tip:** filter to top positions with `filter: [{ column: 'position', filter_type: 'less_or_eq', val: 10 }]`.

---

### 3. report_domain_competitors — organic competitors of a domain

**Use case:** find domains that compete with a target domain for the same organic keywords.

```js
mutagen_api({
  method: 'serp.report',
  params: {
    report: 'report_domain_competitors',
    domain: 'treba-online.ru',
    region: 'yandex_msk',
    sort: '-common_keywords',
    limit: 50,
  }
})
```

**Returns:** array of competitor domains, each containing:
- `domain` — competitor domain
- `common_keywords` — count of keywords both domains rank for
- `domain_organic_keywords` — total keywords the competitor ranks for
- `domain_organic_wsqso` — estimated monthly organic traffic of the competitor
- `visibility` — competitor visibility index

**Estimated cost:** ~3 RUB per call.

---

### 4. report_page_recommended_keywords — missed keywords for a page (growth potential)

**Use case:** find keywords that competitor pages rank for but this page does not — content gaps
and growth opportunities.

```js
mutagen_api({
  method: 'serp.report',
  params: {
    report: 'report_page_recommended_keywords',
    page: 'https://treba-online.ru/molitvy/luke-krymskomu',
    region: 'yandex_msk',
    sort: '-region_wsqso',
    limit: 100,
  }
})
```

**Returns:** array of recommended keywords, each containing:
- `keyword` — recommended search phrase
- `region_wsqso` — точная частотность for the phrase
- `position` — position the competitor ranks at for this phrase
- `competitor_domain` — which competitor ranks for this keyword
- `world_wsqso` — global точная частотность

**Estimated cost:** ~5 RUB per call.

---

## All 23 SERP report types (reference table)

| Report type | Element | Description | Required params | Est. cost |
|---|---|---|---|---|
| `report_keyword_info` | keyword, keywords | Aggregate stats per phrase: frequencies, bid costs, traffic projections | `keyword` or `keywords` (CSV ≤1000), `region` | ~1 RUB |
| `report_keyword_tailings` | keyword | Хвосты — long-tail variations from the normalised query form | `keyword`, `region` | ~3 RUB |
| `report_keyword_variations` | keyword, keywords | Morphological variations of the input phrase | `keyword` or `keywords`, `region` | ~2 RUB |
| `report_keyword_expansion` | keyword | Дополняющие фразы — related/LSI phrases co-occurring on same SERPs | `keyword`, `region` | ~3 RUB |
| `report_keyword_positions_organic` | keyword | Top-50 organic results for the query with domain/page metrics | `keyword`, `region` | ~5 RUB |
| `report_keyword_positions_ppc` | keyword | PPC advertisers showing for the keyword with traffic forecast | `keyword`, `region` | ~3 RUB |
| `report_keywords_organic` | domain, domain_with_subdomains, page | All keywords ranking in organic with position and traffic | `domain` or `page`, `region` | ~10 RUB |
| `report_keywords_organic_up` | domain, domain_with_subdomains, page | Поднявшиеся фразы — keywords improving in position since last update | `domain` or `page`, `region` | ~5 RUB |
| `report_keywords_organic_down` | domain, domain_with_subdomains, page | Упавшие фразы — keywords declining in rank | `domain` or `page`, `region` | ~5 RUB |
| `report_keywords_organic_new` | domain, domain_with_subdomains, page | New keywords appearing in organic | `domain` or `page`, `region` | ~5 RUB |
| `report_keywords_organic_lost` | domain, domain_with_subdomains, page | Потерянные фразы — keywords no longer ranking; prior position included | `domain` or `page`, `region` | ~5 RUB |
| `report_keywords_ppc` | domain, page | Keywords for which the domain runs context ads | `domain` or `page`, `region` | ~5 RUB |
| `report_keywords_ppc_history` | domain, page | Historical context-advertising keyword data | `domain` or `page`, `region` | ~5 RUB |
| `report_domain_pages` | domain | List of indexed pages with per-page keyword and traffic metrics | `domain`, `region` | ~5 RUB |
| `report_domain_subdomains` | domain | Subdomains with their organic/PPC performance | `domain`, `region` | ~3 RUB |
| `report_domain_competitors` | domain | Organic competitor domains (ranking for the same keywords) | `domain`, `region` | ~3 RUB |
| `report_domain_competitors_ppc` | domain | PPC competitor domains (advertising on the same keywords) | `domain`, `region` | ~3 RUB |
| `report_domain_advert` | domain | All active and inactive context advertisements | `domain`, `region` | ~3 RUB |
| `report_domain_advert_active` | domain | Currently active context advertisements only | `domain`, `region` | ~2 RUB |
| `report_domain_info` | domain | Aggregate stats: total keywords, traffic, visibility | `domain`, `region` | ~1 RUB |
| `report_page_info` | page | Page-level stats: ranking keywords, traffic, visibility | `page`, `region` | ~3 RUB |
| `report_page_competitors` | page | Organic competitor pages/domains for the page's queries | `page`, `region` | ~5 RUB |
| `report_page_recommended_keywords` | page | Рекомендуемые ключи — keywords competitors rank for, this page doesn't | `page`, `region` | ~5 RUB |

> Note: costs are estimates based on Mutagen pricing documentation. Actual costs may vary.
> Always verify current rates at https://mutagen.ru/?p=price and check balance first with
> `mutagen_api({ method: 'balance' })`.

---

## Async polling for check_key and parser.mass

The `mutagen_api` tool handles async polling automatically. You do not need to call `.new` and
poll separately.

**How it works — check_key:**
1. Tool submits `check_key.new`.
2. Tool reads `task_id` from response.
3. Tool polls `check_key.get?task_id=N` with exponential backoff until `status='completed'` or timeout.
4. Final result is returned when completed.

**How it works — parser.mass:**
1. Tool submits `parser.mass.new`.
2. Tool reads `id` (NOT `task_id`) from response.
3. Tool polls `parser.mass.id?mass_id=N` (NOT `.get`) until `status='finish'` or timeout.
4. Final result is returned when finished.

> **Critical difference:** `check_key` returns `task_id` and polls via `.get`.
> `parser.mass` returns `id` and polls via `.id` with param `mass_id`.

**Controlling timeout:**

```js
mutagen_api({
  method: 'check_key',
  params: { key: 'редкая фраза' },
  poll_timeout_sec: 120,  // wait up to 2 minutes (default: 60)
})

mutagen_api({
  method: 'parser.mass',
  params: { keys_list: 'фраза1\nфраза2', name: 'batch-1', parser: 'wordstat_qso' },
  poll_timeout_sec: 300,  // batch jobs take longer — default 300s via mutagen_parser_mass tool
})
```

**State machine — check_key:** `created` → `processed` → `completed` | `rejected` | `error`

- `completed` — result is ready, returned immediately
- `rejected` — insufficient balance or subscription issue (terminal state)
- `error` — processing error (terminal state, do not auto-retry)

**State machine — parser.mass:** `stop` → `process` → `finish` | `error`

- `finish` — batch result is ready
- `error` — terminal, do not auto-retry

---

## Pitfalls

- **error_id=111** → no active subscription for SERP reports. Free tier only includes `balance`,
  `check_key`, and `progects`. Purchase subscription at https://mutagen.ru/?p=price.

- **Region mismatch** — default region in Mutagen is `yandex_ru` (global). Moscow-specific
  data requires `region: 'yandex_msk'` (or `region: 213`). Omitting region returns
  Russia-wide data which differs significantly from city-specific SERP and frequency.
  Common Yandex region IDs: 213 = Moscow, 2 = Saint Petersburg, 54 = Yekaterinburg,
  65 = Novosibirsk, 11119 = Kazan, 47 = Nizhny Novgorod, 39 = Rostov-on-Don, 157 = Minsk.

- **Rate limits** — Mutagen rate limits are not publicly documented. The 30-day cache
  (`force_refresh: false`) significantly reduces call frequency. Use caching aggressively.

- **Large domain reports** — `report_keywords_organic` on a large domain can return tens of
  thousands of rows and cost 50+ RUB. Always probe with `count: 1` first:
  ```js
  mutagen_api({ method: 'serp.report', params: { report: 'report_keywords_organic',
    domain: 'example.ru', region: 'yandex_msk', count: 1 } })
  ```
  Then paginate with `limit` and `offset` if the count is acceptable.

- **Balance exhausted** → all paid tasks return `rejected` status. Check balance before batches:
  `mutagen_api({ method: 'balance' })` — if near zero, top up before running reports.

- **UTF-8 for Cyrillic** — all keyword params must be UTF-8 encoded. The `mutagen_api` tool
  handles encoding automatically, but verify if you pass pre-encoded strings manually.

- **Attribution requirement** — if you display Mutagen data publicly, Russian law and Mutagen
  ToS require attribution: *"Данные получены из Мутагена"*.

---

## Частые ошибки и как их избежать

| Метод | Было (неправильно) | Стало (правильно) | Что произошло |
|---|---|---|---|
| parser.get | `parser_type: wordstat_q` | `parser: wordstat_q` | options error 108 |
| parser.mass.new | poll через `.get` | poll через `.id` | task hangs forever |
| parser.mass | poll по `task_id` | poll по `id` field | missing task_id error |
| serp.report | GET с filter[] | POST с body | bad request / silent fail |
| serp.report | `report_type: ...` | `report: ...` | options error |
| parser.mass | `keys: [...]` | `keys_list: "key1\nkey2"` | options error |
