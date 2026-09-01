# Parser types — wordstat variants and direct

> **Важно:** имя параметра — `parser`, **не** `parser_type`. Это самая частая ошибка.
>
> Через MCP tool правильно:
> ```json
> { "method": "parser.get", "params": { "key": "...", "parser": "wordstat_q", "region_id": "0" } }
> ```
>
> Неправильно: `parser_type`, `type`, `parsertype` — Mutagen вернёт error 108 (options error).

The `parser` parameter on `mutagen.parser.get` and `mutagen.parser.mass.new` selects the data source AND the Wordstat modifier syntax applied to the query. Picking the wrong one gives the wrong number and wastes budget.

## Quick decision

| What you want | parser |
|---|---|
| Базовая (широкая) частотность Wordstat | `wordstat_n` |
| Частотность в кавычках `"фраза"` (фразовое соответствие) | `wordstat_q` |
| **Точная частотность** `!"фраза"` (форма слов фиксирована) | `wordstat_qs` |
| Частотность с порядком слов `[фраза]` (квадратные скобки) | `wordstat_no` |
| Кавычки + квадратные `"[фраза]"` | `wordstat_qo` |
| **Точная частотность с порядком слов** `"[!фраза]"` — эталонная для SEO | `wordstat_qso` |
| Левая колонка Wordstat (до 2000 ключей, 10 страниц) + ассоциации | `wordstat_key` |
| Левая колонка, первые 200 ключей с первой страницы | `wordstat_key_50` |
| Биды Яндекс.Директа (ставки + прогноз показов/кликов/CTR/budget) | `direct` |

## Modifier semantics — what each parser sends to Wordstat

Wordstat (Yandex.Wordstat) supports the following query modifiers; the parser types map 1:1:

| Modifier | Symbol | Parser type | Meaning |
|---|---|---|---|
| Базовая | (none) | `wordstat_n` | All matches containing any word in any form / order |
| Фразовое | `""` | `wordstat_q` | Matches containing the phrase, words may vary in form |
| Точное по форме | `!""` (or `! "..."`) | `wordstat_qs` | Words must be in the EXACT form (case + inflection) |
| Порядок слов | `[]` | `wordstat_no` | Order preserved, form flexible |
| Точное по форме + квадратные | `"[]"` | `wordstat_qo` | Combination |
| **Полное точное** | `"[!]"` | `wordstat_qso` | Order + exact form + phrase — narrowest possible |
| Левая колонка | (n/a) | `wordstat_key`, `wordstat_key_50` | List of related keys, not a frequency |

**Why `wordstat_qso` is the SEO standard:** it isolates pure search-demand for the exact phrase as users would type it. Looser variants over-count by including morphology and order variations.

## Per-parser response shapes

All responses are nested under `data` field of the parser.get / parser.mass.id envelope when `status` is `finish`.

### Frequency parsers: `wordstat_n`, `wordstat_q`, `wordstat_qs`, `wordstat_no`, `wordstat_qo`, `wordstat_qso`

```json
{ "frequency": 31460 }
```

A single integer — monthly impressions count according to Wordstat for the given modifier.

### Key-list parsers: `wordstat_key`, `wordstat_key_50`

```json
{
  "frequency": 31460,
  "count_keys": 1842,
  "array": {
    "купить mp3": 1820,
    "mp3 онлайн": 1450,
    ...
  },
  "assotiations": {
    "музыка mp3": 980,
    ...
  }
}
```

| Field | Meaning |
|---|---|
| `frequency` | Base frequency of the seed key |
| `count_keys` | Total left-column key count |
| `array` | Left-column: related queries (object: keyword → frequency) |
| `assotiations` | Right-column: ассоциации (related queries Yandex suggests; provider's spelling preserved) |

Differences:

- `wordstat_key` — up to 2000 keys across 10 result pages (left col) + associations.
- `wordstat_key_50` — first ~200 keys from the first page only. Faster, cheaper, less coverage.

Use `wordstat_key` for semantic-core expansion; `wordstat_key_50` for spot probes.

### Direct parser: `direct`

```json
{
  "shows": 12500,
  "bid1": 8.4,
  "bid2": 5.1,
  "bid3": 3.2,
  "all_positions": {
    "first_premium": {
      "shows": 850, "clicks": 47, "bid": 8.4, "budget": 394.8, "ctr": 5.5
    },
    "premium": {
      "shows": 5800, "clicks": 290, "bid": 5.1, "budget": 1479, "ctr": 5.0
    },
    "first_place": {
      "shows": 800, "clicks": 30, "bid": 3.2, "budget": 96, "ctr": 3.7
    },
    "std": {
      "shows": 500, "clicks": 15, "bid": 1.5, "budget": 22.5, "ctr": 3.0
    }
  }
}
```

| Field | Meaning |
|---|---|
| `shows` | Total monthly shows forecast |
| `bid1`, `bid2`, `bid3` | Premium / first / guaranteed bids (top-line) |
| `all_positions.first_premium` | Топ премиум блок (highest visibility) |
| `all_positions.premium` | Премиум блок |
| `all_positions.first_place` | Первое место гарантии |
| `all_positions.std` | Гарантированные показы (стандарт) |
| Per-position: `shows` / `clicks` / `bid` / `budget` / `ctr` | Прогноз для этой позиции |

Use for media-buying planning, contextual bid forecasting, and cross-check vs `check_key.direct.{spec,first,garant}` (those are price points; `direct` parser also gives volume forecasts).

## Region behavior

`region_id` parameter applies to all parsers. Default `"0"` means no region filter — global RU data.

- For frequency parsers (`wordstat_n` ... `wordstat_qso`): filtering by region shifts the count to that geo only — often 10x–100x smaller numbers.
- For `wordstat_key`: filtered list of related keys for that geo (often shorter).
- For `direct`: bid forecasts and shows projection for that geo's market.

Region codes are comma-separated. Prefix `-` excludes (e.g. `"255,-17"` = include 255 minus 17). See [regions.md](regions.md) for the numeric-code table.

## Picking the parser — decision flow

```
Need a single number for «сколько раз в месяц ищут [фразу]»?
├── Exact, как-есть, нужна для расчёта ROI → wordstat_qso
├── В кавычках, форма гибкая → wordstat_q
└── Broad (для оценки потолка спроса) → wordstat_n

Need related queries / семантическое расширение?
├── Полное расширение, до 2000 ключей → wordstat_key
└── Быстрая проба, первые 200 → wordstat_key_50

Need bid forecast / прогноз Direct?
└── direct
```

## Common mistakes

- Using `wordstat_n` for ROI calculation — over-counts by morphology, leads to overpaying for SEO content.
- Using `wordstat_q` thinking it's «точная» — it's phrase-match, NOT form-locked.
- Looping `parser.get` over hundreds of keys instead of one `parser.mass.new` — see [batch-strategy.md](batch-strategy.md).
- Mixing parser types in one analysis — comparing `wordstat_n` numbers to `wordstat_qso` numbers is meaningless.
- Forgetting region — global numbers for a Moscow-only campaign skew planning.
