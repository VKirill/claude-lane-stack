---
name: team-routes
description: "dev-orchestrator only. Turns any request into a route of specialist and writer steps: which roles work, in what order, what each reads and writes. Use at the start of every new goal. SKIP: writer CLIs; specialists themselves."
---

# Team routes

The operator states a goal, not a staffing plan. You decide who works on it.
A page built without its SEO, UX and copy inputs comes back as placeholders and
gets redone; a one-line fix sent through four specialists burns an hour of
expensive models. Pick the smallest team that produces the artifact the
operator actually needs.

## 1. Name the deliverable

Before Score/Decompose, write one line for yourself:
`deliverable: <artifact> · surface: <page/app/feature> · slug: <kebab-slug>`.

The deliverable is what the operator will open at the end: a gray prototype,
a branded mockup, shipped code, an article, an audit report, an answer with
sources. Ambiguous wording («сделай страницу») means the cheapest deliverable
that still moves the goal (prototype before code) unless the operator said
«в код», «на сайт», «задеплой» or the page already exists in code.

## 2. Pick or compose a route

Start from the closest recipe in [references/recipes.md](references/recipes.md).
Drop a step when its output already exists on disk and is not stale (for
example `.agents/copy/pages/<slug>.md` is there, so copy only fills gaps). Add a step
when the goal needs a role the recipe lacks. No recipe fits → compose a route
from the role cards in [references/roles.md](references/roles.md): each step's
inputs must be outputs of earlier steps or existing files.

Run steps in parallel when neither reads the other's output. Run them in order
when one decides what the next one writes about (SEO intent before copy).

Not every request needs a route. Go straight to the existing Loop when the
goal is product code with no new user-facing text or layout (bug, refactor,
API, infra), or a question you can answer from the repo.

## 3. Announce and start

Post one Russian line, then start the first step in the same turn. Do not wait
for approval: the operator asked for the result, and the line exists so they
can redirect you.

```text
Маршрут: seo ∥ design-lead (UX) → copy-lead → design-lead (прототип) → design-lead (аудит). Начинаю.
```

For routes with 2+ specialist steps, also write the route file
`.agents/plans/routes/<slug>.md` (English):

```text
goal: <operator goal, one line>
deliverable: <artifact>
steps:
  - id: seo | role: seo-specialist | reads: [...] | writes: <path> | status: todo
  - ...
decisions: []   # conflicts you resolved, with the reason
```

Update `status` after each step. It is how `resume-project` and a restarted
session know where the route stopped.

## 4. Brief each specialist

Every specialist prompt has the same five lines. The specialist sees only this
prompt and the disk, so a missing READ path means the work is done blind.

```text
GOAL: <operator goal + this step's part of it>
SLUG: <slug>
READ: <outputs of earlier steps and existing project files, as paths>
WRITE: <the one path this step owns>
DECIDE: <the questions this step must answer for the next step>
```

Close with the role's normal sentinel (`DONE <path>` / `FAILED <reason>`).
Read the file from `DONE`, not the chat summary, before you start the next step.

## 5. Merge the outputs

Specialists do not talk to each other. You merge their outputs. When two outputs
conflict (SEO wants a long FAQ block, design wants one short screen), decide by
the deliverable's primary user action, record the call in `decisions:` with
one reason, and pass it to the next step through READ/DECIDE.

Ask the operator only for what no role can produce from the disk or the web:
prices, guarantees, the offer, legal claims, brand approval, money or
irreversible actions. Specialists must mark unknown facts `[unknown]`, not
invent them. Collect those markers into one question for the operator at the end
of the route, not after each step.

## 6. Hand over

End the route with the deliverable path, what each role contributed (one line
each), open `[unknown]` facts, and the next sensible step (for example «в код —
скажи "делай"»). A route that ends in code continues into the normal WRITE
Loop: specialist steps finish first, then `run-init` with their outputs in
`read_first`. This keeps the Mode XOR rule: no research teammates on a goal
once its write run has started.
