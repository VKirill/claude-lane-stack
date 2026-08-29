# CVD — Content Value Detector v2.3

## Метаданные

Тип: Standalone Skill
Совместимость: агентские LLM-системы, связка с Детектором роботности v3.8.12 (Mode B)
Эмпирическая база: "The Great Blogging Collapse" (Daniel Stanica, 2026), 100 блогов, 2022-2026
Требования к входным данным: полный текст T, URL (опционально), размер owned-аудитории (опционально для OAM)
Внешние API не требуются.

---

## 1. Область применения

Скилл оценивает заменяемость (replaceability) текстового контента AI-суммаризацией и связанную
с этим вероятность устойчивого ранжирования (Ranking Survival Probability, RSP).

Скилл НЕ оценивает: грамотность, стиль, объём, ключевые слова, техническое SEO.
Скилл оценивает: долю контента, теряющую ценность при AI-суммаризации, и структурные факторы,
влияющие на устойчивость страницы за пределами текста.

---

## 2. Входной контроль

1. Получить полный текст T. Если предоставлен только заголовок/мета — запросить полный текст.
2. Зафиксировать: длина T (слова/символы), URL (если есть), ниша.
3. Определить ближайшую нишу по таблице NII (п.6). При отсутствии точного соответствия —
   пометить `niche_source: extrapolated`.
4. Зафиксировать Same-Model Risk Flag: `true`, если саммаризация (Шаг 3) и юнитизация/diff-сверка
   (Шаги 4-6) выполняются одной моделью без разделения ролей на изолированные вызовы.

---

## 3. Саммаризация

1. Определить основной intent страницы (формат: "как сделать X" / "что такое Y" / "сравнение A и B").
2. Сгенерировать summary S: длина 15-20% от T, cap 300 слов; для текстов короче 500 слов — не более 40% от T.
3. Summary формируется как ответ лучшего реального answer engine (AI Overview / ChatGPT) на intent —
   не как сокращённый пересказ структуры текста. Запрещено умышленное упущение деталей.
4. Валидация: если T содержит FIRSTHAND-фрагменты, а S — ни одного, зафиксировать
   `warning: summary_may_underestimate_replaceability`. Если длина S < 80 слов — перегенерировать.

Вывод: `[NICHE]`, `[SAME_MODEL_RISK]`, `[INTENT]`, `[SUMMARY S]`

---

## 4. Юнитизация

Разбить T на Content Units (CU). Для каждого CU зафиксировать 4 атрибута: тип, вес, actionable-флаг,
(для CONCLUSION) результат travel-теста.

### 4.1. Типы CU

| Тип | Определение |
|---|---|
| FIRSTHAND | Личное действие автора (сделал, протестировал, сфотографировал, поехал, измерил) |
| DATA | Конкретные цифры, даты, оригинальные бенчмарки |
| CONCLUSION | Авторский вывод/интерпретация (проходит travel-тест, см. 4.3) |
| GENERIC | Общеизвестный факт, консенсусная информация |
| STRUCTURAL | Переходы, служебные фразы без содержательной ценности |
| MULTIMODAL | Визуальный/интерактивный артефакт (см. 4.4) |

### 4.2. Веса критичности (без нишевого дисконта)

| Вес | Условие |
|---|---|
| CRITICAL (3) | FIRSTHAND; уникальный DATA; CONCLUSION, прошедший travel-тест; MULTIMODAL-CRITICAL |
| MODERATE (2) | Частично уникальные детали, кейсы; MULTIMODAL-SUPPORTING; CONCLUSION, не прошедший travel-тест |
| LOW (1) | GENERIC, STRUCTURAL |

Вес CU определяется исключительно содержательной ценностью юнита. Нишевая калибровка применяется
только на этапе интерпретации итогового RS (п.7), не на этапе присвоения веса.

### 4.3. Travel-тест для CONCLUSION

Вопрос: "Мог бы кто-то дать этот же совет, никогда не оказавшись в описываемой ситуации?"

- ДА → понизить до MODERATE/GENERIC независимо от грамматической формы (первое лицо не защищает вес).
- НЕТ (вывод специфичен для случая и невоспроизводим без повторения действия) → сохранить CRITICAL.

### 4.4. Multimodal CU

| Подтип | Вес | Условие |
|---|---|---|
| MULTIMODAL-CRITICAL | 3 | Артефакт демонстрирует незаменимый текстом процесс (фото шагов, видео теста, схема стежок за стежком) |
| MULTIMODAL-SUPPORTING | 2 | Иллюстративный, заменимый элемент (стоковое фото, обложка) |

