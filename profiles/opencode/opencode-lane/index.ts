import { spawnSync } from "node:child_process"
import { askJev, stackRoot, typesafeKey } from "./jev.ts"
import { laneLog, setLaneLogSink, setLaneSession, withLaneSession } from "./log.ts"
import { createTelemetry, eventSessionID } from "./telemetry.ts"
import {
  STICKY_MARK,
  appendStickyNotes,
  dumpedToolNote,
  ensureStickyMessages,
  lastAssistantText,
  readStickyContract,
  type OcMessage,
} from "./sticky.ts"
import { diagnoseFailure } from "./diagnose.ts"
import { skillHint } from "./skill-hint.ts"
import { evidenceNotes } from "./evidence.ts"
import { recentAttempts, recordTool, repeatHint } from "./budget.ts"
import { sessionKey } from "./session.ts"

export {
  STICKY_MARK,
  dumpedToolNote,
  formatStickyContract,
  lastAssistantText,
  readStickyContract,
  ensureStickyMessages,
} from "./sticky.ts"
export { looksFailed } from "./diagnose.ts"
export { parseAcceptance, collectBashEvidence } from "./evidence.ts"
export { WRITE_SKILLS, skillPhase } from "./skill-hint.ts"
export { toolFingerprint, recordTool, recentAttempts } from "./budget.ts"
export { askCacheKey } from "./jev.ts"
export { sessionKey, pickSessionID } from "./session.ts"

const WINNOW = "http://127.0.0.1:47311/hook/post-tool-use"
const WINNOW_TOOLS = new Set(["read", "grep", "bash", "shell"])

function claudeTool(name: string): string {
  const lower = name.toLowerCase()
  if (lower === "bash" || lower === "shell") return "Bash"
  if (lower === "grep") return "Grep"
  return "Read"
}

async function sidecarHealthy(): Promise<boolean> {
  try {
    const response = await fetch("http://127.0.0.1:47311/health", { signal: AbortSignal.timeout(800) })
    return response.ok
  } catch {
    return false
  }
}

async function ensureSidecar(): Promise<boolean> {
  if (await sidecarHealthy()) return true
  const project = `${stackRoot()}/plugins/lane-stack/winnow/sidecar`
  const key = typesafeKey()
  const started = spawnSync(
    "uv",
    ["run", "-q", "--project", project, "python", "-m", "winnow", "serve", "--ensure"],
    {
      timeout: 20_000,
      stdio: "ignore",
      env: key ? { ...process.env, TYPESAFE_API_KEY: key } : process.env,
    },
  )
  if (started.status !== 0) {
    laneLog({ mod: "winnow", ok: false, session: "", err: "sidecar start failed" })
    return false
  }
  return sidecarHealthy()
}

const lastPrompt = new Map<string, string>()
const lastRoute = new Map<string, { prompt: string; effort: string }>()
const sessionNotes = new Map<string, string[]>()

function rememberPrompt(
  sessionID: string,
  parts: { type?: string; text?: string; synthetic?: boolean }[],
): void {
  const text = parts
    .filter((part) => part.type === "text" && part.text && !part.synthetic)
    .map((part) => part.text)
    .join(" ")
    .trim()
  if (!sessionID || !text) return
  const marker = /^--- RAW TASK YAML \(verbatim\) ---\r?$/m.exec(text)
  const task = marker ? text.slice(marker.index + marker[0].length).trim() : text
  lastPrompt.set(sessionID, task)
}

function modelIdOf(model: { id?: string; modelID?: string } | undefined): string {
  return (model?.id || model?.modelID || "").trim()
}

function setModelId(model: { id?: string; modelID?: string } | undefined, next: string): void {
  if (!model || !next) return
  try {
    if (typeof model.id === "string") model.id = next
    if (typeof model.modelID === "string") model.modelID = next
  } catch {
    /* frozen Model */
  }
}

