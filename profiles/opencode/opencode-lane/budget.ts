import { createHash } from "node:crypto"
import { askJev, choiceOf, extraJevEnabled } from "./jev.ts"
import { laneLog, redactText } from "./log.ts"

const KINDS = new Set(["same_loop", "new_evidence", "unclear"])
const seen = new Map<string, Map<string, number>>()

export type ToolAttempt = {
  tool: string
  cmd: string
  fp: string
  n: number
  chars: number
  tail: string
}

const recent = new Map<string, ToolAttempt[]>()
const progressCounts = new Map<string, Map<string, number>>()
const observedCalls = new Map<string, Map<string, number>>()
const eventWithoutCall = new Map<string, Map<string, number>>()
const sessionStarted = new Map<string, number>()
const firstEdit = new Set<string>()

function stable(value: unknown): string {
  if (value === undefined) return "undefined"
  if (typeof value === "string") return JSON.stringify(value)
  if (value === null || typeof value !== "object") return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`
  return `{${Object.keys(value as Record<string, unknown>)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable((value as Record<string, unknown>)[key])}`)
    .join(",")}}`
}

function valueLength(value: unknown): number {
  return typeof value === "string" ? value.length : value == null ? 0 : stable(value).length
}

function redact(value: unknown): unknown {
  if (typeof value === "string") return redactText(value)
  if (Array.isArray(value)) return value.map(redact)
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, redact(item)]))
  }
  return value
}

function digest(value: unknown): string {
  return createHash("sha256").update(stable(value)).digest("hex").slice(0, 16)
}

function fingerprintArgs(tool: string, args: unknown): unknown {
  const name = tool.toLowerCase()
  if (name !== "bash" && name !== "shell") return args
  if (!args || typeof args !== "object" || Array.isArray(args)) return args
  const transport = new Set(["toolCallId", "requestId", "conversationId"])
  return Object.fromEntries(Object.entries(args as Record<string, unknown>).filter(([key]) => !transport.has(key)))
}

export function argKey(tool: string, args: unknown): string {
  const normalized = fingerprintArgs(tool, args)
  const a = normalized && typeof normalized === "object" ? normalized as Record<string, unknown> : {}
  const path = [a.path, a.filePath, a.file].find((v) => typeof v === "string") as string | undefined
  const cmd = [a.command, a.cmd].find((v) => typeof v === "string") as string | undefined
  const pattern = [a.pattern, a.query].find((v) => typeof v === "string") as string | undefined
  // Keep the old readable suffix for Jev context while hashing the complete args above it.
  return `${stable(normalized)}|${[tool.toLowerCase(), path ?? "", cmd ?? "", pattern ?? ""].join("|")}`
}

export function toolFingerprint(tool: string, args: unknown, output: unknown): string {
  // ponytail: full-body hash; ceiling is RAM of the tool payload. Upgrade: streaming hash if outputs >> 10MB.
  return createHash("sha256")
    .update(argKey(tool, args))
    .update("\0")
    .update(String(valueLength(output)))
    .update("\0")
    .update(stable(output))
    .digest("hex")
    .slice(0, 16)
}

export function recentAttempts(sessionID: string): ToolAttempt[] {
  return recent.get(sessionID) || []
}

export function recordTool(
  sessionID: string,
  tool: string,
  args: unknown,
  output: unknown,
): { n: number; chars: number; fp: string } {
  const fp = toolFingerprint(tool, args, output)
  const bag = seen.get(sessionID) || new Map<string, number>()
  seen.set(sessionID, bag)
  const n = (bag.get(fp) || 0) + 1
  bag.set(fp, n)
  const cmd = argKey(tool, args)
  const list = recent.get(sessionID) || []
  list.push({
    tool: tool.toLowerCase(),
    cmd,
    fp,
    n,
    chars: valueLength(output),
    tail: typeof output === "string" ? output : stable(output),
  })
  recent.set(sessionID, list)
  laneLog({
    mod: "budget",
    ok: true,
    session: sessionID,
    data: { tool: tool.toLowerCase(), chars: valueLength(output), dup: n > 1, n, fp },
  })
  return { n, chars: valueLength(output), fp }
}

export type ToolProgressStatus = "completed" | "error"
export type ToolProgressSource = "event" | "after"

export function markToolStarted(sessionID: string): void {
  if (sessionID && !sessionStarted.has(sessionID)) sessionStarted.set(sessionID, Date.now())
}

function isEditTool(tool: string): boolean {
  return /(?:^|[_:.\/-])(write|edit|patch|apply_patch)(?:$|[_:.\/-])/.test(tool.toLowerCase())
}