Правило: MULTIMODAL CU получают статус ABSENT в текстовом summary по определению (текст не переносит
визуальный контент). MULTIMODAL-CRITICAL автоматически включается в Irreplaceable Core Units (ICU).

### 4.5. Actionable-флаг

Для каждого CU зафиксировать бинарный атрибут `actionable: yes/no`.
`yes` — CU содержит конкретный шаг, инструкцию или проверяемое действие.
`no` — CU описывает факт, контекст или декларативное утверждение без указания действия.

Вывод: таблица CU `[# | Фрагмент | Тип | Вес | Actionable | Travel-тест (для CONCLUSION)]`

---

## 5. Diff-сверка и Counterfactual Value Check

### 5.1. Статусы присутствия в S

| Статус | Определение | Множитель |
|---|---|---|
| PRESENT-FULL | CU полностью и без потери уникальности передан в S | 1.0 |
| PRESENT-DEGRADED | CU упомянут в S, но обобщён (потеря уникальности) | 0.5 |
| ABSENT | CU отсутствует в S | 0.0 |

### 5.2. Counterfactual Value Check

Применяется только к CU с весом CRITICAL и статусом PRESENT-DEGRADED.

Вопрос: "Если пользователь видит только S, достаточно ли обобщённой версии для цели из INTENT,
или потеря детали существенно снижает качество ответа и вызывает необходимость клика по источнику?"

| Результат | Множитель |
|---|---|
| FUNCTIONALLY REPLACED — обобщение полностью закрывает потребность | 0.5 (без изменений) |
| FUNCTIONALLY MISSING — обобщение не закрывает потребность | 0.25 |

Для CU с весом MODERATE/LOW Counterfactual Check не применяется — используется стандартный множитель.

Вывод: обновлённая таблица CU `[# | Фрагмент | Тип | Вес | Статус | Counterfactual | Множитель]`

---

## 6. Niche Irreplaceability Index (NII)

NII не изменяет вес CU. NII задаёт baseline для интерпретации итогового RS.

| Ниша | Медиана трафика (2022-2026) | Baseline RS | Порог "аномально хорошо" |
|---|---|---|---|
| Parenting (малый блог) | +108% | ~35% | RS < 20% |
| DIY/crafts | +2% | ~40% | RS < 25% |
| Food/recipes | -44% | ~45% | RS < 30% |
| Travel | -74% | ~55% | RS < 35% |
| Lifestyle | -90% | ~65% | RS < 40% |
| Entrepreneurship | -93% | ~75% | RS < 45% |
| Health/wellness | -93% | ~75% | RS < 45% |
| Fashion | -95% | ~78% | RS < 50% |
| Finance | -99% | ~85% | RS < 50% |

Правило Niche-Adjusted RSP:

- RS ниже порога "аномально хорошо" → ВЫСОКАЯ (аномальный результат для ниши)
- RS в пределах ±15 п.п. от Baseline → СРЕДНЯЯ (типичный результат для ниши)
- RS выше Baseline на 15+ п.п. → НИЗКАЯ (хуже среднего даже для тяжёлой ниши)

---

## 7. Расчёт Replaceability Score

Raw RS = Σ(вес CU × множитель) / Σ(вес CU) × 100%

Округление до целого процента.

Niche-Adjusted RSP определяется по таблице п.6 на основе Raw RS.

### 7.1. Owned Audience Multiplier (OAM)

Effective RS = Raw RS × (1 − OAM_discount)

| Размер owned-аудитории | OAM_discount |
|---|---|
| 0 | 0% |
| до 1 000 | 5% |
| 1 000-10 000 | 10% |
| 10 000-50 000 | 20% |
| 50 000+ | 30% |

Применяется только при известном размере аудитории. При отсутствии данных поле `effective_rs`
не заполняется.

---

## 8. Классификация архетипа контента

Вычислить три производные плотности на основе весов и атрибутов CU из Части 4:

ExperienceDensity = Σ(вес CU типа FIRSTHAND или MULTIMODAL-CRITICAL) / Σ(вес всех CU)

ActionableDensity = Σ(вес CU с actionable=yes) / Σ(вес всех CU)

GenericityDensity = Σ(вес CU типа GENERIC или STRUCTURAL) / Σ(вес всех CU)

### Таблица классификации

| Условие | Архетип |
|---|---|
| ExperienceDensity > 0.4 И ActionableDensity > 0.4 | DEMONSTRATIVE |
| ExperienceDensity > 0.4 И ActionableDensity ≤ 0.2 | EXPERIENTIAL-DESCRIPTIVE |
| ExperienceDensity ≤ 0.2 И ActionableDensity > 0.4 | ACTIONABLE-GENERIC |
| ExperienceDensity ≤ 0.2 И GenericityDensity > 0.5 | DESCRIPTIVE |
| Остальные случаи | HYBRID |

