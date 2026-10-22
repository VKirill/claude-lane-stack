// opencode-lane for OpenCode v2 (`@opencode/plugin`): one shared background service serves every session on the host.
//
// GATE. The service's process.env is the service's, not the thread's, and a service started from a lane shell would carry that lane's
// LANE_* markers for every later session. So no hook reads LANE_* from process.env. A lane session is one whose agent id starts with
// `lane-` (lane-writer, lane-critic, lane-reviewer, or any other lane-* agent): every hook that matters carries the agent id, the
// prompt hook looks it up with session.get. Winnow and telemetry run in every session, as under v1.
//
// HOOKS (v1 -> v2)
//   event                                   -> ctx.event.subscribe()                     telemetry, every session
//   chat.message                            -> ctx.session.hook("prompt")                prompt state, contract, skill hint
//   experimental.chat.messages.transform    -> ctx.session.hook("context")               evidence, dumped-tool note, sticky block
//   tool.execute.before                     -> ctx.tool.hook("execute.before")           writer guard (throws to refuse)
//   tool.execute.after                      -> ctx.tool.hook("execute.after")            winnow (all), diagnosis/budget/hints (lane)
//   permission.ask (new)                    -> ctx.permission.hook("evaluate")           agent deny rules + hub guard, lane only
// DROPPED, no v2 equivalent:
//   chat.params model-id/effort swap  - the request's model is read-only in v2 and effort is the model variant; set it on the agent
//                                       (`model: provider/model#variant`). The Jev effort route is gone with it.
//   session.compacting / auto-compaction off - no agent-level switch and no hook that can skip a compaction (index.ts header).
//   client.app.log sink               - v2 plugins have no log API; the local opencode-lane.jsonl journal stays.
//   LANE_TASK_FILE / LANE_PROMPT_FILE - per-process, meaningless in a shared service; the contract is read from the prompt instead.
import { spawn } from "node:child_process"
import { jevKeys, stackRoot } from "./jev.ts"
import { laneLog, setLaneSession, withLaneSession } from "./log.ts"
import { createTelemetry } from "./telemetry.ts"
import { appendStickyNotes, dumpedToolNote, formatStickyContract } from "./sticky.ts"
import { diagnoseFailure } from "./diagnose.ts"
import { skillHint } from "./skill-hint.ts"
import { evidenceNotes } from "./evidence.ts"
import { recentAttempts, recordTool, repeatHint, toolRepeatN } from "./budget.ts"
import { guardMcpV2, guardTool, projectHasSkill } from "./guard.ts"
import { agentDenies, hubShellDenial, isLaneAgent, type PermissionRule } from "./hub-guard.ts"
import { ensureStickyContent, lastAssistantTextV2, toOcMessages, type V2Message } from "./messages.ts"

const WINNOW = "http://127.0.0.1:47311/hook/post-tool-use"
const WINNOW_TOOLS = new Set(["read", "grep", "shell"])
const TASK_MARKER = /^--- RAW TASK YAML \(verbatim\) ---\r?$/m
const RULES_TTL_MS = 30_000

type Ctx = any // Context from "@opencode/plugin" (a type-only import would need the package next to the file)
type ResultContent = string | { type?: string; text?: string }[] | undefined
type ToolResult = { content?: ResultContent; metadata?: Record<string, unknown> }

function claudeTool(name: string): string {
  if (name === "shell") return "Bash"
  return name === "grep" ? "Grep" : "Read"
}

async function sidecarHealthy(): Promise<boolean> {
  try {
    return (await fetch("http://127.0.0.1:47311/health", { signal: AbortSignal.timeout(800) })).ok
  } catch {
    return false
  }
}

