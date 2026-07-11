# Troubleshooting — codex

Symptom-indexed. Find what you see, follow diagnosis, apply fix.

---

## `codex app-server` connection refused

**Symptoms**
- Client process can't reach the app-server socket
- `codex app-server` logs "listening on …" but client gets ECONNREFUSED

**Diagnose**
```bash
# 1. Confirm app-server is actually running and on which socket
ps -ef | grep 'codex app-server'

# 2. Confirm CLI version supports app-server (0.130+)
codex --version

# 3. Confirm client points to the same socket path
echo $CODEX_APP_SERVER_SOCKET  # or whatever the client uses
```

**Common causes**
- Version mismatch: app-server requires 0.130+ on both sides
- Stale socket file from a previous run (`/tmp/codex-*.sock`)
- Permissions on the socket path (other user owns it)

**Fix**
- `codex update` to ensure 0.130+
- Remove stale socket file, restart app-server
- Run client and app-server as the same user, or relax socket permissions

---

## Sandbox blocks a legitimate operation

**Symptoms**
- `codex` fails an obvious operation with "blocked by sandbox" / "outside workspace"
- Editor reports "read-only file system" for something it should be allowed to touch

**Diagnose**
1. Confirm current sandbox: `/status` in TUI, or check `codex` startup line
2. Inspect `.codex/config.toml` for `sandbox_mode` override
3. Use `--add-dir <path>` to extend writable paths

**Common causes**
- `sandbox_mode = "read-only"` from a profile is winning over your CLI flag (CLI overrides config, but profile flags propagate)
- File is outside `cwd` and not in `--add-dir`
- Symlink crosses the boundary

**Fix**
- For one-off: `codex -s workspace-write --add-dir /tmp/build`
- For repeated: add the path to the project's profile `[profiles.build]` `extra_workspace_dirs` (if supported), or use a wider `cwd`
- For symlinks: resolve to real path first

See `references/permissions.md` and `references/recommended-defaults.md`.

---

## Approval prompts appear in CI

**Symptoms**
- `codex exec` hangs in CI waiting for input
- Job times out

**Cause**
- `approval_policy` is `untrusted`, `on-request`, or `on-failure` — all prompt humans
- `--full-auto` is `on-request` and still prompts in some scenarios

**Fix**
```bash
codex exec "..." -a never -s workspace-write
# or pin a CI-specific profile:
codex exec "..." -p ci
```

The `[profiles.ci]` block should set `approval_policy = "never"`. See `references/recommended-defaults.md`.

---

## Model not found

**Symptoms**
- `codex` errors with "model X not found" or "no access to model X"

**Common causes**
- Account doesn't have access to the model (`gpt-5-codex` requires Codex CLI access, separate from API key)
- Typo in model name in config
- Mixed auth: using `OPENAI_API_KEY` for a ChatGPT-subscription-only model (or vice versa)

**Fix**
```bash
# Verify auth mode
codex --version
codex logout && codex login   # re-auth via ChatGPT for subscription models

# Or set api key path explicitly
unset OPENAI_API_KEY     # forces ChatGPT auth
# or
export OPENAI_API_KEY=... # forces API auth (limits which models you can use)
```

---

## MCP server stalls handshake

**Symptoms**
- `codex` startup hangs on "connecting to MCP server <name>"
- `/mcp` shows server status "error"

**Diagnose**
```bash
# 1. Run server manually with MCP stdio
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | <command>

# 2. Check command resolves in subprocess PATH
which <command>

# 3. Bump timeout temporarily
# In config.toml under the server block, add timeout = 60000
```

**Common causes**
- `npx` / `uvx` cold install on first run exceeds default timeout
- PATH issue — command not visible to spawned subprocess
- Server crashes on missing env var

**Fix**
- Use absolute paths in `command`
- Add `env` block with required vars: `env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }`
- Pre-install via `npx -y <pkg>` once outside Codex to warm cache
- See `references/recommended-defaults.md` for canonical MCP block

---

## `codex update` fails

**Symptoms**
- `codex update` exits non-zero
- Newer release exists but local version stays old

**Diagnose**
```bash
codex --version
# Compare to https://github.com/openai/codex/releases

# If npm path:
npm i -g @openai/codex@latest

# If brew path:
brew upgrade --cask codex

# If GitHub release binary:
# Manually download the new tarball and replace the binary
```

**Common causes**
- Mixed install paths (npm + brew + binary all coexist; `which codex` shows surprise location)
- Permission issue on install dir
- Network egress blocks GitHub release download

**Fix**
- Pick one install path; remove the others
- See `references/installation.md` for clean install paths

---

## "Codex" ambiguity (deprecated model vs CLI)

**Symptoms**
- User asks about "Codex API" or "code-davinci-002"
- Error: "model not found" when trying old endpoints

**Cause**
- The 2021–2023 Codex completion model (`code-davinci-002`) is **discontinued**
- The 2026 "Codex" is OpenAI's agentic CLI, fundamentally different

**Fix**
- Confirm with user which one they mean
- If old model: explain it's discontinued; redirect to `openai-sdk` (GPT-5 family) or this skill (modern Codex CLI)
- If new CLI: this skill is correct

---

## More symptoms?

Capture: `codex --version`, `codex --debug` output during repro, contents of `~/.codex/config.toml` and `.codex/config.toml` (redacted), platform (`uname -a`). File at <https://github.com/openai/codex/issues>.
