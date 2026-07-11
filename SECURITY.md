# Security Policy

## Supported versions

Latest `main` branch only.

## Reporting a vulnerability

Open a **private** security advisory on GitHub or email the maintainer via GitHub profile. Do not file public issues for secrets/RCE in hooks.

## Design notes

- Task YAML must never contain API keys or tokens.
- Hooks intentionally block force-push, hook bypass, and some destructive SQL patterns.
- `never_touch` should list `.env*`, credential paths, and irreversible migration dirs when relevant.
- Prefer Codex (or another review lane) for auth, payments, and schema changes.
- `install.sh` only writes under `~/.agents` and `~/.claude` — review the script before running on shared machines.
