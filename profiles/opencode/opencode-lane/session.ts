import { createHash } from "node:crypto"
import { STICKY_MARK, type OcMessage } from "./sticky.ts"

export function pickSessionID(input: unknown): string {
  if (!input || typeof input !== "object") return ""
  const rec = input as Record<string, unknown>
  for (const key of ["sessionID", "sessionId"]) {
    const value = rec[key]
    if (typeof value === "string" && value) return value
  }
  const session = rec.session
  if (session && typeof session === "object") {
    const id = (session as { id?: unknown }).id
    if (typeof id === "string" && id) return id
  }
  return ""
}

function firstUserText(messages: OcMessage[]): string {
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const item = part as { type?: string; text?: string; synthetic?: boolean }
      if (item.synthetic || (item.type && item.type !== "text") || !item.text) continue
      if (item.text.startsWith(STICKY_MARK)) continue
      return item.text
    }
  }
  return ""
}

export function sessionKey(
  input: unknown,
  messages: OcMessage[] = [],
  prompts: Map<string, string> = new Map(),
): string {
  const fromInput = pickSessionID(input)
  if (fromInput) return fromInput
  for (const message of messages) {
    const info = message.info as { sessionID?: string; sessionId?: string } | undefined
    const id = info?.sessionID || info?.sessionId
    if (id) return id
  }
  const text = firstUserText(messages)
  if (text) {
    const needle = text.slice(0, 120)
    for (const [sid, prompt] of prompts) {
      if (sid && prompt && (text.includes(prompt.slice(0, 120)) || prompt.includes(needle))) return sid
    }
    return `msg:${createHash("sha256").update(text.slice(0, 400)).digest("hex").slice(0, 16)}`
  }
  return "unknown"
}
