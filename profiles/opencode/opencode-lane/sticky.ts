import { readFileSync } from "node:fs"

export const STICKY_MARK = "LANE CONTRACT (live)"

export type OcMessage = {
  info?: { role?: string; sessionID?: string; sessionId?: string }
  parts?: unknown[]
}

export function stickySourcePath(): string {
  return (process.env.LANE_TASK_FILE || process.env.LANE_PROMPT_FILE || "").trim()
}

export function formatStickyContract(raw: string, sourcePath: string): string {
  return (
    `${STICKY_MARK}\nThe complete current contract from ${sourcePath} is supplied below. Use it directly; open the file only if this copy is missing or uncertain. owns_paths / never_touch / acceptance in this contract win over chat.\n\n` +
    raw
  )
}

export function readStickyContract(): string {
  const path = stickySourcePath()
  if (!path) return ""
  try {
    return formatStickyContract(readFileSync(path, "utf8"), path)
  } catch {
    return ""
  }
}

export function ensureStickyMessages(messages: OcMessage[], block: string): void {
  if (!block) return
  for (const message of messages) {
    if (!message.parts) continue
    message.parts = message.parts.filter((part) => {
      const text = (part as { type?: string; text?: string })?.text
      return !text || !text.startsWith(STICKY_MARK)
    })
  }
  const kept = messages.filter((message) => (message.parts?.length ?? 0) > 0)
  messages.length = 0
  messages.push(...kept, {
    info: { role: "user" },
    parts: [{ type: "text", text: block, synthetic: true }],
  })
}

export function appendStickyNotes(base: string, notes: string[]): string {
  const extra = notes.filter(Boolean)
  if (!extra.length) return base
  if (!base) return `${STICKY_MARK}\n${extra.join("\n")}`
  return `${base}\n\n${extra.join("\n")}`
}

const DUMPED_TOOL_NAME =
  /"name"\s*:\s*"(?:bash|shell|read|edit|write|grep|glob|str_replace|Shell|Read|Write|Grep|Glob)"/i
const CURSOR_CHANNEL_DEAD =
  /инструменты Cursor|Cursor tools.{0,40}unavail|MCP-сервер(?:ы)? не подключен/i

export function lastAssistantText(messages: OcMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i]?.info?.role !== "assistant") continue
    return (messages[i].parts ?? [])
      .map((part) => (part as { text?: string })?.text || "")
      .join("\n")
  }
  return ""
}

export function dumpedToolNote(text: string): string {
  if (!text || (!DUMPED_TOOL_NAME.test(text) && !CURSOR_CHANNEL_DEAD.test(text))) return ""
  return (
    "[opencode-lane tools] JSON-in-chat is ignored. Call OpenCode " +
    "read/edit/write/bash/grep. Cursor/MCP ACP tools do not exist here. " +
    "If done or blocked, emit LANE_REPORT now."
  )
}
