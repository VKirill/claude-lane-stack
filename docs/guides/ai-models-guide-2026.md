---
title: "Какую нейросеть выбрать в 2026"
subtitle: "Практическая методичка для новичков: Fable, Opus, Sonnet, GPT-5.6, Kimi K3, MiniMax M3, Gemini, Antigravity"
author: "Сводка по открытым источникам, X, Reddit и официальным анонсам · июль 2026"
date: "v1.0 · Июль 2026"
lang: ru-RU
mainfont: DejaVu Sans
sansfont: DejaVu Sans
monofont: DejaVu Sans Mono
geometry: margin=2cm
fontsize: 10.5pt
linestretch: 1.12
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
  - \fancyhead[L]{\small Какую модель выбрать · 2026}
  - \fancyhead[R]{\small Методичка v1.0}
  - \fancyfoot[C]{\thepage}
  - \renewcommand{\headrulewidth}{0.4pt}
  - \newtcolorbox{callout}{colback=blue!4,colframe=blue!45!black,boxrule=0.5pt,arc=2pt,left=5pt,right=5pt,top=3pt,bottom=3pt}
  - \newtcolorbox{warnbox}{colback=orange!6,colframe=orange!55!black,boxrule=0.5pt,arc=2pt,left=5pt,right=5pt,top=3pt,bottom=3pt}
  - \newtcolorbox{okbox}{colback=green!4,colframe=green!40!black,boxrule=0.5pt,arc=2pt,left=5pt,right=5pt,top=3pt,bottom=3pt}
  - \newtcolorbox{tipbox}{colback=purple!3,colframe=purple!40!black,boxrule=0.5pt,arc=2pt,left=5pt,right=5pt,top=3pt,bottom=3pt}
---

\newpage

# Зачем эта методичка

Летом 2026 года новичок открывает ChatGPT, Claude, Kimi, MiniMax, Gemini, Antigravity — и тонет. Все обещают «лучшую модель». На X и Reddit одно и то же: *«какая лучшая?»* — и сотня ответов, которые противоречат друг другу.

**Правда простая:** лучшей модели нет. Есть **задача** и **бюджет**. Эта методичка учит выбирать так, как это делают практикующие инженеры и создатели контента: *под работу*, а не под хайп.

\begin{okbox}
\textbf{Правило №1 (запомни навсегда).}
Не спрашивай «какая модель лучшая». Спрашивай: «какая модель лучше \emph{для этой работы} при \emph{моём бюджете}?»
\end{okbox}

**Что внутри**

1. Как думать о моделях (карта ролей).
2. Портреты актуальных моделей: Anthropic (Fable / Opus / Sonnet), OpenAI (GPT-5.6 Sol/Terra/Luna), Moonshot (Kimi K3), MiniMax (M3), Google (Gemini + Antigravity).
3. Прайс-карта «что сколько стоит».
4. Матрицы: код, креатив, research, объём, агенты.
5. Готовые пресеты для новичков.
6. Шпаргалка на одну страницу.

**Источники:** официальные блоги OpenAI, Anthropic, Moonshot, MiniMax, Google; Artificial Analysis / Arena; обсуждения X и Reddit (r/codex, r/ClaudeAI, r/LocalLLaMA и др.), июль 2026. Цены — ориентиры API за 1M tokens (input/output), могут меняться.

\newpage

# 1. Как выбирать модель: 4 вопроса

Перед любым «купи Pro / подключи API» ответь себе:

| № | Вопрос | Зачем |
|---|--------|--------|
| 1 | **Что делаю?** | Код / текст / дизайн / research / чат-бот / агент на сутки |
| 2 | **Цена ошибки?** | Черновик можно переписать; прод-миграцию — нельзя «на глаз» |
| 3 | **Сколько контекста?** | 5 файлов или весь репозиторий / 200 PDF |
| 4 | **Какой бюджет?** | \$20/мес подписка · \$200 API · «хочу почти бесплатно» |

\begin{callout}
\textbf{Ментальная модель «три полки».}
\textbf{Флагман} — дорого, умно, для hard work.\\
\textbf{Рабочая лошадка} — 80\% дней, баланс.\\
\textbf{Дешёвый объём} — чат, batch, классификация, черновики.
\end{callout}

Любая «семья» моделей устроена так:

