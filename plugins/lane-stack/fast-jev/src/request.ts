import { estimateTokens } from './state.js';
import type { JevAnswer, JevQuestions, JevResponse, JevState } from './types.js';

export const SYSTEM_ONE_URL = 'https://api.typesafe.ai/v1/systemone';
export const DEFAULT_MODEL = 'jev-latest';

/**
 * Jev reads at most about 32k tokens of state plus the longest question and
 * answers 400 max_tokens_exceeded past it. A caller that hands over a whole
 * prompt (the router, the opencode hooks) gets its longest texts abridged,
 * head and tail kept, until the state fits with room for the questions.
 */
export const MAX_STATE_TOKENS = 28_000;

export function boundState(state: JevState, maxTokens = MAX_STATE_TOKENS): JevState {
  let copy = JSON.parse(JSON.stringify(state)) as unknown;
  for (let round = 0; round < 24; round++) {
    const tokens = estimateTokens(JSON.stringify(copy));
    if (tokens <= maxTokens) break;
    const keepRatio = Math.max(0.1, (maxTokens / tokens) * 0.95);
    if (typeof copy === 'string') {
      copy = abridge(copy, keepRatio);
      continue;
    }
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
    if (!longest) break;
    const target = longest as { holder: Record<string | number, unknown>; key: string | number };
    target.holder[target.key] = abridge(target.holder[target.key] as string, keepRatio);
  }
  return copy as JevState;
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

/** The HTTP request for one Jev call, for any fetch-like transport. */
export function buildJevRequest(
  params: {
    apiKey: string;
    model?: string;
    baseUrl?: string;
  },
  state: JevState,
  questions: JevQuestions,
): JevRequest {
  return {
    url: params.baseUrl ?? SYSTEM_ONE_URL,
    method: 'POST',
    headers: {
      authorization: `Bearer ${params.apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: params.model ?? DEFAULT_MODEL,
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
