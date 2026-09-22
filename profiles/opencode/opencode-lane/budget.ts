import { createHash } from "node:crypto"
import { askJev, choiceOf, extraJevEnabled } from "./jev.ts"
import { laneLog } from "./log.ts"

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

export function argKey(tool: string, args: unknown): string {
  if (!args || typeof args !== "object") return ""
  const a = args as Record<string, unknown>
  const path = [a.path, a.filePath, a.file].find((v) => typeof v === "string") as string | undefined
  const cmd = [a.command, a.cmd].find((v) => typeof v === "string") as string | undefined
  const pattern = [a.pattern, a.query].find((v) => typeof v === "string") as string | undefined
  return [tool.toLowerCase(), path ?? "", cmd ?? "", pattern ?? ""].join("|")
}

export function toolFingerprint(tool: string, args: unknown, output: string): string {
  // ponytail: full-body hash; ceiling is RAM of the tool payload. Upgrade: streaming hash if outputs >> 10MB.
  return createHash("sha256")
    .update(argKey(tool, args))
    .update("\0")
    .update(String(output.length))
    .update("\0")
    .update(output)
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
  output: string,
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
    chars: output.length,
    tail: output,
  })
  recent.set(sessionID, list)
  laneLog({
    mod: "budget",
    ok: true,
    data: { tool: tool.toLowerCase(), chars: output.length, dup: n > 1, n, fp },
  })
  return { n, chars: output.length, fp }
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
  if (name !== "bash" && name !== "shell") return ""
  const prior = recentAttempts(sessionID)
    .map((row) => ({ cmd: row.cmd, fp: row.fp, n: row.n, tail: row.tail }))
  if (!extraJevEnabled()) {
    return `[opencode-lane budget] same ${name} result ${n} times. Change the hypothesis before retrying.`
  }
  const answers = await askJev(
    { task, output, repeats: n, prior },
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
