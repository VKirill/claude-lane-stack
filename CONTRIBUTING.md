# Contributing

1. Fork and branch from `main`.
2. Keep PM = Claude Code; optional lanes stay pluggable via `profiles/` + `agents-doctor`.
3. Do not commit secrets, personal `metamcp.env`, or machine-local paths.
4. Smoke: `agents-doctor --json` if available; `python3 -m py_compile hooks/*.py`; `lane-bg --help` / `lane-wait --help`.
5. **Docs stay current with product:**
   - User-facing UX → update **`README.md` + `README.ru.md` fully**, and add a short **vX.Y** note block to other `README.*.md` locales.
   - Onboard / lanes / routing changes → `docs/ONBOARD-SCENARIOS.md`, `docs/LANE-EXEC.md`, `docs/ROUTING.md`, `docs/BEGINNER.md` (+ `.ru.md` at least).
   - Agent-written surfaces remain **English** (`docs/LANGUAGE.md`).
6. Long CLI patterns in implementers must use **`lane-bg` + `lane-wait`**, never multi-minute foreground Bash.
7. PR description: what / why / how tested; link release notes if user-visible.
