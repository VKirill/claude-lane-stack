import { existsSync, statSync } from "node:fs"
import { resolve } from "node:path"

const GIT_RESTORE = /\bgit\s+(?:checkout|restore|reset|switch)\b/i
const ALLOWED_SKILLS = new Set(["ui-ux-pro-max"])
const ALLOWED_MCP = new Set(["gitnexus", "agentmemory"])
const MCP_NAME = /^mcp__([^_]+?)__/i

function toolPath(args: unknown): string {
  if (!args || typeof args !== "object" || Array.isArray(args)) return ""
  const a = args as Record<string, unknown>
  const path = [a.path, a.filePath, a.file].find((v) => typeof v === "string") as string | undefined
  return (path ?? "").trim()
}

function toolCommand(args: unknown): string {
  if (typeof args === "string") return args
  if (!args || typeof args !== "object" || Array.isArray(args)) return ""
  const a = args as Record<string, unknown>
  const cmd = [a.command, a.cmd].find((v) => typeof v === "string") as string | undefined
  return cmd ?? ""
}

function toolArg(args: unknown, keys: string[]): string {
  if (!args || typeof args !== "object" || Array.isArray(args)) return ""
  const a = args as Record<string, unknown>
  for (const key of keys) {
    const value = a[key]
    if (typeof value === "string" && value.trim()) return value.trim()
  }
  return ""
}

export function guardTool(tool: string, args: unknown, cwd = process.cwd()): string {
  const name = tool.toLowerCase()
  if (name === "write" || name === "write_file" || name === "oc_write") {
    const path = toolPath(args)
    if (!path) return ""
    const abs = resolve(cwd, path)
    try {
      if (existsSync(abs) && statSync(abs).isFile()) {
        return (
          "[opencode-lane guard] write blocked: file exists. Use edit " +
          "(old_string/new_string). If the file shrank, emit LANE_REPORT " +
          "STATUS: partial — do not git checkout."
        )
      }
    } catch {
      return ""
    }
  }
  if ((name === "bash" || name === "shell") && GIT_RESTORE.test(toolCommand(args))) {
    return (
      "[opencode-lane guard] git checkout/restore/reset/switch blocked. " +
      "Emit LANE_REPORT STATUS: partial instead of restoring a truncated write."
    )
  }
  if (name === "skill" || name === "skills") {
    const skill = toolArg(args, ["name", "skill", "skillName"]).toLowerCase()
    if (!ALLOWED_SKILLS.has(skill)) {
      return (
        "[opencode-lane guard] skill blocked" +
        (skill ? `: ${skill}` : "") +
        ". Writer may load ui-ux-pro-max on UI tasks only."
      )
    }
  }
  const mcpServer =
    name === "mcp" || name === "callmcptool"
      ? toolArg(args, ["serverIdentifier", "server", "mcpServer"]).toLowerCase()
      : (name.match(MCP_NAME)?.[1] ?? "").toLowerCase()
  if (mcpServer && !ALLOWED_MCP.has(mcpServer)) {
    return (
      `[opencode-lane guard] MCP blocked: ${mcpServer}. ` +
      "Only gitnexus and agentmemory."
    )
  }
  return ""
}
