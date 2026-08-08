# Security Policy

## Supported versions

| Branch | Supported |
|--------|-----------|
| `main` / latest release | ✅ |
| Older tags | ⚠️ best-effort only |

## Reporting a vulnerability

**Do not** open a public issue for RCE, secret leaks, or auth bypasses.

1. Prefer a **GitHub Security Advisory** (private) on this repository, or  
2. Contact the maintainer via their [GitHub profile](https://github.com/VKirill).

Include: impact, repro steps, affected version, and any suggested fix.

## Design notes (for auditors)

- Task YAML must **never** contain API keys or tokens  
- Hooks block force-push, hook-bypass patterns, and some destructive ops  
- Prefer review rails (Codex night / `emergency-writer` only when terminal-blocked) for auth, payments, schema  
- `install.sh` writes under `~/.agents`, `~/.claude`, and Codex profiles — review before running on shared machines  
- Writer isolation on Linux uses **bubblewrap** when available  

Thank you for helping keep solo operators safe.
