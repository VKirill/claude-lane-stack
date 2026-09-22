import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenCodeTelemetryTests(unittest.TestCase):
    def test_events_errors_retries_tools_and_permissions(self):
        script = r'''
import { createTelemetry } from "./profiles/opencode/opencode-lane/telemetry.ts"

const first = createTelemetry()
const running = {
  type: "message.part.updated",
  properties: {
    part: {
      id: "part-a", sessionID: "session-a", messageID: "message-a", type: "tool",
      callID: "call-a", tool: "write_file",
      state: { status: "running", input: { path: "x.txt", content: "secret" }, time: { start: 10 } },
    },
  },
}
await first.event({ event: { type: "session.error", properties: { sessionID: "session-a", error: { name: "APIError", data: { message: "provider failed", statusCode: 502, responseBody: "PRIVATE RESPONSE BODY", responseHeaders: { authorization: "PRIVATE HEADER" } } } } } })
await first.event({ event: { type: "session.status", properties: { sessionID: "session-a", status: { type: "retry", attempt: 2, message: "retrying", next: 50 } } } })
await first.event({ event: { type: "message.updated", properties: { info: { id: "message-a", sessionID: "session-a", role: "assistant", error: { name: "APIError", data: { message: "assistant failed", responseBody: "PRIVATE ASSISTANT BODY" } } } } } })
await first.event({ event: running })
await first.event({ event: running })
await first.event({ event: { type: "message.part.updated", properties: { part: { ...running.properties.part, state: { status: "completed", input: running.properties.part.state.input, output: "full output must not be logged", time: { start: 10, end: 25 } } } } } })
await first.event({ event: { type: "message.part.updated", properties: { part: { ...running.properties.part, state: { status: "completed", input: running.properties.part.state.input, output: "full output must not be logged", time: { start: 10, end: 25 } } } } } })
await first.event({ event: { type: "permission.asked", properties: { id: "perm-a", sessionID: "session-a", messageID: "message-a", callID: "call-a", type: "edit" } } })
await first.event({ event: { type: "permission.updated", properties: { id: "perm-b", sessionID: "session-a", permission: "edit", tool: { messageID: "message-a", callID: "call-a" } } } })
await first.event({ event: { type: "permission.replied", properties: { sessionID: "session-a", permissionID: "perm-a", response: "allow" } } })
await first.event({ event: { type: "session.compacted", properties: { sessionID: "session-a" } } })
await first.event({ event: { type: "message.part.updated", properties: { part: { ...running.properties.part, sessionID: "session-b", state: { status: "error", input: {}, error: "tool failed", time: { start: 1, end: 2 } } } } } })

// A second plugin instance has its own bounded dedupe state.
await createTelemetry().event({ event: running })
'''
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "prompt.yaml"
            env = {**os.environ, "LANE_PROMPT_FILE": str(prompt), "LANE_LOG": "1"}
            result = subprocess.run(
                ["node", "--experimental-strip-types", "--input-type=module", "-e", script],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in (Path(directory) / "opencode-lane.jsonl").read_text().splitlines()]

        telemetry = [row for row in rows if row.get("mod") == "telemetry"]
        self.assertEqual(sum(row.get("data", {}).get("event") == "message.part.updated" and row.get("data", {}).get("status") == "running" for row in telemetry), 2)
        self.assertEqual(sum(row.get("data", {}).get("event") == "message.part.updated" and row.get("data", {}).get("status") == "completed" for row in telemetry), 1)
        self.assertTrue(any(row.get("data", {}).get("event") == "session.retry" and row.get("session") == "session-a" for row in telemetry))
        self.assertTrue(any(row.get("data", {}).get("event") == "permission.asked" for row in telemetry))
        self.assertTrue(any(row.get("data", {}).get("event") == "permission.updated" for row in telemetry))
        self.assertTrue(any(row.get("data", {}).get("event") == "permission.replied" for row in telemetry))
        self.assertTrue(any(row.get("data", {}).get("event") == "session.compacted" for row in telemetry))
        failed = [row for row in telemetry if row.get("data", {}).get("status") == "error"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["session"], "session-b")
        self.assertNotIn("full output must not be logged", "\n".join(json.dumps(row) for row in rows))
        self.assertNotIn("PRIVATE RESPONSE BODY", "\n".join(json.dumps(row) for row in rows))
        self.assertNotIn("PRIVATE ASSISTANT BODY", "\n".join(json.dumps(row) for row in rows))
        self.assertNotIn("PRIVATE HEADER", "\n".join(json.dumps(row) for row in rows))
        self.assertNotIn("reasoning", "\n".join(json.dumps(row) for row in rows))
        self.assertIn("output_sha256", next(row for row in telemetry if row.get("data", {}).get("status") == "completed")["data"])


if __name__ == "__main__":
    unittest.main()