- **Anthropic:** Fable 5 (флагман) · Opus 4.x (бывший верх) · Sonnet (лошадка) · Haiku (дешёвый)
- **OpenAI GPT-5.6:** Sol · Terra · Luna
- **Kimi:** K3 (флагман) · K2.x Code (дешевле для рутины)
- **MiniMax:** M3 (флагман) · M2.7 (стабильная дешёвая рутина)
- **Google:** Gemini 3.x Pro · Flash · Antigravity (агентная оболочка)

\newpage

# 2. Карта рынка: кто есть кто (лето 2026)

## 2.1. Одной таблицей

| Модель | Компания | Роль «в двух словах» | Ориентир API \$/1M in→out | Контекст |
|--------|----------|----------------------|---------------------------|----------|
| **Claude Fable 5** | Anthropic | Публичный Mythos-класс: hard coding & agents | ~\$10 → \$50 | до 1M (beta/усл.) |
| **Claude Opus 4.6/4.7/4.8** | Anthropic | Глубокое reasoning, «осторожный» премиум | ~\$5 → \$25 | 200K–1M |
| **Claude Sonnet 4.6** | Anthropic | Default дня: сильный код за нормальные деньги | ~\$3 → \$15 | 200K–1M |
| **GPT-5.6 Sol** | OpenAI | Флагман OpenAI: код, agents, frontend polish | ~\$5 → \$30 | большой |
| **GPT-5.6 Terra** | OpenAI | «Почти Sol» дешевле | ~\$2.50 → \$15 | большой |
| **GPT-5.6 Luna** | OpenAI | Throughput / volume | ~\$0.63 → \$3.75 | большой |
| **Kimi K3** | Moonshot | Open-weight frontier: код, 3D/frontend, 1M | \$3 → \$15 (cache \$0.30) | **1M** |
| **MiniMax M3** | MiniMax | Дешёвый long-context coding + multimodal | **\$0.30 → \$1.20** (promo; list выше) | **1M** |
| **Gemini 3.x Pro** | Google | Мультимодальность, docs, long context | mid/high | очень большой |
| **Gemini Flash** | Google | Быстро и дёшево | low | большой |
| **Grok 4.x** | xAI | Multi-agent / research vibe, X-интеграция | mid | большой |

\begin{tipbox}
\textbf{Как читать цену.}
\$3/\$15 значит: \$3 за миллион \emph{входных} токенов, \$15 за миллион \emph{выходных}. Выход почти всегда дороже. Агенты пишут много «мыслей» и tool-calls — счёт растёт не только от «ответа пользователю».
\end{tipbox}

## 2.2. Свежий «клад» моделей (что все обсуждают)

С июня–июля 2026 рынок встряхнули почти одновременно:

1. **Claude Fable 5** (июнь) — публичная версия Mythos-класса.
2. **MiniMax M3** (1 июня) — open-weight, 1M context, «frontier coding дёшево».
3. **GPT-5.6** Sol/Terra/Luna (июль) — новое семейство OpenAI.
4. **Kimi K3** (16 июля) — 2.8T open-weight, #1 на части frontend/webdev арен.

Люди на X говорят прямо: *«не ищи одну лучшую — переключайся»*.

\newpage

# 3. Anthropic: Fable, Opus, Sonnet

## 3.1. Claude Fable 5 — «тяжёлая артиллерия»

**Что это.** Первая *публичная* модель Mythos-класса. Та же «порода», что и закрытый **Mythos 5** (для партнёров / cyber), но с safety-слоем: часть чувствительных запросов может уходить на более безопасный fallback (например, Opus).

**Сильные стороны (по практике и анонсам)**

- Самый надёжный long-horizon coding у Anthropic.
- Системы «с нуля», сложная архитектура, finance-grade reasoning.
- Высокие SWE / FrontierCode показатели в публичных обзорах.
- Хорошо «держит» большой проект, если платишь.

**Слабые стороны**

- **Дорого** (ориентир ~\$10/\$50 — в 2×+ дороже Opus-уровня).
- Лимиты подписок, safety-interruptions на dual-use темах.
- Overkill для мелких правок и черновиков.

\begin{okbox}
\textbf{Когда брать Fable 5.}
Большая система, high-stakes код, multi-hour agent, «нужен Claude-уровень дисциплины».\\
\textbf{Когда не брать.}
Мелкий bugfix, посты, дешёвый batch — сожжёшь бюджет без выигрыша.
\end{okbox}

