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

UNAME_S="$(uname -s 2>/dev/null || echo unknown)"
IS_DARWIN=0
[[ "$UNAME_S" == "Darwin" ]] && IS_DARWIN=1

install_hint() {
  # $1: missing command name
  if [[ "$IS_DARWIN" == 1 ]]; then
    case "$1" in
      flock) echo "brew install flock" ;;
      node) echo "brew install node" ;;
      git) echo "xcode-select --install, or: brew install git" ;;
      rsync) echo "brew install rsync" ;;
      python3) echo "brew install python3" ;;
      *) echo "brew install $1" ;;
    esac
  else
    case "$1" in
      flock) echo "apt-get install util-linux (or your distro's util-linux package)" ;;
      node) echo "your distro's nodejs package, or https://nodejs.org" ;;
      *) echo "your distro's package manager" ;;
    esac
  fi
}

for command in flock git python3 rsync node; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "error: missing required command: $command (install: $(install_hint "$command"))" >&2
    exit 1
  }
done
python3 -c 'import jsonschema, yaml' >/dev/null 2>&1 || {
  if [[ "$IS_DARWIN" == 1 ]]; then
    PY_HINT="pip3 install --break-system-packages pyyaml jsonschema (or: brew install python-yaml, then pip3 install --break-system-packages jsonschema)"
  else
    PY_HINT="pip3 install --break-system-packages pyyaml jsonschema"
  fi
  echo "error: missing Python modules: PyYAML and jsonschema (install: $PY_HINT)" >&2
  exit 1
}
if [[ "$IS_DARWIN" == 1 ]] && [[ -x /usr/bin/python3 ]]; then
  /usr/bin/python3 -c 'import jsonschema, yaml' >/dev/null 2>&1 || {
    echo "warning: /usr/bin/python3 is missing PyYAML/jsonschema; hooks launched under a" >&2
    echo "  clean PATH (e.g. by Claude Code) may pick it up instead of Homebrew's python3." >&2
    echo "  Fix: /usr/bin/python3 -m pip install --break-system-packages pyyaml jsonschema" >&2
  }
fi
if [[ "$IS_DARWIN" == 1 ]] && [[ ! -x /usr/bin/sandbox-exec ]]; then
  echo "warning: /usr/bin/sandbox-exec (Seatbelt) not found; writer lane sandboxing" >&2
  echo "  falls back per LANE_SANDBOX_BACKEND. This ships with macOS; if it is" >&2
  echo "  missing something on this system is unusual — check Xcode Command Line Tools." >&2
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "warning: Claude Code is not installed; install it before starting dev-orchestrator" >&2
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "warning: uv is not installed; winnow will pass tool results through" >&2
  echo "  install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
fi
# Sidecar reads ~/.winnow/env; Claude settings.json is not in that process.
python3 - <<'PY'
from pathlib import Path
dest = Path.home() / ".winnow" / "env"
if dest.exists():
    raise SystemExit
key = ""
root = Path.home() / "secrets"
for name in ("typesafe.env", "jev.env"):
    path = root / name
    if not path.is_file():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        k, _, v = stripped.partition("=")
        if k.strip() in ("TYPESAFE_API_KEY", "JEV_API_KEY"):
            key = v.strip().strip('"').strip("'")
            break
    if key:
        break
if key:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"TYPESAFE_API_KEY={key}\n", encoding="utf-8")
    dest.chmod(0o600)
PY
# SkillRanker advice. Do not clobber a config the user already edited.
python3 - <<'PY'
from pathlib import Path
path = Path.home() / ".config" / "sr" / "config.toml"
if not path.exists():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[network]\nenabled = true\n\n[hook]\nmode = \"advisory\"\n", encoding="utf-8")
PY
if ! command -v sr >/dev/null 2>&1 && [[ ! -x "${HOME}/.agents/bin/sr" ]]; then
  echo "warning: sr is not installed; skill suggestions stay quiet until ~/.agents/bin/sr exists" >&2
fi
# OpenCode → Cursor subscription models. Skip when this home has no OpenCode config
# (install.sh tests) or the CLIs are missing.
if [[ -f "$HOME/.config/opencode/opencode.json" ]] \
  && command -v opencode >/dev/null 2>&1 \
  && command -v cursor-agent >/dev/null 2>&1 \
  && command -v npm >/dev/null 2>&1; then
  if ! command -v open-cursor >/dev/null 2>&1; then
    npm install -g @rama_nigg/open-cursor || echo "warning: npm install open-cursor failed" >&2
  fi
  if command -v open-cursor >/dev/null 2>&1; then
    open-cursor install || echo "warning: open-cursor install failed; Cursor models stay unavailable in OpenCode" >&2
  fi
fi
if [[ -f "$HOME/.config/opencode/plugin/cursor-acp.js" ]]; then
  python3 "$STACK_ROOT/profiles/opencode/patch_cursor_acp_mcp.py" \
    "$HOME/.config/opencode/plugin/cursor-acp.js" \
    || echo "warning: cursor-acp mcp remap patch failed" >&2
