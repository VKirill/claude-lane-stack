---
title: "GPT-5.6: методичка по выбору модели и уровня размышлений"
subtitle: "Практическое руководство: Sol / Terra / Luna · none → max · Pro · Ultra"
author: "Сводка по официальной документации OpenAI + практике Codex / API (июль 2026)"
date: "Июль 2026 · v1.0"
lang: ru-RU
mainfont: DejaVu Sans
sansfont: DejaVu Sans
monofont: DejaVu Sans Mono
geometry: margin=2.2cm
fontsize: 11pt
linestretch: 1.15
colorlinks: true
header-includes:
  - \usepackage{fancyhdr}
  - \usepackage{booktabs}
  - \usepackage{longtable}
  - \usepackage{array}
  - \usepackage{xcolor}
  - \usepackage{tcolorbox}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyhead[L]{\small GPT-5.6 · модель и reasoning}
  - \fancyhead[R]{\small Методичка v1.0}
  - \fancyfoot[C]{\thepage}
  - \renewcommand{\headrulewidth}{0.4pt}
  - \newtcolorbox{callout}{colback=blue!4,colframe=blue!45!black,boxrule=0.6pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt}
  - \newtcolorbox{warnbox}{colback=orange!6,colframe=orange!60!black,boxrule=0.6pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt}
  - \newtcolorbox{okbox}{colback=green!4,colframe=green!40!black,boxrule=0.6pt,arc=2pt,left=6pt,right=6pt,top=4pt,bottom=4pt}
---

\newpage

# О документе

**Назначение.** Дать однозначные правила: *какую модель GPT-5.6 взять* и *какой уровень reasoning (размышлений) выставить* — для API, Codex, ChatGPT и агентных пайплайнов.

**Источники.** Официальные гайды OpenAI (*Using GPT-5.6*, *Reasoning models*, *Model selection*, Introducing GPT-5.6), Codex-практика, обсуждения power-users в X и Reddit (r/codex и др.), июль 2026.

**Как читать.**

1. Разделы 1–2 — карта моделей и уровней (теория).
2. Разделы 3–5 — матрицы «когда что» (практика).
3. Разделы 6–8 — пресеты, миграция с 5.5, чеклисты.
4. Приложение — шпаргалка на одну страницу.

\begin{okbox}
\textbf{Главное правило в одной строке.}
Начинай с \textbf{минимального} тира и effort, которые дают нужное качество; поднимай только если eval/ревью показали просадку. На GPT-5.6 уровни \textbf{не} мапятся 1:1 с GPT-5.5 — часто хватает effort на один уровень ниже.
\end{okbox}

\newpage

# 1. Семейство GPT-5.6: три модели, не одна

GPT-5.6 — **семейство**. Alias `gpt-5.6` маршрутизирует на **`gpt-5.6-sol`** (флагман).

| Модель | API slug | Роль | Цена (ориентир, $/1M tokens) | Когда брать |
|--------|----------|------|------------------------------|-------------|
| **Sol** | `gpt-5.6` / `gpt-5.6-sol` | Максимальный интеллект | ~$5 input / $30 output | Сложный код, агенты, архитектура, hard research |
| **Terra** | `gpt-5.6-terra` | Баланс качество/цена | ~$2.50 / $15 | «Рабочая лошадка» прод, объём, большинство задач |
| **Luna** | `gpt-5.6-luna` | Скорость и throughput | ~$0.625 / $3.75 | Chat, classify, routing, batch, high-QPS |

## 1.1. Принцип выбора модели (OpenAI)

1. **Сначала accuracy.** Зафиксируй целевое качество (например: 90% успешных agent-runs).
2. **Потом cost и latency.** Удерживая accuracy, спускайся к более дешёвой/быстрой модели.
3. **Eval обязателен.** Меняй модель/effort только по замерам на *своих* задачах, не по бенчмаркам из анонсов.

\begin{callout}
\textbf{Практический порядок.}
Sol medium (baseline качества) → тот же effort на Terra → Luna. На каждом шаге: success rate, токены, wall-clock, \$. Оставляй самый дешёвый вариант, где quality в пределах допуска.
\end{callout}

