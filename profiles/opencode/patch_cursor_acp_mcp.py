#!/usr/bin/env python3
"""Rewrite Cursor dispatcher tool `mcp` to OpenCode `mcp__server__tool` in cursor-acp."""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LANE_MCP_DISPATCH_V1"
NEEDLE = 'log5.warn("Model attempted to call \'mcp\' directly (not a valid tool name)"'
ALT_NEEDLE = 'log.warn("Model attempted to call \'mcp\' directly (not a valid tool name)"'

REWRITE_FN = r'''
function laneRewriteCursorMcpCall(args, allowedToolNames) {
  // LANE_MCP_DISPATCH_V1
  if (!args || typeof args !== "object" || Array.isArray(args)) return null;
  const servers = new Set(["gitnexus", "agentmemory"]);
  const skip = new Set(["name", "args", "arguments", "toolCallId", "providerIdentifier", "toolName", "serverIdentifier", "serverName", "tool", "smartModeApprovalOnly", "skipApproval"]);
  const token = (raw) => String(raw).replace(/[^a-zA-Z0-9]/g, "_");
  let server = "";
  for (const key of ["serverIdentifier", "providerIdentifier", "serverName"]) {
    if (typeof args[key] === "string" && args[key].trim()) {
      server = args[key].trim().toLowerCase();
      break;
    }
  }
  const named = typeof args.name === "string" ? args.name : "";
  if (!server && named) {
    const lower = named.toLowerCase();
    for (const item of servers) {
      if (lower === item || lower.startsWith(item + "-") || lower.startsWith(item + "_")) {
        server = item;
        break;
      }
    }
  }
  if (!servers.has(server)) return null;
  let tool = "";
  for (const key of ["toolName", "tool"]) {
    if (typeof args[key] === "string" && args[key].trim()) {
      tool = args[key].trim();
      break;
    }
  }
  if (!tool && named) {
    const lower = named.toLowerCase();
    for (const prefix of [server + "-", server + "_", server]) {
      if (lower.startsWith(prefix) && named.length > prefix.length) {
        tool = named.slice(prefix.length).replace(/^[-_]+/, "");
        break;
      }
    }
  }
  if (!tool) return null;
  const name = "mcp__" + token(server) + "__" + token(tool);
  if (allowedToolNames && allowedToolNames.size > 0 && !allowedToolNames.has(name)) return null;
  let inner = args.args && typeof args.args === "object" && !Array.isArray(args.args) ? args.args : null;
  if (!inner && args.arguments && typeof args.arguments === "object" && !Array.isArray(args.arguments)) inner = args.arguments;
  if (!inner) {
    inner = {};
    for (const [key, value] of Object.entries(args)) {
      if (!skip.has(key)) inner[key] = value;
    }
  }
  return { name, args: inner };
}
'''

NEW_BLOCK_LOG5 = '''  if (name.toLowerCase() === "mcp") {
    const rewritten = laneRewriteCursorMcpCall(args, allowedToolNames);
    if (rewritten) {
      const callId = event.call_id || event.tool_call_id || "call_unknown";
      log5.info("Rewrote Cursor mcp dispatcher to OpenCode MCP tool", { from: "mcp", to: rewritten.name });
      return {
        action: "intercept",
        toolCall: {
          id: callId,
          type: "function",
          function: {
            name: rewritten.name,
            arguments: toOpenAiArguments(rewritten.args)
          }
        }
      };
    }
    log5.warn("Model attempted to call 'mcp' directly (not a valid tool name)", {
      args,
      hint: "MCP tools must be called by their full name (e.g. mcp__engram__mem_save), not 'mcp'"
    });
    return {
      action: "passthrough",
      passthroughName: name
    };
  }'''

NEW_BLOCK_LOG = NEW_BLOCK_LOG5.replace("log5.", "log.")


def _insert_fn(text: str) -> str:
    if "function laneRewriteCursorMcpCall" in text:
        return text
    anchor = "function extractOpenAiToolCall"
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("extractOpenAiToolCall not found")
    return text[:idx] + REWRITE_FN.strip() + "\n" + text[idx:]


def _replace_block(text: str, needle: str, new_block: str) -> str:
    start = text.find(needle)
    if start < 0:
        return text
    brace = text.rfind("if (name.toLowerCase() === \"mcp\")", 0, start)
    if brace < 0:
        raise SystemExit("mcp if-block start not found")
    depth = 0
    i = text.find("{", brace)
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[:brace] + new_block + text[j + 1 :]
    raise SystemExit("mcp if-block end not found")


def patch_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if MARKER in text and "Rewrote Cursor mcp dispatcher" in text:
        return "already"
    if NEEDLE not in text and ALT_NEEDLE not in text:
        return "skip"
    text = _insert_fn(text)
    if NEEDLE in text:
        text = _replace_block(text, NEEDLE, NEW_BLOCK_LOG5)
    elif ALT_NEEDLE in text:
        text = _replace_block(text, ALT_NEEDLE, NEW_BLOCK_LOG)
    if MARKER not in text:
        raise SystemExit(f"patch failed to insert marker in {path}")
    path.write_text(text, encoding="utf-8")
    return "patched"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: patch_cursor_acp_mcp.py FILE...", file=sys.stderr)
        return 2
    for raw in sys.argv[1:]:
        path = Path(raw).expanduser()
        if not path.is_file():
            print(f"missing {path}")
            continue
        print(f"{patch_file(path)} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
