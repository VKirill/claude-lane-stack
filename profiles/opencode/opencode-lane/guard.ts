import { existsSync, statSync } from "node:fs"
import { join, resolve } from "node:path"

const GIT_RESTORE = new Set(["checkout", "restore", "reset", "switch"])
// The lane controller commits and merges; no lane agent does (the lane-writer agent file denies the same commands).
const GIT_SHIP = new Set(["commit", "push", "merge"])
const SHELL_WRAPPERS = new Set(["sudo", "command", "time", "nohup", "nice", "env"])
const SHELLS = new Set(["sh", "bash", "dash", "zsh", "ksh"])
const GIT_FLAG_WITH_VALUE = new Set(["-C", "-c", "--git-dir", "--work-tree", "--namespace"])
// Lane Pilot gives every writer writer-practices and karpathy-guidelines (its writer role profile); the guard
// refused them with «skill blocked» on OpenCode writers (2026-10-03).
const ALLOWED_SKILLS = new Set(["ui-ux-pro-max", "writer-practices", "karpathy-guidelines"])
const ALLOWED_MCP = new Set(["gitnexus", "agentmemory"])
const MCP_NAME = /^mcp__([^_]+?)__/i

function toolPath(args: unknown): string {
  if (!args || typeof args !== "object" || Array.isArray(args)) return ""
  const a = args as Record<string, unknown>
  const path = [a.path, a.filePath, a.file].find((v) => typeof v === "string") as string | undefined
  return (path ?? "").trim()
}

function commandSegments(command: string): string[] {
  const parts: string[] = []
  let current = ""
  let quote: "'" | '"' | null = null
  for (let i = 0; i < command.length; i++) {
    const ch = command[i]!
    if (quote) {
      current += ch
      if (ch === quote && command[i - 1] !== "\\") quote = null
      continue
    }
    if (ch === "'" || ch === '"') {
      quote = ch
      current += ch
      continue
    }
    const next = command[i + 1]
    if ((ch === "&" && next === "&") || (ch === "|" && next === "|")) {
      parts.push(current)
      current = ""
      i++
      continue
    }
    if (ch === "|" || ch === ";" || ch === "\n") {
      parts.push(current)
      current = ""
      continue
    }
    current += ch
  }
  parts.push(current)
  return parts
}

function commandWords(segment: string): string[] {
  const words: string[] = []
  let current = ""
  let quote: "'" | '"' | null = null
  for (let i = 0; i < segment.length; i++) {
    const ch = segment[i]!
    if (quote) {
      if (ch === quote) quote = null
      else current += ch
      continue
    }
    if (ch === "'" || ch === '"') {
      quote = ch
      continue
    }
    if (/\s/.test(ch)) {
      if (current) words.push(current)
      current = ""
      continue
    }
    current += ch
  }
  if (current) words.push(current)
  return words
}

function basename(word: string): string {
  const slash = Math.max(word.lastIndexOf("/"), word.lastIndexOf("\\"))
  return slash >= 0 ? word.slice(slash + 1) : word
}

function skipWrappers(words: string[]): number {
  let i = 0
  while (i < words.length) {
    const word = words[i]!
    if (word === "env") {
      i++
      while (i < words.length && words[i]!.includes("=") && !words[i]!.startsWith("-")) i++
      continue
    }
    if (word.includes("=") && !word.startsWith("-") && !word.startsWith("/")) {
      i++
      continue
    }
    if (SHELL_WRAPPERS.has(word)) {
      i++
      while (i < words.length && words[i]!.startsWith("-")) i++
      continue
    }
    break
  }
  return i
}

function gitSubcommand(words: string[], index: number): string {
  while (index < words.length) {
    const word = words[index]!
    if (!word.startsWith("-")) return word
    index += GIT_FLAG_WITH_VALUE.has(word) ? 2 : 1
  }
  return ""
}

function shellScript(words: string[], index: number): string | null {
  while (index < words.length) {
    const word = words[index]!
    if (word === "-c" || /^-[a-zA-Z]*c[a-zA-Z]*$/.test(word)) return words[index + 1] ?? null
    if (!word.startsWith("-")) return null
    index++
  }
  return null
}

