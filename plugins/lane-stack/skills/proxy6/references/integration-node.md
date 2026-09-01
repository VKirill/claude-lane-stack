# Node.js / TypeScript integration — fetch + p-retry + bottleneck

Reference implementation for a Node 24 async client.

## Dependencies

```json
{
  "dependencies": {
    "bottleneck": "^2.19.5",
    "p-retry": "^6.2.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "nock": "^14.0.0",
    "vitest": "^2"
  }
}
```

`fetch` is built into Node 24 — no extra HTTP client needed. Axios is an alternative if you want interceptors.

## File layout

```
src/proxy6/
├── index.ts        // public exports
├── client.ts       // Proxy6Client (fetch + limiter + retry)
├── types.ts        // shapes for envelopes and methods
├── errors.ts       // typed errors per error_id
└── limiter.ts      // shared Bottleneck instance
```

## Types

```ts
// types.ts

export type Version = "3" | "4" | "5" | "6";

export interface ErrorEnvelope {
  status: "no";
  error_id: number;
  error: string;
}

export interface SuccessEnvelope {
  status: "yes";
  user_id: string;
  balance: string;
  currency: "RUB" | "USD";
}

export interface Proxy {
  id: string;
  version: Version;
  ip: string;
  host: string;
  port: string;
  user: string;
  pass: string;
  type: "http" | "socks" | "auto";
  country: string;
  date: string;
  date_end: string;
  unixtime: number;
  unixtime_end: number;
  descr: string;
  active: "0" | "1";
}

export interface GetPriceResponse extends SuccessEnvelope {
  price?: string;
  price_single?: string;
  period?: number;
  count?: number;
}

export interface GetCountResponse extends SuccessEnvelope { count: string; }
export interface GetCountryResponse extends SuccessEnvelope { list: string[]; }

export interface GetProxyResponse extends SuccessEnvelope {
  list_count: number;
  list: Record<string, Proxy>;
}

export interface BuyResponse extends SuccessEnvelope {
  order_id: string;
  count: number;
  price: string;
  price_single: string;
  period: number;
  country: string;
  list: Record<string, Proxy>;
}

export interface ProlongResponse extends SuccessEnvelope {
  order_id: string;
  price: string;
  price_single?: string;  // ABSENT on mixed-version batches
  period: number;
  count: number;
  list: Record<string, { date_end: string; unixtime_end: number }>;
}

export interface SetDescrResponse extends SuccessEnvelope { count: number; }
export interface DeleteResponse extends SuccessEnvelope { count: number; }
export interface CheckResponse extends SuccessEnvelope {
  proxy_id: string;
  proxy_status: boolean;
}
```

## Errors

```ts
// errors.ts

export class Proxy6RetryableError extends Error {}
export class Proxy6FatalError extends Error {
  constructor(public readonly errorId: number, message: string) {
    super(`error_id=${errorId}: ${message}`);
  }
}
export class AuthError extends Proxy6FatalError {}
export class BadRequest extends Proxy6FatalError {}
export class OutOfStock extends Proxy6FatalError {}
export class InsufficientFunds extends Proxy6FatalError {}
export class NotFound extends Proxy6FatalError {}
export class InvalidPrice extends Proxy6FatalError {}

const FATAL: Record<number, new (id: number, m: string) => Proxy6FatalError> = {
  100: AuthError, 105: AuthError,
  110: BadRequest, 200: BadRequest, 210: BadRequest, 220: BadRequest,
  230: BadRequest, 240: BadRequest, 250: BadRequest, 260: BadRequest,
  270: BadRequest, 280: BadRequest,
  300: OutOfStock,
  400: InsufficientFunds,
  404: NotFound,
  410: InvalidPrice,
};

export function raiseForError(errorId: number, message: string): never {
  if (errorId === 30) throw new Proxy6RetryableError(`unknown server error: ${message}`);
  const Cls = FATAL[errorId] ?? Proxy6FatalError;
  throw new Cls(errorId, message);
}
```

