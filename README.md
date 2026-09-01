# Claude Lane Stack

**v1.24.0** · [English](README.en.md) · [Changelog](CHANGELOG.md) · [Новичкам](docs/BEGINNER.ru.md) · [MIT](LICENSE)

Один человек. Один ИИ-PM. Настоящие CLI-писатели на конвейере из файлов и git.

Говорите с Claude Code — он гоняет Codex / Qwen / Grok / Kimi / AGY / Cursor / OpenCode, проверяет работу, **мержит в `main`**, ночью делает независимое ревью.

Чат — русский. Ключи и файлы агентов — английские.

---

## Как открыть скилл

| Что | Команда |
|---|---|
| Каталог процессов | `/lane-stack:info` · `/info` · «справка» |
| Карточка одного скилла | `/lane-stack:<имя> info` |
| Сделать работу | `/lane-stack:<имя>` или фраза в чате |

Скилл с одноимённой командой (`resume-project`, `project-onboard`, `app-architect`, `info`) **не** дублируется в меню Skills: команда делает работу, `info` — шпаргалку.

Копирайт и ЦА — агент **`copy-lead`** (скиллы ниже, диск `.agents/copy/`). SEO — `seo-specialist`. Внешность — `design-lead` (`DESIGN.md`). Код — `dev-orchestrator`.

---

## Как устроен завод

```text
Вы ──чат──►  Claude Code · dev-orchestrator
                    │
          run-supervisor + run-controller
      ┌─────┬─────┬─────┬─────┐
      ▼     ▼     ▼     ▼     ▼
   Codex  Qwen  Grok  Kimi   AGY …
                    │
          owns → L1 → acceptance.json → main
                    │
              ночь: Codex Sol
```

Единица работы — карточка `.agents/runs/<slug>/tasks/*.yaml`: `owns_paths`, `verification[]`, квитанция `acceptance.json`. Нет квитанции — не готово.

День: быстро катить. Ночь: независимое ревью + живые `docs/` + корпус фактов (оба модуля opt-in в `adoc`).

Писателя руками не запускаете. Говорите с PM. Writer — фоновый процесс, не субагент с именем бренда.

---

## Скиллы плагина

Все живут в `plugins/lane-stack/skills/`. Префикс `/lane-stack:`.

### Жизнь проекта

| Скилл | Что делает | Не делает |
|---|---|---|
| `info` | Каталог процессов | Ран, онборд, дизайн |
| `resume-project` | CLI: Сейчас / Блок / Дальше | Шпаргалку (только `info`) |
| `project-onboard` | Паспорт репо: CLAUDE.md, MODULE_MAP, тесты | `DESIGN.md` (это `design-lead`) |
| `project-life` | Идея → туду → план → PROGRESS / LESSONS | Холодный старт (это resume) |
| `app-architect` | Новое приложение словами, файлы плана на диск | Ран |
| `project-design` | Роутер на полные `docs/DESIGN.md` | Код UI |
| `ui-ux-pro-max` | Справочник стилей, a11y, баннеры | Сами DESIGN.md |
| `docs-maintain` | Живые `docs/` по диффу | Вики, планы, новые фичи |
| `lane-memory` | Факты, которых нет в коде (`.agents/memory/`) | PROGRESS / LESSONS |

### Конвейер (только сессия `dev-orchestrator`)

| Скилл | Что делает |
|---|---|
| `orchestrator-lanes` | Счёт, DAG, `run-init`, L0/L1/L2, ship. Пока не сказано «делай» — ран не открывать |
| `orchestrator-workflow` | Устаревший алиас `orchestrator-lanes` |
| `lane-contract` | Как писать YAML: owns, verify, acceptance |
| `writer-practices` | Стиль кода внутри `owns_paths` |

### Копирайт сайта (не SEO)

Диск — источник правды. Скиллы заполняют файлы, не Vue и не `DESIGN.md`.

```text
<репо>/.agents/copy/
  INDEX.md                  доска: status / on_site
  ANAMNESIS.md              оффер, доказательство, запреты
  audience.md               герой, боль, альтернативы, темы
  buyer-personas/p1.md      история покупки, не «Мария 34»
  voice.md                  указатель на DESIGN.md + стоп-слова
  pages/<slug>.md           бриф страницы: H1, поток, UI
  research/inbox|used|dead  один файл на запрос, не web.md
```

Шаблоны: `copy-project-life/references/*.template.md`. Копировать 1:1, пустое = `unknown`. Цитаты не выдумывать.