## 1.2. Сильные стороны 5.6 (зачем вообще переходить)

- **Token-efficiency** — frontier-качество при меньшем числе output tokens, чем у 5.5.
- **Frontend / UI** — сильнее layout, hierarchy, design judgment.
- **Intent understanding** — лучше угадывает «сколько работы» нужно; меньше микроменеджмента шагов.
- **Новые режимы:** `max` effort, **Pro mode**, multi-agent (аналог Ultra в Codex), Programmatic Tool Calling, persisted reasoning.

\begin{warnbox}
\textbf{Подводный камень.}
Cache writes у 5.6 биллятся $\approx 1.25\times$ uncached input. На длинных agent-сессиях лимиты могут сгорать быстрее, чем «ожидали по 5.5», даже если «сырой» output меньше.
\end{warnbox}

\newpage

# 2. Уровни размышлений (reasoning.effort)

Параметр `reasoning.effort` (в Codex: *reasoning level*) задаёт, **сколько модель думает** до ответа. Больше effort → больше reasoning tokens, latency и стоимости. Модель **адаптивна**: на простых запросах тратит меньше, на сложных — больше *даже при том же уровне*.

## 2.1. Шкала API (GPT-5.6)

| Effort | Суть | Типичная latency | Типичная стоимость |
|--------|------|------------------|--------------------|
| `none` | Почти без «думания» | минимальная | минимальная |
| `low` | Лёгкое reasoning + tools | низкая | низкая |
| `medium` | Баланс (часто **default**) | средняя | средняя |
| `high` | Глубокий разбор | высокая | высокая |
| `xhigh` | Длинный горизонт / async | очень высокая | очень высокая |
| `max` | Потолок для hardest tasks | максимальная | максимальная |

В UI Codex/ChatGPT иногда встречаются **Light**, **Max**, **Ultra** — см. §2.3: это **не всегда** то же, что `reasoning.effort`.

## 2.2. Официальная матрица «best for» (по docs OpenAI)

| Effort | Лучше всего для | Примеры |
|--------|-----------------|---------|
| **none** | Latency-critical, без tool chains | Voice, classify, быстрый lookup |
| **low** | Tool-use, plan, search, multi-step *с* приоритетом скорости | Data analysis, draft, execution-coding, support |
| **medium** | Quality + reliability, planning, judgement | Agentic coding, research, slides/sheets, long-horizon work |
| **high** | Hard reasoning, complex debug, high-value agents | Сложный код, deep plan, knowledge work |
| **xhigh** | Deep research, async, long runs; **только** если eval доказал выигрыш | Security review, enterprise productivity, hard coding overnight |
| **max** | Максимум для самых сложных single-problem; сравнивай с xhigh | «Одна задача, цена ошибки огромна» |

\begin{okbox}
\textbf{Совет OpenAI при миграции с 5.5 / 5.4.}
Оставь текущий effort как baseline → прогони \textbf{тот же} и \textbf{на уровень ниже}. GPT-5.6 часто держит или улучшает quality при меньшем effort.
\end{okbox}

## 2.3. Max · Ultra · Pro — не путать

| Режим | Что это | Как включить | Когда |
|-------|---------|--------------|--------|
| **Effort `max`** | Один агент думает *максимально долго* над одной задачей | `reasoning.effort: "max"` | Самая жёсткая single-problem |
| **Ultra** (Codex) | Несколько **subagents параллельно** | Режим Ultra в Codex / multi-agent API | Задача **делится** на независимые ветки |
| **Pro mode** | Больше model work → **один** финальный ответ | `reasoning.mode: "pro"` | Quality-first; latency/cost вторичны |

\begin{callout}
\textbf{Mode и effort независимы.}
Можно: Pro + medium, standard + xhigh, Pro + max. Не считай «Pro = всегда xhigh». Сравнивай конфиги на одних и тех же задачах.
\end{callout}

### Когда Pro

**Да:** ошибка дорогая (migration, деньги, security); есть чёткие критерии; latency 2–10× ок.

**Нет:** high-QPS, интерактив «нужен ответ сейчас», evals не показывают прирост.

