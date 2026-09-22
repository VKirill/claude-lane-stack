import { spawnSync } from "node:child_process"
import { askJev, stackRoot, typesafeKey } from "./jev.ts"
import { laneLog, setLaneLogSink, setLaneSession, withLaneSession } from "./log.ts"
import { createTelemetry, eventSessionID } from "./telemetry.ts"
import {
  STICKY_MARK,
  appendStickyNotes,
  ensureStickyMessages,
  readStickyContract,
  type OcMessage,
} from "./sticky.ts"
import { diagnoseFailure } from "./diagnose.ts"
import { skillHint } from "./skill-hint.ts"
import { evidenceNotes } from "./evidence.ts"
import { recentAttempts, recordTool, repeatHint } from "./budget.ts"
import { sessionKey } from "./session.ts"

export { STICKY_MARK, formatStickyContract, readStickyContract, ensureStickyMessages } from "./sticky.ts"
export { looksFailed } from "./diagnose.ts"
export { parseAcceptance, collectBashEvidence } from "./evidence.ts"
export { WRITE_SKILLS, skillPhase } from "./skill-hint.ts"
export { toolFingerprint, recordTool, recentAttempts } from "./budget.ts"
export { askCacheKey } from "./jev.ts"
export { sessionKey, pickSessionID } from "./session.ts"

const WINNOW = "http://127.0.0.1:47311/hook/post-tool-use"
const TOOLS = new Set(["read", "grep", "bash", "shell"])
const PRUNE_CHARS = 40_000

type ToolPart = {
  type: string
  callID: string
  tool?: string
  state?: { status?: string; input?: Record<string, unknown>; output?: string }
}

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
  if (sessionID && text) lastPrompt.set(sessionID, text.slice(0, 1500))
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

function toolChars(messages: OcMessage[]): number {
  let total = 0
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const item = part as ToolPart
      if (item.type === "tool" && typeof item.state?.output === "string") total += item.state.output.length
    }
  }
  return total
}

async function pruneMessages(messages: OcMessage[], sessionID: string): Promise<void> {
  const key = typesafeKey()
  if (!key || toolChars(messages) < PRUNE_CHARS) return
  const root = stackRoot()
  const [{ compact }, request] = await Promise.all([
    import(`${root}/plugins/lane-stack/fast-jev/src/compact.ts`),
    import(`${root}/plugins/lane-stack/fast-jev/src/request.ts`),
  ])
  const mapped = messages.map((message) => {
    const toolUses: { tool_use_id: string; tool: string; input: Record<string, unknown> }[] = []
    const toolResults: { tool_use_id: string; text: string }[] = []
    let text = ""
    for (const part of message.parts ?? []) {
      const item = part as ToolPart & { text?: string }
      if (item.type === "text" && item.text) text += item.text
      if (item.type === "tool" && item.state?.status === "completed" && item.callID) {
        toolUses.push({
          tool_use_id: item.callID,
          tool: item.tool || "tool",
          input: item.state.input || {},
        })
        toolResults.push({ tool_use_id: item.callID, text: item.state.output || "" })
      }
    }
    return {
      role: message.info?.role === "assistant" ? ("assistant" as const) : ("user" as const),
      text,
      toolUses,
      toolResults,
    }
  })
  const result = await compact(
    mapped,
    {
      async ask(state: unknown, questions: unknown) {
        const built = request.buildJevRequest({ apiKey: key, model: request.DEFAULT_MODEL }, state, questions)
        const response = await fetch(built.url, {
          method: built.method,
          headers: built.headers,
          body: built.body,
          signal: AbortSignal.timeout(30_000),
        })
        return request.parseJevResponse(response.status, response.ok, await response.text())
      },
    },
    { preserveRecentMessages: 6 },
  )
  const byShort = new Map<string, string>()
  let n = 0
  for (const message of mapped) {
    for (const item of message.toolResults) {
      n += 1
      byShort.set(`t${n}`, item.tool_use_id)
    }
  }
  const dropped = new Map<string, string>()
  for (const decision of result.decisions) {
    if (decision.action === "keep") continue
    const callID = byShort.get(decision.id)
    if (!callID) continue
    const original = mapped.flatMap((message) => message.toolResults).find((item) => item.tool_use_id === callID)
    const note =
      decision.action === "drop_call"
        ? `[fast-jev] ${decision.tool} removed`
        : `[fast-jev] ${decision.tool} result truncated`
    dropped.set(callID, decision.action === "drop_result" ? `${(original?.text || "").slice(0, 300)}\n${note}` : note)
  }
  if (dropped.size === 0) return
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const item = part as ToolPart
      if (item.type !== "tool" || item.state?.status !== "completed") continue
      const next = dropped.get(item.callID)
      if (next !== undefined && item.state) item.state.output = next
    }
  }
  laneLog({ mod: "compact", ok: true, session: sessionID, data: { dropped: dropped.size } })
}

let pruning = new Set<string>()

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
  laneLog({ mod: "startup", ok: true, session: "", data: { event: "plugin.startup" } })
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
      input: { tool: string; sessionID: string; args: unknown },
      output: { output: string; metadata?: { exit?: unknown } },
    ) => {
      const sessionID = sessionKey(input)
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        const name = (input.tool || "").toLowerCase()
        if (!TOOLS.has(name) || typeof output.output !== "string") return
        const task = lastPrompt.get(sessionID) || ""
        const original = output.output
        try {
          output.output = await winnowOutput(input.tool, input.args, original, sessionID, task)
        } catch (err) {
          laneLog({ mod: "winnow", ok: false, session: sessionID, err: String(err) })
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
          const { n } = recordTool(sessionID, input.tool, input.args, original)
          const note = await repeatHint(task, input.tool, original, n, sessionID)
          if (note) {
            pushNote(sessionID, note)
            output.output = `${output.output}\n${note}`
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
        if (pruning.has(sessionID)) return
        pruning.add(sessionID)
        try {
          await pruneMessages(output.messages, sessionID)
        } catch (err) {
          laneLog({ mod: "compact", ok: false, session: sessionID, err: String(err) })
        } finally {
          pruning.delete(sessionID)
        }
        try {
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
