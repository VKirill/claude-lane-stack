// opencode-lane entry. OpenCode v2 loads the default export as a plugin definition ({ id, setup }); Plugin.define() from
// `@opencode/plugin` is an identity function, so the literal is used and nothing has to be resolved at load time. `server` is the
// v1 entry (hooks in v1.ts): v2 ignores it, OpenCode v1 (>= 1.18.29, still used by the lane-session CLI lanes with cursor-acp)
// ignores `setup`.
//
// Auto-compaction of a lane-writer session cannot be switched off from here (checked against OpenCode 2.1.2):
//   - an agent file has no compaction key (agent `request.settings.compaction` only picks "summary" or "native");
//   - the session `compaction` hook can supply a summary or let the model write one, it cannot cancel the compaction;
//   - the only switch is `compaction.auto: false` in a config, which applies to every session of the directory it is read for.
//     Lane Pilot can write it to the writer worktree's `.opencode/opencode.jsonc` (config is read per directory), not to the global
//     config. v1's OPENCODE_DISABLE_AUTOCOMPACT does not exist in v2; OPENCODE_CONFIG_CONTENT does, for a private `--standalone` server.
import { OpenCodeLanePlugin } from "./v1.ts"
import { laneSetup } from "./v2.ts"

export * from "./v1.ts"
export { laneSetup } from "./v2.ts"
export { LANE_AGENT_PREFIX, HUB_SHELL_DENY, agentDenies, hubShellDenial, isLaneAgent } from "./hub-guard.ts"
export { guardMcpV2 } from "./guard.ts"
export { ensureStickyContent, lastAssistantTextV2, toOcMessages } from "./messages.ts"

export const OpenCodeLaneDefinition = { id: "opencode-lane", setup: laneSetup }

export default { ...OpenCodeLaneDefinition, server: OpenCodeLanePlugin }
