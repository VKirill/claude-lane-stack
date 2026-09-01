# Validator Usage — scripts/validate-ads.py

CLI-валидатор character limits для Google Ads креативов. Корректно работает с Unicode (русский, кириллица, эмодзи).

## Запуск

```bash
python ~/.agents/skills/google/google-ads/scripts/validate-ads.py creative.yaml
```

или с JSON:

```bash
python ~/.agents/skills/google/google-ads/scripts/validate-ads.py creative.json
```

или через stdin:

```bash
cat creative.yaml | python ~/.agents/skills/google/google-ads/scripts/validate-ads.py -
```

## Input format — YAML

```yaml
format: RSA              # обязательное поле: RSA / PMAX / DISPLAY / DEMAND_GEN / VIDEO / APP / CALL / SHOPPING

# RSA / PMax / Display / Demand Gen / App example:
headlines:
  - "Headline 1 (≤30 chars for RSA / PMax / Display / App / Call)"
  - "Headline 2"
  # ... до 5-15 в зависимости от формата

descriptions:
  - "Description 1 (≤90 chars)"
  - "Description 2"
  # ... до 4-5

# RSA specific:
path1: "deals"           # до 15 chars
path2: "spring"          # до 15 chars
final_url: "https://example.com/sale"

# PMax / Display / Demand Gen specific:
long_headline: "..."     # ≤90 chars
business_name: "Acme"    # ≤25 chars
short_description: "..." # ≤60 chars (PMax only)

# Optional — Sitelinks (для Search кампаний с extensions):
sitelinks:
  - text: "Pricing"
    description1: "View all plans and pricing"
    description2: "Free 14-day trial"
    final_url: "https://example.com/pricing"

# Optional — Callouts:
callouts:
  - "Free Shipping"
  - "24/7 Support"
  - "5-Star Rated"

# Optional — Structured Snippets:
structured_snippets:
  - header: "Brands"
    values:
      - "Apple"
      - "Samsung"
      - "Google"
```

## Input format — Shopping (продукт-feed)

```yaml
format: SHOPPING
title: "iPhone 15 Pro 256GB Natural Titanium"
description: "Full product description, до 5000 chars..."
brand: "Apple"
gtin: "0194253433712"
mpn: "MTV63LL/A"
price: "999.00 USD"
availability: in_stock
condition: new
image_link: "https://example.com/iphone15pro.jpg"
google_product_category: "Electronics > Communications > Telephony > Mobile Phones"
```

## Input format — Video Ad

```yaml
format: VIDEO
sub_format: skippable_in_stream    # skippable_in_stream / bumper / non_skippable_in_stream / in_feed / shorts
headline: "Short Headline ≤15"     # для in-stream
description: "Two lines or one of 70"
cta: "Shop Now"                    # ≤10 для skippable
video_duration_sec: 30             # critical для bumper (6 exact)
companion_banner: "300x60"         # desktop only, optional
```

## Output format

```
================================================================
=== Google Ads Creative Validator ===
================================================================
Format: RSA — Responsive Search Ad

Headlines (3-15 required, 30 chars max each):
  [1] OK    27 chars  "Финансовое посредничество B2B"
  [2] OK    25 chars  "Партнёрство — это надёжно"
  [3] OK    16 chars  "ealliance-22.ru"
  ⚠ Only 3 headlines — Google recommends 8-10 for best performance

Descriptions (2-4 required, 90 chars max each):
  [1] FAIL  92 chars  "Объединяем экспортёров и импортёров..."
        ↳ Trim 2 chars
  [2] OK    85 chars  "Платформа для B2B-сделок..."

Paths (15 chars max each):
  path1     OK   3 chars  "b2b"
  path2     OK  11 chars  "partnership"

Final URL: OK (valid format)

================================================================
VERDICT: ❌ 1 hard fail, 1 recommendation.
Action: trim descriptions[1] by 2 chars, then re-run.
Optional: add 5 more headlines for Excellent ad strength.
================================================================
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All checks passed (warnings OK) |
| 1 | At least one hard fail (length / count / format violation) |
| 2 | Invalid input file (parse error / missing required fields) |
| 3 | Unknown format value |

Использование в скриптах:

```bash
python validate-ads.py creative.yaml
if [ $? -eq 0 ]; then
  echo "Ready to upload to Google Ads"
else
  echo "Fix errors before launch"
  exit 1
fi
```

## Что валидатор проверяет

### Length (per-asset)
- Headlines ≤ format-specific limit (30 / 15 / 40 для Demand Gen)
- Descriptions ≤ 90 (Video: 70 OR 2×35)
- Long headline ≤ 90
- Short description (PMax) ≤ 60
- Business name ≤ 25
- Paths ≤ 15
- Sitelink text ≤ 25, descriptions ≤ 35
- Callouts ≤ 25
- Structured snippet values ≤ 25
- Shopping title ≤ 150
- Shopping description ≤ 5000

### Count (min/max per format)
- RSA: 3-15 headlines, 2-4 descriptions
- PMax: 3-5 headlines, 2-5 descriptions
- Display: 1-5 headlines, 1-5 descriptions
- etc. (per format)

### Required fields
- Final URL (для всех clickable форматов)
- Format type (обязательно указать)
- Specific format-required fields (business_name для PMax / Display, etc.)

### URL format
- Final URL = valid HTTP/HTTPS URL
- No spaces, no malformed structure

### Editorial heuristics (warning level)
- Excessive `!!`, `???`, `★★★`, `🔥🔥🔥` → warning
- ALL CAPS more than 1 word → warning
- Repeated text across headlines (Google помечает дубли) → warning

### Soft recommendations
- "Only 3 headlines — Google recommends 8-10"
- "Pinning detected on >2 headlines — reduces ad strength"
- "Description очень похож на headline — diversify"

## Что валидатор НЕ проверяет

- **Policy compliance** (healthcare claims, financial guarantees, etc.) — это manual review через [policies.md](policies.md)
- **Quality Score** — это runtime Google metric, не check-able до запуска
- **Landing page quality** — отдельный manual check
- **Trademark violations** — Google автодиспрувает но мы не можем preflight
- **Bid / budget reasonableness** — это стратегический вопрос, не technical

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'yaml'`
Установите PyYAML: `pip install pyyaml`. JSON работает без зависимостей.

### Error: `Invalid format value: 'RSA_ADS'`
Формат — `RSA` (uppercase), не `RSA_ADS`. Полный список: RSA / PMAX / DISPLAY / DEMAND_GEN / VIDEO / APP / CALL / SHOPPING.

### Warning: "Headline contains keyword X times"
Информационный warning о keyword stuffing risk. Не блокирует.

### Output shows `?` characters
Если терминал не UTF-8, output может быть нечитаемым на нерусских символах. Установите locale: `export LANG=ru_RU.UTF-8`.

## Integration в workflow

### Как ads-specialist использует validator

После написания креатива:

1. Save creative as `creative.yaml` (или передай через stdin).
2. Run validator.
3. Если exit code 0 — переход к pre-launch checklist.
4. Если exit code ≥1 — исправить, re-run.
5. Только после exit code 0 — сдача клиенту.

### CI integration (опционально)

В будущем можно добавить hook на PostToolUse Write, который автоматически валидирует все `*-ads.yaml` файлы в проекте. Сейчас — manual invocation.
