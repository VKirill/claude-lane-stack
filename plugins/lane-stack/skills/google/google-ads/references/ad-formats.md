# 8 рекламных форматов Google Ads

Полное описание каждого формата 2026 года, с лимитами, лучшим применением и типичными ошибками. Лимиты по символам — в [character-limits.md](character-limits.md) (single source of truth), здесь даны только основные для контекста.

---

## 1. RSA (Responsive Search Ads) — поисковые объявления

### Что это
Динамические текстовые объявления в Google Search. Ты даёшь набор assets — Google собирает их в разные комбинации для разных запросов и пользователей.

### Структура
- **Headlines**: 3-15 штук, до **30 символов** каждый
- **Descriptions**: 2-4 штуки, до **90 символов** каждое
- **Path 1**: до **15 символов** (отображается в URL после домена)
- **Path 2**: до **15 символов** (вторая часть пути)
- **Final URL**: обязателен (destination URL)
- **Display URL**: собирается из domain + path1 + path2
- Pinning: можно закрепить headline на позицию 1, 2 или 3; description на позицию 1 или 2 (не рекомендуется без юр.необходимости)

### Когда использовать
- Lower-funnel: пользователь уже ищет твой продукт/решение
- Брендовые кампании (защита бренда)
- Конкурентные кампании
- High-intent keywords

### Не использовать когда
- Brand awareness / top-of-funnel — для этого Demand Gen / Video
- Visual-heavy продукт где текст не передаёт ценность — иди в Display / PMax
- Низкочастотные ключи без покупательского намерения

### Лучшие практики 2026
- **8-12 headlines** (минимум 3, оптимум 8-12) — диверсификация даёт +30% performance
- **3-4 descriptions** — больше assets = больше комбинаций для тестирования
- **Включать keyword в 2-3 headlines** — не во все (Google помечает как keyword stuffing)
- **Включать CTA** в 1-2 headlines: "Get a Free Quote", "Book a Demo Today", "Shop the Sale"
- **Включать USP** в 2-3 headlines: "24/7 Support", "Free Shipping", "5-Star Rated"
- **Pinning минимально** — только когда юридически обязан (например, регистрационный номер брокера)
- Ad Strength target: Excellent (Google показывает в редакторе)

### Типичные ошибки
- 3 headlines из минимума → low ad strength → low impressions
- Один и тот же headline в разных вариациях → Google игнорирует дубли
- Headlines >30 символов → ad disapproved
- Pinning всех headlines → теряется смысл responsive формата

---

## 2. Performance Max (PMax) — кросс-канальный AI

### Что это
AI-managed кампания работающая одновременно во всех Google-сетях: Search, Display, YouTube, Gmail, Discover, Maps. Ты даёшь **Asset Groups** — Google решает где и как показывать.

### Структура Asset Group
- **Headlines**: 3-5 штук, до **30 символов**
- **Long headlines**: 1+ штук, до **90 символов** (для Display формата)
- **Descriptions**: 2-5 штук, до **90 символов**
- **Short description**: 1 штука, до **60 символов** (для краткого формата)
- **Business name**: до **25 символов**
- **Final URL**: обязателен
- **Images**: minimum 1 marketing image (landscape 1200×628), 1 square (1200×1200), 1 logo (square / landscape); максимум 20 images
- **Logos**: square 1:1 (1200×1200) + landscape 4:1 (1200×300)
- **Videos**: minimum 1 video ≥10 sec (если нет — Google автогенерирует из images, качество низкое)
- **Audience signals**: подсказки Google кого таргетить (опционально, но рекомендуется)
- **Sitelinks, callouts, structured snippets**: ассеты extension типа

### Когда использовать
- Lower-funnel + conversion-focused
- Когда уже есть данные по conversion (минимум 30 конверсий за 30 дней — лучше работает)
- Когда хочешь охватить все Google-сети одной кампанией
- Когда есть time-bound промо (Black Friday, sale)

### Не использовать когда
- Совсем новый аккаунт без conversion data — PMax не будет учиться эффективно
- Узкий бренд-таргетинг (PMax сожжёт бюджет в Display сторону)
- Регулируемая ниша где нужен жёсткий контроль над where/how shows (PMax даёт мало визуальной прозрачности)

### Лучшие практики 2026
- Не запускать без хотя бы **50 конверсий в аккаунте** за последние 30 дней
- **Несколько Asset Groups** = разные user personas / use cases
- **Audience Signals**: подскажи Google кого таргетить (customer list / similar audiences / интересы)
- **Brand exclusion lists**: исключи свой бренд из таргетинга, если запускаешь параллельно brand Search кампанию
- **URL Expansion ON** — Google будет искать релевантные landing pages автоматически
- Минимум 2 недели на learning phase, не паниковать на спайки CPA

