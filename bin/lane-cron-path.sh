# Cron-safe PATH for lane writers. Cron has no user profile;
# `codex` is ~/.local/bin/codex, not /usr/bin.
# shellcheck disable=SC2148
export PATH="${HOME}/.agents/bin:${HOME}/.local/bin:${HOME}/.npm-global/bin:${HOME}/.kimi-code/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
