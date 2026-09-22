export type Effort = 'low' | 'medium' | 'high'
export type SessionEffort = Effort | 'xhigh' | 'max'
export type Subagent = 'haiku' | 'sonnet'

export type Route = {
  effort: SessionEffort
  subagent: Subagent
  reason: string
}

export type PolicyInput = {
  tier: string
  effort: string
  risk: number
  tierConf: number
  effortConf: number
  current: SessionEffort
}

export const ROUTE_TIMEOUT_MS = 2500

export const ROUTE_QUESTIONS = {
  tier: {
    type: 'choice' as const,
    instructions: 'Classify the coding task.',
    criteria: {
      mechanical: 'rename, format, typo, boilerplate, one-line fix',
      standard: 'normal feature or bug with local scope',
      hard: 'architecture, concurrency, security, wide blast radius',
    },
  },
  effort: {
    type: 'choice' as const,
    instructions: 'Reasoning effort this turn needs.',
    criteria: {
      low: 'obvious, mechanical, follow an existing pattern',
      medium: 'normal implementation',
      high: 'must think carefully; many tradeoffs or failure modes',
    },
  },
  risk: {
    type: 'noul' as const,
    instructions:
      'Probability this change can cause data loss, a security issue, or a production outage.',
  },
}

const NOTCH: Record<string, number> = {
  low: 0,
  medium: 1,
  high: 2,
  xhigh: 2,
  max: 2,
}

export function routeEnabled(flag: string | undefined | null): boolean {
  const v = (flag ?? '1').trim().toLowerCase()
  return v !== '0' && v !== 'off' && v !== 'false' && v !== 'no'
}

export function asSessionEffort(value: unknown, fallback: SessionEffort = 'medium'): SessionEffort {
  if (value === 'low' || value === 'medium' || value === 'high' || value === 'xhigh' || value === 'max') {
    return value
  }
  return fallback
}

function asEffort(value: SessionEffort): Effort {
  return value === 'xhigh' || value === 'max' ? 'high' : value
}

export function applyPolicy(a: PolicyInput): Route {
  const current = asSessionEffort(a.current)
  if (a.risk >= 0.7) {
    return {
      effort: (NOTCH[current] ?? 0) >= 2 ? current : 'high',
      subagent: 'sonnet',
      reason: 'risk',
    }
  }
  if (a.tier === 'mechanical' && a.tierConf >= 0.6) {
    return { effort: 'low', subagent: 'haiku', reason: 'mechanical' }
  }
  if (a.tier === 'hard' && a.tierConf >= 0.3) {
    return { effort: 'high', subagent: 'sonnet', reason: 'hard' }
  }
  const wanted = asEffort(asSessionEffort(a.effort, current))
  const curN = NOTCH[current] ?? 1
  const wantN = NOTCH[wanted] ?? 1
  let effort: SessionEffort = current
  if (wantN > curN && a.effortConf >= 0.3) effort = wanted
  else if (wantN < curN && a.effortConf >= 0.6) effort = wanted
  return { effort, subagent: 'sonnet', reason: a.tier || 'standard' }
}

export function parseRoute(
  answers: Record<string, { choice?: unknown; confidence?: unknown; noul?: unknown }>,
  current: SessionEffort,
): Route {
  const tierA = answers.tier
  const effortA = answers.effort
  const riskA = answers.risk
  return applyPolicy({
    tier: typeof tierA?.choice === 'string' ? tierA.choice : 'standard',
    effort: typeof effortA?.choice === 'string' ? effortA.choice : current,
    risk: typeof riskA?.noul === 'number' && Number.isFinite(riskA.noul) ? riskA.noul : 0,
    tierConf: typeof tierA?.confidence === 'number' && Number.isFinite(tierA.confidence) ? tierA.confidence : 0,
    effortConf:
      typeof effortA?.confidence === 'number' && Number.isFinite(effortA.confidence) ? effortA.confidence : 0,
    current,
  })
}

export function currentEffortFromModelId(modelId: string): SessionEffort | null {
  const m = modelId.match(/-(low|medium|high|xhigh|max)(?:-fast)?$/)
  return m ? asSessionEffort(m[1], 'medium') : null
}

export function swapModelEffort(modelId: string, effort: SessionEffort): string {
  const m = modelId.match(/^(.*)-(low|medium|high|xhigh|max)(-fast)?$/)
  if (!m) return modelId
  if (m[2] === effort) return modelId
  return `${m[1]}-${asEffort(effort)}${m[3] ?? ''}`
}

export function defaultRoute(current: SessionEffort): Route {
  return { effort: current, subagent: 'sonnet', reason: 'fail-open' }
}

export function assertRoutePolicy(): void {
  const cases: Array<[PolicyInput, Pick<Route, 'effort' | 'subagent' | 'reason'>]> = [
    [
      { tier: 'mechanical', effort: 'low', risk: 0.1, tierConf: 0.8, effortConf: 0.8, current: 'medium' },
      { effort: 'low', subagent: 'haiku', reason: 'mechanical' },
    ],
    [
      { tier: 'hard', effort: 'high', risk: 0.2, tierConf: 0.5, effortConf: 0.5, current: 'medium' },
      { effort: 'high', subagent: 'sonnet', reason: 'hard' },
    ],
    [
      { tier: 'standard', effort: 'low', risk: 0.8, tierConf: 0.9, effortConf: 0.9, current: 'medium' },
      { effort: 'high', subagent: 'sonnet', reason: 'risk' },
    ],
    [
      { tier: 'standard', effort: 'low', risk: 0.8, tierConf: 0.9, effortConf: 0.9, current: 'xhigh' },
      { effort: 'xhigh', subagent: 'sonnet', reason: 'risk' },
    ],
    [
      { tier: 'standard', effort: 'high', risk: 0.1, tierConf: 0.5, effortConf: 0.4, current: 'medium' },
      { effort: 'high', subagent: 'sonnet', reason: 'standard' },
    ],
    [
      { tier: 'standard', effort: 'low', risk: 0.1, tierConf: 0.5, effortConf: 0.4, current: 'medium' },
      { effort: 'medium', subagent: 'sonnet', reason: 'standard' },
    ],
    [
      { tier: 'standard', effort: 'low', risk: 0.1, tierConf: 0.5, effortConf: 0.7, current: 'medium' },
      { effort: 'low', subagent: 'sonnet', reason: 'standard' },
    ],
  ]
  for (const [input, expected] of cases) {
    const got = applyPolicy(input)
    if (got.effort !== expected.effort || got.subagent !== expected.subagent || got.reason !== expected.reason) {
      throw new Error(`applyPolicy ${JSON.stringify(input)} => ${JSON.stringify(got)} expected ${JSON.stringify(expected)}`)
    }
  }
  if (swapModelEffort('cursor-grok-4.6-medium-fast', 'high') !== 'cursor-grok-4.6-high-fast') {
    throw new Error('swap medium-fast → high-fast')
  }
  if (swapModelEffort('ag/gemini-3.8-flash-medium', 'low') !== 'ag/gemini-3.8-flash-low') {
    throw new Error('swap gemini medium → low')
  }
  if (swapModelEffort('cursor-grok-4.6-xhigh-fast', 'xhigh') !== 'cursor-grok-4.6-xhigh-fast') {
    throw new Error('keep xhigh')
  }
  if (currentEffortFromModelId('gpt-5.6-sol-high') !== 'high') {
    throw new Error('parse sol-high')
  }
  if (swapModelEffort('claude-opus-5', 'high') !== 'claude-opus-5') {
    throw new Error('no suffix stays')
  }
}
