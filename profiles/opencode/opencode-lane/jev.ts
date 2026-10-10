import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { homedir } from "node:os"
import { laneLog } from "./log.ts"

/** A key from the environment, else from one secrets file; names are the accepted variable names. */
function keyFrom(envNames: string[], file: string, names: string[]): string {
  for (const name of envNames) {
    const value = (process.env[name] || "").trim()
    if (value) return value
  }
  try {
    const text = readFileSync(`${homedir()}/secrets/${file}`, "utf8")
    for (const line of text.split("\n")) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith("#")) continue
      const eq = trimmed.indexOf("=")
      if (eq < 0) continue
      if (!names.includes(trimmed.slice(0, eq))) continue
      return trimmed.slice(eq + 1).trim().replace(/^['"]|["']$/g, "")
    }
  } catch {
    /* no secrets file */
  }
  return ""
}

/** The keys this lane may use, per provider; the provider choice itself is in fast-jev's provider.ts. */
export function jevKeys(): { openlux: string; typesafe: string } {
  return {
    openlux: keyFrom(["OPENLUX_API_KEY"], "openlux.env", ["OPENLUX_API_KEY"]),
    typesafe: keyFrom(
      ["TYPESAFE_API_KEY", "JEV_API_KEY"],
      "typesafe.env",
      ["TYPESAFE_API_KEY", "JEV_API_KEY"],
    ),
  }
}

export function stackRoot(): string {
  if (process.env.LANE_STACK_ROOT) return process.env.LANE_STACK_ROOT
  try {
    const raw = JSON.parse(readFileSync(`${homedir()}/.agents/install.json`, "utf8"))
    if (typeof raw.source_repo === "string" && raw.source_repo) return raw.source_repo
  } catch {
    /* checkout path unknown */
  }
  return "/home/ubuntu/tools/claude-lane-stack"
}

export function extraJevEnabled(): boolean {
  const v = (process.env.LANE_OPENCODE_JEV ?? "1").trim().toLowerCase()
  return v !== "0" && v !== "off" && v !== "false" && v !== "no"
}

type JevAnswers = Record<string, { choice?: unknown; confidence?: unknown; noul?: unknown }>

const CACHE_MS = 15_000
const cache = new Map<string, { at: number; answers: JevAnswers }>()
const inflight = new Map<string, Promise<JevAnswers | null>>()

export function askCacheKey(state: unknown, questions: unknown): string {
  return createHash("sha256").update(JSON.stringify({ state, questions })).digest("hex").slice(0, 32)
}

export function clearAskCache(): void {
  cache.clear()
  inflight.clear()
}

export async function askJev(
  state: unknown,
  questions: unknown,
  timeoutMs = 2500,
): Promise<JevAnswers | null> {
  let providers: any
  try {
    providers = await import(`${stackRoot()}/plugins/lane-stack/fast-jev/src/provider.ts`)
  } catch (err) {
    laneLog({ mod: "jev", ok: false, ms: 0, err: String(err) })
    return null
  }
  const route = providers.chooseJevProvider(jevKeys(), process.env.JEV_PROVIDER)
  if (!route) return null
  const ck = askCacheKey({ provider: route.provider.id, state }, questions)
  const hit = cache.get(ck)
  if (hit && Date.now() - hit.at < CACHE_MS) {
    laneLog({ mod: "jev", ok: true, ms: 0, data: { cached: true } })
    return hit.answers
  }
  const pending = inflight.get(ck)
  if (pending) return pending
  const work = askJevUncached(route, state, questions, providers.jevTimeoutMs(timeoutMs, route.provider), ck)
  inflight.set(ck, work)
  try {
    return await work
  } finally {
    inflight.delete(ck)
  }
}

async function askJevUncached(
  route: { provider: { id: string }; key: string },
  state: unknown,
  questions: unknown,
  timeoutMs: number,
  ck: string,
): Promise<JevAnswers | null> {
  const started = Date.now()
  try {
    const request = await import(`${stackRoot()}/plugins/lane-stack/fast-jev/src/request.ts`)
    const built = request.buildJevRequest(
      { apiKey: route.key, provider: route.provider.id },
      state,
      questions,
    )
    const response = await fetch(built.url, {
      method: built.method,
      headers: built.headers,
      body: built.body,
      signal: AbortSignal.timeout(timeoutMs),
    })
    const parsed = request.parseJevResponse(response.status, response.ok, await response.text())
    const answers = parsed.answers as JevAnswers
    cache.set(ck, { at: Date.now(), answers })
    laneLog({
      mod: "jev",
      ok: true,
      ms: Date.now() - started,
      data: {
        cached: false,
        jev_in: parsed.usage?.input_tokens,
        jev_out: parsed.usage?.output_tokens,
      },
    })
    return answers
  } catch (err) {
    laneLog({ mod: "jev", ok: false, ms: Date.now() - started, err: String(err) })
    return null
  }
}

export function choiceOf(
  answers: Record<string, { choice?: unknown; confidence?: unknown }> | null,
  key: string,
  allowed: Set<string>,
  fallback: string,
): { choice: string; conf: number } {
  const raw = answers?.[key]
  const choice = typeof raw?.choice === "string" ? raw.choice : fallback
  const conf = typeof raw?.confidence === "number" && Number.isFinite(raw.confidence) ? raw.confidence : 0
  if (!allowed.has(choice)) return { choice: fallback, conf: 0 }
  return { choice, conf }
}