| Скилл | Роль |
|---|---|
| `copy-project-life` | Карта + посев файлов + первый опрос |
| `site-copy-audience` | Анамнез, ЦА, персоны, голос |
| `site-copy-headlines` | H1 и поток страницы |
| `site-copy-ux` | Кнопки, формы, подписи |
| `page-prototype` | Серый HTML + kit + превью 24ч (`publish.py`, тот же URL при правке) |
| `ru-text` · `ru-check` · `ru-score` | Русский: типографика / вычитка / балл (copy-lead) |

**Цепочка**

1. Нет `.agents/copy/` или пустой `product:` → посев шаблонов.
2. Опрос пачками по 2–3 вопроса (`first-interview.md`): оффер → ЦА → персона / доказательства.
3. Ответы сразу в файлы. «не знаю» = `unknown`.
4. `site-copy-audience` дописывает темы и grunt test.
5. На каждую страницу: `site-copy-headlines` → `site-copy-ux`.
6. Нужен кликабельный макет — `page-prototype` (не Vue, не DESIGN.md).
7. Русский текст: `ru-text` на ходу, «вычитай» → `ru-check`, «оцени» → `ru-score`.

Без оффера и `audience.md` заголовки не пишутся.

**Первый опрос**

1. Что продаёте? Кто платит? Цена? Что купят, если вас нет? Полка рынка? Что нельзя обещать?
2. Герой и его желание. Внешняя / внутренняя боль (покупают внутреннюю). Злодей-причина, не логотип. Что делают без вас. С чем путают.
3. День, когда начали искать. Что пробовали. Кто ещё подписывает. Живой клиент или нет. Их слова / наши стоп-слова.

**Страница** (`pages/<slug>.md`)

- Уровень осведомлённости Schwartz 1–5: первый экран обязан совпасть (уровень 5 = оффер+цена; уровень 2 = назвать рану).
- 5–8 заголовков, оценка Bly 4 U’s (срочность, уникальность, конкретность, польза). В бой — если ≥3 оси ≥3.
- Поток: внимание → нужда → закрыть → доказать → попросить.
- UI: один H1, одна главная кнопка = глагол + объект (`Получить аудит`, не `Отправить`).

Открыть: `lane-pm` с `LANE_PM_AGENT=copy-lead` · `claude --agent copy-lead` · `/lane-stack:copy-project-life` · «весь анализ копирайта».

Не путать с `seo-copywriting` (ключи, title, плотность) и с `project-design` (токены).

### SEO (не код сайта)

Два слоя: жизнь клиента в `<репо>/.agents/seo/<slug>/` и каталог умений `~/.agents/seo-system/` (`seo-module`).

| Скилл | Роль |
|---|---|
| `seo-project-life` | Карта: паспорт, доска, фазы, CLI |
| `seo-drmax-orchestrator` | Вести пайплайн DrMax, не один промпт |
| `seo-prompt-engineering-2026` | Канон промптов книги (не переписывать) |
| `seo-evidence-based-2026` | NavBoost / Q* / Twiddlers, аудит |
| `seo-copywriting` | Ключи и мета в тексте |
| `ai-detect` | Роботность LinguaForensic |
| `drmax-cvd` | Выживет ли страница в AI Overview |
| `drmax-latent-intent` | Скрытый интент одной фразы |
| `drmax-text-humanization` | Редактура после GIST, не обход детекторов |
| `drmax-lexadapt` | Упростить под CEFR / ТРКИ |
| `mutagen` | Частотность Wordstat, конкуренция |
| `xmlstock` | Живой SERP Яндекс / Google |
| `proxy6` | Пул прокси для fetch / SERP |
| `yandex-webmaster` | Запросы и индекс своего сайта |
| `yandex-metrica` | Трафик и цели |
| `google-search-console` | GSC searchanalytics / URL Inspection |
| `ga4-data-api` | GA4 Data API |
| `google-cloud-auth` | OAuth / service account для GSC и GA4 |

Агент: `seo-specialist`. Код сайта — не сюда. Ключи API — `~/secrets/*.env`, не в плагине.

### Поведение и инструменты

| Скилл | Роль |
|---|---|
| `karpathy-guidelines` | Не врать про тесты, не плодить абстракции |
| `metamcp` | agentmemory + gitnexus напрямую; остальное через MetaMCP |

---

## Агенты (не скиллы)

