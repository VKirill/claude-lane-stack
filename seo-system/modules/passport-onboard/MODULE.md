# Module: passport-onboard

## Purpose
Create DrMax-aligned living passport (ANAMNESIS) for live sites or greenfield.

## Modes
- **live** — URL + optional first site scan
- **greenfield** — brand/niche brief only

## Protocol
1. `seo-onboard live|greenfield …`
2. Agent runs Universal Project Data Collector v2 (original 1:1)
3. Validator & Normalizer → `passport/validated.md`
4. Merge facts/hypotheses into `ANAMNESIS.md`
5. `seo-prompt-log` for each original used

## Do not
Invent legal form, revenue, partners, market share.
