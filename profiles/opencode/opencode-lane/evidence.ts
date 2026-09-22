import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { askJev, extraJevEnabled } from "./jev.ts"
import { laneLog } from "./log.ts"
import { stickySourcePath } from "./sticky.ts"

export function parseAcceptance(yaml: string): string[] {
  const out: string[] = []
  let inAcc = false
  for (const line of yaml.split(/\r?\n/)) {
    if (/^acceptance:\s*$/.test(line)) {
      inAcc = true
      continue
    }
    if (inAcc) {
      if (/^\S/.test(line)) break
      const match = line.match(/^\s+-\s+(.*)$/)
      if (match) out.push(match[1].replace(/^["']|["']$/g, "").trim())
    }
  }
  return out
}

export function lastToolText(messages: { parts?: unknown[] }[]): string {
  let last = ""
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const item = part as { type?: string; state?: { output?: string } }
      if (item.type === "tool" && typeof item.state?.output === "string") last = item.state.output
    }
  }
  return last
}

export function collectBashEvidence(messages: { parts?: unknown[] }[]): string {
  const chunks: string[] = []
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const item = part as {
        type?: string
        tool?: string
        state?: { output?: string; input?: Record<string, unknown> }
      }
      const tool = (item.tool || "").toLowerCase()
      if (item.type !== "tool" || (tool !== "bash" && tool !== "shell")) continue
      const out = item.state?.output
      if (typeof out !== "string" || !out.trim()) continue
      const cmd = typeof item.state?.input?.command === "string" ? item.state.input.command : ""
      chunks.push(`$ ${cmd}\n${out}`)
    }
  }
  if (!chunks.length) return lastToolText(messages)
  return chunks.join("\n---\n")
}

const checked = new Map<string, string>()

export async function evidenceNotes(sessionID: string, messages: { parts?: unknown[] }[]): Promise<string> {
  if (!extraJevEnabled() || !sessionID) return ""
  const path = stickySourcePath()
  if (!path) return ""
  let yaml = ""
  try {
    yaml = readFileSync(path, "utf8")
  } catch {
    return ""
  }
  const criteria = parseAcceptance(yaml)
  const evidence = collectBashEvidence(messages)
  if (!criteria.length || !evidence.trim()) return ""
  const sig = createHash("sha256").update(JSON.stringify({ path, criteria, evidence })).digest("hex").slice(0, 16)
  if (checked.get(sessionID) === sig) return ""
  const questions: Record<string, unknown> = {}
  for (const [i, criterion] of criteria.entries()) {
    questions[`c${i}`] = {
      type: "choice",
      instructions: `How does \`evidence\` relate to acceptance criterion ${i}: ${criterion}`,
      criteria: {
        supports: "The evidence states or directly implies the criterion is true",
        contradicts: "The evidence states the opposite or implies it is false",
        says_nothing: "The evidence does not address the criterion",
      },
    }
  }
  const answers = await askJev({ evidence, criteria }, questions, 4000)
  if (!answers) return ""
  checked.set(sessionID, sig)
  const gaps: string[] = []
  for (const [i, criterion] of criteria.entries()) {
    const raw = answers[`c${i}`]
    const choice = typeof raw?.choice === "string" ? raw.choice : "says_nothing"
    const conf = typeof raw?.confidence === "number" ? raw.confidence : 0
    if (choice === "supports" && conf >= 0.8) continue
    gaps.push(`- ${choice} (${conf.toFixed(2)}): ${criterion}`)
  }
  laneLog({ mod: "evidence", ok: true, data: { n: criteria.length, gaps: gaps.length } })
  if (!gaps.length) return "[opencode-lane evidence] all listed acceptance criteria have supporting tool output."
  return `[opencode-lane evidence] not confirmed:\n${gaps.join("\n")}`
}
