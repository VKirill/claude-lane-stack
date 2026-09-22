import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { askJev, choiceOf, extraJevEnabled, stackRoot } from "./jev.ts"
import { laneLog } from "./log.ts"

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

const ALLOWED = new Set(Object.keys(WRITE_SKILLS))
const hinted = new Map<string, string>()

export function skillPhase(task: string, tools: string[] = []): string {
  const last = tools.filter(Boolean).slice(-2).join(",")
  return createHash("sha256").update(task.slice(0, 1500)).update("\0").update(last).digest("hex").slice(0, 16)
}

export async function skillHint(sessionID: string, task: string, tools: string[] = []): Promise<string> {
  if (!extraJevEnabled() || !sessionID || !task) return ""
  const sig = skillPhase(task, tools)
  if (hinted.get(sessionID) === sig) return ""
  hinted.set(sessionID, sig)
  const answers = await askJev(
    { task: task.slice(0, 1500), tools: tools.slice(-2) },
    {
      need: {
        type: "noul",
        instructions: "Does this task need a specialized write skill beyond the lane contract?",
      },
      skill: {
        type: "choice",
        instructions: "Which write skill should the implementer follow for this task and recent tools?",
        criteria: WRITE_SKILLS,
      },
    },
  )
  const need = typeof answers?.need?.noul === "number" && Number.isFinite(answers.need.noul) ? answers.need.noul : 1
  const { choice, conf } = choiceOf(answers, "skill", ALLOWED, "none")
  laneLog({ mod: "skill-hint", ok: true, data: { choice, conf, need } })
  if (need < 0.35 || choice === "none" || conf < 0.55) return ""
  return `[opencode-lane skill] ${choice} (conf ${conf.toFixed(2)}). Load ~/.agents/skills/${choice}/SKILL.md if it fits.`
}
