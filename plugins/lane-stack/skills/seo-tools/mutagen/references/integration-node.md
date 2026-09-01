# Node.js / TypeScript integration

Reference implementation patterns. Defaults from [recommended-defaults.md](recommended-defaults.md).

## Dependencies

```json
// package.json (excerpts)
{
  "dependencies": {
    "p-retry": "*"   // retry with backoff
  }
}
```

`fetch` is built into Node 24. `p-retry` provides exponential backoff with jitter. For Pydantic-equivalent runtime validation, use `zod` (separate skill).

## Env var

```ts
const API_KEY = process.env.MUTAGEN_API_KEY;
if (!API_KEY) throw new Error("MUTAGEN_API_KEY not set");
const BASE_URL = "http://api.mutagen.ru/json";
```

NEVER hardcode `API_KEY`. Load from env at startup.

## Types

```ts
// types.ts
export type CheckKeyStatus = "created" | "processed" | "completed" | "rejected" | "error";
export type ParserMassStatus = "stop" | "process" | "finish" | "error";

export interface CheckKeyPending {
  task_id: number;
  status: Exclude<CheckKeyStatus, "completed">;
}

export interface CheckKeyCompleted {
  status: "completed";
  key: string;
  strong: number;
  wordstat: number;
  tails: number;
  direct: { spec: number; first: number; garant: number };
  vital: string | boolean;
  vital_site: string;
}

export type CheckKeyResponse = CheckKeyPending | CheckKeyCompleted;

export interface ParserMassNewResponse { status: "stop" | "process"; id: number; }
export interface ParserMassIdResponse {
  id: number;
  name: string;
  parser: string;
  region_id: string;
  count: number;
  time: number;
  status: ParserMassStatus;
  data?: unknown;
}

export type Region =
  | "yandex_ru" | "yandex_msk" | "yandex_spb" | "yandex_minsk"
  | "yandex_nsk" | "yandex_ekb" | "yandex_rostov" | "yandex_kazan"
  | "yandex_nn";
```

## Errors

```ts
export class MutagenTransientError extends Error {}
export class MutagenTerminalError extends Error {}
```

Distinguishing class is important: `p-retry` retries `MutagenTransientError` only, never `MutagenTerminalError`.

## Client skeleton

