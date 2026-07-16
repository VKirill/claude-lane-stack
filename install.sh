#!/usr/bin/env bash
# Install Claude Lane Stack into ~/.agents + Claude agents/skills
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.agents"
CLAUDE="${HOME}/.claude"

echo "==> Claude Lane Stack install"
echo "    from: $STACK_ROOT"
echo "    to:   $DEST"

mkdir -p "$DEST"/{bin,docs,hooks,templates,skills,agy/agents,grok/instructions,codex/instructions}
mkdir -p "$CLAUDE"/{agents,skills,commands}

# bins
install -m 0755 "$STACK_ROOT"/bin/* "$DEST/bin/" 2>/dev/null || cp -a "$STACK_ROOT"/bin/* "$DEST/bin/"
chmod +x "$DEST"/bin/*

# docs hooks templates
cp -a "$STACK_ROOT"/docs/* "$DEST/docs/"
cp -a "$STACK_ROOT"/hooks/* "$DEST/hooks/"
cp -a "$STACK_ROOT"/templates/* "$DEST/templates/"

# skills
for d in "$STACK_ROOT"/skills/*/; do
  name="$(basename "$d")"
  rsync -a "$d" "$DEST/skills/$name/"
  ln -sfn "$DEST/skills/$name" "$CLAUDE/skills/$name"
done

# platform agents
rsync -a "$STACK_ROOT"/agents/agy/ "$DEST/agy/agents/"
rsync -a "$STACK_ROOT"/agents/grok/ "$DEST/grok/instructions/"
rsync -a "$STACK_ROOT"/agents/codex/ "$DEST/codex/instructions/"

# Claude agents
cp -a "$STACK_ROOT"/agents/claude/*.md "$CLAUDE/agents/"
if [[ -d "$STACK_ROOT/agents/claude/commands" ]]; then
  cp -a "$STACK_ROOT"/agents/claude/commands/* "$CLAUDE/commands/" 2>/dev/null || true
fi

# AGY discovery (optional)
if [[ -d "$HOME/.gemini/config/agents" ]]; then
  for a in lane-coder lane-frontend lane-reviewer consult; do
    if [[ -d "$DEST/agy/agents/$a" ]]; then
      ln -sfn "$DEST/agy/agents/$a" "$HOME/.gemini/config/agents/$a"
    fi
  done
  echo "    linked AGY agents → ~/.gemini/config/agents"
fi

# PATH
if ! grep -q '\.agents/bin' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.agents/bin:$PATH"' >> "$HOME/.bashrc"
  echo "    appended PATH to ~/.bashrc"
fi
export PATH="$HOME/.agents/bin:$PATH"

# profiles into stack copy for reference
mkdir -p "$DEST/profiles"
cp -a "$STACK_ROOT"/profiles/* "$DEST/profiles/" 2>/dev/null || true

echo ""
echo "==> Running agents-doctor in current directory (if git repo)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  agents-doctor --apply . || true
else
  echo "    (skip doctor — not in a git repo; run: agents-doctor --apply /path/to/project)"
fi

echo ""
echo "Done. (v1.3.1+) Start PM:"
echo "  export PATH=\"\$HOME/.agents/bin:\$PATH\""
echo "  claude --agent dev-orchestrator"
echo "Onboard:  /project-onboard   or   project-onboard . [--deep|--fast]"
echo "Cold start: /resume-project   or   resume-project ."
echo "Long lanes: lane-bg + lane-wait (never long foreground Bash)"
echo "Multi-task: progressive accept via lane-poll + MODE=start/finish"
echo "Anti-join: lane-mode-check refuses MODE=full on multi-task runs"
echo "Warm lanes: lane-session resumes run-scoped AGY/Grok conversations"
echo "Beginner: docs/BEGINNER.md · RU: docs/BEGINNER.ru.md"
echo "Docs: $DEST/docs/  (ONBOARD-SCENARIOS, LANE-EXEC, ROUTING, LANGUAGE)"
