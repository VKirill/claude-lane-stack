# Contributing

1. Fork and branch from `main`.
2. Keep PM = Claude Code; optional lanes stay pluggable via `profiles/` + `agents-doctor`.
3. Do not commit secrets, personal `metamcp.env`, or machine-local paths.
4. Run `python3 bin/agents-doctor --json` smoke; ensure hooks have no syntax errors: `python3 -m py_compile hooks/*.py`.
5. Docs: update EN README if UX changes; mirror short notes in `README.ru.md` when user-facing.
6. PR description: what / why / how tested.