```ts
import pRetry, { AbortError } from "p-retry";
import { setTimeout as sleep } from "node:timers/promises";

export class MutagenClient {
  constructor(
    private readonly apiKey: string,
    private readonly timeoutMs = 30_000,
  ) {}

  private async call<T>(
    method: string,
    params: Record<string, unknown> = {},
    { post = false }: { post?: boolean } = {},
  ): Promise<T> {
    const url = `${BASE_URL}/${this.apiKey}/${method}/`;
    const init: RequestInit = {
      headers: { "Content-Type": "application/json; charset=utf-8" },
      signal: AbortSignal.timeout(this.timeoutMs),
    };

    return await pRetry(async () => {
      let resp: Response;
      try {
        if (post) {
          resp = await fetch(url, { ...init, method: "POST", body: JSON.stringify(params) });
        } else {
          const usp = new URLSearchParams();
          for (const [k, v] of Object.entries(params)) usp.set(k, String(v));
          const q = usp.toString();
          resp = await fetch(q ? `${url}?${q}` : url, init);
        }
      } catch (e) {
        // Network error
        throw new MutagenTransientError((e as Error).message);
      }
      if (resp.status >= 500) {
        throw new MutagenTransientError(`HTTP ${resp.status}`);
      }
      if (resp.status >= 400) {
        // 4xx is terminal — do not retry
        throw new AbortError(new MutagenTerminalError(`HTTP ${resp.status}`));
      }
      return (await resp.json()) as T;
    }, {
      retries: 5,
      minTimeout: 500,
      maxTimeout: 30_000,
      factor: 2,
      randomize: true,
    });
  }

  // Free methods
  balance() { return this.call<{ balance: number }>("mutagen.balance"); }
  progects() { return this.call<Array<{ progect_id: number; name: string }>>("mutagen.progects"); }
  progectKeywords(progect_id: number) {
    return this.call<Array<{ keyword: string; claster_id: number }>>(
      "mutagen.progect.keywords",
      { progect_id },
    );
  }

  // check_key
  checkKeyNew(key: string) {
    return this.call<{ task_id: number; status: CheckKeyStatus }>(
      "mutagen.check_key.new", { key },
    );
  }
  checkKeyGet(task_id: number) {
    return this.call<CheckKeyResponse>("mutagen.check_key.get", { task_id });
  }

  // parser.mass
  parserMassNew(params: {
    keys_list: string[];
    name: string;
    parser: string;
    region_id?: string;
  }) {
    return this.call<ParserMassNewResponse>(
      "mutagen.parser.mass.new", params, { post: true },
    );
  }
  parserMassId(mass_id: number) {
    return this.call<ParserMassIdResponse>("mutagen.parser.mass.id", { mass_id });
  }
  parserMassList() {
    return this.call<ParserMassIdResponse[]>("mutagen.parser.mass.list");
  }

  // serp.report
  serpReport<T = unknown>(params: {
    region: Region;
    report: string;
    keyword?: string;
    keywords?: string;
    domain?: string;
    domain_with_subdomains?: string;
    page?: string;
    filter?: Array<Record<string, unknown>>;
    sort?: string;
    limit?: number;
    count?: 1;
  }) {
    const usePost =
      (params.keywords && params.keywords.length > 50_000) ||
      (params.filter && params.filter.length > 10);
    return this.call<T>("mutagen.serp.report", params, { post: !!usePost });
  }
}
```

## Polling helpers — `check_key`

```ts
export interface TaskStore {
  get(key: string): Promise<number | null>;
  put(key: string, task_id: number): Promise<void>;
}

export async function checkKeyWithPolling(
  client: MutagenClient,
  key: string,
  store: TaskStore,
  {
    initialDelay = 2_000,
    cap = 30_000,
    maxAttempts = 60,
  }: { initialDelay?: number; cap?: number; maxAttempts?: number } = {},
): Promise<CheckKeyCompleted> {
  // Idempotency lookup
  let task_id = await store.get(key);
  if (task_id === null) {
    const submit = await client.checkKeyNew(key);
    task_id = submit.task_id;
    await store.put(key, task_id);
  }

  let delay = initialDelay;
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await client.checkKeyGet(task_id);
    if (resp.status === "completed") return resp as CheckKeyCompleted;
    if (resp.status === "rejected" || resp.status === "error") {
      throw new MutagenTerminalError(
        `check_key terminal state ${resp.status} for task_id=${task_id}`,
      );
    }
    await sleep(Math.min(delay, cap));
    delay = Math.min(delay * 1.5, cap);
  }
  throw new MutagenTerminalError(`check_key timeout for task_id=${task_id}`);
}
```

## Polling helpers — `parser.mass.id`

```ts
export async function parserMassWithPolling(
  client: MutagenClient,
  mass_id: number,
  {
    initialDelay = 5_000,
    cap = 60_000,
    maxAttempts = 120,
  }: { initialDelay?: number; cap?: number; maxAttempts?: number } = {},
): Promise<unknown> {
  let delay = initialDelay;
  for (let i = 0; i < maxAttempts; i++) {
    const resp = await client.parserMassId(mass_id);
    if (resp.status === "finish") return resp.data;
    if (resp.status === "error") {
      throw new MutagenTerminalError(`parser.mass terminal for mass_id=${mass_id}`);
    }
    await sleep(Math.min(delay, cap));
    delay = Math.min(delay * 1.5, cap);
  }
  throw new MutagenTerminalError(`parser.mass timeout for mass_id=${mass_id}`);
}
```