Порядок проверки строгий, сверху вниз, первое совпадение фиксирует результат.

---

## 9. Citation Substrate Note

Обязательный фиксированный текст в финальном отчёте:

"Citation Substrate Note: низкий RS снижает риск замещения контента AI-суммаризацией на уровне
текста, но не гарантирует AI-цитирование страницы (только 38% AI-цитирований в 2026 приходят
из топ-10 органики против 76% в середине 2025; доминируют Reddit, YouTube, LinkedIn). Для повышения
вероятности цитирования — дистрибуция через community-платформы, видео, структурированные
первичные данные на собственном домене."

Флаг не влияет на расчёт RS/RSP.

---

## 10. Irreplaceable Core Units и Critical Loss Map

ICU: CU с весом CRITICAL и статусом ABSENT/PRESENT-DEGRADED, включая все MULTIMODAL-CRITICAL.

Critical Loss Map: CU с весом CRITICAL/MODERATE, ушедшие в ABSENT/PRESENT-DEGRADED, с приоритетом
записей, помеченных FUNCTIONALLY MISSING (п.5.2).

Вывод: топ-5 каждого списка.

---

## 11. Режимы работы

### Mode A — Solo Audit

Полный проход по Частям 2-10. Выход: Raw RS, Niche-Adjusted RSP, Effective RS (если доступен),
Archetype, ICU, Critical Loss Map, Citation Substrate Note.

### Mode B — Combined Risk Audit

Параллельный или последовательный вызов с Детектором роботности v3.8.12.

Combined Risk Index (CRI):

| Robotness | Replaceability | CRI |
|---|---|---|
| Высокая | Высокая | Критический |
| Высокая | Низкая | Умеренный (рерайт стилистики достаточен) |
| Низкая | Высокая | Умеренно-высокий (требуется доработка содержания) |
| Низкая | Низкая | Низкий |

### Mode C — Batch/Cluster Audit

Прогон Mode A по массиву страниц для выявления смысловой монокультуры (кластеров с системно
высоким Raw RS).

### Mode D — Business Model Overlay

Оценка структурной устойчивости сайта/страницы независимо от содержания текста.

| Признак | Проверка |
|---|---|
| Demonstrated Experience | Документируемое реальное действие (фото процесса, тестирование, личные данные) |
| Owned Audience | Email-лист, community, Telegram/WhatsApp-канал, независимый от поисковой выдачи |
| Product/Brand Tie | Продукт/услуга/бренд, монетизирующий не только через клик по рекламе/партнёрке |
| Brand Search | Аудитория ищет сайт/автора по имени |

Business Risk Index (BRI) = количество признаков "да" (0-4).

Комбинированная рекомендация (Mode A × Mode D):

| Raw RS | BRI | Рекомендация |
|---|---|---|
| Низкий | 3-4 | Инвестировать — устойчивый актив |
| Низкий | 0-1 | Строить owned audience, не улучшать текст далее |
| Высокий | 3-4 | Доработать текст — бренд смягчает риск |
| Высокий | 0-1 | Критическая зона: консолидация / конвертация / продуктизация / продажа |

### Mode E — Deep Text Quality Signals (опциональный, не влияет на RS/Archetype)

Дополнительный диагностический слой для качественного аудита текста. Не участвует в расчёте
Raw RS, Effective RS или Archetype — вычисляется отдельно, во избежание дублирования с CU-метриками.

Шесть шкал, значение 0.0-1.0 каждая:

| Сигнал | Определение |
|---|---|
| Specificity Density | Доля утверждений с числами/датами/именами собственными/проприетарными терминами |
| Authorship & Expertise | Наличие и верифицируемость авторства (имя, credentials, биография) |
| Experience Markers | Плотность языковых маркеров личного опыта в тексте (не тождественно доле FIRSTHAND CU) |
| Objectivity/Neutrality | Отсутствие манипулятивной лексики, суперлативов, гарантийных формулировок |
| Actionability | Доля пошаговых/императивных конструкций от общего объёма |
| Structure & Justification | Наличие списков, таблиц, сравнений, явных value propositions |

E-E-A-T Text Proxy (композит из сигналов Mode E):

| Компонент E-E-A-T | Источник | Порог HIGH/MEDIUM/LOW |
|---|---|---|
| Experience | Experience Markers | >0.5 / 0.2-0.5 / <0.2 |
| Expertise | Authorship + Specificity | >0.6 / 0.3-0.6 / <0.3 |
| Authoritativeness | Structure & Justification + доля CONCLUSION CU | >0.5 / 0.2-0.5 / <0.2 |
| Trustworthiness | Objectivity | >0.7 / 0.4-0.7 / <0.4 |