## 3.2. Claude Opus 4.6 / 4.7 / 4.8 — «умный премиум»

**Роль.** До Fable это был верх линейки. Сейчас Opus — *почти-флагман*: глубокое reasoning, осторожность, сильный code review, сложные trade-off'ы.

**Когда Opus**

- Архитектурные решения, security review, math-heavy.
- Когда Sonnet «чуть не дотягивает», а Fable жалко по деньгам.
- Качественный long-form reasoning «с головой».

**Когда не Opus**

- 80\% повседневного кода — лучше **Sonnet**.
- High-volume API — слишком дорого.

## 3.3. Claude Sonnet 4.6 — «рабочая лошадка Claude»

**Роль.** Default Anthropic для большинства людей и продуктов.

- Цена ~\$3/\$15.
- Код, ревью, агенты «на каждый день».
- Многие тесты 2026: Sonnet ≈ Opus по «обычным» задачам при меньшей цене; Opus нужен на 10–15\% hard cases.

\begin{callout}
\textbf{Практический рецепт Claude-стека.}
День: \textbf{Sonnet 4.6}.\\
Hard day: \textbf{Opus} или \textbf{Fable}.\\
Мелочь/скорость: \textbf{Haiku} (если доступен в вашем тарифе).
\end{callout}

## 3.4. Claude Code (продукт, не модель)

**Claude Code** — агентная оболочка Anthropic (терминал/IDE). Модель внутри выбираешь: Sonnet / Opus / Fable.  
Многие на Reddit: *«живу в Claude Code на Sonnet, Fable — на архитектуру и аудит»*.

\newpage

# 4. OpenAI: GPT-5.6 Sol, Terra, Luna

## 4.1. Семейство, не одна кнопка

| Тир | Для кого | Цена (ориентир) |
|-----|----------|-----------------|
| **Sol** (`gpt-5.6`) | Максимум OpenAI: hard code, agents, UI polish | ~\$5 / \$30 |
| **Terra** | Баланс: почти Sol, дешевле | ~\$2.50 / \$15 |
| **Luna** | Объём, latency, mass | ~\$0.63 / \$3.75 |

## 4.2. Уровни «размышлений» (reasoning)

У GPT-5.6 (и в Codex) важна не только модель, но и **effort**:  
`none → low → medium → high → xhigh → max`.

| Effort | Простыми словами | Когда |
|--------|------------------|--------|
| none / low | Быстро, мало думает | Мелкий fix, execute готового плана |
| **medium** | Нормальный день | 80\% работы |
| high | Думает серьёзно | Hard debug, plan |
| xhigh / max | Долго и дорого | Audit, overnight, nightmare-task |

Ещё есть:

- **Pro mode** — больше «внутренней работы» ради одного сильного ответа (quality-first).
- **Ultra** (в Codex) — несколько subagents **параллельно** (если задача режется на части).

\begin{warnbox}
\textbf{Типичная ошибка новичков.}
Ставить Sol + xhigh «на всё». Модель overthink'ит, трогает 100 файлов, сжигает лимит. Правильно: \textbf{plan на high} → \textbf{execute на low/medium}.
\end{warnbox}

## 4.3. За что хвалят GPT-5.6 на практике

- Token-efficient (часто меньше «воды», чем 5.5).
- Сильный **frontend / layout** (OpenAI прямо позиционирует).
- Хороший **intent**: меньше микроменеджмента шагов.
- Terra/Luna — удобная лестница цен.

**Когда Sol:** сложный agent, hard code, design-heavy UI.  
**Когда Terra:** daily prod / Codex без флагманского счёта.  
**Когда Luna:** классификация, чат, batch, cheap volume.

## 4.4. Codex

**Codex** — coding-agent OpenAI (CLI/IDE/cloud). Почти всегда берут **Sol/Terra** + conscious effort.  
Сообщество r/codex: *«Sol medium default; high только на plan/review»*.

\newpage

# 5. Kimi K3 (Moonshot) — «открытый тяжёлый боец»

## 5.1. Что это

- **2.8 триллиона** параметров (open-weight MoE, веса — по плану open source).
- Контекст **1M tokens**.
- Native vision (картинки/скрины в loop).
- Цена API: **\$3 input / \$15 output**, cache hit **\$0.30** — как у Sonnet-уровня, но с кэшем очень выгодно на длинных agent-сессиях.
- На старте часто **max thinking** по умолчанию.

