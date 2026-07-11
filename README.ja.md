# Claude Lane Stack

**Claude Code 向けマルチエージェント開発オーケストレーション** — ファイルベースのタスク契約、任意の AGY / Grok / Codex レーン、パス所有権、ボード、ストール検知、**PM による `main` への自動マージ**。

## クイックスタート

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"
agents-doctor --apply .
claude --agent dev-orchestrator
```

PM は常に Claude Code。補助 CLI は `agents-doctor` が検出します。

---

Author: [@VKirill](https://github.com/VKirill) · Telegram [Помогающий маркетолог](https://t.me/pomogay_marketing)

![](docs/images/01-hero-conveyor.jpg)
