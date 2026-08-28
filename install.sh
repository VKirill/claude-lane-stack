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

mkdir -p "$DEST"/{bin,board,docs,hooks,templates,skills,pm-skills,schemas,agents,agy/instructions,grok/instructions,codex/instructions}
mkdir -p "$CLAUDE"/{agents,skills,commands}
mkdir -p "$CODEX"

# Writer CLIs (Grok/Codex/Kimi/Qwen) scan ~/.agents/skills. Keep the PM
# playbook out of that catalog. Claude Code still gets a ~/.claude/skills link.
PM_ONLY_SKILLS="orchestrator-lanes orchestrator-workflow info app-architect"
# User-kept copies (do not wipe on install; they override the plugin).
KEEP_CLAUDE_SKILLS="project-life"
# User-owned skills in ~/.agents/skills: canonical on this host, never
# overwritten by install (repo copy is the distribution snapshot).
KEEP_AGENTS_SKILLS="project-life"
STALE_SKILLS="agent-todos project-memory"

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
  "$CLAUDE/settings.json" "$DEST/hooks/guard_shell.py" \
  --statusline "$DEST/bin/lane-statusline" \
  --session-mark "$DEST/hooks/lane_statusline_session.py" \
  --plugin-root "$STACK_ROOT"

# skills — writers get ~/.agents/skills. Claude loads them from the plugin
# (namespaced). Do not link stack skills into ~/.claude/skills (Codex also
# scans that catalog; user copies override plugin agents too).
for d in "$STACK_ROOT"/skills/*/; do
  name="$(basename "$d")"
  if [[ " $PM_ONLY_SKILLS " == *" $name "* ]]; then
    dest_dir="$DEST/pm-skills/$name"
    rm -rf "$DEST/skills/$name"
    rsync -a "${RSYNC_FILTERS[@]}" "$d" "$dest_dir/"
  else
    dest_dir="$DEST/skills/$name"
    if [[ " $KEEP_AGENTS_SKILLS " == *" $name "* && -e "$dest_dir" ]]; then
      echo " keep user skill: $dest_dir"
    else
      rsync -a "${RSYNC_FILTERS[@]}" "$d" "$dest_dir/"
    fi
  fi
  if [[ " $KEEP_CLAUDE_SKILLS " != *" $name "* ]]; then
    rm -rf "$CLAUDE/skills/$name"
  fi
done
# Drop stale shared-catalog copies even if a name was removed from skills/
for name in $PM_ONLY_SKILLS $STALE_SKILLS; do
  rm -rf "$DEST/skills/$name"
  if [[ " $KEEP_CLAUDE_SKILLS " != *" $name "* ]]; then
    rm -rf "$CLAUDE/skills/$name"
  fi
done

python3 - "$HOME/.grok/config.toml" <<'PY'
"""Hide PM-only skills from Grok's shared skill catalog."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(0)
names = ["orchestrator-lanes", "orchestrator-workflow", "info", "app-architect"]
ignore_path = "~/.agents/pm-skills"
text = path.read_text(encoding="utf-8")
original = text
if "[skills]" not in text:
    text = text.rstrip() + "\n\n[skills]\nignore = [\"~/.claude/skills\", \"" + ignore_path + "\"]\ndisabled = " + str(names).replace("'", '"') + "\n"
else:
    if "disabled = []" in text:
        text = text.replace(
            "disabled = []",
            "disabled = [" + ", ".join(f'"{n}"' for n in names) + "]",
            1,
        )
    elif "disabled =" in text:
        for name in names:
            quoted = f'"{name}"'
            if quoted not in text:
                text = text.replace("disabled = [", "disabled = [" + quoted + ", ", 1)
    else:
        text = text.replace("[skills]", "[skills]\ndisabled = [" + ", ".join(f'"{n}"' for n in names) + "]", 1)
    if ignore_path not in text:
        if 'ignore = ["~/.claude/skills"]' in text:
            text = text.replace(
                'ignore = ["~/.claude/skills"]',
                'ignore = ["~/.claude/skills", "' + ignore_path + '"]',
                1,
            )
        elif "ignore = [" in text:
            text = text.replace("ignore = [", 'ignore = ["' + ignore_path + '", ', 1)
        else:
            text = text.replace("[skills]", '[skills]\nignore = ["' + ignore_path + '"]', 1)
if text != original:
    path.write_text(text, encoding="utf-8")
PY

# platform agents (-L: agents/claude is a compat symlink into the plugin)
rsync -aL "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/ "$DEST/agents/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/agy/ "$DEST/agy/instructions/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/grok/ "$DEST/grok/instructions/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT"/agents/codex/instructions/ "$DEST/codex/instructions/"
if [[ -d "$DEST/codex/instructions/instructions" ]]; then
  rm -rf -- "$DEST/codex/instructions/instructions"
fi

# AGY writer profile: explicit tool allowlist excludes all subagent tools.
mkdir -p "$AGY/agents/agy-writer"
install -m 0644 "$STACK_ROOT/agents/agy/agent.md" "$AGY/agents/agy-writer/agent.md"

# Claude plugin marketplace. User ~/.claude/agents copies override plugins.
PLUGIN_ROOT="$STACK_ROOT/plugins/lane-stack"
MARKETPLACE_LINK="$CLAUDE/plugins/marketplaces/claude-lane-stack"
mkdir -p "$CLAUDE/plugins/marketplaces" "$CLAUDE/agents" "$CLAUDE/commands" "$CLAUDE/skills"
if [[ -L "$MARKETPLACE_LINK" || ! -e "$MARKETPLACE_LINK" ]]; then
  ln -sfn "$STACK_ROOT" "$MARKETPLACE_LINK"
fi
if [[ -d "$PLUGIN_ROOT/agents" ]]; then
  for agent_file in "$PLUGIN_ROOT/agents/"*.md; do
    [[ -f "$agent_file" ]] || continue
    rm -f "$CLAUDE/agents/$(basename "$agent_file")"
  done
fi
if [[ -d "$PLUGIN_ROOT/commands" ]]; then
  for command_file in "$PLUGIN_ROOT/commands/"*.md; do
    [[ -f "$command_file" ]] || continue
    rm -f "$CLAUDE/commands/$(basename "$command_file")"
  done
fi
if [[ "${LANE_INSTALL_CLAUDE_PLUGIN:-1}" != "0" ]] && command -v claude >/dev/null 2>&1; then
  if ! CLAUDE_CONFIG_DIR="$CLAUDE" claude plugin marketplace add "$MARKETPLACE_LINK" --scope user; then
    echo "warning: claude plugin marketplace add failed; extraKnownMarketplaces is still set" >&2
  fi
  if ! CLAUDE_CONFIG_DIR="$CLAUDE" claude plugin install lane-stack@claude-lane-stack -y -s user; then
    echo "warning: claude plugin install lane-stack@claude-lane-stack failed; enable after next Claude launch" >&2
  fi
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
if [[ -f "$STACK_ROOT/profiles/codex/lane-writer.config.toml" ]]; then
  install -m 0644 \
    "$STACK_ROOT/profiles/codex/lane-writer.config.toml" \
    "$CODEX/lane-writer.config.toml"
fi
if [[ -d "$STACK_ROOT/profiles/opencode/agents" ]]; then
  mkdir -p "${HOME}/.config/opencode/agents"
  for f in "$STACK_ROOT/profiles/opencode/agents/"*.md; do
    [[ -f "$f" ]] || continue
    install -m 0644 "$f" "${HOME}/.config/opencode/agents/"
  done
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
echo " Claude plugin: lane-stack@claude-lane-stack (marketplace → ~/.claude/plugins/marketplaces/claude-lane-stack)"
echo " lane-pm   # or: claude --agent dev-orchestrator (boot may not auto-send)"
echo "Onboard: /project-onboard or project-onboard . [--deep|--fast]"
echo "Cold start: /resume-project or resume-project ."
echo "Daytime runs: one visible run-supervisor watches durable run-controller"
echo "Run controller: run-controller start/watch/status (survives Claude exit)"
echo "Long lanes: lane-ctl + lane-bg user-systemd backend (never foreground Bash)"
echo "Control plane: lane-ctl start/status/events/tail/retry/cancel/verify/accept"
echo "Manual lane recovery: lane-supervisor (Kimi, Qwen, AGY, or Grok writer)"
echo "Pools: provider default 5/max 10; verification default 2/max 10"
echo "Warm lanes: lane-session resumes run-scoped Kimi, Qwen, AGY, or Grok conversations"
echo "Night shift: night-shift-all (Codex Sol high review; selectable Kimi/Qwen/AGY/Grok repair with typed Sol fallback)"
echo "Beginner: docs/BEGINNER.md · RU: docs/BEGINNER.ru.md"
echo "Docs: $DEST/docs/ (ONBOARD-SCENARIOS, LANE-EXEC, ROUTING, LANGUAGE)"