Сам Moonshot честно пишет: *overall* пока чуть ниже **Fable 5** и **GPT-5.6 Sol**, но на ряде coding/agent бенчмарков — frontier; на **Arena Code WebDev** — лидер.

## 5.2. Где K3 реально блестит (X + тесты)

- **Frontend / WebDev / 3D / game-ish builds** — много клипов: «K3 > Fable на визуальном loop».
- **Долгие agent-сессии** по большому репо.
- **Vision-in-the-loop**: скриншот → правка → снова скрин.
- Research + interactive dashboards / motion graphics (кейсы Kimi Work).

## 5.3. Где слабее (важно для новичков)

- Может **переигрывать** и «додумывать за тебя» (excessive proactiveness) — нужен жёсткий AGENTS.md.
- Чувствителен к thinking history harness (не все оболочки одинаковы).
- На «просто follow the plan» часть людей ставит Fable/Sol выше.
- На старте — GPU pressure, лимиты подписок.

\begin{okbox}
\textbf{Когда Kimi K3.}
Визуальный код, 1M context, open-weight стратегия, «Sonnet-цена + длинный agent».\\
\textbf{Когда не только K3.}
High-stakes прод без human review — держи Fable/Sol как second opinion.
\end{okbox}

## 5.4. K2.x Code vs K3

| | K2.7 Code (примерно) | K3 |
|--|----------------------|-----|
| Цена | заметно дешевле | \$3/\$15 |
| Роль | рутина, обычный coding loop | long-horizon, vision, 1M |
| Совет | default для «просто почини» | когда упёрся в контекст/горизонт |

\newpage

# 6. MiniMax M3 — «дешёвый long-context coding»

## 6.1. Что это

- Open-weight frontier от MiniMax (июнь 2026).
- **1M context**, sparse attention (MSA).
- **Native multimodal** (image/video) + computer use.
- Цена-убийца: ориентир **\$0.30 / \$1.20** за 1M (promo; list ~2×).  
  Выше **512K** input — отдельный long-context тариф (примерно ×2).

**Token Plan (подписка):** Plus \$20 / Max \$50 / Ultra \$120 — очень жирные token quotas по меркам рынка.

## 6.2. Когда M3 — лучший выбор

- Большой репозиторий / миграция «всё в одном окне».
- Много **retry-циклов** агента (дёшево перезапускать).
- Мультимодальный coding: скрины UI, PDF, диаграммы.
- Self-host / open-weight compliance.
- Бюджет tight, а Claude/GPT «съедают» месяц за неделю.

## 6.3. Когда M3 не единственный ответ

- Нужна максимальная «дисциплина» и polish Fable/Sol.
- Сверх-high-stakes без второго opinion.
- Провайдеры/квоты подписки бывают «маркетингово жирными» — читай fine print (Reddit: осторожно с Token Plan).

\begin{callout}
\textbf{Hybrid, который рекомендуют на практике.}
Daily: Claude/Codex (Sonnet или Terra).\\
Repo-scale / batch / cheap loops: \textbf{MiniMax M3}.\\
Visual frontend showcase: \textbf{Kimi K3}.\\
Архитектура high-stakes: \textbf{Fable 5} или \textbf{Sol high}.
\end{callout}

## 6.4. M2.7 vs M3

| | M2 / M2.7 | M3 |
|--|-----------|-----|
| Фокус | стабильный coding loop | long-context + multimodal + long-horizon |
| Цена | похожий дешёвый tier | тот же «cheap frontier» |
| Бери | рутина | когда упираешься в контекст/зрение/сутки работы |

\newpage

# 7. Google: Gemini и Antigravity

## 7.1. Gemini 3.x Pro / Flash

**Gemini Pro (3 / 3.1)** — силён в:

- Очень длинных документах, PDF-пачках, «весь диск в контекст».
- Мультимодальности: картинки, видео, таблицы.
- Research + синтез из кучи источников.
- Workspace-экосистеме (Docs, Drive, и т.д.).

**Gemini Flash** — быстрый и дешёвый: triage, summarize, high-QPS, черновики.

\begin{tipbox}
\textbf{Типичное «Google-место» в стеке.}
«Прочитай 40 PDF и сделай brief» → Gemini Pro.\\
«Классифицируй 10k тикетов» → Flash.\\
«Собери production-agent на 8 часов с тестами» → чаще Claude/Codex/Kimi/MiniMax.
\end{tipbox}

