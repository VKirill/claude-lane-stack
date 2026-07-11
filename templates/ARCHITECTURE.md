# Architecture

> Evidence-based map. Mark unknowns as `// hypothesis`. Keep ≤300 lines; link out for detail.

## 1. Purpose

One paragraph: what the product does for users.

## 2. Boundaries

| In scope | Out of scope / external |
|----------|-------------------------|
| … | … |

## 3. Containers

| Name | Role | Tech |
|------|------|------|
| e.g. api | HTTP API | … |
| e.g. web | UI | … |
| e.g. worker | jobs | … |

Stores: Postgres / Redis / S3 / …

## 4. Key flows

1. **…** — step → step → step  
2. **…**

## 5. Module map

```
apps/
packages/
```

Dependency rules (who may import whom).

## 6. Invariants

- Hard rules that break the system if violated (or → CLAUDE.md).

## 7. Entry points

- Process boots, crons, queues, CLIs.

## 8. Cross-cutting

Auth · billing · logging · feature flags · i18n

## 9. Non-goals

…

## 10. Further reading

- `CLAUDE.md` · `docs/decisions.md` · `docs/plans/` · OpenAPI
