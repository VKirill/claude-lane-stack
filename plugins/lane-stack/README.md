# lane-stack (Claude Code plugin)

Claude-facing half of Claude Lane Stack: PM agents, slash commands, and playbook skills.

Install from the repo marketplace (not by copying into `~/.claude/agents` / `~/.claude/skills`):

```bash
claude plugin marketplace add /path/to/claude-lane-stack
claude plugin install lane-stack@claude-lane-stack -y
```

`./install.sh` does that and still rsyncs the host runtime (`bin/`, board, writer profiles) to `~/.agents`.

Skills are namespaced as `/lane-stack:<skill>`. Work cheat sheet: `/lane-stack:info` or `/info`. New app/service talk: `/lane-stack:app-architect`. PM playbooks (`orchestrator-lanes`, `orchestrator-workflow`, `info`, `app-architect`) live only in this plugin + `~/.agents/pm-skills` — they are not copied to the shared writer catalog.