## 7.2. Antigravity — что это вообще

**Google Antigravity** (публичный запуск конца 2025 → развитие в 2026) — это не «ещё одна LLM», а **агентная платформа** Google:

- IDE-like / agent-first среда.
- Работает с **Gemini** (и, по заявлениям/интеграциям, с другими моделями).
- Агенты, которые **планируют, пишут код, запускают команды, проверяют результат** (browser/terminal).
- Философия: «mission control» для agent fleets, а не один chat.

\begin{okbox}
\textbf{Как думать об Antigravity.}
Это \emph{где} крутится агент (как Claude Code / Codex / Cursor), а не \emph{какой} мозг внутри.\\
Выбор: «работать в Antigravity на Gemini Pro» vs «в Claude Code на Fable» vs «в Codex на Sol».
\end{okbox}

**Когда Antigravity + Gemini**

- Ты в Google-экосистеме.
- Нужны агенты с сильным multimodal/docs.
- Хочешь «родной» Google agent stack.

**Когда смотреть в сторону Claude Code / Codex / Kimi Code / MiniMax Code**

- Coding-агенты «как все в Twitter» — там сейчас больше living knowledge.
- Нужен конкретный мозг (Fable / Sol / K3 / M3), а не обязательно Google shell.

\newpage

# 8. Прайс-карта: сколько это «в жизни»

## 8.1. API (ориентир, \$ за 1M tokens)

| Модель | Input | Output | «Ощущение» |
|--------|-------|--------|------------|
| MiniMax M3 (promo ≤512k) | 0.30 | 1.20 | почти даром для agent loops |
| GPT-5.6 Luna | ~0.63 | ~3.75 | mass production |
| GPT-5.6 Terra | ~2.50 | ~15 | рабочий mid |
| Claude Sonnet 4.6 | 3 | 15 | industry default mid |
| Kimi K3 | 3 (cache 0.30) | 15 | mid + выгодный cache |
| Claude Opus 4.x | 5 | 25 | premium |
| GPT-5.6 Sol | 5 | 30 | flagship OpenAI |
| Claude Fable 5 | ~10 | ~50 | top \$\$\$ |

\begin{warnbox}
\textbf{Подписки ≠ API.}
ChatGPT Plus / Claude Pro / Kimi Membership / MiniMax Token Plan — это \emph{квоты и rate limits}, не «безлимит». Fable/Sol high на подписке сгорают за часы agent-work. Смотри usage dashboard.
\end{warnbox}

## 8.2. Как считать «цену задачи», а не «цену токена»

Агент, который 2 часа читает репо:

- 500k input + 80k output на **M3** ≈ копейки.
- Тот же объём на **Fable** ≈ в десятки раз дороже.

Поэтому:

- **Исследование / draft / explore** → дешёвые модели.
- **Финальный merge в прод** → дорогая модель + human review.

## 8.3. Бюджетные корзины для новичков

| Бюджет | Что собрать |
|--------|-------------|
| **\$0–20/мес** | Бесплатные тиры + MiniMax/Kimi free trials + Gemini Flash |
| **\$20–50** | Один сильный: Claude Pro *или* ChatGPT *или* MiniMax Max *или* Kimi |
| **\$50–150** | Hybrid: Claude/Codex (mid) + M3 или K3 на объём |
| **\$150+ / API** | Sol/Fable на hard + Terra/Sonnet/M3 на volume |

\newpage

# 9. Матрица «задача → модель»

## 9.1. Код и разработка

| Задача | 1-й выбор | 2-й выбор | Избегай |
|--------|-----------|-----------|---------|
| Мелкий bugfix | Sonnet / Terra / M3 | K2.x / Luna | Fable xhigh |
| Feature по плану | Sonnet / Terra medium | K3 / M3 | всегда Ultra |
| Архитектура / ADR | Fable / Sol high | Opus | Flash/Luna alone |
| Большой рефакторинг репо | M3 / K3 (1M) | Sol + plan | один промпт «перепиши всё» |
| Frontend / landing / 3D UI | **K3** / Sol | Fable | только Flash |
| Security audit | Fable / Sol xhigh | Opus | дешёвые alone |
| Overnight unattended | Sol/K3/M3 + **узкий scope** | Fable | «сделай весь продукт» |
| Tests writing | Sonnet / Terra | M3 | — |

## 9.2. Креатив и контент

