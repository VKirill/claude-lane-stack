import type { On, PluginOptions, Register } from 'claude-code'

import { jevTimeoutMs, resolveJevRoute, type JevRoute } from '../fast-jev/src/provider.js'
import { buildJevRequest, parseJevResponse } from '../fast-jev/src/request.js'
import {
  ROUTE_QUESTIONS,
  ROUTE_TIMEOUT_MS,
  claudeSessionEffort,
  defaultRoute,
  parseRoute,
  routeEnabled,
  type Route,
  type SessionEffort,
} from './jev-route-core.js'

const RAW_TASK_MARKER = /^--- RAW TASK YAML \(verbatim\) ---\r?$/m

function canonicalTask(text: string): string {
  const marker = RAW_TASK_MARKER.exec(text)
  return marker ? text.slice(marker.index + marker[0].length).trim() : text
}

async function getJevRoute($: {
  env: { get: (name: string) => Promise<string | undefined> }
  settings: { read: () => Promise<Readonly<Record<string, unknown>>> }
}): Promise<JevRoute | null> {
  // The engine accepts only a literal name in $.env.get, so each variable is read by name.
  const fromEnv: Record<string, string | undefined> = {
    OPENLUX_API_KEY: await $.env.get('OPENLUX_API_KEY'),
    TYPESAFE_API_KEY: await $.env.get('TYPESAFE_API_KEY'),
    JEV_API_KEY: await $.env.get('JEV_API_KEY'),
    JEV_PROVIDER: await $.env.get('JEV_PROVIDER'),
  }
  const read = async (name: string): Promise<string | undefined> => {
    if (fromEnv[name]) return fromEnv[name]
    const settings = await $.settings.read()
    const env = settings['env']
    if (env && typeof env === 'object') {
      const value = (env as Record<string, unknown>)[name]
      if (typeof value === 'string' && value) return value
    }
    return undefined
  }
  return resolveJevRoute(read)
}

async function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error('timeout')), ms)
      }),
    ])
  } finally {
    if (timer !== undefined) clearTimeout(timer)
  }
}

async function classify(
  $: {
    http: { fetch: (url: string, init?: { method?: string; headers?: Record<string, string>; body?: string }) => Promise<{ status: number; ok: boolean; text: string }> }
    env: { get: (name: string) => Promise<string | undefined> }
    settings: { read: () => Promise<Readonly<Record<string, unknown>>> }
  },
  prompt: string,
  current: SessionEffort,
): Promise<Route> {
  if (!prompt) return defaultRoute(current)
  const jev = await getJevRoute($)
  if (!jev) return defaultRoute(current)
  try {
    const request = buildJevRequest(
      { apiKey: jev.key, provider: jev.provider.id },
      { task: prompt },
      ROUTE_QUESTIONS,
    )
    const response = await withTimeout(
      $.http.fetch(request.url, { method: request.method, headers: request.headers, body: request.body }),
      jevTimeoutMs(ROUTE_TIMEOUT_MS, jev.provider),
    )
    const parsed = parseJevResponse(response.status, response.ok, response.text)
    return parseRoute(parsed.answers, current)
  } catch {
    return defaultRoute(current)
  }
}

// Routing picks a subagent's model and effort once, when a lane session spawns it. The session's own turns (the owner's
// messages) keep the effort the owner chose, and the owner's plain sessions are never routed (owner 2026-10-13).
// The engine accepts only a literal name in $.env.get, so each marker is read by name.
async function laneRouting($: { env: { get: (name: string) => Promise<string | undefined> } }): Promise<boolean> {
  if (!routeEnabled(await $.env.get('LANE_JEV_EFFORT'))) return false
  const markers = [
    await $.env.get('LANE_PILOT_AGENT_TYPE'),
    await $.env.get('LANE_PILOT_ROLE'),
    await $.env.get('LANE_STACK_SESSION'),
    await $.env.get('LANE_PROMPT_FILE'),
    await $.env.get('LANE_TASK_FILE'),
  ]
  return markers.some((value) => Boolean(value?.trim()))
}

export const register: Register = (on: On, _options: PluginOptions) => {
  const byAgent = new Map<string, Route>()

  on('agent.spawn', async ($, e, next) => {
    if (e.fork) return next(e)
    if (!(await laneRouting($))) return next(e)
    const route = await classify($, canonicalTask(e.prompt.trim()), 'medium')
    if (route.reason === 'fail-open') return next(e)
    const result = await next({ ...e, model: route.subagent })
    if (result.agentId) byAgent.set(result.agentId, route)
    return result
  })

  on('turn.step', async function* ($, e, next) {
    if (!(await laneRouting($))) return yield* next(e)
    try {
      const cached = e.agentId ? byAgent.get(e.agentId) : undefined
      if (!cached) return yield* next(e)
      const nextEffort = claudeSessionEffort(cached.effort)
      if (nextEffort === e.effort) return yield* next(e)
      return yield* next({ ...e, effort: nextEffort })
    } catch {
      return yield* next(e)
    }
  })
}
