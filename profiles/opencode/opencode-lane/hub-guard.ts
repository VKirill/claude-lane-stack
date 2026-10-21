// Shell and permission rules for lane agents under OpenCode v2.
//
// v2 runs one shared service for every session on the host, so a lane session is told apart by its agent id (`lane-*`), not by
// process environment. BB's opencode2 provider puts a session rule `* allow` after the agent's own rules ("last match wins"), so the
// deny rules written in the lane agent files would lose. The permission hook in v2.ts re-applies them through agentDenies().

export const LANE_AGENT_PREFIX = "lane-"

export function isLaneAgent(agent: unknown): boolean {
  return typeof agent === "string" && agent.startsWith(LANE_AGENT_PREFIX)
}

export type PermissionRule = { action: string; resource: string; effect: string }

/** Glob where `*` is any characters (newlines too) and `?` one character; the whole text must match. */
export function globMatch(pattern: string, text: string, ignoreCase = false): boolean {
  const body = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[\\s\\S]*").replace(/\?/g, "[\\s\\S]")
  return new RegExp(`^${body}$`, ignoreCase ? "i" : "").test(text)
}

/** Last matching rule wins; true when it says deny for any of the resources. No match or ask/allow leaves OpenCode's own answer. */
export function agentDenies(rules: readonly PermissionRule[], action: string, resources: readonly string[]): boolean {
  return resources.some((resource) => {
    let effect = ""
    for (const rule of rules) {
      if (globMatch(rule.action, action) && globMatch(rule.resource, resource)) effect = rule.effect
    }
    return effect === "deny"
  })
}

// The hub and the machines behind it: a lane agent never needs a shell there. Same list as Lane Pilot's former OPENCODE_BASH_DENY and
// as hooks/guard_shell.py (strict); matched against the whole command line.
const PLUGIN_ADMIN = ["config", "token", "disable", "enable", "reload", "remove", "safe-mode"]
const HUB_HOSTS = [
  "ovh-main", "ovh-vps", "vechkasov-ovh", "selfystudio-work", "claude-dev-key", "10.8.0.1", "54.37.129.153", "rescue-vps",
  "10.8.1", "10.524289", "0x0a080001", "0x0A080001", "0xa080001", "0xA080001", "168296449", "012.010.0.1", "0x36258199",
  "908427673", "ffff:",
]
const REMOTE_SHELLS = ["ssh", "scp", "sftp", "rsync"]

export const HUB_SHELL_DENY: readonly string[] = [
  ...PLUGIN_ADMIN.map((sub) => `*bb plugin ${sub}*`),
  ...PLUGIN_ADMIN.map((sub) => `*plugin ${sub}*`),
  ...HUB_HOSTS.flatMap((host) => REMOTE_SHELLS.map((shell) => `*${shell} *${host}*`)),
  "*base64*|*sh*",
  "*base64*|*bash*",
]

/** Why a lane agent's shell command is refused, or "" when it may run. */
export function hubShellDenial(command: string): string {
  const hit = HUB_SHELL_DENY.find((pattern) => globMatch(pattern, command, true))
  if (!hit) return ""
  return (
    `[hub-guard] ${hit.replace(/^\*|\*$/g, "")} is not available to Lane Pilot agents: it can break the hub or BB's plugin runtime ` +
    "by mistake. Ask the owner to run it in their own terminal."
  )
}
