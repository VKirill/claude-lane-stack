---
name: browser-qa
description: "Live browser QA + Playwright-compatible replay. Disk .agents/qa/. Use when: проверь в браузере, кликни сценарий, вёрстка 375, screenshot QA. SKIP: DESIGN.md taste (design-lead); product Vue/CSS (run-supervisor); L0/L1 unit/API (lane-contract)."
argument-hint: "[info]"
---

# Browser QA

Adapted from [lee-to/ai-factory#154](https://github.com/lee-to/ai-factory/pull/154)
replay rules. Paths and gates are lane-stack. No `.ai-factory`, no human
«работает или нет».

## Info

If `$ARGUMENTS` is `info` / `справка`: print the block, **stop**.

```text
browser-qa — живой браузер, не writer.

.agents/qa/context.md     безопасный setup (без паролей)
.agents/qa/<slug>/
  cases.md   REPORT.md   shots/   replay/TC-00N.js   replay/history/

Дигесты: qa-digest cases|script|target
Кто кликает: adoc → Stages → browser_qa. По умолчанию codex gpt-6-astra low
в живом Chrome (browser-qa-codex); provider claude = Haiku + chrome-devtools MCP.
Нет chrome-devtools / Playwright / codex → blocked, не pass.
Свой Chrome для QA: chrome-qa start (профиль ~/.agents/chrome-qa, порт 9333, без диалогов)
+ chrome-devtools MCP --browserUrl http://127.0.0.1:9333. --autoConnect к личному Chrome —
диалог при каждом подключении; работать только в своих вкладках.
```

## Layout

```text
.agents/qa/context.md          # cross-run, non-secret
.agents/qa/<slug>/
  cases.md                     # source of truth for TC-*
  REPORT.md                    # execution only; never overwrite cases
  shots/
  replay/TC-00N.js
  replay/history/
```

Copy structure from `references/` next to this skill. English on disk.
Chat may be Russian. Redact tokens, cookies, OTP, `password`, `jwt` → `[REDACTED]`.

## Cases

PM / SPEC acceptance → `cases.md`. One `## TC-00N` heading per case (see
`references/cases.md`). Fields: Surface, Priority, Viewport, Preconditions,
Steps, Expected.

| Surface | This agent |
|---------|------------|
| `browser-ui` | Required. Live browser. Replay first. |
| `cli` / `backend-test` / `api` | Do not click. Note `blocked: use L0/L1`. No human array-checking. |
| `human` | Leave pending. Fable asks the operator. |

Default viewports if omitted: `375` `768` `1280`.

## Bindings

```bash
qa-digest cases .agents/qa/<slug>/cases.md
qa-digest script .agents/qa/<slug>/replay/TC-001.js
qa-digest target local 'http://127.0.0.1:5173/'
git -C . rev-parse HEAD
```

`tree` is `clean` if `git status --porcelain` has nothing **except** `.agents/qa/`;
else `dirty`.

`target_fingerprint` input is `QA TARGET\n<class>\n<normalized_base_url>\n`.
Normalize: drop userinfo, query, fragment; keep scheme/host/port/base path;
strip trailing slash except origin `/`. Class:
`local` | `staging` | `preview` | `production` | `unknown`.

Matching replay = embedded `case_digest` + embedded `target_fingerprint` +
file `script_digest` all equal REPORT's last **proven** values.

Stale (uncheck, keep old evidence, do not count as current):

- HEAD or `tree` changed → all results stale; **scripts stay reusable** if matching
- `cases.md` `source_digest` changed → stale only cases whose `case_digest` changed
- new TC → pending; removed TC → Stale / removed
- script bytes ≠ recorded script digest → that case stale, needs proof run
- missing digest metadata → unproven, not matching

## Replay (PR #154)

One case → `replay/TC-00N.js`. Smallest `async (page) => { … }`. No imports,
no new npm deps. Navigation uses the literal `"BASE_URL"` placeholder. At run
time substitute `normalized_base_url` **in memory**; do not rewrite the file
just to inject the host.

```js
// case_digest: <from qa-digest cases>
// target_fingerprint: <from qa-digest target>
async (page) => { /* goto("BASE_URL"+"/…"); asserts throw */ };
```

1. Write the script **before** the first click. That first execution is the proof. Do not auto-run a new/updated script a second time.
2. If mechanics were clarified after the observed run and the file changed, mark `unproven`. Repeat only after preconditions restored. Stateful (submit, pay, delete, email, permissions) needs a fresh go-ahead that says this is a **repeat**.
3. Record `script_digest` as proven only after **that exact file** executed. Until then: `n/a`, proof `unproven`.
4. Before repair/rebind: `cp` to `replay/history/TC-00N-<old_script_digest>.js`. Keep the first error in REPORT. Never run history.
5. Missing selector = **product fail** until the same control and behavior are proven in-browser and only the locator changed. Do not pick a similar element. Syntax/runner errors may be repaired (new proof). Assertion mismatch = fail, not a reason to regenerate the script.
6. Target mismatch → stop. Rebind changes `script_digest` and needs a new proof. Never treat a staging script as matching localhost.
7. After HEAD/`tree` change: replay every **matching** script (old pass and fail). Capability and side-effect rules still apply.
8. `proven` means the script ran, not that the product passed.
9. Discrete chrome-devtools actions: treat the file as the program; do not rewrite steps because the surface is MCP not `npx playwright`.
10. After replay, at most one bounded exploratory pass when the change is cross-cutting (nav, auth, layout, shared state) or a replay needed repair. Skip when the fix is narrow and matching replay already covers it. New bug → REPORT only; add `## TC-00N` first, then a script.

## Delegation (`stages.browser_qa`)

| provider | Who clicks | Command |
|----------|------------|---------|
| `codex` (default) | Codex `model`/`reasoning_effort` (default `gpt-6-astra` / `low`) with its browser, Chrome-extension and computer-use plugins; `backend` = `live-chrome` \| `chrome-qa` \| `headless` | `browser-qa-codex --project-cwd . --url … --slug … --case "…"` |
| `claude` | this agent via `chrome-devtools` MCP | steps below |

`browser-qa-codex` writes `cases.md`, `REPORT.md`, `shots/TC-00N-<w>.png`,
`codex-run.json` (model, effort, backend, exit) and `codex-result.json`
(structured verdict). Replay scripts are not produced in codex mode; the
receipt + shots are the proof. `approve: auto` passes `--approve-for-me`.

## Preflight

1. Read `.agents/qa/context.md` if present (routes, how to start the app, test-user **role**). No secrets.
2. Live browser: host-level `chrome-devtools` MCP (`mcp__chrome-devtools__*`: `list_pages`, `new_page`, `navigate_page`, `take_snapshot`, `take_screenshot`), else MetaMCP `chrome-devtools`, else existing project Playwright. If the MCP reports no browser, run `chrome-qa start` (dedicated profile, fixed port, no consent dialog) and retry once. No new dependency. None → every `browser-ui` case `blocked`. Do not write `pass`. WebFetch is not a browser.
   **Attached to the user's real Chrome** (macOS `--autoConnect`, or `--browserUrl`): the server exposes every open tab. Create your own page with `new_page`, act only in pages you created, never snapshot, navigate or close other tabs, close yours when done, and prefer a dedicated QA profile for sensitive sites.
3. `production` or `unknown`, or any side-effect case: do not run until the PM wrote `authorized` in the spawn prompt. Deny → `blocked`.
4. Auth: reuse a safe local fixture from context/docs. Never store prod/personal passwords, cookies, OTP. Disposable local users only if the repo already has a seed command.

## Run

1. `cd` project root. Slug from PM or `qa-<YYYYMMDD-HHMM>`.
2. Write or refresh `cases.md` from SPEC/acceptance. Do not invent URLs.
3. `qa-digest cases` + `qa-digest target`. If REPORT exists, apply stale rules before changing statuses.
4. Create REPORT from `references/REPORT.md` when missing. All new cases start pending.
5. Each `browser-ui` case: matching replay first; else write script, run once, shots `shots/TC-00N-<w>.png`.
6. Supporting L0/L1 commands may be listed; they do not count as extra TC results.
7. Last line to PM: `DONE .agents/qa/<slug>/REPORT.md` plus fail list and 3–5 shots.

## NEVER

- Product Vue/TS/CSS or `docs/DESIGN.md`
- `pass` without a live browser run of that `browser-ui` case
- Human mode, `.ai-factory`, `/aif-qa`
- Persist credentials; bake a preview host into the script
- Open-ended browsing
- `rm` / `git reset` / shared DB wipe
