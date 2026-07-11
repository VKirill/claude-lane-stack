# Deployment

> How this product ships and rolls back. Evidence from repo only; no invented infra.  
> Language: **English**.

## Environments

| Name | Purpose | URL / host (if known) |
|------|---------|------------------------|
| local | dev | … |
| staging | … | … |
| production | … | … |

## Ship path

1. …
2. …

## Runtime

- Process manager: PM2 / systemd / k8s / …
- Config files: `ecosystem.config.js`, compose, helm, …
- Port / bind: …

## Database / migrations

- …

## Media / object storage (if any)

- …

## Rollback

1. …
2. …

## Smoke checks after deploy

```bash
# e.g. curl health, pm2 status
```

## Secrets

- Where they live (env names only — **never** paste values).
