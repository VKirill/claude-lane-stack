import { createHash } from "node:crypto"
import { markToolStarted, observeToolProgress, recordTool } from "./budget.ts"
import { laneLog } from "./log.ts"

type EventInput = { event?: unknown }
type AnyRecord = Record<string, unknown>

const MAX_SEEN = 2048

function record(value: unknown): AnyRecord {
  return value && typeof value === "object" ? (value as AnyRecord) : {}
}

function text(value: unknown): string {
  if (typeof value === "string") return value
  if (value instanceof Error) return value.message || value.name || "OpenCode error"
  const item = record(value)
  const data = record(item.data)
  const name = typeof item.name === "string" ? item.name : ""
  const message = typeof item.message === "string"
    ? item.message
    : typeof data.message === "string"
      ? data.message
      : ""
  const status = typeof item.statusCode === "number"
    ? `status=${item.statusCode}`
    : typeof data.statusCode === "number"
      ? `status=${data.statusCode}`
      : ""
  return [name, message, status].filter(Boolean).join(": ") || "OpenCode error"
}

function stable(value: unknown): string {
  if (value === undefined) return "undefined"
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`
  if (!value || typeof value !== "object") return JSON.stringify(value)
  return `{${Object.keys(value as AnyRecord)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable((value as AnyRecord)[key])}`)
    .join(",")}}`
}

function digest(value: unknown): string {
  return createHash("sha256").update(stable(value)).digest("hex").slice(0, 16)
}

function lengthOf(value: unknown): number {
  if (typeof value === "string") return value.length
  if (value == null) return 0
  return stable(value).length
}

function sessionOf(value: AnyRecord): string {
  for (const key of ["sessionID", "sessionId"]) {
    if (typeof value[key] === "string") return value[key] as string
  }
  const info = record(value.info)
  if (typeof info.sessionID === "string") return info.sessionID
  if (typeof info.sessionId === "string") return info.sessionId
  const part = record(value.part)
  return typeof part.sessionID === "string" ? part.sessionID : ""
}

export function eventSessionID(value: unknown): string {
  const event = record(value)
  const props = record(event.properties)
  const session = sessionOf(props)
  if (session) return session
  const info = record(props.info)
  return typeof info.id === "string" ? info.id : ""
}

function duration(time: unknown): number | undefined {
  const item = record(time)
  if (typeof item.start !== "number" || typeof item.end !== "number") return undefined
  return Math.max(0, item.end - item.start)
}

function messageData(info: AnyRecord): AnyRecord {
  const data: AnyRecord = {
    message_id: typeof info.id === "string" ? info.id : "",
    role: typeof info.role === "string" ? info.role : "",
  }
  const elapsed = duration(info.time)
  if (elapsed !== undefined) data.duration_ms = elapsed
  return data
}

type ToolAfterInput = { tool: string; sessionID: string; callID?: string; args: unknown }
type ToolAfterOutput = { output: unknown; metadata?: { exit?: unknown } }

function failedExit(value: unknown): boolean {
  if (typeof value === "number") return value !== 0
  if (typeof value === "string") return value !== "" && value !== "0"
  return false
}

export type Telemetry = {
  event(input: EventInput): Promise<void>
  after(input: ToolAfterInput, output: ToolAfterOutput): Promise<{ n: number; deduped: boolean; skipped: boolean }>
}

export function createTelemetry(): Telemetry {
  const seen = new Map<string, true>()

  function once(key: string): boolean {
    if (seen.has(key)) return false
    seen.set(key, true)
    if (seen.size > MAX_SEEN) seen.delete(seen.keys().next().value as string)
    return true
  }

  function emit(
    session: string,
    ok: boolean,
    data: AnyRecord,
    err?: unknown,
  ): void {
    laneLog({
      mod: "telemetry",
      ok,
      session,
      ...(err === undefined ? {} : { err: text(err) }),
      data,
    })
  }

  // OpenCode v2 events: { type, data } with the session id inside data; they replace the v1 { type, properties } events below.
  const v2Tools = new Map<string, { name: string; input: unknown }>()

  function textOfContent(content: unknown): string {
    if (typeof content === "string") return content
    if (!Array.isArray(content)) return ""
    return content.map((part) => (typeof record(part).text === "string" ? (record(part).text as string) : "")).join("")
  }

  function eventV2(event: AnyRecord): void {
    const type = typeof event.type === "string" ? event.type : ""
    const data = record(event.data)
    const session = typeof data.sessionID === "string" ? data.sessionID : ""
    const id = typeof data.id === "string" ? data.id : ""

    if (type === "session.execution.failed" || type === "session.step.failed") {
      emit(session, false, { event: "session.error" }, data.error)
    } else if (type === "session.retry.scheduled") {
      emit(session, false, {
        event: "session.retry",
        attempt: data.attempt,
        next_ms: typeof data.at === "number" ? Math.max(0, data.at - Date.now()) : undefined,
      }, data.error)
    } else if (type === "session.execution.succeeded") {
      emit(session, true, { event: "session.idle" })
    } else if (type === "session.compaction.started") {
      emit(session, true, { event: "session.compaction.started", reason: data.reason })
    } else if (type === "session.compaction.ended") {
      emit(session, true, { event: "session.compacted", reason: data.reason })
    } else if (type === "session.compaction.failed") {
      emit(session, false, { event: "session.compaction.failed", reason: data.reason }, data.error)
    } else if (type === "session.tool.input.started") {
      v2Tools.set(`${session}|${id}`, { name: typeof data.name === "string" ? data.name : "", input: undefined })
      if (v2Tools.size > MAX_SEEN) v2Tools.delete(v2Tools.keys().next().value as string)
    } else if (type === "session.tool.called") {
      const known = v2Tools.get(`${session}|${id}`)
      v2Tools.set(`${session}|${id}`, { name: known?.name ?? "", input: data.input })
      markToolStarted(session)
      emit(session, true, {
        event: "tool.running",
        call_id: id,
        tool: known?.name ?? "",
        input_sha256: digest(data.input),
        input_chars: lengthOf(data.input),
      })
    } else if (type === "session.tool.success" || type === "session.tool.failed") {
      const known = v2Tools.get(`${session}|${id}`)
      v2Tools.delete(`${session}|${id}`)
      const failed = type === "session.tool.failed"
      const result = failed ? (record(data.error).message ?? data.error) : textOfContent(data.content)
      const tool = known?.name ?? ""
      const row: AnyRecord = {
        event: failed ? "tool.error" : "tool.completed",
        call_id: id,
        tool,
        input_sha256: digest(known?.input),
        input_chars: lengthOf(known?.input),
      }
      if (failed) row.error_chars = lengthOf(result)
      else {
        row.output_sha256 = digest(result)
        row.output_chars = lengthOf(result)
      }
      emit(session, !failed, row, failed ? result : undefined)
      const observed = observeToolProgress(session, tool, known?.input, result, failed ? "error" : "completed", "event", id)
      if (!observed.deduped) recordTool(session, tool, known?.input, result)
    } else if (type === "permission.asked" || type === "permission.replied") {
      emit(session, true, {
        event: type,
        permission_id: typeof data.id === "string" ? data.id : typeof data.requestID === "string" ? data.requestID : "",
        permission_type: typeof data.action === "string" ? data.action : "",
        response: typeof data.reply === "string" ? data.reply : typeof data.response === "string" ? data.response : undefined,
      })
    }
  }

  async function event(input: EventInput): Promise<void> {
    const event = record(input.event)
    if (event.properties === undefined && event.data !== undefined) return eventV2(event)
    const type = typeof event.type === "string" ? event.type : ""
    const props = record(event.properties)
    const session = eventSessionID(event)

    if (type === "session.error") {
      emit(session, false, { event: type }, props.error)
      return
    }

    if (type === "session.status") {
      const status = record(props.status)
      if (status.type !== "retry") return
      emit(session, false, {
        event: "session.retry",
        attempt: status.attempt,
        next_ms: typeof status.next === "number" ? status.next : undefined,
      }, status.message)
      return
    }

    if (type === "message.updated") {
      const info = record(props.info)
      if (info.role !== "assistant" || !info.error) return
      emit(sessionOf({ info }), false, { event: type, ...messageData(info) }, info.error)
      return
    }

    if (type === "message.part.updated") {
      const part = record(props.part)
      if (part.type !== "tool") return
      const state = record(part.state)
      const status = typeof state.status === "string" ? state.status : ""
      if (status !== "running" && status !== "completed" && status !== "error") return
      const sessionID = session || (typeof part.sessionID === "string" ? part.sessionID : "")
      const input = state.input
      const output = state.output
      const error = state.error
      const key = [
        sessionID,
        part.messageID,
        part.id,
        part.callID,
        status,
        digest(input),
        digest(status === "error" ? error : output),
        duration(state.time) ?? "",
      ].join("|")
      if (!once(key)) return
      if (status === "running") {
        markToolStarted(sessionID)
      }
      const data: AnyRecord = {
        event: type,
        message_id: typeof part.messageID === "string" ? part.messageID : "",
        part_id: typeof part.id === "string" ? part.id : "",
        call_id: typeof part.callID === "string" ? part.callID : "",
        tool: typeof part.tool === "string" ? part.tool : "",
        status,
        input_sha256: digest(input),
        input_chars: lengthOf(input),
      }
      if (status === "completed") {
        data.output_sha256 = digest(output)
        data.output_chars = lengthOf(output)
      } else if (status === "error") {
        data.error_chars = lengthOf(error)
      }
      const elapsed = duration(state.time)
      if (elapsed !== undefined) data.duration_ms = elapsed
      emit(sessionID, status !== "error", data, status === "error" ? error : undefined)
      if (status !== "running") {
        const observed = observeToolProgress(
          sessionID,
          typeof part.tool === "string" ? part.tool : "",
          input,
          status === "error" ? error : output,
          status === "error" ? "error" : "completed",
          "event",
          typeof part.callID === "string" ? part.callID : "",
        )
        if (!observed.deduped) recordTool(sessionID, typeof part.tool === "string" ? part.tool : "", input, status === "error" ? error : output)
      }
      return
    }

    if (type === "permission.asked" || type === "permission.updated") {
      const permission = props
      const tool = record(permission.tool)
      emit(session, true, {
        event: type,
        permission_id: typeof permission.id === "string" ? permission.id : "",
        message_id: typeof permission.messageID === "string" ? permission.messageID : tool.messageID || "",
        call_id: typeof permission.callID === "string" ? permission.callID : tool.callID || "",
        permission_type: typeof permission.permission === "string" ? permission.permission : permission.type || "",
      })
      return
    }

    if (type === "permission.replied") {
      emit(session, true, {
        event: type,
        permission_id:
          typeof props.permissionID === "string"
            ? props.permissionID
            : typeof props.requestID === "string"
              ? props.requestID
              : "",
        response: typeof props.response === "string" ? props.response : props.reply || "",
      })
      return
    }

    if (type === "session.created" || type === "session.updated" || type === "session.deleted") {
      const info = record(props.info)
      const sessionID = sessionOf({ ...props, info })
      if (type === "session.created") markToolStarted(sessionID)
      emit(sessionID, true, {
        event: type,
        session_id: typeof info.id === "string" ? info.id : session,
      })
      return
    }

    if (type === "session.idle" || type === "session.compacted") {
      emit(session, true, { event: type })
    }
  }

  async function after(input: ToolAfterInput, output: ToolAfterOutput): Promise<{ n: number; deduped: boolean; skipped: boolean }> {
    const sessionID = input.sessionID || "unknown"
    const status = failedExit(output.metadata?.exit) ? "error" : "completed"
    const observed = observeToolProgress(sessionID, input.tool || "", input.args, output.output, status, "after", input.callID || "")
    return { n: observed.n, deduped: observed.deduped, skipped: observed.skipped }
  }

  return { event, after }
}
