# fast-jev-compaction provenance

- Source: https://github.com/tamaratran/fast-jev-compaction
- Revision: `e3f262a7f4d42bd8dd32ced30d26176f7cb545b0`
- Package version: `0.2.0`
- Synced: 2026-09-25
- License: MIT, retained in `LICENSE`.

`src/compact.ts`, `src/state.ts`, `src/types.ts`, and `src/request.ts`
are verbatim copies from this revision. Keep the algorithm in sync with
upstream; host-specific integration lives in `../hooks/fast-jev.ts` and
`../hooks/lane-mods.ts`.

Upstream fits the judging state into 25,000 estimated tokens and batches
questions into 30,000-token requests. Tool outputs become size/status notes
in that state, inputs may be clipped, and long conversation text is abridged
as necessary. This is intentionally a lossy judging view. The returned
transcript preserves user and assistant text; only tool calls/results are
removed or shortened according to Jev's decisions. The first and most recent
messages are pinned. Transport/validation failures and insufficient reduction
still fall back to the original event through our host adapter.

Do not install a second standalone compaction plugin alongside this module:
lane-stack already registers the `session.compact` handler.
