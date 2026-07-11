# Claude Lane Stack

<p align="center">
  <img src="docs/images/01-hero-conveyor.jpg" alt="Конвейер мультиагентной разработки" width="100%" />
</p>

**Мультиагентная оркестрация кода для Claude Code** — file-контракты, опциональные линии AGY / Grok / Codex, ownership путей, board, stall-watch и **авто-merge в `main` оркестратором**.

[![Telegram](https://img.shields.io/badge/Telegram-Помогающий%20маркетолог-2CA5E0?logo=telegram)](https://t.me/pomogay_marketing)

| Язык | |
|------|--|
| [English](README.md) | EN |
| **Русский** | этот файл |

---

## Автор

<p align="center">
  <a href="https://github.com/VKirill">
    <img src="https://avatars.githubusercontent.com/u/17155104?v=4" width="120" height="120" alt="Кирилл Вечкасов" style="border-radius:50%" />
  </a>
</p>

<p align="center">
  <strong>Кирилл Вечкасов</strong> · <a href="https://github.com/VKirill">@VKirill</a><br/>
  Telegram: <a href="https://t.me/pomogay_marketing"><strong>Помогающий маркетолог</strong></a>
</p>

Собираю **рабочие конвейеры**, а не очередной «поговори с LLM».  
Один человек · PM на Claude · остальные модели — на линиях · **merge в main делает оркестратор**.

→ [t.me/pomogay_marketing](https://t.me/pomogay_marketing)

---

## Как устроен завод (визуал)

| | |
|--|--|
| Конвейер | ![](docs/images/01-hero-conveyor.jpg) |
| Линии PM → AGY / Grok / Codex → main | ![](docs/images/02-lanes-routing.jpg) |
| Авто-merge, ты не мержишь | ![](docs/images/03-auto-merge-main.jpg) |
| File contracts + owns_paths | ![](docs/images/04-file-contracts.jpg) |

## Быстрый старт

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"
cd /path/to/project && agents-doctor --apply .
# онбординг CLAUDE.md — Codex sol xhigh:
# /project-onboard
claude --agent dev-orchestrator
```

**PM всегда Claude.** AGY / Grok / Codex — по наличию (`agents-doctor`).

- Execution → `.agents/runs/`
- Стратегия / COCOON → `docs/plans/`
- Документация: `docs/`

MIT · [@VKirill](https://github.com/VKirill) · [Помогающий маркетолог](https://t.me/pomogay_marketing)