### Когда Ultra / multi-agent

**Да:** независимые модули, parallel research, разные срезы аудита.

**Нет:** один запутанный bug с сильной связностью; «размажет» scope и сожжёт токены.

\newpage

# 3. Когда какой уровень: полная матрица

## 3.1. По типу задачи

| Задача | Модель | Effort | Комментарий |
|--------|--------|--------|-------------|
| Голосовой / мгновенный чат | Luna | none / low | Latency first |
| Классификация, tagging, routing | Luna | none / low | High volume |
| Черновик письма / post | Luna / Terra | low | Style → в prompt, не в effort |
| Мелкий bugfix, rename, UI tweak | Terra или Sol | **low** | 5.6 часто «закрывает» low |
| Feature по **готовому** плану | Terra / Sol | low–**medium** | Execute, не re-architect |
| Написать SPEC / план / ADR | Sol | **medium–high** | Plan high → execute low |
| Agentic coding (я рядом) | Sol / Terra | **medium** | Default 80% дней |
| Hard debug (race, data loss) | Sol | **high** / xhigh | + Pro при цене ошибки |
| Security / deep code review | Sol | **xhigh** / max | Async ок |
| Deep research overnight | Sol | xhigh | Scope + done-criteria |
| Большой рефакторинг по модулям | Sol | high + **Ultra** | Только если параллелится |
| Frontend landing / design polish | Sol | medium | Сильная сторона 5.6 |
| Batch 10k документов | Luna | low / none | Caching, batch API |
| Customer support agent | Terra / Luna | low–medium | Escalate hard cases → Sol |

## 3.2. По «цене ошибки»

| Цена ошибки | Рекомендация |
|-------------|--------------|
| Низкая (черновик, brainstorm) | Luna / Terra · low |
| Средняя (фича, PR под ревью) | Terra / Sol · medium |
| Высокая (прод-миграция, платежи) | Sol · high ± Pro |
| Критическая (security, data loss) | Sol · xhigh / max + human gate |

## 3.3. По режиму работы человека

| Режим | Effort | Почему |
|-------|--------|--------|
| Pair-programming, я смотрю каждый diff | low–medium | Feedback loop быстрый |
| «Сделай PR, я проверю вечером» | medium–high | Меньше итераций |
| Unattended overnight, без меня | xhigh (узкий scope!) | Но **жёсткий** owns_paths / plan |
| «Я код не читаю, верь модели» | high–xhigh + тесты | Иначе лотерея |

\begin{warnbox}
\textbf{Антипаттерн №1.}
Sol Ultra / xhigh \textbf{на весь день execution} в monorepo 1000+ файлов. Часто: часы runtime, 100+ файлов, mess, быстрее burn лимитов. Правильно: \textbf{plan high} → \textbf{execute low/medium} по кускам.
\end{warnbox}

\newpage

# 4. Decision tree: что выбрать за 30 секунд

```
1) Какая ставка?
   · frontier / hard agent / hard code  → Sol
   · хорошее качество, много объёма    → Terra
   · QPS / batch / cheap chat          → Luna

2) Какой effort?
   · ответ за секунды, без tools       → none
   · мелкая правка / execute plan      → low
   · обычная работа / agent day-to-day → medium   ← START HERE
   · hard debug / deep plan            → high
   · long research / audit overnight   → xhigh
   · «одна суперсложная задача»        → max (± pro)

3) Нужен ли Pro?
   · да, если ошибка дорогая И evals зелёные
   · иначе standard

4) Нужен ли Ultra / multi-agent?
   · да, только если задача режется на независимые ветки
   · иначе Max/high на одном агенте
```

## 4.1. ASCII-дерево

```
Нужен frontier / hard multi-step?
├─ ДА → SOL
│   ├─ Я рядом, интерактив     → low / medium
│   ├─ Plan / design / hard bug → high
│   ├─ Deep review / research   → xhigh
│   ├─ Одна nightmare-задача    → max (± pro)
│   └─ Параллелится по частям   → Ultra / multi-agent
│
Нужен баланс цена/качество?
├─ ДА → TERRA · medium (hard steps: high/xhigh)
│
High volume / latency / \$?
└─ LUNA · none / low
```

