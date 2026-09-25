# Codex Lane

Repo-local Codex adapter for the installed Claude Lane Stack control plane.
The plugin provides two skills: `codex-lane` for operator lifecycle work and
`codex-lane-worker` for the bounded writer contract used by `lane-session`.

## Install and use

Run `./install.sh` from the repository root. It installs the shared core,
registers this checkout as the `claude-lane-stack` Codex marketplace, and
installs `codex-lane`. Set `LANE_INSTALL_CODEX_PLUGIN=0` to skip registration.
Open a new Codex session, then use `/hooks` to review and trust this plugin's
`SessionStart` and `UserPromptSubmit` hooks. Installation does not grant hook
trust. Invoke `$codex-lane` to inspect or operate an existing run.

The isolated writer receives this package's worker protocol as its own
`CODEX_HOME/AGENTS.md`; host plugins and hooks remain disabled there.

Dependencies:

- Python 3 for the two fail-open hook adapters. The Codex hook runner must
  provide `PLUGIN_ROOT` or `CLAUDE_PLUGIN_ROOT`.
- `~/.agents/bin/run-controller`, `lane-ctl`, `lane-session`, `run-validate`,
  and `check-owns-paths` from the installed lane stack.
- `~/.agents/bin/night-review` when a read-only review is requested.
- `~/.agents/hooks/skill_hint.py` for the optional main-session prompt hint;
  the hook fails open when the installed helper is absent.

The package contains no MCP server and no provider implementation. Lane
execution, report/evidence receipts, verification, review, and acceptance stay
in the installed `~/.agents` wrappers. `LANE_CODEX_WORKER=1` suppresses the
main-session catalog bridge and changes the SessionStart marker to worker
protocol text. The package does not replace native Codex compaction.

The lane runtime owns that worker marker and the isolated `CODEX_HOME`; the
plugin does not set either value. The prompt bridge removes plugin-root
discovery before delegating to the shared hint helper, so the worker skill is
not offered through the main-session catalog.