## Normalize + dedup helper

```ts
export function normalizeKeys(raw: readonly string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (let k of raw) {
    k = k.trim().split(/\s+/).join(" ").toLocaleLowerCase("ru-RU");
    if (!k || seen.has(k)) continue;
    seen.add(k);
    out.push(k);
  }
  return out;
}
```

## Balance gating helper

```ts
export class InsufficientFunds extends Error {}

export async function gateBalance(
  client: MutagenClient,
  expectedCost: number,
  safety = 2.0,
): Promise<void> {
  const { balance } = await client.balance();
  if (balance < expectedCost * safety) {
    throw new InsufficientFunds(
      `balance=${balance} < expected=${expectedCost} × safety=${safety}`,
    );
  }
}
```

## Usage examples

### One-key competition check

```ts
async function main() {
  const client = new MutagenClient(API_KEY!);
  await gateBalance(client, 1.0);
  const store = makeRedisTaskStore(); // your impl
  const result = await checkKeyWithPolling(client, "купить квадроцикл", store);
  console.log(result);
}
```

### Mass-parse frequency

```ts
async function parseFrequencies(client: MutagenClient, rawKeys: string[]) {
  const keys = normalizeKeys(rawKeys);
  const expected = keys.length * 0.05; // rate from config
  await gateBalance(client, expected, 2.0);

  const submit = await client.parserMassNew({
    keys_list: keys,
    name: "semantics-2026-05-q1",
    parser: "wordstat_qso",
    region_id: "213",
  });
  // PERSIST mass_id BEFORE first poll
  await myDb.saveMassId(submit.id, keys.length);
  return await parserMassWithPolling(client, submit.id);
}
```

### SERP report — probe then pull

```ts
async function organicKeywords(client: MutagenClient, domain: string) {
  const filter = [
    { column: "region_wsqso", filter_type: "gr_or_eq", val: 100 },
    { column: "words",        filter_type: "less_or_eq", val: 7 },
  ];
  const probe = await client.serpReport<{ count: number }>({
    region: "yandex_msk",
    report: "report_keywords_organic",
    domain, filter, count: 1,
  });
  if (probe.count > 5000) {
    throw new Error(`refuse full pull: ${probe.count} rows`);
  }
  return client.serpReport<Array<Record<string, unknown>>>({
    region: "yandex_msk",
    report: "report_keywords_organic",
    domain,
    filter,
    limit: Math.min(probe.count, 5000),
    sort: "-region_wsqso",
  });
}
```

## Testing — using a fake fetch

```ts
import { test, expect, vi } from "vitest";

test("check_key polling completes", async () => {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    calls.push(url);
    if (url.includes("check_key.new")) {
      return new Response(JSON.stringify({ task_id: 1, status: "created" }), { status: 200 });
    }
    if (calls.filter(u => u.includes("check_key.get")).length === 1) {
      return new Response(JSON.stringify({ task_id: 1, status: "processed" }), { status: 200 });
    }
    return new Response(JSON.stringify({
      status: "completed", key: "t", strong: 5, wordstat: 100, tails: 1000,
      direct: { spec: 1, first: 0.5, garant: 0.5 }, vital: "", vital_site: "",
    }), { status: 200 });
  }));

  const client = new MutagenClient("test-key");
  const store = makeMemoryStore();
  const result = await checkKeyWithPolling(client, "t", store, {
    initialDelay: 1, maxAttempts: 5,
  });
  expect(result.strong).toBe(5);
});
```

## Things NOT to do

See [wrong-vs-right.md](wrong-vs-right.md) for the full catalogue. Key:

- Don't loop `parserGet` — batch with `parserMassNew`.
- Don't tight-loop `checkKeyGet` — use exp backoff via `setTimeout`.
- Don't omit balance pre-check.
- Don't log full URL — key is in path.
- Don't hardcode `API_KEY`.
