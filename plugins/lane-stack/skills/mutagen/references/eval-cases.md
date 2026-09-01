# Eval cases — routing tests

v3 format: **user-voice phrasing** (Russian / typos / incomplete wording) + **Expected behavior** column (which sub-files should load, not just "this skill activates").

## Positive — should activate (12)

| User-voice prompt | Expected behavior |
|---|---|
| "проверь точную частотность через mutagen для 500 ключей" | Load `batch-strategy.md` + `parser-types.md` (wordstat_qso) + `methods.md` (parser.mass.new); enforce dedup + balance pre-check |
| "напиши клиент mutagen.ru на httpx" | Load `integration-python.md` + `setup.md` + `recommended-defaults.md` |
| "mutagen client в Node.js TypeScript" | Load `integration-node.md` + types section + `recommended-defaults.md` retry policy |
| "mutagen.check_key зависает на processed что делать" | Load `troubleshooting.md` (stuck processed) + `check-key-async-pattern.md` polling backoff |
| "конкуренция директа через mutagen API" | Load `methods.md` (check_key) + `check-key-async-pattern.md` (strong, direct.spec/first/garant) |
| "массовая проверка частотности яндекс через mutagen" | Load `batch-strategy.md` + `parser-types.md` (wordstat_qso) + dedup pattern |
| "SERP отчет mutagen по домену конкуренты" | Load `serp-report.md` (report_domain_competitors) + `filtering.md` + `regions.md` |
| "mutagen упавшие фразы за месяц для домена" | Load `serp-report.md` (report_keywords_organic_down) + `filtering.md` |
| "wordstat_qso vs wordstat_n разница в mutagen" | Load `parser-types.md` (modifier semantics table) |
| "мутаген баланс упал — почему" | Load `troubleshooting.md` (balance 0) + `pricing-and-balance.md` reconciliation |
| "claster_id в mutagen что это" | Load `projects-and-clustering.md` (claster_id semantics) |
| "filter mutagen serp report gr_or_eq val 100" | Load `filtering.md` (17 filter types) + `serp-report.md` |

## Negative — should NOT activate (10)

| User-voice prompt | Should route to | Why |
|---|---|---|
| "Wordstat API напрямую от Яндекса" | **wordstat-api** (cascade) | Direct Yandex API, not Mutagen |
| "Key Collector pro десктоп лицензия" | **key-collector** (cascade) | Desktop tool, not Mutagen |
| "Топвизор парсинг через API" | **topvisor-api** (cascade) | Different RU SEO SaaS |
| "Rush Analytics массовая проверка" | **rush-analytics** (cascade) | Different RU SEO SaaS |
| "Semrush domain overview API" | **semrush** (cascade) | Foreign SEO, different API |
| "Ahrefs backlink check" | **ahrefs** (cascade) | Foreign SEO |
| "Google Keyword Planner forecast" | **google-ads-api** (cascade) | Google data, Mutagen is Yandex-only |
| "Selenium парсинг wordstat" | **playwright** / **selenium** | Browser automation, not Mutagen API |
| "Spyserp / Spywords API" | **spywords** (cascade) | Different RU SEO SaaS |
| "Serpstat API connect" | **serpstat** (cascade) | Foreign / RU SEO SaaS, different API |

## Edge cases — 5

| User-voice prompt | Resolution |
|---|---|
| "собрать семядро через mutagen и скрапить выдачу через httpx" | Cross-skill: **mutagen** PRIMARY (`batch-strategy.md` + `parser-types.md`) + cross-link **httpx** for downstream scraping |
| "сравни mutagen vs Key Collector для сбора частотности" | Out of scope for direct integration — this skill is mutagen-only. Surface differences (cloud REST vs desktop UI) without claiming Key Collector details |
| "интеграция mutagen в Telegram-боте для SEO-команды" | **mutagen** PRIMARY (`integration-python.md` or `integration-node.md`) + cross-link **telegram-bot** for bot scaffolding |
| "кластеризация семантики после mutagen в Python" | **mutagen** primary for fetching `claster_id` (`projects-and-clustering.md`); custom clustering algorithm = general data-science task; cross-link **scikit-learn** if relevant |
| "хочу dashboard на vechkasov.pro показывать частотность из mutagen" | **mutagen** primary chain (`integration-python.md` + `setup.md`) + **REQUIRED** attribution per public-service rule (see [setup.md](setup.md)) + cross-link **nextjs** for the dashboard |

## How to verify (manual)

1. Open a fresh session with this skill loaded.
2. Paste each Positive prompt → confirm:
   - The system reminder lists `mutagen` as an active skill.
   - The response references files matching the "Expected behavior" column.
   - Specific Mutagen terms appear: `mutagen.check_key`, `mutagen.parser.mass`, `mutagen.serp.report`, `wordstat_qso`, `region_wsqso`, `claster_id`, `strong`, `task_id`, `mass_id`, `точная частотность`, `yandex_msk`, etc.
3. Paste each Negative prompt → confirm `mutagen` does NOT appear in the routed skill response, and the suggested fallback skill is mentioned.
4. Edge cases: confirm the response calls out the cross-link explicitly ("primary: mutagen, see also: httpx / telegram-bot / nextjs").

If a prompt routes wrong:

- Negative becoming Positive → tighten SKIP rules in `description` (e.g. add the missing competitor name).
- Positive becoming Negative → add the missing trigger term to `description` (it already includes `mutagen.ru`, `мутаген`, `mutagen.check_key`, `mutagen.parser.mass`, `mutagen.serp.report`, `wordstat_qso`, `claster_id`, `точная частотность`, `yandex_msk` etc.).
- Edge routing only to one skill → enrich Related Skills cross-links.

Run after any change to `SKILL.md` description or major reference restructure — that's the regression check.