// Not spawnSync: the service is shared, a blocked event loop would stall every session on the host.
let starting: Promise<boolean> | null = null
async function ensureSidecar(): Promise<boolean> {
  if (await sidecarHealthy()) return true
  starting ??= new Promise<boolean>((resolve) => {
    const keys = jevKeys()
    const child = spawn(
      "uv",
      ["run", "-q", "--project", `${stackRoot()}/plugins/lane-stack/winnow/sidecar`, "python", "-m", "winnow", "serve", "--ensure"],
      {
        stdio: "ignore",
        env: {
          ...process.env,
          ...(keys.openlux ? { OPENLUX_API_KEY: keys.openlux } : {}),
          ...(keys.typesafe ? { TYPESAFE_API_KEY: keys.typesafe } : {}),
        },
      },
    )
    const timer = setTimeout(() => { child.kill(); resolve(false) }, 20_000)
    child.on("error", () => { clearTimeout(timer); resolve(false) })
    child.on("exit", (code) => { clearTimeout(timer); resolve(code === 0) })
  }).finally(() => { starting = null })
  const started = await starting
  if (!started) laneLog({ mod: "winnow", ok: false, session: "", err: "sidecar start failed" })
  return started && sidecarHealthy()
}

export function resultText(content: ResultContent): string {
  if (typeof content === "string") return content
  if (!Array.isArray(content)) return ""
  return content.map((part) => (part?.type === "text" && typeof part.text === "string" ? part.text : "")).join("")
}

/** Replaces the text of a tool result and keeps its non-text parts (files). */
export function setResultText(result: ToolResult, text: string): void {
  if (Array.isArray(result.content)) {
    result.content = [{ type: "text", text }, ...result.content.filter((part) => part?.type !== "text")]
  } else {
    result.content = text
  }
}

function appendResultNote(result: ToolResult, note: string): void {
  if (Array.isArray(result.content)) result.content = [...result.content, { type: "text", text: `\n${note}` }]
  else result.content = `${resultText(result.content)}\n${note}`
}

async function winnowOutput(tool: string, args: unknown, text: string, sessionID: string, task: string): Promise<string> {
  if (text.length < 1500 || !(await ensureSidecar())) return text
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
  const updated = (await response.json())?.hookSpecificOutput?.updatedToolOutput
  const next = typeof updated === "string" && updated ? updated : text
  laneLog({ mod: "winnow", ok: true, session: sessionID, data: { chars_in: text.length, chars_out: next.length } })
  return next
}

