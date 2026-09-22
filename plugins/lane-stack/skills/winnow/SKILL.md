---
name: winnow
description: How to read winnow stubs in tool results. A block marked "[winnow] ... hidden" was judged unlikely to matter for the current task and replaced with a short summary plus a recall key; call winnow_recall to restore it. Use when a tool result contains "[winnow]" lines or when winnow_recall / winnow_stats tools are available.
---

# winnow

winnow sits between Claude Code's tools and your context. After `Read`, `Bash`, or `Grep` returns a large result, winnow splits it into blocks, asks a System One model (TypeSafe's Jev, or an LLM-backed adapter) one yes/no question per block ("is this block needed for the current task?"), and replaces the low-probability blocks with a stub.

## What a stub looks like

```
[winnow] Lines 41-188 (148 lines) hidden: judged unlikely to matter for the current task (relevance <= 0.22).
[winnow] Summary: Boilerplate license header and the argparse setup for flags that are not part of this task.
[winnow] Full text cached as key a1b2c3d4e5f6. Call winnow_recall(key="a1b2c3d4e5f6", start=41, end=188) if you need it.
```

## How to treat it

- The summary is written by a cheap model and preserves identifiers, paths, numbers and error text. Trust it for orientation, not for exact values.
- If the hidden lines might matter after all, call the `winnow_recall` tool with the key. Add `start` and `end` to fetch only part of the cached text. Do not re-run the original command just to see the hidden part; recall is cheaper and does not re-trigger side effects.
- Outputs that show an error are never pruned. If you see a stub, the judge believed the output was clean.
- Line numbers in a stub refer to the original file or output. Claude Code renumbers the rewritten result from 1, so the numbers you see in the margin of a pruned `Read` do not match the file; use the stub's range with `Read` `offset`/`limit` or `winnow_recall` to reach the original lines. `Edit` is unaffected because it matches on text, not line numbers.

## Tools

- `winnow_recall(key, start?, end?)`: return the cached full text for a key.
- `winnow_stats()`: tokens saved, outputs rewritten, and the regret rate (how often a pruned key was later recalled).
