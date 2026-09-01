# Contributing to Claude Lane Stack

Thanks for helping make the factory better.

## Ground rules

1. **Fork** → branch from `main` → PR back to `main`.
2. **PM is always Claude Code.** Optional writer CLIs stay pluggable via `profiles/` + `agents-doctor`.
3. **No secrets** in commits (no `.env`, tokens, personal `metamcp.env`, machine-local absolute paths in docs).
4. **Long CLI jobs** use **`lane-bg` + `lane-wait` / `lane-ctl`** — never multi-minute foreground Bash under Claude.
5. **Agent-written durable files are English** ([docs/LANGUAGE.md](docs/LANGUAGE.md)). Chat language is free.

## Dev loop

```bash
# smoke
python3 -m py_compile hooks/*.py bin/lane-session bin/run-controller
python3 -m unittest discover -s tests -v
agents-doctor --json   # if installed
lane-bg --help && lane-wait --help
```

## Documentation (required for user-facing changes)

| Change | Update |
|--------|--------|
| UX / mental model | **`README.md`** (Russian canon) · **`README.en.md`** (English) |
| Onboard / lanes / routing | `docs/ONBOARD-SCENARIOS.md`, `LANE-EXEC.md`, `ROUTING.md`, `BEGINNER.md` (+ `.ru.md`) |
| Release | `CHANGELOG.md` + version badges in READMEs |

Only **English + Russian** README are maintained. Other locales were removed.

## PR checklist

- [ ] What / why in the description  
- [ ] How tested (commands above)  
- [ ] Docs updated if user-visible  
- [ ] No force-push to `main`  

## Code of conduct

Be excellent: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

Report privately: [SECURITY.md](SECURITY.md).
