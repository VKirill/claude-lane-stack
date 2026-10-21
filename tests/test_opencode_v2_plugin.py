"""opencode-lane under OpenCode v2: definition shape, lane-agent gate, guards, sticky contract, v2 telemetry, agent and install layout.

The plugin runs in node here (type stripping) against a recording fake of the v2 plugin context; no bun and no OpenCode needed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENCODE = ROOT / "profiles" / "opencode"
INDEX = OPENCODE / "opencode-lane" / "index.ts"

HARNESS = r"""
import { mkdtempSync, writeFileSync } from "node:fs"
import { join } from "node:path"
import { tmpdir } from "node:os"
import plugin from "%(index)s"
import * as lane from "%(index)s"

globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({}), text: async () => "" })
const dir = mkdtempSync(join(tmpdir(), "oc-v2-"))
writeFileSync(join(dir, "existing.txt"), "x")
const agents = { "sess-lane": "lane-writer", "sess-plain": "build" }
const rules = {
  "lane-writer": [
    { action: "*", resource: "*", effect: "allow" },
    { action: "shell", resource: "git commit*", effect: "deny" },
    { action: "webfetch", resource: "*", effect: "deny" },
  ],
}
const hooks = {}
const hook = (domain) => ({ hook: async (name, cb) => { hooks[`${domain}.${name}`] = cb } })
const ctx = {
  location: { directory: dir },
  event: { subscribe: () => (async function* () {})() },
  session: { ...hook("session"), get: async ({ sessionID }) => ({ id: sessionID, agent: agents[sessionID], location: { directory: dir } }) },
  tool: hook("tool"),
  permission: hook("permission"),
  // agent.get and mcp.list answer { location, data }, as measured on 2.1.2
  agent: { get: async ({ agentID }) => ({ location: {}, data: { id: agentID, permissions: rules[agentID] ?? [] } }) },
  mcp: { list: async () => ({ data: [{ name: "gitnexus" }, { name: "agentmemory" }, { name: "metamcp" }] }) },
  storage: { get: async () => undefined, set: async () => {} },
}
const cleanup = await plugin.setup(ctx)
const refuses = async (fn) => { try { await fn(); return false } catch (err) { return String(err.message || err) } }
const out = {}
%(body)s
if (typeof cleanup === "function") cleanup()
console.log(JSON.stringify(out))
"""


def run_harness(body: str, extra_env: dict[str, str] | None = None) -> dict:
    script = HARNESS % {"index": INDEX.resolve().as_uri(), "body": body}
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "LANE_LOG": "0", "LANE_OPENCODE_JEV": "0", "HOME": home, **(extra_env or {})}
        for key in ("LANE_PROMPT_FILE", "LANE_TASK_FILE", "LANE_PILOT_ROLE"):
            env.pop(key, None)
        result = subprocess.run(
            ["node", "--experimental-strip-types", "--input-type=module", "-e", script],
            cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=60,
        )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])


class DefinitionTests(unittest.TestCase):
    def test_default_export_is_a_v2_definition_with_a_v1_server(self) -> None:
        out = run_harness(
            "out.id = plugin.id; out.setup = typeof plugin.setup; out.server = typeof plugin.server; "
            "out.hooks = Object.keys(hooks).sort(); out.cleanup = typeof cleanup",
        )
        self.assertEqual(out["id"], "opencode-lane")
        self.assertEqual((out["setup"], out["server"], out["cleanup"]), ("function", "function", "function"))
        self.assertEqual(
            out["hooks"],
            ["permission.evaluate", "session.context", "session.prompt", "tool.execute.after", "tool.execute.before"],
        )

    def test_setup_ignores_the_v1_plugin_input(self) -> None:
        # v1 calls setup() with its PluginInput too; it must neither throw nor register anything.
        out = run_harness(
            "out.v1 = typeof (await plugin.setup({ client: {}, project: {}, directory: dir })); "
            "out.hooks = Object.keys(hooks).length",
        )
        self.assertEqual(out["v1"], "function")
        self.assertEqual(out["hooks"], 5)  # only the real v2 setup of the harness registered hooks

    def test_wrapper_stays_a_default_reexport_and_no_module_is_a_plugin_folder_entry(self) -> None:
        wrapper = (OPENCODE / "opencode-lane.ts").read_text(encoding="utf-8")
        self.assertIn('export { default } from "./opencode-lane/index.ts"', wrapper)
        v2 = (OPENCODE / "opencode-lane" / "v2.ts").read_text(encoding="utf-8")
        self.assertNotIn("process.env.LANE_", v2)  # the shared service's env is not the thread's


class GateAndGuardTests(unittest.TestCase):
    def test_tool_guard_acts_only_for_lane_agents(self) -> None:
        out = run_harness(r"""
