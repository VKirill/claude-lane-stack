#!/bin/sh
# UserPromptSubmit: SkillRanker if present, else shared Jev catalog (write-skills.json).
# Missing helper is a no-op so the session still runs.
for sr in \
  "${HOME}/.agents/bin/sr" \
  "${CLAUDE_PLUGIN_ROOT}/skillranker/sr"
do
  if [ -n "$sr" ] && [ -x "$sr" ]; then
    exec "$sr" hook claude
  fi
done
if command -v sr >/dev/null 2>&1; then
  exec sr hook claude
fi
hint="${CLAUDE_PLUGIN_ROOT}/hooks/skill_hint.py"
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  hint="$(dirname "$0")/skill_hint.py"
fi
if [ -f "$hint" ]; then
  exec python3 "$hint"
fi
exit 0