## Limiter

```ts
// limiter.ts
import Bottleneck from "bottleneck";

export function makeLimiter(): Bottleneck {
  return new Bottleneck({
    reservoir: 3,
    reservoirRefreshAmount: 3,
    reservoirRefreshInterval: 1_000,
    maxConcurrent: 2,
    minTime: 340,
  });
}
```

One instance per process per api_key. For multi-process coordination use Bottleneck's IORedis store.

## Client

```ts
// client.ts
import Bottleneck from "bottleneck";
import pRetry, { AbortError } from "p-retry";
import { makeLimiter } from "./limiter.js";
import { Proxy6RetryableError, Proxy6FatalError, raiseForError } from "./errors.js";
import type {
  GetPriceResponse, GetCountResponse, GetCountryResponse, GetProxyResponse,
  BuyResponse, ProlongResponse, SetDescrResponse, DeleteResponse, CheckResponse,
  Version,
} from "./types.js";

export interface Proxy6ClientOptions {
  apiKey?: string;          // defaults to process.env.PROXY6_API_KEY
  timeoutMs?: number;       // default 10_000
  limiter?: Bottleneck;
}

export class Proxy6Client {
  static readonly BASE = "https://px6.link/api";
  private readonly apiKey: string;
  private readonly timeoutMs: number;
  private readonly limiter: Bottleneck;

  constructor(opts: Proxy6ClientOptions = {}) {
    const key = opts.apiKey ?? process.env.PROXY6_API_KEY;
    if (!key) throw new Error("PROXY6_API_KEY not set");
    this.apiKey = key;
    this.timeoutMs = opts.timeoutMs ?? 10_000;
    this.limiter = opts.limiter ?? makeLimiter();
  }

  private async call<T>(method: string, params: Record<string, string | number>): Promise<T> {
    const url = new URL(`${Proxy6Client.BASE}/${this.apiKey}/${method}/`);
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));

    return pRetry(
      async () => {
        const res = await this.limiter.schedule(() =>
          fetch(url, { signal: AbortSignal.timeout(this.timeoutMs) }),
        );
        if (res.status === 429) throw new Proxy6RetryableError("HTTP 429");
        if (res.status >= 500) throw new Proxy6RetryableError(`HTTP ${res.status}`);
        const data = (await res.json()) as { status: string; error_id?: number; error?: string };
        if (data.status === "no") {
          try {
            raiseForError(data.error_id ?? 30, data.error ?? "");
          } catch (e) {
            if (e instanceof Proxy6RetryableError) throw e;
            throw new AbortError(e as Error);
          }
        }
        return data as T;
      },
      { retries: 5, factor: 2, minTimeout: 500, maxTimeout: 30_000, randomize: true },
    );
  }

  // --- methods ---

  getprice(count: number, period: number, version: Version): Promise<GetPriceResponse> {
    return this.call("getprice", { count, period, version });
  }
  getcount(country: string, version: Version): Promise<GetCountResponse> {
    return this.call("getcount", { country, version });
  }
  getcountry(version: Version): Promise<GetCountryResponse> {
    return this.call("getcountry", { version });
  }
  getproxy(opts: { state?: string; descr?: string; page?: number; limit?: number } = {}): Promise<GetProxyResponse> {
    const p: Record<string, string | number> = {
      state: opts.state ?? "all",
      page: opts.page ?? 1,
      limit: opts.limit ?? 1000,
    };
    if (opts.descr) p.descr = opts.descr;
    return this.call("getproxy", p);
  }
  async buy(opts: {
    count: number; period: number; country: string; version: Version;
    descr: string;             // REQUIRED by convention
    auto_prolong?: boolean;    // default false
    type?: "http" | "socks" | "auto";
  }): Promise<BuyResponse> {
    if (!opts.descr) throw new Error("descr is required by convention");
    const p: Record<string, string | number> = {
      count: opts.count, period: opts.period, country: opts.country,
      version: opts.version, descr: opts.descr,
    };
    if (opts.auto_prolong) p.auto_prolong = "";
    if (opts.type) p.type = opts.type;
    return this.call("buy", p);
  }
  prolong(period: number, ids: string[]): Promise<ProlongResponse> {
    return this.call("prolong", { period, ids: ids.join(",") });
  }
  async setdescr(opts: { newDescr: string; old?: string; ids?: string[] }): Promise<SetDescrResponse> {
    if (!opts.old && !opts.ids) throw new Error("setdescr requires old or ids");
    if (opts.newDescr.length > 50) throw new Error("descr max 50 chars");
    const p: Record<string, string | number> = { new: opts.newDescr };
    if (opts.old) p.old = opts.old;
    if (opts.ids) p.ids = opts.ids.join(",");
    return this.call("setdescr", p);
  }
  async delete(opts: { ids?: string[]; descr?: string; confirmDryRun?: boolean }): Promise<DeleteResponse> {
    if (!opts.ids && !opts.descr) throw new Error("delete requires ids or descr");
    if (opts.descr && !opts.ids && opts.confirmDryRun !== false) {
      throw new Error(
        "Refusing delete-by-descr without ids. Call getproxy({descr}) first, then delete({ids:[...]}); " +
        "or pass confirmDryRun:false to override.",
      );
    }
    const p: Record<string, string | number> = {};
    if (opts.ids) p.ids = opts.ids.join(",");
    else if (opts.descr) p.descr = opts.descr;
    return this.call("delete", p);
  }
  check(opts: { proxyId?: string; proxy?: string }): Promise<CheckResponse> {
    if (!opts.proxyId && !opts.proxy) throw new Error("check requires proxyId or proxy");
    return this.call("check", opts.proxyId ? { ids: opts.proxyId } : { proxy: opts.proxy! });
  }
  ipauth(ip: string[] | "delete"): Promise<unknown> {
    const ipParam = ip === "delete" ? "delete" : ip.join(",");
    return this.call("ipauth", { ip: ipParam });
  }
}
```