| Задача | 1-й выбор | Почему |
|--------|-----------|--------|
| Рекламные креативы / офферы | Claude Sonnet или GPT mid | сильный copy + структура |
| Длинные статьи / tone of voice | Claude (Sonnet/Opus) | «человечнее», меньше slop |
| Сценарии / storytelling | Claude / GPT Sol | narrative control |
| Визуальные концепции + код UI | **Kimi K3**, GPT-5.6 Sol | vision + frontend |
| Картинки / банеры | Специализированные image-модели (не LLM-чат) | LLM пишет бриф, не «рисует» всегда |
| Видео-скрипты / motion brief | K3 (motion cases) / Gemini | multimodal |
| SMM-посты RU | Claude + human edit | тон; всегда редактура |
| Бренд-голос «не AI-шно» | Claude + короткий style guide | меньше «нейросетевой» воды |

\begin{callout}
\textbf{Креатив = модель + бриф, не «магия».}
Даже Fable напишет шаблон, если бриф пустой. Лучший стек: сильная mid-модель + 5–10 строк audience/offer/tone + human pass.
\end{callout}

## 9.3. Research, документы, данные

| Задача | Модель |
|--------|--------|
| 50 PDF → summary | Gemini Pro / K3 / M3 |
| Deep research report | Sol / Fable / K3 Work |
| Таблицы, sheets, finance | Fable (finance praise) / Opus / Sol |
| Быстрый fact-check | Flash / Luna / web-tool agent |
| Научный pipeline + код | K3 / M3 (long-horizon cases) |

## 9.4. Продуктовые API и боты

| Нагрузка | Модель |
|----------|--------|
| High QPS chat | Luna / Flash / Haiku-class |
| Support с tools | Sonnet / Terra |
| Hard escalation | Sol / Fable / Opus |
| Batch offline | M3 / Luna / Flash |

\newpage

# 10. Агентные оболочки: где «живёт» модель

Новички путают **чат** и **агента**.

| Оболочка | Чей «дом» | Типичный мозг | Когда |
|----------|-----------|---------------|--------|
| **Claude Code** | Anthropic | Sonnet / Opus / Fable | coding agent Claude-style |
| **Codex** | OpenAI | Sol / Terra + effort | OpenAI coding agent |
| **Kimi Code / Work** | Moonshot | K3 | visual + long coding |
| **MiniMax Code** | MiniMax | M3 | cheap long agents, multimodal |
| **Antigravity** | Google | Gemini (+ multi) | Google agent IDE |
| **Cursor / Windsurf / etc.** | IDE | любая через API | editor-first |
| **ChatGPT / Claude.ai / Gemini app** | Chat UI | флагманы подписки | не-агентный день |

\begin{tipbox}
\textbf{Практический совет.}
Сначала выбери \emph{оболочку под привычку} (терминал / IDE / чат), потом \emph{мозг под задачу}. Менять мозг внутри одной оболочки проще, чем прыгать между продуктами каждый час.
\end{tipbox}

\newpage

# 11. Готовые пресеты (скопируй и живи)

## 11.1. «Я новичок, \$20–30/мес»

1. Возьми **один** основной: Claude Pro *или* ChatGPT *или* Kimi *или* MiniMax Max.
2. Для тяжёлых задач — free web другого вендора как second opinion.
3. Не гонись за Fable/Sol high каждый день.

**Default дня:** Sonnet или GPT mid или K3 (если визуал).

## 11.2. «Я разработчик, \$50–100»

| Слот | Модель |
|------|--------|
| Daily code | Sonnet 4.6 **или** GPT-5.6 Terra medium |
| Plan / architecture | Fable **или** Sol high |
| Big repo / cheap loops | **MiniMax M3** |
| Frontend showcase | **Kimi K3** |
| Docs/PDF dump | Gemini Pro |

## 11.3. «Я агентство / контент»

| Слот | Модель |
|------|--------|
| Черновики постов | Sonnet / GPT mid |
| Финальная вычитка | Opus / human |
| Лендинги (текст+структура) | Sol / Sonnet |
| Визуальный прототип UI | K3 / Sol |
| Research ниши | Gemini + K3/Sol |

## 11.4. «Я строю продукт на API»

```
Router:
  simple  → Luna / Flash / Haiku-class
  normal  → Terra / Sonnet / M3
  hard    → Sol / Fable / Opus
  visual long-horizon → K3
```

