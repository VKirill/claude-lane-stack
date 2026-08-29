# Module: core-harness

## Purpose
Durable SEO control plane: project STATUS, global BOARD/HANDOFF, runs and tasks.

## When
- Any SEO work session start/end
- Need recoverable state after restart

## Protocol
1. `seo-resume .` (or bootstrap via passport-onboard)
2. Work only under `.agents/seo/<slug>/`
3. After meaningful work: `seo-board && seo-handoff-write`
4. Multi-step work → `seo-run-init` + `seo-task`

## Outputs
See module.yaml artifacts.writes

## Failure
Missing `.agents/seo` → run passport-onboard or seo-init.
