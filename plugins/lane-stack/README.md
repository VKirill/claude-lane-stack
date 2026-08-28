# lane-stack (Claude Code plugin)

Claude-facing half of Claude Lane Stack: PM agents, slash commands, and playbook skills.

Install from the repo marketplace (not by copying into `~/.claude/agents` / `~/.claude/skills`):

```bash
claude plugin marketplace add VKirill/claude-lane-stack
claude plugin install lane-stack@claude-lane-stack -y
```

`./install.sh` registers that GitHub marketplace with `autoUpdate: true` and still rsyncs the host runtime (`bin/`, board, writer profiles) to `~/.agents`. Host files do not auto-update — rerun `./install.sh`. Live checkout: `LANE_INSTALL_LOCAL_MARKETPLACE=1 ./install.sh`.

Skills are namespaced as `/lane-stack:<skill>`. Work cheat sheet: `/lane-stack:info` or `/info`. New app/service talk: `/lane-stack:app-architect`. Living docs: `/lane-stack:docs-maintain`. Fact corpus: `/lane-stack:lane-memory`. PM playbooks (`orchestrator-lanes`, `orchestrator-workflow`, `info`, `app-architect`) live only in this plugin + `~/.agents/pm-skills` — they are not copied to the shared writer catalog.