// Quoted text is data. `git commit` is blocked only when git is the program being run.
function gitVerb(command: string): string | null {
  for (const segment of commandSegments(command)) {
    const verb = gitVerbInWords(commandWords(segment))
    if (verb) return verb
  }
  return null
}

function gitVerbInWords(words: string[]): string | null {
  const index = skipWrappers(words)
  const program = basename(words[index] ?? "")
  if (program === "git") return gitSubcommand(words, index + 1) || null
  if (SHELLS.has(program)) {
    const script = shellScript(words, index + 1)
    if (script) return gitVerbInWords(commandWords(script))
  }
  return null
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

export function projectHasSkill(cwd: string, name: string): boolean {
  let cur = cwd
  for (let i = 0; i < 8; i++) {
    if (existsSync(join(cur, ".opencode", "skills", name, "SKILL.md"))) return true
    if (existsSync(join(cur, ".git"))) break
    const parent = resolve(cur, "..")
    if (parent === cur) break
    cur = parent
  }
  return false
}

// The plugin is installed for every OpenCode session on the machine. Only a lane process carries one of these: lane-session sets
// LANE_PROMPT_FILE/LANE_TASK_FILE, Lane Pilot sets LANE_PILOT_ROLE on the threads it starts. The owner's own sessions have none
// and get no writer guard or writer notes (skills were refused in a plain session, 2026-10-13).
export function laneMarked(env: NodeJS.ProcessEnv = process.env): boolean {
  return ["LANE_PROMPT_FILE", "LANE_TASK_FILE", "LANE_PILOT_ROLE"].some((key) => Boolean(env[key]?.trim()))
}

// skills: false leaves the skill allowlist to the agent file (lane-critic and lane-reviewer name their own skills there).
export function guardTool(tool: string, args: unknown, cwd = process.cwd(), opts: { skills?: boolean } = {}): string {
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
  if (name === "bash" || name === "shell") {
    const verb = gitVerb(toolCommand(args))
    if (verb && GIT_RESTORE.has(verb)) {
      return (
        "[opencode-lane guard] git checkout/restore/reset/switch blocked. " +
        "Emit LANE_REPORT STATUS: partial instead of restoring a truncated write."
      )
    }
    if (verb && GIT_SHIP.has(verb)) {
      return "[opencode-lane guard] git commit/push/merge blocked: the controller commits and merges. Emit LANE_REPORT instead."
    }
  }
  if ((name === "skill" || name === "skills") && opts.skills !== false) {
    const skill = toolArg(args, ["name", "skill", "skillName", "id"]).toLowerCase()
    const allowed = ALLOWED_SKILLS.has(skill) || projectHasSkill(cwd, skill)
    if (!allowed) {
      return (
        "[opencode-lane guard] skill blocked" +
        (skill ? `: ${skill}` : "") +
        ". Writer may load writer-practices, karpathy-guidelines, ui-ux-pro-max on UI tasks, or a skill bound on this session."
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

// A Lane Pilot thread (agent lane-pilot) also gets metamcp (its writer role profile grants gitnexus + metamcp) and BB's per-session
// proxy servers `bb_opencode2_<hash>`, which carry the BB tools it needs (lane_pilot_*, env-catalog, relay).
const PILOT_MCP = new Set([...ALLOWED_MCP, "metamcp"])
const PILOT_MCP_PREFIX = "bb_opencode2_"

// OpenCode v2 names an MCP tool `<server>_<tool>` (v1: mcp__<server>__<tool>); `servers` are the connected MCP server names.
export function guardMcpV2(tool: string, servers: readonly string[], agent = ""): string {
  const name = tool.toLowerCase()
  const server = [...servers]
    .map((item) => item.toLowerCase())
    .sort((a, b) => b.length - a.length)
    .find((item) => name.startsWith(`${item}_`))
  if (!server || ALLOWED_MCP.has(server)) return ""
  if (agent === "lane-pilot" && (PILOT_MCP.has(server) || server.startsWith(PILOT_MCP_PREFIX))) return ""
  return `[opencode-lane guard] MCP blocked: ${server}. ` + (agent === "lane-pilot" ? "Only gitnexus, agentmemory, metamcp and BB's own tools." : "Only gitnexus and agentmemory.")
}