\newpage

# 5. Рекомендованные пресеты

## 5.1. Daily coding (Codex / IDE)

| Слот | Модель | Effort | Заметки |
|------|--------|--------|---------|
| Default | Sol или Terra | **medium** | Старт дня |
| Quick fix | Terra / Sol | **low** | 1–3 файла |
| /plan | Sol | **high** | Только план, без кода |
| Execute plan | Sol / Terra | **low–medium** | По чеклисту |
| Review / audit | Sol | **xhigh** | Read-only |
| Overnight | Sol | **xhigh** | Узкий scope + tests |

**Команда Codex (пример):**

```bash
# Execute
codex -m gpt-5.6-sol -c model_reasoning_effort=medium

# Plan-heavy
codex -m gpt-5.6-sol -c model_reasoning_effort=high
```

## 5.2. Product API (продакшен)

| Слой | Модель | Effort | Mode |
|------|--------|--------|------|
| Hot path (chat, classify) | Luna | none / low | standard |
| Tool agent (обычный) | Terra | medium | standard |
| Escalation hard cases | Sol | high | ± pro |
| Offline batch | Luna | low | standard + Batch |

## 5.3. Research / аналитика

| Слой | Модель | Effort |
|------|--------|--------|
| Quick brief | Terra | medium |
| Deep dive | Sol | xhigh |
| Board one-shot | Sol | high / xhigh + **pro** |

## 5.4. Оркестратор (несколько ролей)

| Роль | Модель | Effort |
|------|--------|--------|
| Planner / architect | Sol | high |
| Coder / implementer | Terra или Sol | low–medium |
| Reviewer | Sol | high / xhigh |
| Tester (узкий scope) | Terra | medium |
| Cheap triage / router | Luna | none / low |

\begin{okbox}
\textbf{Золотой паттерн.}
Plan на Sol high → Execute на Terra/Sol medium (или low) → Review на Sol high/xhigh.
Не гоняй Ultra на каждый коммит.
\end{okbox}

\newpage

# 6. Миграция с GPT-5.5

## 6.1. Таблица конверсии effort

| Было на GPT-5.5 | Попробуй на GPT-5.6 (primary) | Control |
|-----------------|-------------------------------|---------|
| none / minimal | none | low |
| low | **none или low** | medium |
| medium | **low** | medium |
| high | **medium** | high |
| xhigh | **high** | xhigh |
| — | max только если xhigh мало | — |

\begin{callout}
\textbf{Совет power-users (X / Reddit).}
«На 5.5 default medium/high; на 5.6 — \textbf{start low}, medium если надо. High/xhigh/max — редко.»
Уровни \textbf{не} переносятся один-в-один: 5.6 умнее на low/medium.
\end{callout}

## 6.2. Эвристики сообщества (не догма)

| Ты жил на 5.5… | Часто хорошо на 5.6… |
|----------------|----------------------|
| medium / low | Terra high **или** Sol medium |
| high / xhigh | Sol medium (+ hard steps high); иногда Luna Max в Codex |
| xhigh unattended | Sol high/xhigh **с** жёстким plan; не Ultra «на всё» |

## 6.3. Hybrid 5.5 + 5.6

Часть инженеров оставляет:

- **5.6 Sol high/xhigh/Ultra** — brainstorm, architecture, plan;
- **5.5 xhigh** — implementation (быстрее, меньше «размаза»).

Это **валидный** hybrid, если на твоих задачах 5.6 overthink'ит execute. Не стыдно — стыдно не мерить.

## 6.4. Что поменять в промптах

1. **Убери** лишние «Be concise / think step by step» — 5.6 и так компактнее; `text.verbosity` для длины.
2. **Задай autonomy boundaries:** что можно делать без спроса, что — только с approval.
3. **Lean system prompt:** один раз каждая инструкция; меньше tools = лучше.
4. **Done-criteria:** «готово = tests green + …», иначе high effort «копает вечно».

\newpage

# 7. Экономика и антипаттерны

## 7.1. Что реально жжёт бюджет

