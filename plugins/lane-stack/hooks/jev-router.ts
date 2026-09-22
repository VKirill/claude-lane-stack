import type { On, PluginOptions, Register, SessionMessage } from 'claude-code'

import { buildJevRequest, parseJevResponse } from '../fast-jev/src/request.js'
import {
  ROUTE_QUESTIONS,
  ROUTE_TIMEOUT_MS,
  asSessionEffort,
  defaultRoute,
  parseRoute,
  routeEnabled,
  type Route,
  type SessionEffort,
} from './jev-route-core.js'

const TASK_CHARS = 1500

function lastUser(messages: readonly SessionMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]
    if (m.role !== 'user') continue
    if (m.toolResults && m.toolResults.length > 0) continue
    const text = m.text.trim()
    if (text) return text.length <= TASK_CHARS ? text : text.slice(0, TASK_CHARS)
  }
  return ''
}

async function getApiKey($: {
  env: { get: (name: string) => Promise<string | undefined> }
  settings: { read: () => Promise<Readonly<Record<string, unknown>>> }
}): Promise<string | undefined> {
  const fromEnv = await $.env.get('TYPESAFE_API_KEY')
  if (fromEnv) return fromEnv
  const settings = await $.settings.read()
  const env = settings['env']
  if (env && typeof env === 'object') {
    const value = (env as Record<string, unknown>)['TYPESAFE_API_KEY']
    if (typeof value === 'string' && value) return value
  }
  return undefined
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
  const apiKey = await getApiKey($)
  if (!apiKey) return defaultRoute(current)
  try {
    const request = buildJevRequest({ apiKey }, { task: prompt }, ROUTE_QUESTIONS)
    const response = await withTimeout(
      $.http.fetch(request.url, { method: request.method, headers: request.headers, body: request.body }),
      ROUTE_TIMEOUT_MS,
    )
    const parsed = parseJevResponse(response.status, response.ok, response.text)
    return parseRoute(parsed.answers, current)
  } catch {
    return defaultRoute(current)
  }
}

export const register: Register = (on: On, _options: PluginOptions) => {
  const byTurn = new Map<string, Route>()
  const byAgent = new Map<string, Route>()

  on('agent.spawn', async ($, e, next) => {
    if (e.fork) return next(e)
    const off = await $.env.get('LANE_JEV_EFFORT')
    if (!routeEnabled(off)) return next(e)
    const route = await classify($, e.prompt.trim().slice(0, TASK_CHARS), 'medium')
    if (route.reason === 'fail-open') return next(e)
    const result = await next({ ...e, model: route.subagent })
    if (result.agentId) byAgent.set(result.agentId, route)
    return result
  })

  on('turn.step', async function* ($, e, next) {
    const off = await $.env.get('LANE_JEV_EFFORT')
    if (!routeEnabled(off)) return yield* next(e)
    try {
      if (e.agentId) {
        const cached = byAgent.get(e.agentId)
        if (!cached || cached.effort === e.effort) return yield* next(e)
        return yield* next({ ...e, effort: cached.effort })
      }
      let route = byTurn.get(e.turnId)
      if (!route) {
        if (e.index !== 0) return yield* next(e)
        const messages = await $.session.messages()
        route = await classify($, lastUser(messages), asSessionEffort(e.effort))
        byTurn.set(e.turnId, route)
      }
      if (route.effort === e.effort) return yield* next(e)
      return yield* next({ ...e, effort: route.effort })
    } catch {
      return yield* next(e)
    }
  })
}
