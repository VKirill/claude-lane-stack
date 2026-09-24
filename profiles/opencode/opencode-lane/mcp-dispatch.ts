const LANE_MCP_SERVERS = new Set(["gitnexus", "agentmemory"])
const DISPATCH_KEYS = new Set([
  "name",
  "args",
  "arguments",
  "toolCallId",
  "providerIdentifier",
  "toolName",
  "serverIdentifier",
  "serverName",
  "tool",
  "smartModeApprovalOnly",
  "skipApproval",
])

function token(raw: string): string {
  return raw.replace(/[^a-zA-Z0-9]/g, "_")
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function pickServer(args: Record<string, unknown>): string {
  for (const key of ["serverIdentifier", "providerIdentifier", "serverName"] as const) {
    const value = args[key]
    if (typeof value === "string" && value.trim()) return value.trim()
  }
  const named = args.name
  if (typeof named === "string") {
    const lower = named.toLowerCase()
    for (const server of LANE_MCP_SERVERS) {
      if (lower === server || lower.startsWith(`${server}-`) || lower.startsWith(`${server}_`)) {
        return server
      }
    }
  }
  return ""
}

function pickTool(args: Record<string, unknown>, server: string): string {
  for (const key of ["toolName", "tool"] as const) {
    const value = args[key]
    if (typeof value === "string" && value.trim()) return value.trim()
  }
  const named = args.name
  if (typeof named === "string") {
    const prefixes = [`${server}-`, `${server}_`, `${server}`]
    for (const prefix of prefixes) {
      if (named.toLowerCase().startsWith(prefix) && named.length > prefix.length) {
        return named.slice(prefix.length).replace(/^[-_]+/, "")
      }
    }
  }
  return ""
}

function pickInner(args: Record<string, unknown>): Record<string, unknown> {
  const nested = asRecord(args.args) || asRecord(args.arguments)
  if (nested) return nested
  const inner: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(args)) {
    if (!DISPATCH_KEYS.has(key)) inner[key] = value
  }
  return inner
}

export function rewriteCursorMcpCall(
  args: unknown,
  allowedNames: Iterable<string> = [],
): { name: string; args: Record<string, unknown> } | null {
  const record = asRecord(args)
  if (!record) return null
  const server = pickServer(record).toLowerCase()
  if (!LANE_MCP_SERVERS.has(server)) return null
  const tool = pickTool(record, server)
  if (!tool) return null
  const name = `mcp__${token(server)}__${token(tool)}`
  const allowed = new Set(allowedNames)
  if (allowed.size > 0 && !allowed.has(name)) return null
  return { name, args: pickInner(record) }
}
