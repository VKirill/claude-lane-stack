import { existsSync, statSync } from "node:fs"
import { resolve } from "node:path"

const GIT_RESTORE = /\bgit\s+(?:checkout|restore|reset|switch)\b/i

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
  return ""
}
