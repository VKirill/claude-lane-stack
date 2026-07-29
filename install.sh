#!/usr/bin/env bash
# Install Claude Lane Stack into ~/.agents + Claude agents/skills
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.agents"
CLAUDE="${HOME}/.claude"
CODEX="${CODEX_HOME:-${HOME}/.codex}"
AGY="${HOME}/.gemini/config"
APPLY_PROJECT=""

usage() {
  echo "Usage: ./install.sh [--apply-project /path/to/project]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply-project)
      [[ $# -ge 2 ]] || { echo "error: --apply-project requires a path" >&2; exit 2; }
      APPLY_PROJECT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

for command in flock git python3 rsync node; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "error: missing required command: $command" >&2
    exit 1
  }
done
python3 -c 'import jsonschema, yaml' >/dev/null 2>&1 || {
  echo "error: missing Python modules: PyYAML and jsonschema" >&2
  exit 1
}
if ! command -v claude >/dev/null 2>&1; then
  echo "warning: Claude Code is not installed; install it before starting dev-orchestrator" >&2
fi
if [[ -f "$CLAUDE/settings.json" ]]; then
  python3 "$STACK_ROOT/hooks/merge_claude_settings.py" --check "$CLAUDE/settings.json"
fi

RSYNC_FILTERS=(--exclude "__pycache__/" --exclude "*.py[co]")

echo "==> Claude Lane Stack install"
echo " from: $STACK_ROOT"
echo " to: $DEST"

mkdir -p "$DEST"/{bin,board,docs,hooks,templates,skills,schemas,agents,agy/instructions,grok/instructions,codex/instructions}
mkdir -p "$CLAUDE"/{agents,skills,commands}
mkdir -p "$CODEX"

# bins
for executable in "$STACK_ROOT"/bin/*; do
  [[ -f "$executable" ]] || continue
  [[ "$executable" != *.py[co] ]] || continue
  install -m 0755 "$executable" "$DEST/bin/"
done

# board, docs, hooks, templates
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/board/" "$DEST/board/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/docs/" "$DEST/docs/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/hooks/" "$DEST/hooks/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/templates/" "$DEST/templates/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/schemas/" "$DEST/schemas/"
find "$DEST/hooks" "$DEST/board" -type f -name '*.py[co]' -delete
find "$DEST/hooks" "$DEST/board" -depth -type d -name __pycache__ -empty -delete
python3 "$DEST/hooks/merge_claude_settings.py" \
  "$CLAUDE/settings.json" "$DEST/hooks/guard_shell.py"

# skills
for d in "$STACK_ROOT"/skills/*/; do
  name="$(basename "$d")"
  rsync -a "${RSYNC_FILTERS[@]}" "$d" "$DEST/skills/$name/"
  claude_skill="$CLAUDE/skills/$name"
  if [[ -L "$claude_skill" ]]; then
    ln -sfn "$DEST/skills/$name" "$claude_skill"
  elif [[ -d "$claude_skill" ]]; then
    # Preserve an existing user-managed directory, but keep stack-owned files
    # current. Plain `ln -sfn` would create a misleading nested self-link.
    rsync -a "${RSYNC_FILTERS[@]}" "$d" "$claude_skill/"
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
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/ "$DEST/agents/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/agy/ "$DEST/agy/instructions/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/grok/ "$DEST/grok/instructions/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/codex/instructions/ "$DEST/codex/instructions/"
if [[ -d "$DEST/codex/instructions/instructions" ]]; then
  rm -rf -- "$DEST/codex/instructions/instructions"
fi

# AGY writer profile: explicit tool allowlist excludes all subagent tools.
mkdir -p "$AGY/agents/agy-writer"
install -m 0644 "$STACK_ROOT/agents/agy/agent.md" "$AGY/agents/agy-writer/agent.md"

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
if [[ -n "$APPLY_PROJECT" ]]; then
  echo "==> Applying agents-doctor profile to: $APPLY_PROJECT"
  agents-doctor --apply "$APPLY_PROJECT"
else
  echo "==> Project profile unchanged"
  echo " Run explicitly: agents-doctor --apply /path/to/project"
fi

echo ""
echo "Done. Start PM:"
echo " export PATH=\"\$HOME/.agents/bin:\$PATH\""
echo " claude --agent dev-orchestrator"
echo "Onboard: /project-onboard or project-onboard . [--deep|--fast]"
echo "Cold start: /resume-project or resume-project ."
echo "Daytime runs: one visible run-supervisor watches durable run-controller"
echo "Run controller: run-controller start/watch/status (survives Claude exit)"
echo "Long lanes: lane-ctl + lane-bg user-systemd backend (never foreground Bash)"
echo "Control plane: lane-ctl start/status/events/tail/retry/cancel/verify/accept"
echo "Manual lane recovery: lane-supervisor (Kimi, Qwen, AGY, or Grok writer)"
echo "Pools: provider default 5/max 10; verification default 2/max 10"
echo "Warm lanes: lane-session resumes run-scoped Kimi, Qwen, AGY, or Grok conversations"
echo "Night shift: night-shift-all (Codex Sol xhigh review; selectable Kimi/Qwen/AGY/Grok repair with typed Sol fallback)"
echo "Beginner: docs/BEGINNER.md · RU: docs/BEGINNER.ru.md"
echo "Docs: $DEST/docs/ (ONBOARD-SCENARIOS, LANE-EXEC, ROUTING, LANGUAGE)"
