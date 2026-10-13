import type { On, PluginOptions, Register, SessionMessage } from 'claude-code'

import { jevTimeoutMs, resolveJevRoute, type JevRoute } from '../fast-jev/src/provider.js'
import { buildJevRequest, parseJevResponse } from '../fast-jev/src/request.js'
import {
  ROUTE_QUESTIONS,
  ROUTE_TIMEOUT_MS,
  asSessionEffort,
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

function lastUser(messages: readonly SessionMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m.role !== 'user') continue
    if (m.toolResults && m.toolResults.length > 0) continue
    const text = m.text.trim()
    if (text) return canonicalTask(text)
  }
  return ''
}

async function getJevRoute($: {
  env: { get: (name: string) => Promise<string | undefined> }
  settings: { read: () => Promise<Readonly<Record<string, unknown>>> }
}): Promise<JevRoute | null> {
  const read = async (name: string): Promise<string | undefined> => {
    const fromEnv = await $.env.get(name)
    if (fromEnv) return fromEnv
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

// Routing runs only in a lane session (the owner's own sessions keep the effort they chose) and once, at the session's
// first turn, not on every message (owner 2026-10-13). A subagent is routed once at its spawn.
const LANE_MARKERS = ['LANE_PILOT_AGENT_TYPE', 'LANE_PILOT_ROLE', 'LANE_STACK_SESSION', 'LANE_PROMPT_FILE', 'LANE_TASK_FILE']

async function laneRouting($: { env: { get: (name: string) => Promise<string | undefined> } }): Promise<boolean> {
  if (!routeEnabled(await $.env.get('LANE_JEV_EFFORT'))) return false
  for (const name of LANE_MARKERS) if ((await $.env.get(name))?.trim()) return true
  return false
}

export const register: Register = (on: On, _options: PluginOptions) => {
  let sessionRoute: Route | undefined
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
      if (e.agentId) {
        const cached = byAgent.get(e.agentId)
        if (!cached) return yield* next(e)
        const nextEffort = claudeSessionEffort(cached.effort)
        if (nextEffort === e.effort) return yield* next(e)
        return yield* next({ ...e, effort: nextEffort })
      }
      let route = sessionRoute
      if (!route) {
        if (e.index !== 0) return yield* next(e)
        const messages = await $.session.messages()
        route = await classify($, lastUser(messages), asSessionEffort(e.effort))
        sessionRoute = route
      }
      const nextEffort = claudeSessionEffort(route.effort)
      if (nextEffort === e.effort) return yield* next(e)
      return yield* next({ ...e, effort: nextEffort })
    } catch {
      return yield* next(e)
    }
  })
}
