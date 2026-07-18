#!/usr/bin/env bash
# Install Claude Lane Stack into ~/.agents + Claude agents/skills
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.agents"
CLAUDE="${HOME}/.claude"
CODEX="${CODEX_HOME:-${HOME}/.codex}"

echo "==> Claude Lane Stack install"
echo " from: $STACK_ROOT"
echo " to: $DEST"

mkdir -p "$DEST"/{bin,docs,hooks,templates,skills,schemas,agents,grok/instructions,codex/instructions}
mkdir -p "$CLAUDE"/{agents,skills,commands}
mkdir -p "$CODEX"

# bins
for executable in "$STACK_ROOT"/bin/*; do
  [[ -f "$executable" ]] || continue
  install -m 0755 "$executable" "$DEST/bin/"
done
chmod +x "$DEST"/bin/*

# docs hooks templates
cp -a "$STACK_ROOT"/docs/* "$DEST/docs/"
cp -a "$STACK_ROOT"/hooks/* "$DEST/hooks/"
cp -a "$STACK_ROOT"/templates/* "$DEST/templates/"
cp -a "$STACK_ROOT"/schemas/* "$DEST/schemas/"

# skills
for d in "$STACK_ROOT"/skills/*/; do
  name="$(basename "$d")"
  rsync -a "$d" "$DEST/skills/$name/"
  claude_skill="$CLAUDE/skills/$name"
  if [[ -L "$claude_skill" ]]; then
    ln -sfn "$DEST/skills/$name" "$claude_skill"
  elif [[ -d "$claude_skill" ]]; then
    # Preserve an existing user-managed directory, but keep stack-owned files
    # current. Plain `ln -sfn` would create a misleading nested self-link.
    rsync -a "$d" "$claude_skill/"
    legacy_nested="$claude_skill/$name"
    if [[ -L "$legacy_nested" ]] \
      && [[ "$(readlink -f "$legacy_nested")" == "$DEST/skills/$name" ]]; then
      unlink "$legacy_nested"
    fi
  elif [[ -e "$claude_skill" ]]; then
    echo "error: cannot install skill over non-directory: $claude_skill" >&2
    exit 1
  else
    ln -s "$DEST/skills/$name" "$claude_skill"
  fi
done

# platform agents
rsync -a "$STACK_ROOT"/agents/ "$DEST/agents/"
rsync -a "$STACK_ROOT"/agents/grok/ "$DEST/grok/instructions/"
rsync -a "$STACK_ROOT"/agents/codex/ "$DEST/codex/instructions/"

# Claude agents
cp -a "$STACK_ROOT"/agents/claude/*.md "$CLAUDE/agents/"
if [[ -d "$STACK_ROOT/agents/claude/commands" ]]; then
  cp -a "$STACK_ROOT"/agents/claude/commands/* "$CLAUDE/commands/" 2>/dev/null || true
fi

#  discovery (optional)
if [[ -d "$HOME/.gemini/config/agents" ]]; then
  for a in lane-coder lane-frontend lane-reviewer consult; do
    if [[ -d "$DEST/agents/$a" ]]; then
      ln -sfn "$DEST/agents/$a" "$HOME/.gemini/config/agents/$a"
    fi
  done
  echo " linked agents → ~/.gemini/config/agents"
fi

# PATH
if ! grep -q '\.agents/bin' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.agents/bin:$PATH"' >> "$HOME/.bashrc"
  echo " appended PATH to ~/.bashrc"
fi
export PATH="$HOME/.agents/bin:$PATH"

# profiles into stack copy for reference
mkdir -p "$DEST/profiles"
cp -a "$STACK_ROOT"/profiles/* "$DEST/profiles/" 2>/dev/null || true
if [[ -f "$STACK_ROOT/profiles/codex/night-review.config.toml" ]]; then
  install -m 0644 \
    "$STACK_ROOT/profiles/codex/night-review.config.toml" \
    "$CODEX/night-review.config.toml"
fi

# Machine-readable local deploy receipt consumed by merge.json.
SOURCE_SHA="$(git -C "$STACK_ROOT" rev-parse HEAD 2>/dev/null || true)"
SOURCE_DIRTY=false
if [[ -n "$(git -C "$STACK_ROOT" status --porcelain 2>/dev/null || true)" ]]; then
  SOURCE_DIRTY=true
fi
python3 - "$DEST/install.json" "$STACK_ROOT" "$SOURCE_SHA" "$SOURCE_DIRTY" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

target, source_repo, source_sha, source_dirty = sys.argv[1:]
path = Path(target)
temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
temporary.write_text(json.dumps({
    "schema_version": 1,
    "installed_at": datetime.now(timezone.utc).isoformat(),
    "source_repo": source_repo,
    "source_sha": source_sha or None,
    "source_dirty": source_dirty == "true",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temporary, path)
PY

echo ""
echo "==> Running agents-doctor in current directory (if git repo)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  agents-doctor --apply . || true
else
  echo " (skip doctor — not in a git repo; run: agents-doctor --apply /path/to/project)"
fi

echo ""
echo "Done. (v1.5.0+) Start PM:"
echo " export PATH=\"\$HOME/.agents/bin:\$PATH\""
echo " claude --agent dev-orchestrator"
echo "Onboard: /project-onboard or project-onboard . [--deep|--fast]"
echo "Cold start: /resume-project or resume-project ."
echo "Daytime runs: one visible run-supervisor watches durable run-controller"
echo "Run controller: run-controller start/watch/status (survives Claude exit)"
echo "Long lanes: lane-ctl + lane-bg user-systemd backend (never foreground Bash)"
echo "Control plane: lane-ctl start/status/events/tail/retry/cancel/verify/accept"
echo "Manual lane recovery: lane-supervisor (Grok remains the code writer)"
echo "Pools: provider default 5/max 10; verification default 2/max 10"
echo "Warm lanes: lane-session resumes run-scoped Grok conversations"
echo "Night shift: night-shift-all (Codex Sol xhigh review; Grok-only repair worktrees)"
echo "Beginner: docs/BEGINNER.md · RU: docs/BEGINNER.ru.md"
echo "Docs: $DEST/docs/ (ONBOARD-SCENARIOS, LANE-EXEC, ROUTING, LANGUAGE)"
