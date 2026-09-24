import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { stackRoot } from "./jev.ts"

function loadWriteSkills(): Record<string, string> {
  try {
    const raw = JSON.parse(
      readFileSync(`${stackRoot()}/plugins/lane-stack/hooks/write-skills.json`, "utf8"),
    )
    if (raw && typeof raw === "object") return raw as Record<string, string>
  } catch {
    /* catalog missing: session still runs */
  }
  return { none: "No extra skill; the writer contract is enough" }
}

export const WRITE_SKILLS: Record<string, string> = loadWriteSkills()

export function skillPhase(task: string, tools: string[] = []): string {
  const last = tools.filter(Boolean).join(",")
  return createHash("sha256").update(task).update("\0").update(last).digest("hex").slice(0, 16)
}

export async function skillHint(
  _sessionID: string,
  _task: string,
  _tools: string[] = [],
): Promise<string> {
  // Writer contract is enough. Do not inject SKILL.md (guard + lane-writer deny).
  return ""
}
