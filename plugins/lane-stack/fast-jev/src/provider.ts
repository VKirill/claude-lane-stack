// The one TypeScript table of System One endpoints. Keep it in step with
// bin/jev_provider.py; tests/test_jev_provider.py compares the two.

export type JevProviderId = 'openlux' | 'typesafe';

export type JevProvider = {
  id: JevProviderId;
  url: string;
  model: string;
  keyName: string;
  /** Fixed headroom added to every timeout on this provider, in milliseconds. */
  timeoutPadMs: number;
};

export const JEV_PROVIDERS: Record<JevProviderId, JevProvider> = {
  openlux: {
    id: 'openlux',
    url: 'https://api.openlux.ai/v1/systemone',
    model: 'jev-1.13.0:stable',
    keyName: 'OPENLUX_API_KEY',
    timeoutPadMs: 1500,
  },
  typesafe: {
    id: 'typesafe',
    url: 'https://api.typesafe.ai/v1/systemone',
    model: 'jev-latest',
    keyName: 'TYPESAFE_API_KEY',
    timeoutPadMs: 0,
  },
};

export type JevKeys = Partial<Record<JevProviderId, string>>;

export type JevRoute = {
  provider: JevProvider;
  key: string;
};

/**
 * Picks the provider and its key. `forced` (JEV_PROVIDER) selects one and
 * returns null when that provider has no key. Otherwise OpenLux wins when its
 * key exists, then TypeSafe; with no key at all the result is null.
 */
export function chooseJevProvider(keys: JevKeys, forced?: string): JevRoute | null {
  const wanted = (forced ?? '').trim().toLowerCase();
  if (wanted === 'openlux' || wanted === 'typesafe') {
    const key = keys[wanted]?.trim() ?? '';
    return key ? { provider: JEV_PROVIDERS[wanted], key } : null;
  }
  for (const id of ['openlux', 'typesafe'] as const) {
    const key = keys[id]?.trim() ?? '';
    if (key) return { provider: JEV_PROVIDERS[id], key };
  }
  return null;
}

/** Reads the keys and JEV_PROVIDER through `read` (env first, then settings) and chooses a route. */
export async function resolveJevRoute(
  read: (name: string) => Promise<string | undefined>,
  typesafeKey = '',
): Promise<JevRoute | null> {
  const keys: JevKeys = {
    openlux: (await read('OPENLUX_API_KEY')) ?? '',
    typesafe: typesafeKey || (await read('TYPESAFE_API_KEY')) || (await read('JEV_API_KEY')) || '',
  };
  return chooseJevProvider(keys, await read('JEV_PROVIDER'));
}

/** A timeout with the provider's fixed headroom added. */
export function jevTimeoutMs(baseMs: number, provider: JevProvider): number {
  return baseMs + provider.timeoutPadMs;
}
