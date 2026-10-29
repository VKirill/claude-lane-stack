import { JEV_PROVIDERS, type JevProviderId } from './provider.js';
import { estimateTokens } from './state.js';
import type { JevAnswer, JevQuestions, JevResponse, JevState } from './types.js';

/**
 * Jev reads at most about 32k tokens of state plus the longest question and
 * answers 400 max_tokens_exceeded past it. A caller that hands over a whole
 * prompt (the router, the opencode hooks) gets its longest texts abridged,
 * head and tail kept, until the state fits with room for the questions.
 */
export const MAX_STATE_TOKENS = 28_000;

function abridgeLongest(copy: unknown, maxTokens: number, tokens: number): boolean {
  const keepRatio = Math.max(0.1, (maxTokens / tokens) * 0.95);
  if (typeof copy === 'string') return false;
  let longest: { holder: Record<string | number, unknown>; key: string | number; size: number } | null = null;
  const visit = (value: unknown, holder: Record<string | number, unknown> | null, key: string | number | null): void => {
    if (typeof value === 'string') {
      if (holder && key !== null && (!longest || value.length > longest.size)) longest = { holder, key, size: value.length };
    } else if (Array.isArray(value)) {
      value.forEach((item, index) => visit(item, value as unknown as Record<number, unknown>, index));
    } else if (value && typeof value === 'object') {
      for (const [name, item] of Object.entries(value)) visit(item, value as Record<string, unknown>, name);
    }
  };
  visit(copy, null, null);
  if (!longest) return false;
  const target = longest as { holder: Record<string | number, unknown>; key: string | number; size: number };
  const next = abridge(target.holder[target.key] as string, keepRatio);
  if (next === target.holder[target.key]) return false;
  target.holder[target.key] = next;
  return true;
}

function dropWidestArray(copy: unknown): boolean {
  let best: unknown[] | null = null;
  let bestSize = 0;
  const visit = (value: unknown): void => {
    if (Array.isArray(value)) {
      if (value.length > 1) {
        const size = JSON.stringify(value).length;
        if (size > bestSize) {
          best = value;
          bestSize = size;
        }
      }
      value.forEach(visit);
    } else if (value && typeof value === 'object') {
      for (const item of Object.values(value)) visit(item);
    }
  };
  visit(copy);
  if (!best) return false;
  const target = best as unknown[];
  target.splice(0, Math.max(1, Math.floor(target.length / 2)));
  return true;
}

export function boundState(state: JevState, maxTokens = MAX_STATE_TOKENS): JevState {
  let copy = JSON.parse(JSON.stringify(state)) as unknown;
  for (let round = 0; round < 24; round++) {
    const tokens = estimateTokens(JSON.stringify(copy));
    if (tokens <= maxTokens) return copy as JevState;
    if (typeof copy === 'string') {
      const next = abridge(copy, Math.max(0.1, (maxTokens / tokens) * 0.95));
      if (next === copy) break;
      copy = next;
      continue;
    }
    if (!abridgeLongest(copy, maxTokens, tokens)) break;
  }
  // A wide array of long strings survives one-string abridgement. Drop oldest items until it fits.
  for (let round = 0; round < 32; round++) {
    const tokens = estimateTokens(JSON.stringify(copy));
    if (tokens <= maxTokens) return copy as JevState;
    if (!dropWidestArray(copy)) break;
  }
  const tokens = estimateTokens(JSON.stringify(copy));
  if (tokens <= maxTokens) return copy as JevState;
  throw new Error(`Jev state exceeds ${maxTokens} tokens (${tokens})`);
}

function abridge(text: string, keepRatio: number): string {
  const keep = Math.max(400, Math.floor(text.length * keepRatio));
  if (keep >= text.length) return text;
  const head = Math.floor(keep * 0.7);
  return `${text.slice(0, head)}\n[… ${text.length - keep} chars omitted …]\n${text.slice(text.length - (keep - head))}`;
}

export interface JevRequest {
  url: string;
  method: 'POST';
  headers: Record<string, string>;
  body: string;
}

/**
 * The HTTP request for one Jev call, for any fetch-like transport. The URL and
 * model come from the provider table (TypeSafe when `provider` is omitted);
 * `model` and `baseUrl` override them.
 */
export function buildJevRequest(
  params: {
    apiKey: string;
    provider?: JevProviderId;
    model?: string;
    baseUrl?: string;
  },
  state: JevState,
  questions: JevQuestions,
): JevRequest {
  const provider = JEV_PROVIDERS[params.provider ?? 'typesafe'];
  return {
    url: params.baseUrl ?? provider.url,
    method: 'POST',
    headers: {
      authorization: `Bearer ${params.apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: params.model ?? provider.model,
      state: boundState(state),
      questions,
    }),
  };
}

/** Validates a Jev response body; throws on anything but an `answers` object. */
export function parseJevResponse(
  status: number,
  ok: boolean,
  text: string,
): JevResponse {
  if (!ok) {
    throw new Error(`Jev request failed (${status}): ${text.slice(0, 200)}`);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error('Jev returned malformed JSON');
  }
  if (
    parsed === null ||
    typeof parsed !== 'object' ||
    !('answers' in parsed) ||
    parsed.answers === null ||
    typeof parsed.answers !== 'object'
  ) {
    throw new Error('Jev response is missing answers');
  }
  return parsed as JevResponse;
}

/** The `noul` probability of one answer; throws when it is not there. */
export function noulAnswer(
  answers: Record<string, JevAnswer>,
  name: string,
): number {
  const answer = answers[name];
  if (
    !answer ||
    !('noul' in answer) ||
    typeof answer.noul !== 'number' ||
    !Number.isFinite(answer.noul)
  ) {
    throw new Error(`Invalid Jev answer for ${name}`);
  }
  return answer.noul;
}
