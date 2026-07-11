# Claude Lane Stack

<p align="center">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Конвейер мультиагентной разработки" width="100%" />
</p>

**Маленький ИИ-завод по коду для одного человека.**  
Ты говоришь с одним прорабом (Claude Code). Он раздаёт работу (AGY / Grok / Codex — по желанию), проверяет и **кладёт готовое в ветку `main`**. Ты не ведёшь пять чатов и не мержишь ветки.

[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)
[![Новичкам](https://img.shields.io/badge/Старт-Гайд%20новичка-brightgreen)](docs/BEGINNER.ru.md)

| | |
|--|--|
| [English](README.md) | EN |
| **Русский** | этот файл |

**Впервые слышишь про «оркестрацию»?** → **[Гайд новичка простым языком](docs/BEGINNER.ru.md)**

---

## Автор

<p align="center">
  <a href="https://github.com/VKirill"><img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="120" height="120" alt="Кирилл Вечкасов" style="border-radius:50%" /></a>
</p>

<p align="center">
  <strong>Кирилл Вечкасов</strong> · <a href="https://github.com/VKirill">@VKirill</a><br/>
  Telegram: <a href="https://t.me/pomogay_marketing"><strong>Помогающий маркетолог</strong></a>
</p>

Собираю **рабочие конвейеры**, а не «ещё один чат с нейросетью».  
Один человек · Claude-прораб · модели на линиях · **merge в main делает оркестратор**.

→ [t.me/pomogay_marketing](https://t.me/pomogay_marketing)

---

## Если запомнить только три шага

```bash
# 1) Один раз на компьютере
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"

# 2) В папке ТВОЕГО проекта — какие ИИ-CLI есть
cd /path/to/your-project
agents-doctor --apply .

# 3) Запустить прораба и писать по-человечески
claude --agent dev-orchestrator
# первый раз в проекте:  /project-onboard
# после перерыва:         /resume-project
```

| Шаг | Простыми словами |
|-----|------------------|
| `./install.sh` | Поставить «набор завода» на компьютер |
| `agents-doctor --apply .` | Кто из работников доступен в этом проекте |
| `claude --agent dev-orchestrator` | Единственный чат, который тебе нужен — **PM** |
| `/project-onboard` | Паспорт проекта (CLAUDE.md) — делает **Codex** |
| `/resume-project` | «На чём остановились?» после сна / нового чата — **не** шаг установки |

Полный путь: [docs/BEGINNER.ru.md](docs/BEGINNER.ru.md).

---

## Что это за 30 секунд

| Роль | Кто | Ты |
|------|-----|-----|
| Хозяин | **Ты** | Говоришь *что* нужно обычным языком |
| Прораб | Claude `dev-orchestrator` | Планирует, раздаёт, проверяет, мержит в `main` |
| Работники | AGY / Grok / Codex (опционально) | Пишут или ревьюят код |
| Карточки задач | `.agents/runs/` | Создаёт PM |
| Официальный код | ветка **`main`** | Конец успешной работы |

---

## Визуал

| | |
|--|--|
| Конвейер, не хаос чатов | ![](docs/images/01-hero-conveyor.jpg) |
| Линии → в main | ![](docs/images/02-lanes-routing.jpg) |
| Merge делает оркестратор | ![](docs/images/03-auto-merge-main.jpg) |
| У каждой задачи — свои файлы | ![](docs/images/04-file-contracts.jpg) |

---

## Шпаргалка команд (новичок)

### Установка (один раз)

| Команда | Зачем | Когда |
|---------|--------|------|
| `git clone …` | Скачать репозиторий | Первый раз |
| `./install.sh` | Поставить агентов и утилиты | Первый раз |
| `export PATH=…` | Чтобы команды находились | Новый терминал |

### Каждый проект (один раз)

| Команда | Зачем | Когда |
|---------|--------|------|
| `agents-doctor --apply .` | Профиль работников | Первый заход / новый CLI |
| `/project-onboard` | CLAUDE.md + первичная дока | Пустой/новый проект |
| `claude --agent dev-orchestrator` | Старт PM | Каждая сессия |

### Каждый день

| Что пишешь | Зачем | Когда |
|------------|--------|------|
| *«Добавь кнопку входа»* | Обычная работа | Фичи и баги |
| `/resume-project` | Сейчас / блок / дальше | **После перерыва** |
| *«Зависло»* | Найти замолчавшего | Долго нет ответа |

### Обычно только PM

`run-board`, `wt-create`, `wt-merge-main`, `check-owns-paths`, `lane-stall-check` — см. [BEGINNER.ru.md](docs/BEGINNER.ru.md).

---

## Сноски для тех, кто впервые

1. **Не нужны сразу все CLI.** Достаточно Claude Code.  
2. **`/resume-project` — не шаг №1 установки.** Это шпаргалка, когда чат «забыл» вчерашний день.  
3. **Планы/SEO (COCOON)** → `docs/plans/`. **Код** → `.agents/runs/`. Скажи *«реализуй»*, чтобы перейти от плана к цеху.  
4. **Если просят смержить ветку вручную — что-то не так.** Merge в `main` делает PM.  
5. **Закрыл терминал — проект не пропал.** Пропал только контекст чата → `/resume-project`.

---

## Дальше, если интересно

- [SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) — solo-режим  
- [FILE-CONTRACT.md](docs/FILE-CONTRACT.md) — формат задач  
- [ROUTING.md](docs/ROUTING.md) — кто пишет / ревьюит  

MIT · [@VKirill](https://github.com/VKirill) · [Помогающий маркетолог](https://t.me/pomogay_marketing)