Всегда: логи model + cost + success. Раз в месяц пересматривай пороги.

## 11.5. «Золотой hybrid 2026» (как делают сильные)

1. **Plan** — Fable 5 или Sol high.  
2. **Execute** — Sonnet / Terra / M3 / K3.  
3. **Review** — Fable / Sol / Opus.  
4. **Bulk** — M3 / Luna / Flash.

\newpage

# 12. Decision tree для новичка (30 секунд)

```
Что делаю?
│
├─ Мелкая правка / вопрос
│    → Sonnet / Terra / M3 / Flash
│
├─ Код feature / agent день
│    → Sonnet или Terra (default)
│    → упёрся? Sol / Fable / K3
│
├─ Огромный репо / 1M контекст / дёшево крутить loops
│    → MiniMax M3
│
├─ Красивый frontend / 3D / game-ish / screenshots
│    → Kimi K3 (потом Sol)
│
├─ Архитектура / security / «нельзя ошибиться»
│    → Fable 5 или Sol high (+ human)
│
├─ Гора PDF / multimodal research
│    → Gemini Pro или K3
│
├─ Массовый chat/API
│    → Luna / Flash
│
└─ Не знаю
     → Sonnet 4.6 или GPT-5.6 Terra medium
        и не усложняй
```

\newpage

# 13. Частые мифы

| Миф | Реальность |
|-----|------------|
| «Fable всегда лучше» | На мелких задачах — дороже без выигрыша |
| «Open-source = слабый» | K3/M3 бьют закрытых на части задач |
| «Дороже = лучше для креатива» | Нужен бриф и редактор, не max effort |
| «Одна модель на всё» | Побеждает hybrid |
| «Ultra/max = режим бога» | Часто overthink и \$\$\$ |
| «Подписка = безлимит» | Rate limits реальны |
| «Бенчмарк = мой use case» | Мерь на *своих* задачах |

\newpage

# 14. Как не сойти с ума: система на неделю

**День 1–2.** Выбери default (Sonnet или Terra). Делай всё на нём.  
**День 3.** Одну hard-задачу прогони на Fable/Sol. Сравни время и качество.  
**День 4.** Одну long-repo задачу — на M3.  
**День 5.** Один UI/frontend — на K3.  
**День 6.** Один PDF-research — на Gemini.  
**День 7.** Запиши: что оставить default, что — «по кнопке».

\begin{okbox}
\textbf{Критерии сравнения (простые).}
1) Сделало ли задачу? 2) Сколько правок руками? 3) Сколько времени? 4) Сколько денег?\\
Победитель — не «умный в чате», а \textbf{дешевле доведённый результат}.
\end{okbox}

\newpage

# 15. Портреты моделей — «как люди»

| Модель | Метафора | Характер |
|--------|----------|----------|
| **Fable 5** | Старший архитектор | Дорого, глубоко, надёжно на hard |
| **Opus** | Осторожный профессор | Думает, иногда медленно, качественно |
| **Sonnet** | Сильный middle+ | Default, без драмы |
| **GPT-5.6 Sol** | Старший full-stack + UI eye | Быстрый интеллект, agents, polish |
| **Terra** | Sol «без пиджака» | Почти то же, дешевле |
| **Luna** | Оператор call-центра | Много, быстро, просто |
| **Kimi K3** | Гениальный джун-сеньор с глазами | Вау-frontend, длинные забеги, иногда самовольничает |
| **MiniMax M3** | Дешёвый марафонец | 1M контекст, loops, multimodal |
| **Gemini Pro** | Библиотекарь-аналитик | Docs, multimodal, Google world |
| **Antigravity** | Завод агентов Google | Оболочка, не мозг |

\newpage

# 16. Шпаргалка на одну страницу

## Быстрый выбор

| Хочу… | Беру… |
|-------|--------|
| Не думать, default | **Sonnet 4.6** или **GPT-5.6 Terra medium** |
| Максимум надёжности на hard code | **Fable 5** / **Sol high** |
| Дешёвый большой репо | **MiniMax M3** |
| Вау UI / 3D / visual coding | **Kimi K3** |
| Много дешёвых запросов | **Luna** / **Gemini Flash** |
| Куча PDF / research | **Gemini Pro** / **K3** |
| Google agent IDE | **Antigravity + Gemini** |
| Креатив-тексты | **Sonnet** / **GPT mid** + human edit |
| Security / audit | **Fable** / **Sol xhigh** |

