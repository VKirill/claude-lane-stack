# Claude Lane Stack

**Orquestación multi-agente de código para Claude Code** — contratos YAML en archivos, carriles opcionales AGY / Grok / Codex, ownership de rutas, tablero, detección de stalls y **auto-merge a `main` por el PM**.

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
agents-doctor --apply .
claude --agent dev-orchestrator
```

El PM es **siempre** Claude Code. Ver `docs/` y [README.md](README.md).