1. **Высокий effort** на простых задачах (reasoning tokens дорогие).
2. **Ultra / multi-agent** без параллелизуемой структуры.
3. **Pro mode** на каждый запрос.
4. **Cache writes 1.25×** на часто меняющемся prefix.
5. **Длинный system prompt + 20 tools** на каждом turn.

## 7.2. Антипаттерны

| Антипаттерн | Почему плохо | Что вместо |
|-------------|--------------|------------|
| Всегда xhigh «чтобы SOTA» | Latency, \$\$\$, overthink | medium default |
| Ultra на monorepo «сделай всё» | 100+ файлов, mess | plan → chunks |
| Sol на classify | Переплата 10–50× | Luna |
| Luna на hard architecture | Тихие ошибки | Sol high |
| Менять effort вместо промпта | Effort — тюнинг, не костыль | goal + constraints + eval |
| Max без сравнения с xhigh | Насыщение качества | A/B на eval set |

## 7.3. Когда effort уже «насытился»

Сообщество и наблюдения: у **Sol** кривая high → xhigh → max часто **убывающая**. Если medium уже закрывает tests — **не** крути max «для спокойствия».

Признаки overthinking:

- правит несвязанные файлы;
- «улучшает» архитектуру без запроса;
- runtime часы на scoped bug;
- diff, который ты не можешь review'нуть.

**Лечение:** effort −1, ужесточить scope, approval boundaries, короткий plan-файл.

\newpage

# 8. Чеклисты

## 8.1. Перед запуском задачи

- [ ] Цель и definition of done ясны
- [ ] Выбран тир: Sol / Terra / Luna
- [ ] Выбран effort: start low/medium
- [ ] Scope файлов / owns_paths ограничен
- [ ] Destructive / external writes = approval only
- [ ] Есть тесты / eval / rubric

## 8.2. Если качество плохое

1. Улучши **контекст** (файлы, ошибки, constraints) — не сразу effort.
2. Подними effort **на один** уровень.
3. Если мало — Sol (если был Terra/Luna) или **pro**.
4. Если multi-part — Ultra / multi-agent.
5. Зафиксируй выигрыш в eval — иначе откат.

## 8.3. Если слишком дорого / медленно

1. Effort −1.
2. Sol → Terra → Luna.
3. Выключи Pro / Ultra.
4. Укороти system prompt и список tools.
5. Explicit prompt caching, batch, parallel only where independent.

## 8.4. Production gate

- [ ] Accuracy target выполнен на eval set
- [ ] p50/p95 latency в SLA
- [ ] \$ / 1k requests в бюджете
- [ ] Fallback на более сильную модель для hard cases
- [ ] Логи: model, effort, mode, tokens, success

\newpage

# 9. API: минимальные примеры

