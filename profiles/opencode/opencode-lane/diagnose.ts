import { askJev, choiceOf, extraJevEnabled } from "./jev.ts"
import { laneLog } from "./log.ts"

const KINDS = new Set(["code", "env", "contract", "context", "unclear"])

export function looksFailed(text: string): boolean {
  return /traceback|assertionerror|\bfail(ed|ure)?\b|error:|npm err|exit code [1-9]|eacces|permission denied|command not found/i.test(
    text.slice(0, 4000),
  )
}

export async function diagnoseFailure(task: string, output: string): Promise<string> {
  if (!extraJevEnabled() || !looksFailed(output)) return ""
  const answers = await askJev(
    { task: task.slice(0, 1500), output: output.slice(0, 2500) },
    {
      kind: {
        type: "choice",
        instructions: "Why did this tool output fail, given `task`?",
        criteria: {
          code: "The code or test is wrong; a patch would fix it",
          env: "Missing binary, auth, docker, network, or host setup",
          contract: "owns_paths, never_touch, or the task YAML made the work impossible",
          context: "Needed API contract, file, or fact was not in context",
          unclear: "Not enough evidence to say",
        },
      },
    },
  )
  const { choice, conf } = choiceOf(answers, "kind", KINDS, "unclear")
  const kind = conf >= 0.5 ? choice : "unclear"
  laneLog({ mod: "diagnose", ok: true, data: { kind, conf } })
  if (kind === "unclear") return ""
  const next =
    kind === "context"
      ? "Do not bump the model yet: add the missing contract/file to context."
      : kind === "env"
        ? "Do not retry the same patch: fix the environment first."
        : kind === "contract"
          ? "Do not retry: fix owns_paths / never_touch / acceptance in the YAML."
          : "A code change is the next step."
  return `[opencode-lane diagnose] ${kind} (conf ${conf.toFixed(2)}). ${next}`
}
