// OpenCode v2 request messages ({ role, content: [...] }) seen through the v1 helpers ({ info.role, parts }) that evidence.ts and
// sticky.ts were written for.
import { STICKY_MARK, type OcMessage } from "./sticky.ts"

export type V2Message = { role?: string; content?: unknown }

type Part = { type?: string; text?: string; id?: string; name?: string; input?: unknown; result?: { value?: unknown } }

function parts(message: V2Message): Part[] {
  return Array.isArray(message.content) ? (message.content as Part[]) : []
}

function valueText(value: unknown): string {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.map((item) => (typeof item?.text === "string" ? item.text : "")).join("")
  return value == null ? "" : JSON.stringify(value)
}

export function toOcMessages(messages: V2Message[]): OcMessage[] {
  const calls = new Map<string, Part>()
  for (const message of messages) for (const part of parts(message)) if (part.type === "tool-call" && part.id) calls.set(part.id, part)
  return messages.map((message) => ({
    info: { role: message.role === "tool" ? "assistant" : message.role },
    parts: parts(message).flatMap((part): unknown[] => {
      if (part.type === "text") return [{ type: "text", text: part.text ?? "" }]
      if (part.type !== "tool-result") return []
      return [{
        type: "tool",
        tool: part.name ?? "",
        state: { input: calls.get(part.id ?? "")?.input ?? {}, output: valueText(part.result?.value) },
      }]
    }),
  }))
}

export function lastAssistantTextV2(messages: V2Message[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role !== "assistant") continue
    return parts(messages[i]).map((part) => (part.type === "text" ? (part.text ?? "") : "")).join("\n")
  }
  return ""
}

/** Same as ensureStickyMessages for v2 messages: drops an earlier contract block and appends the current one as the last user message. */
export function ensureStickyContent(messages: V2Message[], block: string): void {
  if (!block) return
  const kept = messages.filter((message) => {
    const list = parts(message)
    if (!list.length) return true
    const rest = list.filter((part) => !(part.type === "text" && part.text?.startsWith(STICKY_MARK)))
    if (rest.length === list.length) return true
    if (!rest.length) return false
    message.content = rest
    return true
  })
  messages.length = 0
  messages.push(...kept, { role: "user", content: [{ type: "text", text: block }] })
}