const before = hooks["tool.execute.before"]
const call = (agent, tool, input) => before({ tool, sessionID: agent === "lane-writer" ? "sess-lane" : "sess-plain", agent, input })
const existing = join(dir, "existing.txt")
out.laneWriteExisting = await refuses(() => call("lane-writer", "write", { path: existing, content: "y" }))
out.laneWriteNew = await refuses(() => call("lane-writer", "write", { path: join(dir, "new.txt"), content: "y" }))
out.laneRestore = await refuses(() => call("lane-writer", "shell", { command: "git checkout -- a.ts" }))
out.laneCommit = await refuses(() => call("lane-writer", "shell", { command: "git commit -m x" }))
out.laneEcho = await refuses(() => call("lane-writer", "shell", { command: "echo ok" }))
out.laneMcpBlocked = await refuses(() => call("lane-writer", "metamcp_search", {}))
out.laneMcpOk = await refuses(() => call("lane-writer", "gitnexus_impact", { target: "x" }))
out.laneSkillBlocked = await refuses(() => call("lane-writer", "skill", { id: "orchestrator-lanes" }))
out.laneSkillOk = await refuses(() => call("lane-writer", "skill", { id: "writer-practices" }))
out.plainWrite = await refuses(() => call("build", "write", { path: existing, content: "y" }))
out.plainCommit = await refuses(() => call("build", "shell", { command: "git commit -m x" }))
out.plainMcp = await refuses(() => call("build", "metamcp_search", {}))
""")
        self.assertIn("file exists", out["laneWriteExisting"])
        self.assertIs(out["laneWriteNew"], False)
        self.assertIn("checkout/restore/reset/switch blocked", out["laneRestore"])
        self.assertIn("git commit/push/merge blocked", out["laneCommit"])
        self.assertIs(out["laneEcho"], False)
        self.assertIn("MCP blocked: metamcp", out["laneMcpBlocked"])
        self.assertIs(out["laneMcpOk"], False)
        self.assertIn("skill blocked", out["laneSkillBlocked"])
        self.assertIs(out["laneSkillOk"], False)
        self.assertEqual((out["plainWrite"], out["plainCommit"], out["plainMcp"]), (False, False, False))

    def test_permission_hook_denies_hub_shell_and_agent_rules_only_for_lane_agents(self) -> None:
        deny = [
            "$BB_CLI plugin config lane-pilot",
            "/opt/homebrew/bin/bb plugin remove lane-pilot",
            "ssh ubuntu@10.8.1",
            "ssh ubuntu@0x0a080001 id",
            "ssh 168296449",
            "ssh 012.010.0.1",
            "scp x.txt ubuntu@ovh-main:/tmp",
            "echo c2g= | base64 -d | sh",
        ]
        allow = ["bb env-catalog get X --raw", "bb lane-pilot status", "git push", "bb plugin rpc call lane-pilot x", "ssh git@github.com"]
        out = run_harness(
            f"""