### Типичные ошибки
- Запуск без Audience Signals → Google долго ищет аудиторию → плохой CPA в первые 2 недели
- Один Asset Group для разных продуктов → не оптимизируется
- Слишком маленький дневной бюджет (<$50/day) → недостаточно данных для оптимизации
- Параллельный запуск с brand Search без exclusion → каннибализация

---

## 3. Display Responsive Ads — баннеры в Google Display Network

### Что это
Адаптивные баннеры в Google Display Network — 2+ млн сайтов, YouTube, Gmail. Google автогенерирует разные размеры/комбинации.

### Структура
- **Headlines**: до **5 штук**, до **30 символов**
- **Long headline**: 1 штука, до **90 символов**
- **Descriptions**: до **5 штук**, до **90 символов**
- **Business name**: до **25 символов**
- **Final URL**: обязателен
- **Images**: до 15 (landscape 1.91:1, square 1:1, portrait 4:5), max 5 МБ each
- **Logos**: square + landscape (опционально)
- **Videos**: до 5 (опционально)

### Когда использовать
- Brand awareness и remarketing
- Top-of-funnel
- Когда есть качественные изображения / иллюстрации
- Retargeting посетителей сайта

### Не использовать когда
- Search-intent клиент уже ищет тебя — иди в RSA
- Нет качественных изображений — Display без визуала бесполезен
- B2B sales cycle где Display плохо конвертит

### Лучшие практики 2026
- **5 headlines + 5 descriptions** — максимум диверсификации
- **Качественный визуал > всё остальное** — лучший headline на плохом баннере не работает
- **Минимум 5 images** в разных пропорциях
- **Frequency capping**: 3-5 impressions per user per day максимум
- **Placement exclusions**: исключи нерелевантные сайты (parking domains, mobile games, политика)

### Типичные ошибки
- Только одно изображение — Google не может оптимизировать
- Длинные tagline-style headlines — Display требует чёткой ценности
- Без frequency cap — ad fatigue → раздражение пользователя

---

## 4. Demand Gen Ads — Discovery + YouTube Shorts + Gmail

### Что это
Бывший Discovery Ads, переименован в 2024 в Demand Gen. Показывается в YouTube Shorts feed, YouTube Home, Gmail Promotions tab, Google Discover feed. Mid-funnel awareness/consideration.

### Структура
- **Headlines**: 1-5 штук, до **40 символов** ⚠ (исключение — не 30)
- **Long headline**: 1 штука, до **90 символов**
- **Descriptions**: 1-5 штук, до **90 символов**
- **Business name**: до **25 символов**
- **Final URL**: обязателен
- **Images**: до 15, 1.91:1 + 1:1 + 4:5
- **Logos**: square
- **Videos**: до 5

### Когда использовать
- Mid-funnel: пользователь не ищет активно, но может заинтересоваться
- Brand awareness для consumer brands
- Lifestyle / fashion / FMCG / DTC e-commerce
- Когда YouTube Shorts важный канал для аудитории

### Не использовать когда
- B2B Tech / SaaS — Demand Gen audience не тот
- Узкая ниша с малым охватом
- Performance-focused (используй PMax вместо)

### Лучшие практики 2026
- Visual-first thinking — это не Search, это feed
- Headlines работают как "stop the scroll" — должны быть intriguing
- Включай emotional triggers > rational
- Video assets > image assets (но both работают)

---

## 5. Video Ads (YouTube)

### Что это
Семейство видеоформатов на YouTube. Несколько подформатов:

### Подформаты

#### Skippable In-Stream
- Pre-roll / mid-roll, можно skip через 5 сек
- **Headline**: 15 символов
- **Description**: 2 lines × 35 символов each OR 1 line × 70 символов
- **CTA**: 10 символов
- **Companion banner**: 300×60 desktop only
- Длина видео: 12+ секунд (минимум для bid pricing); рекомендуется 30-90 сек

#### Bumper Ads
- Non-skippable, 6 секунд
- Только видео, no companion text overlays
- Pay per CPM
- Top-of-funnel awareness

#### Non-Skippable In-Stream
- 15-30 секунд, non-skippable
- Premium placement, high CPM
- Высокая видимость

#### In-Feed Video Ads (бывший Discovery)
- Показывается в feed YouTube, suggested videos
- **Headline**: 15 символов
- **Description**: 2 lines × 35 символов
- **Thumbnail**: custom (опционально)

#### YouTube Shorts Ads
- Vertical 9:16 видео
- В feed Shorts
- Длина: 10-60 секунд
- Часть Demand Gen или Video кампаний

### Когда использовать
- Brand awareness, reach
- Video-first продукты (FMCG, лайфстайл, edu)
- Стратегия омниканальная (Video + Search + Display)

### Лучшие практики
- **Hook за первые 3-5 секунд** — иначе skip
- CTA в первые 5 секунд (до skip-кнопки)
- Mobile-first composition (вертикальный или адаптивный)
- Brand name + logo в первые 5 секунд для bumper

---

## 6. App Campaigns (UAC — Universal App Campaigns)