fi
if [[ -f "$HOME/.config/opencode/opencode.json" && -f "$STACK_ROOT/profiles/opencode/opencode-lane.ts" ]]; then
  mkdir -p "$HOME/.config/opencode/plugins/opencode-lane"
  install -m 0644 "$STACK_ROOT/profiles/opencode/opencode-lane.ts" "$HOME/.config/opencode/plugins/opencode-lane.ts"
  rm -f "$HOME/.config/opencode/plugins/lane-context.ts"
  cp -a "$STACK_ROOT/profiles/opencode/opencode-lane/"*.ts "$HOME/.config/opencode/plugins/opencode-lane/"
  mkdir -p "$HOME/.config/opencode/commands"
  install -m 0644 "$STACK_ROOT/profiles/opencode/commands/opencode-lane.md" \
    "$HOME/.config/opencode/commands/opencode-lane.md"
  python3 - <<'PY'
import json
from pathlib import Path
path = Path.home() / ".config" / "opencode" / "opencode.json"
data = json.loads(path.read_text(encoding="utf-8"))
plugins = data.get("plugin")
if not isinstance(plugins, list):
    plugins = []
new = "./plugins/opencode-lane.ts"
plugins = [item for item in plugins if item not in ("./plugins/lane-context.ts", new)]
plugins.append(new)
data["plugin"] = plugins
# Default compaction.auto is true and wipes tool history on large sessions.
compaction = data.get("compaction")
if not isinstance(compaction, dict):
    compaction = {}
compaction["auto"] = False
compaction["prune"] = False
data["compaction"] = compaction
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
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
PM_ONLY_SKILLS="orchestrator-lanes orchestrator-workflow info app-architect bulk-reader opencode-lane"
# User-kept copies (do not wipe on install; they override the plugin).
# Cloud (~/.claude/skills) owns google/ yandex/ seo-tools trees; do not rm them.
KEEP_CLAUDE_SKILLS="project-life google yandex seo-tools"
# User-owned skills in ~/.agents/skills: canonical on this host, never
# overwritten by install (repo copy is the distribution snapshot).
KEEP_AGENTS_SKILLS="project-life"
STALE_SKILLS="agent-todos project-memory ga4-data-api google-cloud-auth google-search-console yandex-metrica yandex-webmaster mutagen xmlstock seo-prompt-engineering-2026 seo-evidence-based-2026 seo-copywriting drmax-cvd drmax-lexadapt"