const evaluate = hooks["permission.evaluate"]
const ask = async (agent, action, command, effect = "allow") => {{
  const event = {{ sessionID: "s", agent, action, resources: [command], effect }}
  await evaluate(event)
  return event
}}
out.deny = []
for (const command of {json.dumps(deny)}) out.deny.push((await ask("lane-writer", "shell", command)).effect)
out.allow = []
for (const command of {json.dumps(allow)}) out.allow.push((await ask("lane-writer", "shell", command)).effect)
out.plainHub = (await ask("build", "shell", "ssh ubuntu@10.8.1")).effect
out.noAgent = (await ask(undefined, "shell", "ssh ubuntu@10.8.1")).effect
out.askBecomesDeny = (await ask("lane-writer", "shell", "ssh ubuntu@10.8.1", "ask")).effect
const ruleDenied = await ask("lane-writer", "shell", "git commit -m x")
out.ruleDenied = [ruleDenied.effect, ruleDenied.message]
out.ruleDeniedWebfetch = (await ask("lane-writer", "webfetch", "https://example.com")).effect
out.otherRulesKeep = (await ask("lane-writer", "edit", "a.ts")).effect
""",
        )
        self.assertEqual(set(out["deny"]), {"deny"})
        self.assertEqual(set(out["allow"]), {"allow"})
        self.assertEqual((out["plainHub"], out["noAgent"], out["askBecomesDeny"]), ("allow", "allow", "deny"))
        self.assertEqual(out["ruleDenied"][0], "deny")
        self.assertIn("denied for lane-writer", out["ruleDenied"][1])
        self.assertEqual((out["ruleDeniedWebfetch"], out["otherRulesKeep"]), ("deny", "allow"))


class StickyAndAfterTests(unittest.TestCase):
    def test_contract_from_the_prompt_is_pinned_last_for_lane_agents_only(self) -> None:
        out = run_harness(r"""
const prompt = hooks["session.prompt"]
const context = hooks["session.context"]
const task = "id: T-1\nacceptance:\n  - it works\n"
await prompt({ sessionID: "sess-lane", prompt: { text: "do it\n--- RAW TASK YAML (verbatim) ---\n" + task } })
await prompt({ sessionID: "sess-plain", prompt: { text: "do it\n--- RAW TASK YAML (verbatim) ---\n" + task } })
const history = () => [
  { role: "user", content: [{ type: "text", text: lane.STICKY_MARK + "\nold block" }] },
  { role: "user", content: [{ type: "text", text: "first" }] },
  { role: "assistant", content: [{ type: "text", text: 'try {"name":"write","args":{}}' }] },
]
const laneMessages = history()
await context({ sessionID: "sess-lane", agent: "lane-writer", messages: laneMessages })
const plainMessages = history()
await context({ sessionID: "sess-plain", agent: "build", messages: plainMessages })
out.laneRoles = laneMessages.map((m) => m.role)
out.laneLast = laneMessages.at(-1).content[0].text
out.laneOldGone = laneMessages.every((m) => !m.content.some((p) => p.text === lane.STICKY_MARK + "\nold block"))
out.plain = JSON.stringify(plainMessages) === JSON.stringify(history())
""")
        self.assertEqual(out["laneRoles"], ["user", "assistant", "user"])
        self.assertTrue(out["laneLast"].startswith("LANE CONTRACT (live)"))
        self.assertIn("id: T-1", out["laneLast"])
        self.assertIn("[opencode-lane tools] JSON-in-chat is ignored", out["laneLast"])
        self.assertTrue(out["laneOldGone"])
        self.assertTrue(out["plain"])

    def test_after_hook_adds_budget_notes_for_lane_agents_and_leaves_plain_results(self) -> None:
        out = run_harness(r"""
