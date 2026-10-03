---
id: your-fact-id
schema_version: 2
status: active
memory_type: normative
truth_mode: decision
claim: One sentence that will fire again next month
language: en
source:
  authority: owner
evidence:
  - type: conversation
    ref: YYYY-MM-DD
risk: low
sensitivity: internal
context_priority: always
retrieval:
  areas: [procedures]
  hint: synonyms, including russian
verification:
  command: test -f .agents/PROGRESS.md
---

Why this rule exists. Related: [[other-id]].
Copy this file to `.cls/drafts/<id>.md` (not under `.agents/memory/`), replace placeholders, then:
lane-memory write --apply .cls/drafts/<id>.md --confirm .agents/memory/<id>.md --yes
(With the hub on, the record goes to the hub; `.agents/memory/<id>.md` is only the destination the CLI checks. `LANE_MEMORY_HUB=off` = old local corpus.)