Их спавнит оркестратор. В меню CC они есть, но **не** стартуют от клика — нужен `lane-pm` или фраза «старт» / `/resume-project`.

| Агент | Зачем |
|---|---|
| `dev-orchestrator` | PM: план, диспатч, merge |
| `run-supervisor` | Смотрит один ран |
| `lane-supervisor` | Одно действие `lane-ctl` |
| `emergency-writer` | Codex после terminal block |
| `project-onboarder` | Паспорт (первый) |
| `docs-maintainer` | Wiki после онборда / ночные docs |
| `night-reviewer` | Ночной review |
| `design-lead` | Полные DESIGN.md |
| `memory-maintainer` | Корпус фактов |
| `seo-specialist` | SEO harness |
| `copy-lead` | Копирайт, ЦА, страницы |
| `tavily` | Поиск Tavily, отчёт с URL |

Запуск копирайтера: `LANE_PM_AGENT=copy-lead lane-pm` или `claude --agent copy-lead`. Модель сессии — **Opus**. В `/config` стиль `copywriter` — **только в этой сессии** (не дефолт проекта). Профессий в модели нет: шляпы зашиты в агенте (`craft.md`).

---

## Быстрый старт

### 1. Один раз на машину

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && git checkout v1.24.0
./install.sh
export PATH="$HOME/.agents/bin:$PATH"
```

Плагин: `lane-stack@claude-lane-stack`, marketplace сам обновляется с GitHub. Хост `~/.agents` — снова `./install.sh`. Живой чекаут: `LANE_INSTALL_LOCAL_MARKETPLACE=1 ./install.sh`.

Нужно: Claude Code · Git · Python 3 (+ PyYAML/jsonschema) · Node · rsync · `flock`. Writers — по желанию.

### 2. Один раз в проекте

```bash
cd /path/to/your-project
agents-doctor --apply .
```

### 3. PM

```bash
lane-pm
```

| В чате | Когда |
|---|---|
| `/project-onboard` | Первый раз в репо |
| `/resume-project` | После перерыва |
| `/info` | Каталог |
| `/app-architect` | Новый продукт |
| `LANE_PM_AGENT=copy-lead lane-pm` | Сессия копирайтера |
| «весь анализ копирайта» | Оффер, ЦА, страницы |
| «Добавь тёмную тему» | Фича → конвейер |

---

## adoc

Вкладки: Кодер · Этапы · Память · Документация · Работа · Ночь · UI · Статус · Инфо · Применить.

| Ручка | Смысл |
|---|---|
| Writer `main_write` | `codex` / `qwen` / `grok` / `kimi` / `agy` / `cursor` / `opencode` |
| Этапы | критика плана · код · ночной ревью · онбординг |
| Память / Docs | opt-in; writer фичи их не пишет |
| Workspace | `in_place` · `worktree` · `auto` |

---

## Хост-команды

| Команда | Зачем |
|---|---|
| `agents-doctor` / `adoc` | Профиль машины |
| `resume-project .` | Сейчас / Блок / Дальше |
| `run-init` · `run-controller` | Раны (обычно PM) |
| `lane-memory` | Корпус фактов |
| `docs-maintain-project` | Живые docs |
| `night-shift` | Ночь |

---

## Нельзя

- Claude Plan mode и `~/.claude/plans/`
- `run-init`, пока не сказано **«делай»**
- UI-ран без `docs/DESIGN.md` / `apps/<app>/docs/DESIGN.md`
- H1 копирайта без `audience.md`
- Копировать агентов стека в `~/.claude/agents` — копии перебивают плагин

Чат: русский. Файлы агентов: английский ([LANGUAGE.md](docs/LANGUAGE.md)). Merge делает PM, не вы.

---

## Документация

| Док | Зачем |
|---|---|
| [BEGINNER.ru.md](docs/BEGINNER.ru.md) | С нуля |
| [SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md) | День / ночь |
| [ROUTING.md](docs/ROUTING.md) | Модели |
| [LANE-EXEC.md](docs/LANE-EXEC.md) | Процессы |
| [FILE-CONTRACT.md](docs/FILE-CONTRACT.md) | Раскладка |
| [plugins/lane-stack/README.md](plugins/lane-stack/README.md) | Плагин |
| [README.en.md](README.en.md) | English |
| [CHANGELOG.md](CHANGELOG.md) | Релизы |

Канал: [Помогающий маркетолог](https://t.me/pomogay_marketing)