## Деньги (грубо)

`M3 << Luna < Terra ~ Sonnet ~ K3 < Opus < Sol < Fable`

## Золотые правила

1. Модель = под задачу, не под хайп.  
2. Plan дорогой → Execute дешёвый → Review дорогой.  
3. 1M context нужен не всегда.  
4. Effort/max/Ultra — только когда medium провалился.  
5. Hybrid побеждает mono.  
6. Считай \$ за *готовую задачу*.  
7. Человек в конце — особенно на прод и креатив.

\begin{okbox}
\textbf{Если совсем лень.}
Поставь \textbf{Claude Sonnet 4.6} или \textbf{GPT-5.6 Terra}.\\
Когда упрёшься — добавь \textbf{M3} (объём) + \textbf{K3} (визуал) + \textbf{Fable/Sol} (hard).
\end{okbox}

\newpage

# 17. Мини-глоссарий

| Слово | Простыми словами |
|-------|------------------|
| **Токен** | Кусочек текста; примерно 1 токен ≈ ¾ слова EN |
| **Контекст** | Сколько текст/код модель «держит в голове» за раз |
| **Reasoning / effort** | Насколько долго модель «думает» |
| **Agent** | Модель + инструменты (терминал, браузер, файлы) в цикле |
| **Open-weight** | Веса можно скачать/хостить (при релизе) |
| **Frontier** | Уровень лучших закрытых моделей |
| **Harness** | Оболочка агента (Claude Code, Codex…) |
| **Cache** | Повторный ввод дешевле |
| **Multimodal** | Текст + картинки/видео |
| **SWE-bench** | Бенчмарк «чинить реальные GitHub issues» |

\newpage

# 18. Источники и как обновлять методичку

Рынок меняется каждые 2–4 недели. Обновляй этот файл, когда:

1. Выходит новый флагман (как Fable / K3 / 5.6 / M3).  
2. Меняются цены >20\%.  
3. Твой default 2 недели подряд «не заходит» — пересобери hybrid.

**Официальные точки входа**

- Anthropic: claude.com / docs (Fable, Opus, Sonnet, pricing)  
- OpenAI: developers.openai.com (GPT-5.6, Codex, reasoning)  
- Moonshot: kimi.com/blog/kimi-k3  
- MiniMax: minimax.io/blog/minimax-m3  
- Google: antigravity.google / Gemini docs  
- Сравнения: Artificial Analysis, Arena.ai, Reddit r/codex, r/ClaudeAI, X

\begin{warnbox}
\textbf{Дисклеймер.}
Это практическая методичка, не финансовый/юридический совет и не официальный документ вендоров. Бенчмарки у компаний часто в своих harness — доверяй своим A/B на реальных задачах.
\end{warnbox}

\newpage

# Приложение A. Карточка «повесь у монитора»

```
┌──────────────────────────────────────────────────────────┐
│  AI MODELS 2026 — QUICK PICK                             │
├──────────────────────────────────────────────────────────┤
│  DEFAULT DAY ...... Sonnet 4.6  или  GPT-5.6 Terra       │
│  HARD CODE ........ Fable 5  /  Sol high                 │
│  BIG REPO CHEAP ... MiniMax M3                           │
│  PRETTY UI / 3D ... Kimi K3                              │
│  PDF / RESEARCH ... Gemini Pro  /  K3                    │
│  MASS API ......... Luna  /  Flash                       │
│  GOOGLE AGENTS .... Antigravity + Gemini                 │
├──────────────────────────────────────────────────────────┤
│  FLOW:  PLAN (\$\$) → EXECUTE (\$) → REVIEW (\$\$)         │
│  RULE:  не max effort «на всякий»                        │
│  RULE:  hybrid > mono                                    │
└──────────────────────────────────────────────────────────┘
```

# Приложение B. Чеклист первой недели

- [ ] Выбрал default-модель  
- [ ] Понял разницу chat vs agent shell  
- [ ] Один раз сравнил hard-задачу на 2 флагманах  
- [ ] Один раз прогнал cheap long-context (M3)  
- [ ] Один раз UI на K3  
- [ ] Записал \$ и время  
- [ ] Собрал свой hybrid из 2–3 моделей  
- [ ] Добавил human review на прод  

---

**Конец методички · v1.0 · Июль 2026**

*Сделано как понятное руководство для людей, а не как API-reference.*
