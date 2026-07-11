# Claude Lane Stack

**Мультиагентная оркестрация кода для Claude Code** — file-контракты, опциональные линии AGY / Grok / Codex, ownership путей, board, stall-watch и **авто-merge в `main` оркестратором**.

> Ключевые слова: оркестрация Claude Code · мультиагентная разработка · AGY Grok Codex · file-based task contracts · solo-разработчик · auto-merge main

| Язык | |
|------|--|
| [English](README.md) | EN |
| **Русский** | этот файл |

## Зачем

Один человек · один PM на Claude · дешёвые/быстрые модели пишут код · **ты не мержишь ветки**.

## Быстрый старт

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"
cd /path/to/project && agents-doctor --apply .
claude --agent dev-orchestrator
```

## Профили

| Профиль | Что нужно | Write | Review |
|---------|-----------|-------|--------|
| `full` | AGY+Grok+Codex | AGY+Grok | Codex |
| `claude-codex` | Codex | Codex | Codex |
| `claude-agy` / `claude-grok` | один write CLI | этот CLI | Claude reviewer |
| `claude-only` | только Claude | subagents | Claude |

PM **всегда** Claude Code.

## Документация

- [docs/SOLO-ORCHESTRATION.md](docs/SOLO-ORCHESTRATION.md)
- [docs/FILE-CONTRACT.md](docs/FILE-CONTRACT.md)
- [docs/ROUTING.md](docs/ROUTING.md)
- [docs/HOOKS.md](docs/HOOKS.md)

MIT · [@VKirill](https://github.com/VKirill)
