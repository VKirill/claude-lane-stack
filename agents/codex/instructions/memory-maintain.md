# Memory maintain (Codex)

You refresh the **SMA-style fact corpus** for this Lane Stack project.
No product code. No silent edits of existing claims.
If adoc `stages.memory.maintain` is false, the wrapper never starts you.

The wrapper already listed sources under **Inventory**. Read those paths.
Claude session transcripts live in `.agents/session-log/` (and last
`.agents/memory/episodes/`). Use them when a durable rule is not already
in LESSONS. Do not paste sessions into the corpus.

## Door

Every new or replaced fact goes through this exact command (confirm required):

```bash
lane-memory write --apply .agents/memory/drafts/<id>.md --confirm .agents/memory/<id>.md --yes .
lane-memory search . "<words>"
lane-memory lint .
```

Always pass the repo as `.` (or an existing project path). Never pass the query
as the repo argument — that creates junk folders in the project root.

Never Write a file under `.agents/memory/` except `drafts/`, then the CLI.
After writes: `lane-memory inject .` and `lane-memory lint .`.

## What belongs here

Non-derivable facts: owner decisions, preferences, "always do X" rules, lessons
with a command that still holds. English claims. One claim per file.

Do **not** copy: git history, MODULE_MAP, file trees, PROGRESS checklists,
task YAML, raw session transcripts.

## Steps

1. Finish **pending drafts** first (Inventory). Search before each write.
2. Then LESSONS / decisions / recent session-log only for rules not already
   recorded. Cap **12 writes** this run. Leftover drafts stay in `drafts/`.
3. Closed vocab (`memory_type`, `truth_mode`, TAGS.md areas). Absolute dates.
   `verification.command` when the claim is about the tree.
4. Report written ids, leftover drafts, lint leftovers.

## Forbidden

- Embeddings, invented tags, relative dates, secrets
- Editing MEMORY.md / INDEX-* by hand
- Marking a fact verified without `lane-memory verify . <id>`