## Usage

```ts
import { Proxy6Client, InsufficientFunds } from "./proxy6/index.js";

const client = new Proxy6Client(); // reads PROXY6_API_KEY

try {
  const price = await client.getprice(10, 30, "4");
  const stock = await client.getcount("ru", "4");
  if (Number(stock.count) < 10) throw new Error("not enough stock");
  if (Number(price.balance) < Number(price.price) * 1.1) throw new Error("balance too low");

  const order = await client.buy({
    count: 10, period: 30, country: "ru", version: "4",
    descr: "prod:scraper-A:reviews",
  });
  console.log(`Bought ${order.count}, order_id=${order.order_id}`);
} catch (e) {
  if (e instanceof InsufficientFunds) {
    // alert ops, do not retry
  }
  throw e;
}
```

## Testing with nock / undici MockAgent

```ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import nock from "nock";
import { Proxy6Client, InsufficientFunds } from "./client.js";

describe("Proxy6Client", () => {
  beforeAll(() => nock.disableNetConnect());
  afterAll(() => nock.enableNetConnect());

  it("throws InsufficientFunds on error_id 400", async () => {
    nock("https://px6.link")
      .get(/\/api\/k\/buy\/.*/)
      .reply(200, { status: "no", error_id: 400, error: "Error no money" });
    const client = new Proxy6Client({ apiKey: "k" });
    await expect(
      client.buy({ count: 1, period: 1, country: "ru", version: "4", descr: "t" }),
    ).rejects.toBeInstanceOf(InsufficientFunds);
  });
});
```

## Secrets

Load `PROXY6_API_KEY` from `process.env`. NEVER hardcode. NEVER log the constructed URL — log `method` + sanitised params only. Add `PROXY6_API_KEY` to `.gitignore`'d `.env.local`.