## 9.1. Standard · medium

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5.6",  # = Sol
    reasoning={"effort": "medium"},
    input="Составь план рефакторинга auth-модуля. Код не пиши.",
)
print(response.output_text)
```

## 9.2. Pro · high (quality-first)

```python
response = client.responses.create(
    model="gpt-5.6-sol",
    reasoning={"mode": "pro", "effort": "high"},
    input=(
        "Проверь plan миграции БД на failure modes с data loss. "
        "Топ-5 рисков по severity + mitigation."
    ),
)
```

## 9.3. Luna · low (high volume)

```python
response = client.responses.create(
    model="gpt-5.6-luna",
    reasoning={"effort": "low"},
    input="Классифицируй тикет: billing | tech | spam. Ответ — одно слово.",
)
```

## 9.4. Параметры, которые стоит знать

| Параметр | Зачем |
|----------|--------|
| `reasoning.effort` | Сколько думать |
| `reasoning.mode` | `standard` \| `pro` |
| `reasoning.context` | `auto` \| `current_turn` \| `all_turns` |
| `text.verbosity` | Длина ответа (low/medium/high) |
| `max_output_tokens` | Потолок (заложи запас на reasoning) |
| `previous_response_id` | Сохранить reasoning continuity |

\begin{warnbox}
\textbf{Context window.}
Reasoning tokens тоже занимают окно и биллятся. Для тяжёлых режимов OpenAI советует резервировать порядка \textbf{25k+} tokens на reasoning+output при экспериментах.
\end{warnbox}

\newpage

# 10. Шпаргалка на одну страницу

## Модели

| | Sol | Terra | Luna |
|--|-----|-------|------|
| Зачем | frontier | баланс | volume |
| \$ | высокий | средний | низкий |
| Default use | hard agent/code | daily prod | chat/batch |

## Effort

| Уровень | Одна фраза |
|---------|------------|
| none | мгновенно, без tools |
| low | мелкие правки, execute |
| **medium** | **дефолт 80%** |
| high | hard plan/debug |
| xhigh | audit / overnight |
| max | nightmare single task |

## Режимы

- **Pro** = дорогая ошибка + eval
- **Ultra** = задача параллелится
- **Max effort** = одна модель думает до упора

## Миграция 5.5 → 5.6

**Effort −1** как первый эксперимент.

## Золотые правила

1. Accuracy first, cost second.
2. Plan high → execute low/medium.
3. Не поднимай effort вместо хорошего ТЗ.
4. Ultra ≠ «просто сильнее».
5. Мерить: success, tokens, latency, \$.
6. На 5.6 high часто избыточен.
7. Hybrid 5.5 execute ок, если 5.6 overthink'ит.

\begin{okbox}
\textbf{Default, если лень думать.}
\textbf{Sol medium} (или \textbf{Terra medium} при бюджете).
Поднял effort только после провала medium на конкретных критериях.
\end{okbox}

\newpage

# Приложение A. Глоссарий

| Термин | Значение |
|--------|----------|
| **Reasoning tokens** | «Скрытые» токены размышления; в usage, в счёте как output |
| **Effort** | Бюджет «думания» (none…max) |
| **Pro mode** | Режим с большим объёмом model work → один ответ |
| **Ultra** | Параллельные subagents (Codex / multi-agent) |
| **Sol / Terra / Luna** | Тиры 5.6: flagship / mid / efficient |
| **Eval** | Набор задач с эталоном для сравнения конфигов |
| **Owns_paths** | Ограничение «какие пути можно трогать» |
| **Done-criteria** | Явное «что считается готово» |

# Приложение B. Источники

1. OpenAI Docs — *Using GPT-5.6* / latest-model guide  
2. OpenAI Docs — *Reasoning models* (`reasoning.effort`, mode, context)  
3. OpenAI Docs — *Model selection* (accuracy → cost)  
4. OpenAI — *Introducing GPT-5.6* (анонс, тиры, Pro/Max)  
5. Community: Codex Reddit, X threads (в т.ч. OpenAI staff guidance по efforts)

*Документ составлен как практическая методичка. Цены и дефолты effort уточняйте в актуальной документации OpenAI — они могут меняться.*

\newpage

# Приложение C. Карточка «повесь у монитора»

```
┌─────────────────────────────────────────────────────────┐
│  GPT-5.6 QUICK PICK                                     │
├─────────────────────────────────────────────────────────┤
│  МОДЕЛЬ                                                 │
│   Hard / agent / design ........ Sol                    │
│   Daily prod / volume .......... Terra                  │
│   Chat / batch / classify ...... Luna                   │
├─────────────────────────────────────────────────────────┤
│  EFFORT                                                 │
│   Instant / no tools ........... none                   │
│   Fix / execute plan ........... low                    │
│   Default day-to-day ........... medium  ← START        │
│   Hard plan / debug ............ high                   │
│   Audit / overnight ............ xhigh                  │
│   Nightmare one-shot ........... max                    │
├─────────────────────────────────────────────────────────┤
│  SPECIAL                                                │
│   Pro ........ ошибка дорогая + есть eval               │
│   Ultra ...... задача режется на параллель              │
├─────────────────────────────────────────────────────────┤
│  FLOW                                                   │
│   PLAN high → EXECUTE low/medium → REVIEW high/xhigh    │
│   5.5→5.6: сначала попробуй effort −1                   │
└─────────────────────────────────────────────────────────┘
```

---

**Конец методички · v1.0 · Июль 2026**