export function observeToolProgress(
  sessionID: string,
  tool: string,
  args: unknown,
  output: unknown,
  status: ToolProgressStatus,
  source: ToolProgressSource,
  callID = "",
): { fp: string; n: number; duplicate: boolean; deduped: boolean; skipped: boolean; firstEditCallbackMs?: number } {
  const name = tool.toLowerCase()
  const fp = toolFingerprint(name, args, output)
  const key = `${name}|${fp}`
  const calls = observedCalls.get(sessionID) || new Map<string, number>()
  observedCalls.set(sessionID, calls)
  if (callID && calls.has(callID)) {
    return { fp, n: calls.get(callID) || 1, duplicate: true, deduped: true, skipped: false }
  }
  if (!callID && source === "after") {
    const events = eventWithoutCall.get(sessionID) || new Map<string, number>()
    const eventN = events.get(key)
    if (eventN !== undefined) {
      events.delete(key)
      return { fp, n: eventN, duplicate: true, deduped: true, skipped: false }
    }
    return { fp, n: 0, duplicate: false, deduped: false, skipped: true }
  }
  const counts = progressCounts.get(sessionID) || new Map<string, number>()
  progressCounts.set(sessionID, counts)
  const n = (counts.get(key) || 0) + 1
  counts.set(key, n)
  const duplicate = n > 1
  if (callID) calls.set(callID, n)
  else if (source === "event") {
    const events = eventWithoutCall.get(sessionID) || new Map<string, number>()
    events.set(key, n)
    eventWithoutCall.set(sessionID, events)
  }
  const data: Record<string, unknown> = {
    event: "tool.progress",
    tool: name,
    status,
    source,
    input_sha256: digest(args),
    output_sha256: digest(output),
    fingerprint: fp,
    evidence: duplicate ? "unchanged" : "novel",
    evidence_count: n,
  }
  let firstEditMs: number | undefined
  if (status === "completed" && isEditTool(name) && !firstEdit.has(sessionID)) {
    firstEdit.add(sessionID)
    const started = sessionStarted.get(sessionID)
    if (started !== undefined) {
      firstEditMs = Math.max(0, Date.now() - started)
      data.first_edit_callback_ms = firstEditMs
    }
    data.edit_proof = "callback_success_only"
    data.bytes_changed_proven = false
  }
  laneLog({ mod: "progress", ok: status !== "error", session: sessionID, data })
  return { fp, n, duplicate, deduped: false, skipped: false, ...(firstEditMs === undefined ? {} : { firstEditCallbackMs: firstEditMs }) }
}

export async function repeatHint(
  task: string,
  tool: string,
  output: string,
  n: number,
  sessionID = "",
): Promise<string> {
  if (n < 3) return ""
  const name = tool.toLowerCase()
  if (name === "read" || name === "grep") {
    laneLog({ mod: "budget", ok: true, session: sessionID, data: { event: "repeated_read", tool: name, n } })
    return `[opencode-lane budget] Identical ${name} content has already been returned ${n} times. Reuse the earlier result and take the next task step. If you cannot proceed, report the concrete blocker instead of rereading it.`
  }
  if (name !== "bash" && name !== "shell") {
    laneLog({ mod: "budget", ok: true, session: sessionID, data: { event: "repeated_tool", tool: name, n } })
    return `[opencode-lane budget] Identical ${name} result has already been returned ${n} times. This is advisory: reuse it when it answers the task, or change the input when new evidence is needed.`
  }
  const prior = recentAttempts(sessionID)
    .map((row) => redact({ cmd: row.cmd, fp: row.fp, n: row.n, tail: row.tail })) as {
      cmd: string
      fp: string
      n: number
      tail: string
    }[]
  if (!extraJevEnabled()) {
    return `[opencode-lane budget] same ${name} result ${n} times. Change the hypothesis before retrying.`
  }
  const answers = await askJev(
    { task: redactText(task), output: redactText(output), repeats: n, prior },
    {
      kind: {
        type: "choice",
        instructions:
          "Given `prior` attempts (command, fingerprint, tail), did this repeat add new evidence or is it the same failed loop?",
        criteria: {
          same_loop: "Same error and same hypothesis; another identical call will not help",
          new_evidence: "Output or environment changed enough that a retry is justified",
          unclear: "Not enough to say",
        },
      },
    },
  )
  const { choice, conf } = choiceOf(answers, "kind", KINDS, "unclear")
  laneLog({ mod: "budget", ok: true, data: { kind: choice, conf, n } })
  if (choice !== "same_loop" || conf < 0.55) return ""
  const cmds = prior.map((row) => row.cmd).filter(Boolean)
  const extra = cmds.length ? ` Last: ${cmds[cmds.length - 1]}.` : ""
  return `[opencode-lane budget] same_loop ×${n} (conf ${conf.toFixed(2)}).${extra} Do not retry the same command; check env or change the patch.`
}