function pushNote(sessionID: string, note: string): void {
  if (!note) return
  const prefix = note.match(/^\[opencode-lane [^\]]+\]/)?.[0]
  let list = sessionNotes.get(sessionID) || []
  if (prefix) list = list.filter((item) => !item.startsWith(prefix))
  if (!list.includes(note)) list.push(note)
  sessionNotes.set(sessionID, list.slice(-6))
}

async function routeChatParams(
  sessionID: string,
  model: { id?: string; modelID?: string } | undefined,
  output: { options?: Record<string, unknown> },
): Promise<void> {
  const flag = (process.env.LANE_JEV_EFFORT ?? "1").trim().toLowerCase()
  if (flag === "0" || flag === "off" || flag === "false" || flag === "no") return
  const prompt = lastPrompt.get(sessionID) || ""
  if (!prompt) return
  const core = await import(`${stackRoot()}/plugins/lane-stack/hooks/jev-route-core.ts`)
  const id = modelIdOf(model)
  const fromId = core.currentEffortFromModelId(id)
  const current = fromId || core.asSessionEffort(output.options?.reasoningEffort, "medium")
  let effort = current
  const cached = lastRoute.get(sessionID)
  if (cached && cached.prompt === prompt) {
    effort = cached.effort
  } else {
    try {
      const answers = await askJev({ task: prompt }, core.ROUTE_QUESTIONS, core.ROUTE_TIMEOUT_MS)
      if (answers) effort = core.parseRoute(answers, current).effort
      laneLog({ mod: "route", ok: true, session: sessionID, data: { effort } })
    } catch (err) {
      laneLog({ mod: "route", ok: false, session: sessionID, err: String(err) })
      effort = current
    }
    lastRoute.set(sessionID, { prompt, effort })
  }
  if (effort === current) return
  if (id) {
    const nextId = core.swapModelEffort(id, effort)
    if (nextId !== id) setModelId(model, nextId)
  }
  output.options = { ...output.options, reasoningEffort: effort, reasoning_effort: effort }
}

async function winnowOutput(
  tool: string,
  args: unknown,
  text: string,
  sessionID: string,
  task: string,
): Promise<string> {
  if (text.length < 1500) return text
  if (!(await ensureSidecar())) return text
  const response = await fetch(WINNOW, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      hook_event_name: "PostToolUse",
      source: "opencode",
      session_id: sessionID,
      cwd: process.cwd(),
      tool_name: claudeTool(tool),
      tool_input: args && typeof args === "object" ? args : {},
      tool_response: text,
      tool_use_id: `oc-${sessionID}`,
      task: { user_request: task, assistant_intent: "" },
    }),
    signal: AbortSignal.timeout(20_000),
  })
  if (!response.ok) {
    laneLog({ mod: "winnow", ok: false, session: sessionID, err: `http ${response.status}` })
    return text
  }
  const data = await response.json()
  const updated = data?.hookSpecificOutput?.updatedToolOutput
  const next = typeof updated === "string" && updated ? updated : text
  laneLog({
    mod: "winnow",
    ok: true,
    session: sessionID,
    data: { chars_in: text.length, chars_out: next.length },
  })
  return next
}

type PluginContext = {
  client?: { app?: { log?: (input: { body: Record<string, unknown> }) => Promise<unknown> } }
}