# bins
for executable in "$STACK_ROOT"/bin/*; do
  [[ -f "$executable" ]] || continue
  [[ "$executable" != *.py[co] ]] || continue
  install -m 0755 "$executable" "$DEST/bin/"
done

# board, docs, hooks, templates
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/board/" "$DEST/board/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/docs/" "$DEST/docs/"
if [[ -d "$STACK_ROOT/seo-system" ]]; then
  mkdir -p "$DEST/seo-system"
  rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/seo-system/" "$DEST/seo-system/"
fi
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/hooks/" "$DEST/hooks/"
if [[ -d "$STACK_ROOT/.git/hooks" && -f "$STACK_ROOT/githooks/gitnexus-reindex" ]]; then
  install -m 0755 "$STACK_ROOT/githooks/gitnexus-reindex" "$STACK_ROOT/.git/hooks/post-commit"
  install -m 0755 "$STACK_ROOT/githooks/gitnexus-reindex" "$STACK_ROOT/.git/hooks/post-merge"
fi
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/templates/" "$DEST/templates/"
rsync -a "${RSYNC_FILTERS[@]}" "$STACK_ROOT/schemas/" "$DEST/schemas/"
find "$DEST/hooks" "$DEST/board" -type f -name '*.py[co]' -delete
find "$DEST/hooks" "$DEST/board" -depth -type d -name __pycache__ -empty -delete
PLUGIN_LOCAL=0
if [[ "${LANE_INSTALL_LOCAL_MARKETPLACE:-0}" != "0" ]]; then
  PLUGIN_LOCAL=1
fi
MERGE_PLUGIN_ARGS=(--plugin-root "$STACK_ROOT")
if [[ "$PLUGIN_LOCAL" == 1 ]]; then
  MERGE_PLUGIN_ARGS+=(--plugin-local)
fi
python3 "$DEST/hooks/merge_claude_settings.py" \
  "$CLAUDE/settings.json" "$DEST/hooks/guard_shell.py" \
  --statusline "$DEST/bin/lane-statusline" \
  --session-mark "$DEST/hooks/lane_statusline_session.py" \
  "${MERGE_PLUGIN_ARGS[@]}"

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
names = ["orchestrator-lanes", "orchestrator-workflow", "info", "app-architect", "bulk-reader", "opencode-lane"]
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
MARKETPLACE_GITHUB="VKirill/claude-lane-stack"
mkdir -p "$CLAUDE/plugins/marketplaces" "$CLAUDE/agents" "$CLAUDE/commands" "$CLAUDE/skills"
if [[ "$PLUGIN_LOCAL" == 1 ]]; then
  # A GitHub clone already at this path is not the checkout. Replace it.
  if [[ -e "$MARKETPLACE_LINK" && ! -L "$MARKETPLACE_LINK" ]]; then
    rm -rf "$MARKETPLACE_LINK"
  fi
  ln -sfn "$STACK_ROOT" "$MARKETPLACE_LINK"
  MARKETPLACE_ADD="$MARKETPLACE_LINK"
else
  if [[ -L "$MARKETPLACE_LINK" ]]; then
    rm -f "$MARKETPLACE_LINK"
  fi
  MARKETPLACE_ADD="$MARKETPLACE_GITHUB"
fi
if [[ -d "$PLUGIN_ROOT/agents" ]]; then
  for agent_file in "$PLUGIN_ROOT/agents/"*.md; do
    [[ -f "$agent_file" ]] || continue
    rm -f "$CLAUDE/agents/$(basename "$agent_file")"
  done
fi
# Brand aliases removed from the plugin; wipe host copies that still override it.
for stale_agent in \
  codex-implementer.md \
  codex-reviewer.md \
  codex-onboarder.md \
  codex-docs-maintainer.md \
  grok-implementer.md
do
  rm -f "$CLAUDE/agents/$stale_agent"
done
if [[ -d "$PLUGIN_ROOT/commands" ]]; then
  for command_file in "$PLUGIN_ROOT/commands/"*.md; do
    [[ -f "$command_file" ]] || continue
    rm -f "$CLAUDE/commands/$(basename "$command_file")"
  done
fi
if [[ "${LANE_INSTALL_CLAUDE_PLUGIN:-1}" != "0" ]] && command -v claude >/dev/null 2>&1; then
  # Do not force CLAUDE_CONFIG_DIR: claude's own default already resolves to
  # $CLAUDE ($HOME/.claude) for plugin state, while its top-level session
  # config lives at $HOME/.claude.json (outside that directory). Forcing
  # CLAUDE_CONFIG_DIR="$CLAUDE" here made claude look for a nonexistent
  # $CLAUDE/.claude.json and left known_marketplaces.json entries without
  # installLocation, breaking every later `claude plugin` command. Only an
  # env var the caller already exported should change this.
  CLAUDE_MARKETPLACES_DIR="${CLAUDE_CONFIG_DIR:-$CLAUDE}"
  python3 - "$CLAUDE_MARKETPLACES_DIR/plugins/known_marketplaces.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.is_file():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = None
    if isinstance(data, dict):
        entry = data.get("claude-lane-stack")
        if isinstance(entry, dict) and "installLocation" not in entry:
            del data["claude-lane-stack"]
            temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.replace(temporary, path)
PY
  if ! claude plugin marketplace add "$MARKETPLACE_ADD" --scope user; then
    echo "warning: claude plugin marketplace add failed; extraKnownMarketplaces is still set" >&2
  fi
  if [[ "$PLUGIN_LOCAL" != 1 ]]; then
    claude plugin marketplace update claude-lane-stack >/dev/null || true
  fi
  python3 "$DEST/hooks/merge_claude_settings.py" \
    "$CLAUDE/settings.json" "$DEST/hooks/guard_shell.py" \
    --statusline "$DEST/bin/lane-statusline" \
    --session-mark "$DEST/hooks/lane_statusline_session.py" \
    "${MERGE_PLUGIN_ARGS[@]}"
  if ! claude plugin install lane-stack@claude-lane-stack -y -s user; then
    echo "warning: claude plugin install lane-stack@claude-lane-stack failed; enable after next Claude launch" >&2
  fi
  # Compaction hook is inside lane-stack. Drop the standalone plugin if a
  # previous install left it, so /compact is not hooked twice.
  claude plugin uninstall fast-jev-compaction@fast-jev-compaction -y -s user >/dev/null 2>&1 || true
  claude plugin uninstall fast-jev-compaction@claude-lane-stack -y -s user >/dev/null 2>&1 || true
  claude plugin marketplace remove fast-jev-compaction --scope user >/dev/null 2>&1 || true
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
# macOS login shells are zsh by default; keep ~/.zshrc in sync too.
if [[ "${SHELL:-}" == */zsh || -f "$HOME/.zshrc" ]] && ! grep -q '\.agents/bin' "$HOME/.zshrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.agents/bin:$PATH"' >> "$HOME/.zshrc"
  echo " appended PATH to ~/.zshrc"
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

if [[ -f "$DEST/routing.profile.yaml" ]]; then
  python3 - "$DEST" <<'PY'
import sys
from pathlib import Path

dest = Path(sys.argv[1])
sys.path.insert(0, str(dest / "bin"))
from pipeline_stages import migrate_profile_stages

changed = migrate_profile_stages(dest / "routing.profile.yaml")
if changed:
    print(f"==> Host profile remapped: {', '.join(changed)}")
PY
fi

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
echo " Claude plugin: lane-stack@claude-lane-stack (GitHub autoUpdate; host ~/.agents still needs ./install.sh)"
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
