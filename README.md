# Claude Lane Stack

Claude Lane Stack is a self-hosted toolkit for coordinating coding agents through CLI processes, task contracts, Git workspaces, and verification receipts (`bin/run-controller:117-159`, `schemas/task-v2.schema.json:1-60`). Claude Code provides the project manager interface; other provider CLIs are selected through the configured stages (`plugins/lane-stack/.claude-plugin/plugin.json:1-40`, `bin/pipeline_stages.py:205-300`).

## Quick start

```sh
./install.sh
export PATH="$HOME/.agents/bin:$PATH"
cd /path/to/your/project
project-onboard .
lane-pm
```

`install.sh` installs the host tools and prints the PATH setup and PM command (`install.sh:465-480`, `install.sh:560-567`).

## Documentation

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Gotchas](docs/gotchas.md)
- [Beginner guide](docs/BEGINNER.ru.md)
- [Hooks](docs/HOOKS.md)
- [Routing](docs/ROUTING.md)
- [English README](README.en.md)
- [Changelog](CHANGELOG.md)