E-E-A-T Text Proxy не заменяет реальную E-E-A-T оценку, требующую внешних сигналов (ссылочный
профиль, репутация домена, off-page данные). Используется как вспомогательный текстовый индикатор.

---

## 12. Выходные метрики

| Метрика | Диапазон | Режим |
|---|---|---|
| Raw RS | 0-100% | A |
| Niche-Adjusted RSP | anomalously_good / typical / worse_than_typical | A |
| Effective RS | 0-100% или null | A (при известном OAM) |
| Content Archetype | demonstrative / hybrid / descriptive / experiential-descriptive / actionable-generic | A |
| ICU | список | A |
| Critical Loss Map | список | A |
| Counterfactual Warnings | список | A |
| Same-Model Risk Flag | true/false | A |
| Citation Substrate Note | текст | A |
| Ranking Survival Probability | low/medium/high | A |
| Combined Risk Index | критический/умеренный/умеренно-высокий/низкий | B |
| Business Risk Index | 0-4 | D |
| Deep Text Quality Signals | 6 × 0.0-1.0 | E (опционально) |
| E-E-A-T Text Proxy | 4 × low/medium/high | E (опционально) |

---

## 13. Финальный отчёт

### Человекочитаемый формат

1. Вердикт: Raw RS = X%, Ниша = [...], Niche-Adjusted RSP = [...], Effective RS = [...] (если доступен)
2. Архетип: [...]
3. Топ-3 ICU
4. Топ-3 Critical Loss Map + Counterfactual Warnings
5. Рекомендация (Mode A, по таблице архетипа и RSP; при активном Mode D — по комбинированной матрице п.11)
6. Citation Substrate Note (обязательно)
7. (Mode E, если запрошен) Deep Text Quality Signals и E-E-A-T Text Proxy

### Машиночитаемый JSON

```json
{
  "skill": "CVD-2.3",
  "mode": "A|B|C|D|E",
  "same_model_risk": true,
  "intent": "string",
  "niche": "string",
  "niche_source": "table|extrapolated",
  "nii_baseline_rs": 0-100,
  "replaceability_score_raw": 0-100,
  "niche_adjusted_rsp": "anomalously_good|typical|worse_than_typical",
  "effective_rs": null,
  "owned_audience_size": null,
  "content_archetype": "demonstrative|hybrid|descriptive|experiential-descriptive|actionable-generic",
  "experience_density": 0.0,
  "actionable_density": 0.0,
  "genericity_density": 0.0,
  "irreplaceable_core_units": [
    {"text_fragment": "string", "unit_type": "firsthand|data|conclusion|multimodal", "weight": 1}
  ],
  "critical_loss_map": [
    {"text_fragment": "string", "status": "absent|degraded", "weight": 1}
  ],
  "counterfactual_warnings": [
    {"text_fragment": "string", "reason": "functionally_missing"}
  ],
  "ranking_survival_probability": "low|medium|high",
  "citation_substrate_note": "string",
  "business_risk_index": null,
  "deep_text_quality_signals": null,
  "eeat_text_proxy": null,
  "robotness_score": null,
  "combined_risk_index": null
}
```

---

## 14. Anti-adversarial правила

1. Summary (Часть 3) формируется на уровне лучшего реального answer engine. Запрещено умышленное
   упрощение/упущение деталей с целью занижения Raw RS.
2. Вес CRITICAL присваивается только за реально демонстрируемый firsthand-опыт, уникальные данные
   или MULTIMODAL-CRITICAL артефакт — не за уверенный тон или экспертную формулировку.
3. Travel-тест (п.4.3) применяется строго к каждому CONCLUSION независимо от грамматической формы
   изложения (первое лицо не защищает от понижения веса).
4. Если ниша системно неблагоприятна (Finance/Health/Fashion), итоговый вердикт не формулируется
   как "текст плохой" при RS в пределах Niche Baseline — используется Niche-Adjusted RSP (п.6).
5. Если текст на 90%+ состоит из GENERIC/STRUCTURAL CU — фиксировать это прямо в вердикте как
   сигнал, не как ошибку юнитизации.
6. При same_model_risk=true — явно указывать в отчёте, что оценка RS может быть занижена на 10-20%
   и рекомендован независимый повторный прогон другой моделью.
7. Mode E не участвует в расчёте Raw RS, Effective RS или Archetype. Смешение Mode E с ядром
   методологии запрещено во избежание дублирования одного и того же сигнала через разные метрики.
