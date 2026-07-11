# Claude Lane Stack

**Claude Code용 멀티 에이전트 코딩 오케스트레이션** — 파일 기반 태스크 계약, 선택적 AGY/Grok/Codex 레인, 경로 소유권, 보드, 스톨 감지, **PM이 `main`으로 자동 머지**.

```bash
git clone https://github.com/VKirill/claude-lane-stack.git
cd claude-lane-stack && ./install.sh
agents-doctor --apply .
claude --agent dev-orchestrator
```

PM은 항상 Claude Code입니다. 자세한 내용: [README.md](README.md).
