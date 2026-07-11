---
name: docs-maintain
description: Keep ARCHITECTURE/README/PROGRESS fresh for Claude Lane Stack projects after daily code changes. Use when: nightly docs, docs-maintain, обновить документацию, актуализировать ARCHITECTURE.
---

# Docs maintain

## Who

**Codex** `gpt-5.6-terra` + `high` via `codex-docs-maintainer` or bin:

```bash
docs-maintain-project /path/to/repo "24 hours ago"
docs-maintain-all "24 hours ago"           # scan ~/apps ~/sites ~/tools
docs-maintain-all "24 hours ago" --dry-run
```

## Markers (project is Lane Stack)

- `CLAUDE.md` contains `Claude Lane Stack`, or  
- `.agents/routing.profile.yaml`, or  
- `.agents/runs/` exists  

## Rules

- Skip if no substantive commits since window.  
- Surgical updates only to `docs/ARCHITECTURE.md`, README agent sections, PROGRESS.  
- No feature code. Report in `.agents/session-log/DOCS-YYYY-MM-DD.md`.  

## Cron

```bash
0 3 * * * $HOME/.agents/bin/docs-maintain-all "24 hours ago" >>/tmp/docs-maintain.log 2>&1
```
