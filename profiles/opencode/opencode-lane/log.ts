import { appendFileSync, mkdirSync, renameSync, statSync } from "node:fs"
import { AsyncLocalStorage } from "node:async_hooks"
import { dirname } from "node:path"
import { homedir } from "node:os"

export type LaneLog = {
  mod: string
  ok: boolean
  ms?: number
  err?: string
  session?: string
  data?: Record<string, unknown>
}

let session = ""
const context = new AsyncLocalStorage<string>()
let nativeSink: ((row: Record<string, unknown>) => unknown) | undefined
let warned = false

export function withLaneSession<T>(id: string, work: () => T): T {
  return context.run(id, work)
}

export function setLaneLogSink(sink: (row: Record<string, unknown>) => unknown): void {
  nativeSink = sink
}

export function redactText(value: string): string {
  let text = value
  for (const [key, secret] of Object.entries(process.env)) {
    if (/key|token|secret|password|credential/i.test(key) && secret && secret.length >= 6) {
      text = text.split(secret).join("[REDACTED]")
    }
  }
  return text
    .replace(/(Bearer\s+)\S+/gi, "$1[REDACTED]")
    .replace(/((?:responseBody|requestBody|headers)["']?\s*[:=]\s*)"(?:\\.|[^"\\])*"/gi, '$1"[REDACTED]"')
    .replace(/((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|authorization|cookie|set-cookie)[\s"']*[:=][\s"']*)[^\s"'&,}]+/gi, "$1[REDACTED]")
    .replace(/(https?:\/\/)[^\s/@]+:[^\s/@]+@/gi, "$1[REDACTED]@")
    .replace(/(https?:\/\/[^\s?#"']+)\?[^\s"']+/gi, "$1?[REDACTED]")
}

export function sanitizeLog(value: unknown, depth = 0): unknown {
  if (depth > 6) return "[depth limit]"
  if (typeof value === "string") return redactText(value).slice(0, 4000)
  if (Array.isArray(value)) return value.slice(0, 40).map((item) => sanitizeLog(item, depth + 1))
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).slice(0, 60).map(([key, item]) => [
      key,
      /^(?:authorization|cookie|set-cookie|.*password.*|.*secret.*|.*api[_-]?key.*|access[_-]?token|refresh[_-]?token|responseBody|requestBody|headers)$/i.test(key)
        ? "[REDACTED]"
        : sanitizeLog(item, depth + 1),
    ]))
  }
  return value
}

export function setLaneSession(id: string): void {
  session = id
}

function taskId(): string {
  const path = (process.env.LANE_TASK_FILE || "").trim()
  if (!path) return ""
  return path.replace(/^.*\//, "").replace(/\.ya?ml$/i, "")
}

function src(): string {
  const raw = (process.env.LANE_LOG_SRC || "").trim()
  if (raw) return raw
  return "lane"
}

export function laneLogPath(): string {
  const prompt = (process.env.LANE_PROMPT_FILE || "").trim()
  if (prompt) return prompt.replace(/[^/]+$/, "opencode-lane.jsonl")
  return `${homedir()}/.config/opencode/opencode-lane.jsonl`
}

export function laneLog(event: LaneLog): void {
  const flag = (process.env.LANE_LOG ?? "1").trim().toLowerCase()
  if (flag === "0" || flag === "off" || flag === "false" || flag === "no") return
  try {
    const row: Record<string, unknown> = {
      t: new Date().toISOString(),
      src: src(),
      ...event,
    }
    const task = taskId()
    if (task && row.task == null) row.task = task
    const sid = event.session ?? context.getStore() ?? session
    if (sid && row.session == null) row.session = sid
    const path = laneLogPath()
    const fallback = `${homedir()}/.config/opencode/opencode-lane.jsonl`
    const clean = sanitizeLog({ ...row, pid: process.pid, log_origin: path }) as Record<string, unknown>
    if (nativeSink && (!event.ok || event.mod === "startup")) {
      try { void Promise.resolve(nativeSink(clean)).catch(() => {}) } catch { /* local journal remains available */ }
    }
    // Lane sandboxes mount .agents read-only, including the attempt directory.
    for (const destination of new Set([path, fallback])) {
      try {
        mkdirSync(dirname(destination), { recursive: true })
        // ponytail: one 5 MiB backup; use a log collector if longer retention is needed.
        try {
          if (statSync(destination).size >= 5 * 1024 * 1024) renameSync(destination, `${destination}.1`)
        } catch { /* missing log or another process already rotated it */ }
        appendFileSync(destination, `${JSON.stringify(clean)}\n`, { encoding: "utf8", mode: 0o600 })
        return
      } catch {
        /* Try the provider's writable state directory next. */
      }
    }
    if (!warned) {
      warned = true
      console.error("[opencode-lane] telemetry write failed: primary and fallback logs unavailable")
    }
  } catch {
    /* logging must never break the session */
  }
}
