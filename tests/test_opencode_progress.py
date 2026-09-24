import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenCodeProgressTests(unittest.TestCase):
    def test_shell_transport_ids_do_not_hide_repeated_command(self):
        script = r'''
import { recordTool } from "./profiles/opencode/opencode-lane/budget.ts"
process.env.LANE_LOG = "0"
const output = "same shell output"
const first = recordTool("shell-fingerprint", "shell", {
  command: "npm test", toolCallId: "tool-a", requestId: "request-a", conversationId: "conversation-a",
}, output)
const repeated = recordTool("shell-fingerprint", "shell", {
  command: "npm test", toolCallId: "tool-b", requestId: "request-b", conversationId: "conversation-b",
}, output)
const changed = recordTool("shell-fingerprint", "shell", {
  command: "npm test -- --changed", toolCallId: "tool-c", requestId: "request-c", conversationId: "conversation-c",
}, output)
if (first.n !== 1 || repeated.n !== 2 || changed.n !== 1) throw new Error(JSON.stringify({ first, repeated, changed }))
console.log("shell-fingerprint-ok")
'''
        result = subprocess.run(["bun", "-e", script], cwd=ROOT, env={**os.environ, "LANE_LOG": "0"}, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shell-fingerprint-ok", result.stdout)

    def test_jev_history_redacts_new_mcp_entries_without_truncation(self):
        script = r'''
import { recordTool, repeatHint } from "./profiles/opencode/opencode-lane/budget.ts"
process.env.LANE_OPENCODE_JEV = "1"
process.env.TYPESAFE_API_KEY = "fixture-key"
let requestBody = ""
globalThis.fetch = async (_url, request) => {
  requestBody = request.body
  return new Response(JSON.stringify({ answers: { kind: { choice: "unclear", confidence: 1 } } }))
}
const secret = "private-mcp-secret"
const bearer = "mcp-bearer-secret"
recordTool("redaction", "mcp__server__search", {
  arguments: { token: secret, headers: { authorization: `Authorization: Bearer ${bearer}` }, keep: "safe-mcp-value" },
}, JSON.stringify({ result: "safe-mcp-value", token: secret, authorization: `Bearer ${bearer}` }))
for (let i = 0; i < 3; i++) recordTool("redaction", "shell", { command: "printf evidence" }, `shell ${i}`)
await repeatHint(JSON.stringify({ task: "progress", token: secret }), "shell", "shell 2", 3, "redaction")
if (requestBody.includes(secret)) throw new Error("secret reached Jev")
if (requestBody.includes(bearer)) throw new Error("bearer reached Jev")
if (!requestBody.includes("safe-mcp-value")) throw new Error("safe evidence was lost")
if (!requestBody.includes("shell 0")) throw new Error("prior evidence was lost")
console.log("redaction-ok")
'''
        env = {**os.environ, "LANE_LOG": "0"}
        result = subprocess.run(["bun", "-e", script], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("redaction-ok", result.stdout)

    def test_all_tool_progress_is_session_scoped_and_preserves_output(self):
        script = r'''
import { OpenCodeLanePlugin } from "./profiles/opencode/opencode-lane/index.ts"

globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({}) })
const hooks = await OpenCodeLanePlugin()
const after = hooks["tool.execute.after"]
let callNumber = 0
const call = (tool, sessionID, args, output, metadata = {}) => after({ tool, sessionID, callID: `call-${++callNumber}`, args }, { output, metadata })

const globArgs = { pattern: "**/*.ts", offset: 0, limit: 20 }
const full = "glob result must survive unchanged"
const first = { output: full, metadata: {} }
await after({ tool: "glob", sessionID: "session-a", callID: "call-glob-1", args: globArgs }, first)
if (first.output !== full) throw new Error("glob output changed")
await call("glob", "session-a", globArgs, full)
await call("glob", "session-a", { ...globArgs, offset: 20 }, full)
await call("mcp__server__search", "session-a", {
  query: "needle", offset: 2, limit: 5, arguments: { includeDrafts: true, nested: { page: 3 } },
}, "MCP result")
await call("mcp__server__search", "session-a", {
  query: "needle", offset: 2, limit: 5, arguments: { includeDrafts: true, nested: { page: 3 } },
}, "MCP result")
await call("write_file", "session-a", { path: "out.txt", content: "new bytes" }, "write callback ok")
await call("edit_file", "session-a", { path: "out.txt", oldString: "missing", newString: "x" }, "tool failed", { exit: 1 })
for (let i = 0; i < 3; i++) {
  const bareWrite = { output: "write callback ok", metadata: {} }
  await after({ tool: "write", sessionID: "session-a", callID: `call-write-${i}`, args: { path: "out.txt" } }, bareWrite)
  if (i === 2 && !bareWrite.output.includes("do not git checkout")) throw new Error("write loop hint missing")
}
const sessionB = { output: full, metadata: {} }
await after({ tool: "glob", sessionID: "session-b", callID: "call-glob-b", args: globArgs }, sessionB)
if (sessionB.output !== full) throw new Error("session-b output changed")

await hooks.event({ event: { type: "message.part.updated", properties: { part: {
  id: "part-error", sessionID: "session-a", messageID: "message-a", callID: "call-error",
  type: "tool", tool: "patch", state: { status: "error", input: { path: "x" }, error: "patch failed" },
} } } })
const errorAfter = { output: "patch failed", metadata: { exit: 1 } }
await after({ tool: "patch", sessionID: "session-a", callID: "call-error", args: { path: "x" } }, errorAfter)
if (errorAfter.output !== "patch failed") throw new Error("error output changed")
'''
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "prompt.yaml"
            env = {**os.environ, "LANE_PROMPT_FILE": str(prompt), "LANE_LOG": "1"}
            result = subprocess.run(
                ["bun", "-e", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in prompt.with_name("opencode-lane.jsonl").read_text().splitlines()]

        progress = [row for row in rows if row.get("mod") == "progress"]
        glob = [row for row in progress if row.get("data", {}).get("tool") == "glob" and row.get("session") == "session-a"]
        self.assertEqual([row["data"]["evidence"] for row in glob], ["novel", "unchanged", "novel"])
        self.assertEqual(sum(row.get("session") == "session-b" and row.get("data", {}).get("tool") == "glob" for row in progress), 1)
        mcp = [row for row in progress if row.get("data", {}).get("tool") == "mcp__server__search"]
        self.assertEqual([row["data"]["evidence"] for row in mcp], ["novel", "unchanged"])
        write = next(row for row in progress if row.get("data", {}).get("tool") == "write_file")
        self.assertEqual(write["data"]["edit_proof"], "callback_success_only")
        self.assertFalse(write["data"]["bytes_changed_proven"])
        failed = [row for row in progress if row.get("data", {}).get("tool") == "patch"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["ok"], False)
        self.assertNotIn("glob result must survive unchanged", "\n".join(json.dumps(row) for row in rows))


if __name__ == "__main__":
    unittest.main()
