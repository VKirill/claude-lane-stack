# Pre-Launch Checklist — Google Ads

35-пунктовый чек-лист перед запуском. Не проходишь — не запускаешь. Деление: технический setup / creative / measurement / compliance.

## 1. Technical setup (10 пунктов)

- [ ] **Google Ads аккаунт активен**, billing настроен, payment method верифицирован
- [ ] **Зарубежное юрлицо** для оплаты (если клиент из РФ — критично, см. [russia-context.md](russia-context.md))
- [ ] **Conversion tracking** настроен — events GA4 + Google Ads conversion goals связаны
- [ ] **Enhanced Conversions** включены — user data hashing для better attribution
- [ ] **GTM container** установлен на сайте, проверен через Tag Assistant Debug
- [ ] **Google Analytics 4** property подключен и собирает данные (минимум 7 дней до launch)
- [ ] **Audiences** настроены — Remarketing list / Customer Match / Similar audiences
- [ ] **Negative keyword lists** загружены (global + per-campaign)
- [ ] **Campaign settings**: правильные locations / languages / devices / ad rotation
- [ ] **Budget pacing**: дневной бюджет установлен, monthly cap определён

## 2. Keyword research & match types (5 пунктов)

- [ ] **Keyword research** проведён — Keyword Planner + Ahrefs/SemRush
- [ ] **Match types** правильно использованы:
  - Exact `[keyword]` — для high-intent + brand
  - Phrase `"keyword"` — для controlled expansion
  - Broad — только с smart bidding + close monitoring
- [ ] **Negative keywords** добавлены — minimum 50 (general + ниша-specific)
- [ ] **Keyword groups** логичные — small (5-15 keywords per ad group)
- [ ] **Search query report** будет проверяться еженедельно в первый месяц

## 3. Creative (10 пунктов)

- [ ] **RSA: 8-12 headlines** на ad group (минимум 5)
- [ ] **RSA: 3-4 descriptions** на ad group
- [ ] **Headlines diverse** — разные angles (cost, time, trust, USP, CTA)
- [ ] **Keyword в 2-3 headlines, не во всех** — иначе keyword stuffing flag
- [ ] **Ad Strength = Good / Excellent** в Google Ads editor
- [ ] **Pinning минимально** — только legally required
- [ ] **Все assets прошли validator** — `scripts/validate-ads.py creative.yaml` → all pass
- [ ] **PMax: 5 images, 1 logo, 1 video minimum** в каждом Asset Group
- [ ] **Display: 5 images, 1 logo** в каждой Display Ad
- [ ] **A/B variants**: минимум 2 ad variations per ad group (для тестирования)

## 4. Extensions / Assets (5 пунктов)

- [ ] **Sitelink Extensions**: 4-6 sitelinks (минимум 2)
- [ ] **Callout Extensions**: 4-6 callouts
- [ ] **Structured Snippets**: минимум 1 snippet с 3+ values
- [ ] **Call Extension** (если применимо): phone number верифицирован
- [ ] **Promotion Extensions** (если есть offer): dates, discount type правильные

## 5. Landing page (5 пунктов)

- [ ] **Mobile responsive** — тест на iPhone + Android
- [ ] **Load time <3 sec** — проверен через PageSpeed Insights
- [ ] **HTTPS активен**, SSL certificate valid
- [ ] **Privacy policy linked**, GDPR-compliant (если EU traffic)
- [ ] **Match ad promise** — что обещает headline, то и на LP видно в первом fold

## 6. Compliance (бывает зависит от ниши)

- [ ] **Ниша allowed в Google Ads policies** (см. [policies.md](policies.md))
- [ ] **Если restricted ниша** (healthcare / finance / gambling / adult) — Google certification получена
- [ ] **Claims в ad copy обоснованы** в LP (если "best", "leading", "#1" — доказательство в LP)
- [ ] **No fake urgency** ("only 2 left!" каждый день)
- [ ] **No excessive punctuation / capitalization** — все assets прошли validator policy check

---

## Финальный sanity check перед "Enable Campaign"

| Вопрос | Ответ |
|---|---|
| Бюджет на день / месяц — клиент подтвердил? | yes / no |
| Целевой CPA / ROAS клиент знает реалистичный? (см. benchmarks.md) | yes / no |
| Conversion tracking покажет данные в GA4 через 24 ч? | yes / no |
| Если кампания не работает — какой план эскалации? | defined / not |
| Кто мониторит первые 7 дней ежедневно? | name / TBD |

Все yes → можно enable.

---

## Первые 7 дней (post-launch)

День 1:
- Проверить что impressions начались (через 1-3 часа)
- Если no impressions → check bid / budget / location / ad approval status

День 2-3:
- Search query report — какие реальные запросы триггерят ads
- Добавить obvious negative keywords

День 4-5:
- CTR analysis: какие headlines/descriptions работают, какие нет
- Если CTR <1% search → проблема с relevance

День 7:
- Quality Score первая оценка
- Cost per conversion vs target — корректировка бюджета или bid strategy

День 14:
- Learning phase обычно завершается
- Можно начинать оптимизацию более серьёзно

День 30:
- Полный performance review
- Решение: scale up / pause / iterate

---

## Если кампания disapproved

См. [policies.md](policies.md) → раздел "Что делать при disapproval". 4-шаговый процесс: read reason → identify policy → fix → resubmit.

---

## Если первые 7 дней нет impressions

Возможные причины:
1. **Bid too low** — увеличить bid или сменить bid strategy
2. **Quality Score = 1-3** — ad relevance / LP / CTR проблемы
3. **Targeting слишком narrow** — geo / device / language restrictions слишком жёсткие
4. **Ad disapproved** — check status, починить
5. **Budget exhausted** — daily budget слишком мал для niche CPC

---

## Если первые 7 дней impressions есть, но 0 conversions

1. **Conversion tracking сломан** — debug через Tag Assistant
2. **LP не работает / mismatch с ad** — пересмотр LP
3. **Mobile vs Desktop split** — может конвертит только один
4. **Keyword intent не покупательский** — пересмотр negative keywords
5. **Offer слаб** — A/B test другого offer / CTA