### Что это
Кросс-канальные кампании для продвижения мобильных приложений. Show в Google Search, Play Store, YouTube, Display, Discover.

### Структура
- **Headlines**: до **5 штук**, до **30 символов**
- **Descriptions**: до **5 штук**, до **90 символов**
- **Videos**: 1+ (любой aspect ratio), до 20
- **Images**: до 20 (landscape + square + portrait)
- **HTML5 assets**: до 20 (опционально)
- **App store assets**: Google автоматически использует screenshots/icon из Play Store / App Store

### Когда использовать
- Install кампании для мобильных приложений
- Re-engagement существующих пользователей (Android only)
- iOS — частично, с ограничениями ATT iOS 14+

### Лучшие практики
- **Video > images** для App Campaigns
- Bidding: tCPI (target cost per install) или tROAS (target return on ad spend)
- Минимум 10 conversions/day для smart bidding
- Каждый asset группируется по theme (different audiences)

---

## 7. Call Ads — звонки прямо из поиска

### Что это
Search-объявления с большой кнопкой "Позвонить" вместо клика на сайт. Прямой звонок пользователя бизнесу.

### Структура
- **Business name**: до **25 символов**
- **Headlines**: 2 штуки, до **30 символов** каждая
- **Descriptions**: 2 штуки, до **90 символов** каждая
- **Verification URL**: обязателен (сайт компании, для верификации Google)
- **Phone number**: верифицируется Google
- **Show only on mobile**: рекомендуется (на desktop клики на телефон бесполезны)

### Когда использовать
- Local services: сантехник, доктор, юрист, ремонт, эвакуатор
- High-intent emergency запросы
- B2B sales где первый контакт по телефону критичен
- Когда LP с формой плохо конвертит

### Лучшие практики
- Headlines подчеркивают urgency: "24/7 Emergency", "Free Quote", "Call Now"
- Descriptions раскрывают service area, hours, qualifications
- Track calls через Google Forwarding Numbers (60+ secsa = conversion)
- Ставка call-only кампания vs Search RSA — A/B

---

## 8. Shopping Ads — feed-based catalog

### Что это
Feed-based product ads, показываются в Search Shopping tab, Google Display, YouTube Shopping, Discover. Не текстовые объявления — **product feeds** через Google Merchant Center.

### Структура feed
- **Title**: до **150 символов** (но первые 70 — критичны для CTR)
- **Description**: до **5000 символов**
- **Image URL**: обязателен, white background, no overlays/watermarks
- **GTIN**: глобальный товарный номер
- **MPN**: manufacturer part number
- **Brand**: обязателен
- **Price**: с валютой
- **Availability**: in_stock / out_of_stock / preorder
- **Condition**: new / refurbished / used
- **Product category**: Google taxonomy

### Когда использовать
- E-commerce с physical products
- B2C онлайн-магазины
- Catalog 50+ SKU
- Достаточная маржа чтобы платить за clicks

### Лучшие практики
- **Title первые 70 символов**: brand + model + key attribute (size/color/material)
- **High-res images**: white background, full product visible, не cropped
- **Feed quality > всё**: ошибочный feed = низкие impressions
- **GTIN критичен**: товары без GTIN получают меньше показов
- **Дисциплина наполнения custom_label**: для сегментации в bidding

### Типичные ошибки
- Title с маркетинговыми фразами ("Best Deal!", "Limited Stock!") — Google помечает feed как low-quality
- Image с overlay (badges, text, watermarks) — automatic disapproval
- Заявленная цена не совпадает с landing page — disapproval

---

## Сводная таблица — какой формат когда

| Цель / контекст | Рекомендуемый формат |
|---|---|
| Lower-funnel search-intent | RSA |
| Конверсия + multi-channel + 50+ конверсий в аккаунте | PMax |
| Brand awareness + visual | Display + Video |
| Mid-funnel discovery (Shorts feed) | Demand Gen |
| Mobile app installs | App Campaigns (UAC) |
| Local services / звонки | Call Ads |
| E-commerce каталог | Shopping |
| Brand safety priority + visual | Video (manually-curated placements) |
| Retargeting посетителей сайта | Display Remarketing |

## Связки форматов в одном аккаунте

Хорошие маркетинговые стеки:
- **B2B SaaS**: RSA (brand+competitor+intent) + Demand Gen (awareness) + LinkedIn rare for sync
- **E-commerce DTC**: PMax (lower-funnel) + Shopping (catalog) + Demand Gen (awareness) + Display Remarketing
- **Local Services**: Call Ads + RSA Local + Performance Max Local
- **Mobile App**: App Campaigns (install) + YouTube Shorts (awareness)
- **Enterprise B2B**: RSA (high-intent) + Video (thought leadership) + Demand Gen exclude prospects

См. также: [character-limits.md](character-limits.md) для всех точных лимитов, [creative-frameworks.md](creative-frameworks.md) для подходов к копирайтингу.
