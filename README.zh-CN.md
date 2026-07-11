# Claude Lane Stack

**面向 Claude Code 的多智能体编程编排** — 基于文件的任务契约、可选 AGY / Grok / Codex 通道、路径所有权、看板、卡死检测，以及**编排器自动合并到 `main`**。

> 关键词：Claude Code 多智能体 · AI 编程编排 · 多模型 coding agent · 文件任务队列 · 自动合并 main

## 快速开始

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
export PATH="$HOME/.agents/bin:$PATH"
agents-doctor --apply .
claude --agent dev-orchestrator
```

**PM 始终是 Claude Code**；AGY / Grok / Codex 为可选辅助通道。

文档见 `docs/`。MIT License。
