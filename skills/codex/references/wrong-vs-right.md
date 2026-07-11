# Wrong vs Right — codex

Side-by-side contrast for common Codex CLI footguns. Both sides under 15 lines so the point lands.

---

### Sandbox: `danger-full-access` vs `workspace-write`

**❌ Wrong — DFA mode on host machine for daily work:**

```bash
codex --dangerously-bypass-approvals-and-sandbox
# or in config.toml:
sandbox_mode = "danger-full-access"
approval_policy = "never"
```

This disables the Rust-enforced filesystem and network boundary on the host. A prompt-injection or a misled model can now `rm -rf $HOME`, exfil SSH keys, or modify your shell rc.

**✅ Right — `workspace-write` + `on-request`, scoped to `cwd`:**

```bash
codex --full-auto
# expands to: -s workspace-write -a on-request
```

Or, when you genuinely need DFA (large refactors, system-level work): do it in a **devcontainer** or VM where the blast radius is contained.

**Why it matters:** Codex's sandbox is its strongest differentiator (Rust-enforced, not just polite warnings). Disabling it on the host throws away the safety budget. The Anthropic and OpenAI agents have both demonstrated capability to chain shell commands that delete files — sandbox is the cheap insurance.

---

### Approval policy: `never` in CI vs `on-request` in CI

**❌ Wrong — interactive approval policy in CI:**

```yaml
# .github/workflows/review.yml
- run: codex exec "review the diff" -a on-request -s workspace-write
```

The CI job hangs forever waiting for a human to answer the prompt. Eventually times out.

**✅ Right — `never` in CI; humans approve via PR review afterward:**

```yaml
- run: codex exec "review the diff" -p ci --json
```

With `[profiles.ci]` setting `approval_policy = "never"`.

**Why it matters:** `on-request` requires a tty + a human. CI is neither. The model picks `never` only when there's an external review (PR review) catching what the model can't approve. Don't combine `never` with `danger-full-access` outside a fully-disposable runner.

---

### Profile-per-task vs global tweaking

**❌ Wrong — `codex` with stacked inline flags every time:**

```bash
codex -m gpt-5-codex --model-reasoning-effort high -s workspace-write -a on-request --add-dir /tmp/build "refactor module"
# next time:
codex -m gpt-5.5 --model-reasoning-effort low -s read-only -a untrusted "quick review"
```

Long, error-prone, and the flag combo drifts across sessions.

**✅ Right — named profiles, switch with `-p`:**

```toml
# ~/.codex/config.toml
[profiles.refactor]
model = "gpt-5-codex"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[profiles.review]
model = "gpt-5.5"
model_reasoning_effort = "low"
sandbox_mode = "read-only"
approval_policy = "untrusted"
```

```bash
codex -p refactor "refactor module"
codex -p review "quick review"
```

**Why it matters:** Profiles encode intent ("I'm doing a refactor") not flags ("medium effort, write mode"). They live in `~/.codex/config.toml` and travel across repos. Auditable, version-controlled, and the flag set stays consistent.

---

### Secrets in config.toml: inline vs env interpolation

**❌ Wrong — inline secret in committed config:**

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" }
```

If `.codex/config.toml` is committed (it often is — profiles, sandbox config are useful in repo), the token leaks to the git history.

**✅ Right — `${ENV_VAR}` interpolation:**

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }
```

Token comes from the shell/secret-store; config.toml is safe to commit.

**Why it matters:** Codex resolves `${VAR}` at startup from the process env. Combine with direnv or 1Password CLI for ergonomic local dev. Committed secrets are forever — even after rotation, history retains them.