export async function laneSetup(ctx: Ctx): Promise<() => void> {
  // OpenCode v1 (1.18.30) calls every function of a default-exported object, setup() included, with its own PluginInput; that
  // input has no session.hook. v1 gets its hooks from server().
  if (typeof ctx?.session?.hook !== "function") return () => {}
  const telemetry = createTelemetry()
  const events = new AbortController()
  const prompts = new Map<string, string>() // session -> the task as last prompted
  const contracts = new Map<string, { block: string; yaml: string }>() // session -> contract from a RAW TASK YAML prompt
  const notes = new Map<string, string[]>() // session -> hints appended to the sticky block
  const sessions = new Map<string, { lane: boolean; directory: string }>()
  const rules = new Map<string, { at: number; list: PermissionRule[] }>()
  let servers: { at: number; names: string[] } = { at: 0, names: [] }

  const pushNote = (sessionID: string, note: string): void => {
    if (!note) return
    const prefix = note.match(/^\[opencode-lane [^\]]+\]/)?.[0]
    let list = notes.get(sessionID) || []
    if (prefix) list = list.filter((item) => !item.startsWith(prefix))
    if (!list.includes(note)) list.push(note)
    notes.set(sessionID, list.slice(-6))
  }

  const refreshSession = async (sessionID: string): Promise<{ lane: boolean; directory: string }> => {
    const raw = await ctx.session.get({ sessionID })
    const info = raw?.data ?? raw // session.get answers the info itself, agent.get and mcp.list wrap it as { location, data }
    const known = { lane: isLaneAgent(info?.agent), directory: String(info?.location?.directory || process.cwd()) }
    sessions.set(sessionID, known)
    return known
  }

  const agentRules = async (agentID: string): Promise<PermissionRule[]> => {
    const hit = rules.get(agentID)
    if (hit && Date.now() - hit.at < RULES_TTL_MS) return hit.list
    const raw = await ctx.agent.get({ agentID })
    const agent = raw?.data ?? raw
    const list = Array.isArray(agent?.permissions) ? (agent.permissions as PermissionRule[]) : []
    rules.set(agentID, { at: Date.now(), list })
    return list
  }

  const mcpServers = async (): Promise<string[]> => {
    if (Date.now() - servers.at < RULES_TTL_MS) return servers.names
    const listed = await ctx.mcp.list()
    servers = { at: Date.now(), names: (listed?.data ?? []).map((item: { name: string }) => item.name) }
    return servers.names
  }

  void ensureSidecar().then(
    (ready) => { if (!ready) laneLog({ mod: "winnow", ok: false, session: "", err: "sidecar unavailable" }) },
    (err) => laneLog({ mod: "winnow", ok: false, session: "", err: String(err) }),
  )
  laneLog({ mod: "startup", ok: true, session: "", data: { event: "plugin.startup", api: "v2", gate: "agent:lane-*" } })

  // event -> telemetry, every session
  void (async () => {
    try {
      for await (const event of ctx.event.subscribe({ signal: events.signal })) {
        // The stream carries every location's events and setup() runs once per location: take only this location's, or each is logged N times.
        if (event?.location?.directory && event.location.directory !== ctx.location.directory) continue
        try {
          await telemetry.event({ event })
        } catch (err) {
          laneLog({ mod: "telemetry", ok: false, session: "", err: String(err) })
        }
      }
    } catch (err) {
      if (!events.signal.aborted) laneLog({ mod: "telemetry", ok: false, session: "", err: `event stream: ${String(err)}` })
    }
  })()

  // chat.message
  await ctx.session.hook("prompt", async (e: { sessionID: string; prompt: { text?: string } }) => {
    const sessionID = e.sessionID
    try {
      const session = await refreshSession(sessionID)
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        const text = (e.prompt?.text ?? "").trim()
        if (!text) return
        const marker = TASK_MARKER.exec(text)
        const task = marker ? text.slice(marker.index + marker[0].length).trim() : text
        prompts.set(sessionID, task)
        if (!session.lane) return
        if (marker) {
          contracts.set(sessionID, { block: formatStickyContract(task, "the task prompt"), yaml: task })
          await ctx.storage.set(`contract:${sessionID}`, task).catch(() => {})
        }
        try {
          pushNote(sessionID, await skillHint(sessionID, task, recentAttempts(sessionID).map((row) => row.tool)))
        } catch (err) {
          laneLog({ mod: "skill-hint", ok: false, session: sessionID, err: String(err) })
        }
      })
    } catch (err) {
      laneLog({ mod: "prompt", ok: false, session: sessionID, err: String(err) })
    }
  })

  // experimental.chat.messages.transform (+ system.transform)
  await ctx.session.hook("context", async (e: { sessionID: string; agent: string; messages: V2Message[] }) => {
    if (!isLaneAgent(e.agent)) return
    const sessionID = e.sessionID
    await withLaneSession(sessionID, async () => {
      setLaneSession(sessionID)
      try {
        let contract = contracts.get(sessionID)
        if (!contract) {
          const saved = await ctx.storage.get(`contract:${sessionID}`).catch(() => undefined)
          contract = typeof saved === "string"
            ? { block: formatStickyContract(saved, "the task prompt"), yaml: saved }
            : { block: "", yaml: "" }
          contracts.set(sessionID, contract)
        }
        try {
          pushNote(sessionID, await evidenceNotes(sessionID, toOcMessages(e.messages), contract.yaml))
        } catch (err) {
          laneLog({ mod: "evidence", ok: false, session: sessionID, err: String(err) })
        }
        pushNote(sessionID, dumpedToolNote(lastAssistantTextV2(e.messages)))
        ensureStickyContent(e.messages, appendStickyNotes(contract.block, notes.get(sessionID) || []))
      } catch (err) {
        laneLog({ mod: "sticky", ok: false, session: sessionID, err: String(err) })
      }
    })
  })

  // tool.execute.before
  await ctx.tool.hook("execute.before", async (e: { tool: string; sessionID: string; agent: string; input: unknown }) => {
    if (!isLaneAgent(e.agent)) return
    const session = sessions.get(e.sessionID) ?? (await refreshSession(e.sessionID))
    const ownSkills = e.agent === "lane-critic" || e.agent === "lane-reviewer"
    const msg =
      guardTool(e.tool, e.input, session.directory, { skills: !ownSkills }) || guardMcpV2(e.tool, await mcpServers(), e.agent)
    if (!msg) return
    laneLog({ mod: "guard", ok: false, session: e.sessionID, err: msg })
    throw new Error(msg)
  })

  // tool.execute.after
  await ctx.tool.hook(
    "execute.after",
    async (e: { tool: string; sessionID: string; agent: string; id: string; input: unknown; status: string; result?: ToolResult; error?: { message?: string } }) => {
      const sessionID = e.sessionID
      await withLaneSession(sessionID, async () => {
        setLaneSession(sessionID)
        const lane = isLaneAgent(e.agent)
        const task = prompts.get(sessionID) || ""
        const failed = e.status === "error"
        const result: ToolResult = failed ? {} : (e.result as ToolResult)
        const original = failed ? String(e.error?.message ?? "") : resultText(result?.content)
        let output = original
        if (!failed && WINNOW_TOOLS.has(e.tool) && original) {
          try {
            output = await winnowOutput(e.tool, e.input, original, sessionID, task)
            if (output !== original) setResultText(result, output)
          } catch (err) {
            laneLog({ mod: "winnow", ok: false, session: sessionID, err: String(err) })
          }
        }
        if (!lane) return
        const note = (text: string): void => {
          pushNote(sessionID, text)
          if (!failed) appendResultNote(result, text)
        }
        const exit = failed ? 1 : result?.metadata?.exit
        try {
          const diagnosis = await diagnoseFailure(task, original, exit)
          if (diagnosis) note(diagnosis)
        } catch (err) {
          laneLog({ mod: "diagnose", ok: false, session: sessionID, err: String(err) })
        }
        try {
          const observed = await telemetry.after(
            { tool: e.tool, sessionID, callID: e.id, args: e.input },
            { output: original, metadata: { exit } },
          )
          if (!observed.skipped) {
            const n = observed.deduped
              ? Math.max(observed.n, toolRepeatN(sessionID, e.tool, e.input))
              : recordTool(sessionID, e.tool, e.input, original).n
            const hint = await repeatHint(task, e.tool, original, n, sessionID, typeof exit === "number" && exit !== 0)
            if (hint) note(hint)
          }
        } catch (err) {
          laneLog({ mod: "budget", ok: false, session: sessionID, err: String(err) })
        }
        try {
          pushNote(sessionID, await skillHint(sessionID, task, recentAttempts(sessionID).map((row) => row.tool)))
        } catch (err) {
          laneLog({ mod: "skill-hint", ok: false, session: sessionID, err: String(err) })
        }
      })
    },
  )

  // permission.ask. Runs after OpenCode's own rules, so it can turn the answer to deny but never grants.
  await ctx.permission.hook(
    "evaluate",
    async (e: { sessionID: string; agent?: string; action: string; resources: string[]; effect: string; message?: string }) => {
      if (!e.agent || !isLaneAgent(e.agent) || e.effect === "deny") return
      const deny = (message: string): void => {
        e.effect = "deny"
        e.message = message
        laneLog({ mod: "guard", ok: false, session: e.sessionID, err: message })
      }
      // A skill Lane Pilot linked into the session directory's .opencode/skills is the thread's own: the agent file's skill rules do not apply.
      if (e.action === "skill") {
        const session = sessions.get(e.sessionID) ?? (await refreshSession(e.sessionID))
        if (e.resources.every((skill) => projectHasSkill(session.directory, skill.toLowerCase()))) return
      }
      if (agentDenies(await agentRules(e.agent), e.action, e.resources)) {
        return deny(`[opencode-lane guard] ${e.action} is denied for ${e.agent} by its agent file.`)
      }
      if (e.action !== "shell") return
      for (const command of e.resources) {
        const message = hubShellDenial(command)
        if (message) return deny(message)
      }
    },
  )

  return () => events.abort()
}
