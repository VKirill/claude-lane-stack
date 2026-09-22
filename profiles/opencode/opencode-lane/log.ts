import { appendFileSync, mkdirSync } from "node:fs"
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
    const path = laneLogPath()
    mkdirSync(dirname(path), { recursive: true })
    const row: Record<string, unknown> = {
      t: new Date().toISOString(),
      src: src(),
      ...event,
    }
    const task = taskId()
    if (task && row.task == null) row.task = task
    const sid = event.session || session
    if (sid && row.session == null) row.session = sid
    appendFileSync(path, `${JSON.stringify(row)}\n`, "utf8")
  } catch {
    /* logging must never break the session */
  }
}
