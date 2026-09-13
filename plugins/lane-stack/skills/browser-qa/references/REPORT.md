# QA `<slug>`

- Source: `.agents/qa/<slug>/cases.md`
- Source digest: `<qa-digest cases>`
- Tested revision: `<git rev-parse HEAD>`
- Tree: `clean` | `dirty` (ignore `.agents/qa/**`)
- Target class: `local` | `staging` | `preview` | `production` | `unknown`
- Target fingerprint: `<qa-digest target>`
- BASE_URL: `<normalized, no query/userinfo>`
- Replay: `.agents/qa/<slug>/replay/`
- Updated: `<UTC>`

## Summary

- Total / Passed / Failed / Blocked / Pending: n
- Next for Fable: `fix` | `done` | `blocked`

## Exploration

- Decision: `ran` | `skipped`
- Reason:
- Findings: none | …

## Results

### TC-001 Title
- [ ] Status: pending | passed | failed | blocked | stale
- Surface: browser-ui
- Case digest:
- Replay: `replay/TC-001.js`
- Script digest: n/a | `<proven>`
- Proof: unproven | proven
- Target fingerprint:
- Capability: chrome-devtools | playwright
- History: n/a | `replay/history/TC-001-<old>.js`
- First error:
- Shots: `shots/TC-001-375.png`
- Evidence:
- L1 (optional): `BASE_URL=… npx playwright test` only if the repo already has Playwright

## Stale / removed

- TC-000: reason (HEAD | dirty tree | case digest | script digest | target)
