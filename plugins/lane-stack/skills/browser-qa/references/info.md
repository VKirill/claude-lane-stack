browser-qa — живой браузер, не writer.

.agents/qa/context.md     безопасный setup (без паролей)
.agents/qa/<slug>/
  cases.md   REPORT.md   shots/   replay/TC-00N.js   replay/history/

Дигесты: qa-digest cases|script|target
Кто кликает: adoc → Stages → browser_qa. По умолчанию jev (browser-qa-jev:
CDP + таблица контролов). provider codex = gpt-6-astra; claude = Haiku + chrome-devtools.
Нет chrome-devtools / Playwright / codex → blocked, не pass.
Свой Chrome для QA: chrome-qa start (профиль ~/.agents/chrome-qa, порт 9333, без диалогов)
+ chrome-devtools MCP --browserUrl http://127.0.0.1:9333. --autoConnect к личному Chrome —
диалог при каждом подключении; работать только в своих вкладках.