export const OpenCodeLanePlugin = async (ctx?: PluginContext) => {
  if (ctx?.client?.app?.log) {
    setLaneLogSink((row) =>
      ctx.client!.app!.log!({
        body: {
          service: "opencode-lane",
          level: row.ok === false ? "error" : "info",
          message: String(row.mod || "telemetry"),
          extra: row,
        },
      }),
    )
  }
  const telemetry = createTelemetry()
  laneLog({
    mod: "startup",
    ok: true,
    session: "",
    data: { event: "plugin.startup", history_compaction: "off" },
  })
  void ensureSidecar().then(
    (ready) => {
      if (!ready) laneLog({ mod: "winnow", ok: false, session: "", err: "sidecar unavailable" })
    },
    (err) => laneLog({ mod: "winnow", ok: false, session: "", err: String(err) }),
  )
  return {
    event: async (input: { event: unknown }) => {
      try {
        await telemetry.event(input)
      } catch (err) {
        laneLog({ mod: "telemetry", ok: false, session: eventSessionID(input.event), err: String(err) })
      }
    },
    "chat.message": async (
      input: { sessionID: string },
      output: { parts?: { type?: string; text?: string; synthetic?: boolean }[] },
    ) => {
      const sessionID = sessionKey(input, [{ info: { role: "user" }, parts: output.parts }], lastPrompt)
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        rememberPrompt(sessionID, output.parts ?? [])
        try {
          const hint = await skillHint(
            sessionID,
            lastPrompt.get(sessionID) || "",
            recentAttempts(sessionID).map((row) => row.tool),
          )
          pushNote(sessionID, hint)
        } catch (err) {
          laneLog({ mod: "skill-hint", ok: false, session: sessionID, err: String(err) })
        }
      })
    },
    "chat.params": async (
      input: {
        sessionID: string
        model?: { id?: string; modelID?: string }
      },
      output: { options?: Record<string, unknown> },
    ) => {
      try {
        const sessionID = sessionKey(input)
        await withLaneSession(sessionID, async () => {
          setLaneSession(sessionID)
          await routeChatParams(sessionID, input.model, output)
        })
      } catch (err) {
        laneLog({ mod: "route", ok: false, session: sessionKey(input), err: String(err) })
      }
    },
    "tool.execute.after": async (
      input: { tool: string; sessionID: string; callID?: string; args: unknown },
      output: { output: string; metadata?: { exit?: unknown } },
    ) => {
      const sessionID = sessionKey(input)
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        const name = (input.tool || "").toLowerCase()
        if (typeof output.output !== "string") return
        const task = lastPrompt.get(sessionID) || ""
        const original = output.output
        if (WINNOW_TOOLS.has(name)) {
          try {
            output.output = await winnowOutput(input.tool, input.args, original, sessionID, task)
          } catch (err) {
            laneLog({ mod: "winnow", ok: false, session: sessionID, err: String(err) })
          }
        }
        try {
          const note = await diagnoseFailure(task, original, output.metadata?.exit)
          if (note) {
            pushNote(sessionID, note)
            output.output = `${output.output}\n${note}`
          }
        } catch (err) {
          laneLog({ mod: "diagnose", ok: false, session: sessionID, err: String(err) })
        }
        try {
          const observed = await telemetry.after(input, { output: original, metadata: output.metadata })
          if (!observed.skipped) {
            const n = observed.deduped ? observed.n : recordTool(sessionID, input.tool, input.args, original).n
            const note = await repeatHint(task, input.tool, original, n, sessionID)
            if (note) {
              pushNote(sessionID, note)
              output.output = `${output.output}\n${note}`
            }
          }
        } catch (err) {
          laneLog({ mod: "budget", ok: false, session: sessionID, err: String(err) })
        }
        try {
          const hint = await skillHint(
            sessionID,
            task,
            recentAttempts(sessionID).map((row) => row.tool),
          )
          pushNote(sessionID, hint)
        } catch (err) {
          laneLog({ mod: "skill-hint", ok: false, session: sessionID, err: String(err) })
        }
      })
    },
    "experimental.chat.messages.transform": async (
      input: { sessionID?: string },
      output: { messages: OcMessage[] },
    ) => {
      const sessionID = sessionKey(input, output.messages, lastPrompt)
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        try {
          const evidence = await evidenceNotes(sessionID, output.messages)
          pushNote(sessionID, evidence)
        } catch (err) {
          laneLog({ mod: "evidence", ok: false, session: sessionID, err: String(err) })
        }
        try {
          pushNote(sessionID, dumpedToolNote(lastAssistantText(output.messages)))
          ensureStickyMessages(
            output.messages,
            appendStickyNotes(readStickyContract(), sessionNotes.get(sessionID) || []),
          )
        } catch (err) {
          laneLog({ mod: "sticky", ok: false, session: sessionID, err: String(err) })
        }
      })
    },
  }
}

export const LaneContextPlugin = OpenCodeLanePlugin
export default OpenCodeLanePlugin