const after = hooks["tool.execute.after"]
const run = async (agent, session, n) => {
  let result
  for (let i = 0; i < n; i++) {
    result = { content: [{ type: "text", text: "same file body" }], metadata: {} }
    await after({ tool: "read", sessionID: session, agent, id: `${session}-${i}`, input: { path: "a.ts" }, status: "completed", result })
  }
  return result.content.map((p) => p.text).join("|")
}
out.lane = await run("lane-writer", "sess-lane", 3)
out.plain = await run("build", "sess-plain", 3)
const failed = { content: "boom", metadata: { exit: 1 } }
await after({ tool: "shell", sessionID: "sess-lane", agent: "lane-writer", id: "e1", input: { command: "false" }, status: "error", error: { message: "boom" } })
out.errorSurvived = true
""")
        self.assertIn("[opencode-lane budget] Identical read content", out["lane"])
        self.assertEqual(out["plain"], "same file body")
        self.assertTrue(out["errorSurvived"])


class TelemetryV2Tests(unittest.TestCase):
    def test_v2_events_are_logged_like_the_v1_ones(self) -> None:
        script = r"""
import { createTelemetry } from "./profiles/opencode/opencode-lane/telemetry.ts"
const t = createTelemetry()
const ev = (type, data) => t.event({ event: { type, data: { sessionID: "s1", ...data } } })
await ev("session.tool.input.started", { id: "c1", name: "shell" })
await ev("session.tool.called", { id: "c1", input: { command: "ls" } })
await ev("session.tool.success", { id: "c1", content: [{ type: "text", text: "secret output" }] })
await ev("session.retry.scheduled", { attempt: 2, at: Date.now() + 500, error: { message: "rate limit" } })
await ev("session.compaction.started", { reason: "auto" })
await ev("session.compaction.ended", { reason: "auto" })
await ev("session.execution.failed", { error: { type: "unknown", message: "kaput" } })
"""
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "prompt.yaml"
            env = {**os.environ, "LANE_PROMPT_FILE": str(prompt), "LANE_LOG": "1"}
            result = subprocess.run(
                ["node", "--experimental-strip-types", "--input-type=module", "-e", script],
                cwd=ROOT, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in (Path(directory) / "opencode-lane.jsonl").read_text().splitlines()]
        events = [row["data"]["event"] for row in rows if row["mod"] == "telemetry"]
        self.assertEqual(
            events,
            ["tool.running", "tool.completed", "session.retry", "session.compaction.started", "session.compacted", "session.error"],
        )
        completed = next(row for row in rows if row.get("data", {}).get("event") == "tool.completed")
        self.assertEqual(completed["data"]["tool"], "shell")
        self.assertNotIn("secret output", json.dumps(rows))


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(re.match(r"---\n(.*?)\n---\n", text, re.S).group(1))


class AgentFileTests(unittest.TestCase):
    def test_lane_agents_are_v2_files_that_load_as_primary_capable(self) -> None:
        for name in ("lane-writer", "lane-critic", "lane-reviewer"):
            meta = frontmatter(OPENCODE / "agents" / f"{name}.md")
            self.assertEqual(meta["mode"], "all", name)  # a writer thread picks it as its primary agent
            self.assertNotIn("permission", meta, name)  # v2 prefers the legacy key over `permissions`, so never both
            self.assertNotIn("temperature", meta, name)
            self.assertRegex(meta["color"], r"^#[0-9a-f]{6}$")
            for rule in meta["permissions"]:
                self.assertEqual(set(rule), {"action", "resource", "effect"}, name)
                self.assertIn(rule["effect"], {"allow", "deny", "ask"}, name)
        writer = frontmatter(OPENCODE / "agents" / "lane-writer.md")["permissions"]
        self.assertIn({"action": "shell", "resource": "git commit*", "effect": "deny"}, writer)
        self.assertIn({"action": "subagent", "resource": "*", "effect": "deny"}, writer)
        for name in ("lane-critic", "lane-reviewer"):
            rules = frontmatter(OPENCODE / "agents" / f"{name}.md")["permissions"]
            self.assertIn({"action": "edit", "resource": "*", "effect": "deny"}, rules)
            self.assertIn({"action": "shell", "resource": "*", "effect": "deny"}, rules)

    def test_command_uses_only_documented_v2_keys(self) -> None:
        meta = frontmatter(OPENCODE / "commands" / "opencode-lane.md")
        self.assertEqual(set(meta), {"description"})


if __name__ == "__main__":
    unittest.main()
