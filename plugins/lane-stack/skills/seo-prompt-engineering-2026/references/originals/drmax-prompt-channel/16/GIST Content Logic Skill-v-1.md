# GIST Content Logic Skill

## Purpose

This skill teaches an LLM how to design, audit, and rewrite content using a GIST-inspired logic.

Important framing:
- GIST originally comes from data subset selection, not from a public Google Search ranking specification.
- In its original form, GIST balances two competing goals:
  - utility: how valuable or informative the selected items are,
  - diversity: how non-redundant and well-spread the selected items are.
- In content work, this skill adapts that logic into a practical editorial method:
  - keep the essential, high-value parts of the topic,
  - reduce semantic redundancy,
  - avoid producing a page that is replaceable by existing leaders,
  - add the missing, decision-relevant parts of the topic.

Use this skill as:
- a page planning framework,
- a competitor analysis framework,
- a content brief framework,
- a page rewriting and audit framework,
- a safeguard against “good but replaceable” content.

Do **not** use this skill to claim:
- that GIST is a confirmed Google ranking factor,
- that Google Search directly scores pages with the same formula as the paper,
- that “unique wording” alone satisfies GIST logic,
- that longer content is automatically better content.

---

## Methodological basis

Primary references:
- [Google Research blog: Introducing GIST](https://research.google/blog/introducing-gist-the-next-stage-in-smart-sampling/)
- [Paper: GIST: Greedy Independent Set Thresholding for Max-Min Diversification with Monotone Submodular Utility](https://arxiv.org/pdf/2405.18754)

What matters from the original methodology:
1. The problem is subset selection under two tensions:
   - select highly useful items,
   - avoid selecting overly similar items.
2. Diversity is modeled as max-min diversity:
   - selected elements should not collapse into a tight, repetitive cluster.
3. Utility is modeled as value/information coverage:
   - selected elements should contribute meaningful value.
4. The goal is not randomness.
   - The goal is a strong subset that is both informative and minimally redundant.
5. A naive greedy approach is often not enough.
   - Local “best next item” selection can still create poor overall sets.
6. The practical lesson for content:
   - a page should not merely accumulate relevant statements,
   - it should select the right statements,
   - remove overlaps,
   - and create a compact but high-value structure.

---

## Core translation from GIST to content

Translate the original logic into editorial work like this:

### Original GIST idea
Select a subset of items that maximizes:
- utility,
- while maintaining strong diversity.

### Content adaptation
Build a page that maximizes:
- decision-support value,
- information gain,
- practical usefulness,
- coverage of the true intent,
while minimizing:
- semantic redundancy,
- interchangeable sections,
- template repetition,
- predictable filler,
- repeated competitor patterns.

### The content-level interpretation
A strong page is not the page that says the most.
A strong page is the page that says the most **useful** things with the least semantic waste.

---

## Working definitions

### 1. Utility

Utility is the amount of genuinely useful information delivered per unit of attention.

In content, a block has high utility if it does one or more of the following:
- helps the user make a decision,
- resolves uncertainty,
- distinguishes between options,
- explains limitations or exceptions,
- reveals hidden trade-offs,
- gives criteria for choosing,
- shows when common advice fails,
- adds evidence, examples, cases, data, or clear reasoning,
- reduces the chance of user error.

A block has low utility if it:
- states the obvious,
- restates the query in broader words,
- adds generic introduction text,
- repeats common definitions without adding a decision advantage,
- exists mainly to inflate length.

### 2. Semantic redundancy

Semantic redundancy is not textual duplication.
It is content duplication at the meaning level.

A block is semantically redundant if:
- it says what other leaders already say in nearly the same way,
- it repeats another block on the same page,
- removing it causes almost no loss of value,
- the user could swap it with a standard competitor paragraph and lose little.

### 3. Semantic conflict

Semantic conflict happens when multiple blocks try to solve the same informational job with near-identical meaning.

Examples:
- two sections both explain the same basic concept without adding new value,
- the intro and FAQ repeat the same warnings,
- a comparison table and a later list duplicate the same distinctions,
- the page gives multiple generalized answers to the same question instead of one sharp answer.

When semantic conflict appears:
- merge,
- compress,
- elevate the strongest version,
- delete weaker repeats.

### 4. Missing semantic nodes

Missing semantic nodes are important parts of the topic that competitors ignore, underdevelop, or hide.

Typical missing nodes:
- exceptions,
- limitations,
- boundary cases,
- decision criteria,
- failure modes,
- “when this advice does not apply,”
- differences by user type, geo, device, budget, intent, or risk,
- comparison frameworks,
- cost of mistakes,
- practical scenarios,
- uncommon but important evidence,
- expert observations,
- contradiction handling,
- operational details.

These nodes are often what make a page less replaceable.

### 5. Replaceability

Replaceability is the most important practical test.

If a user or a search system could replace your page with one of the top results and lose very little value, your page is weak under GIST logic.

Low replaceability requires:
- preserved topic core,
- strong relevance,
- visibly added value,
- reduced redundancy,
- earlier surfacing of unique decision-support material.

---

## First principles of GIST-oriented content

1. Keep the essential core.
2. Remove redundant matter.
3. Add what is missing but important.
4. Surface unique value early.
5. Reduce interchangeable sections.
6. Prefer decision-support over explanation bloat.
7. Prefer evidence over generic reassurance.
8. Prefer structured distinctions over repetitive completeness.
9. Prefer compact clarity over length inflation.
10. Judge each section by contribution, not by effort already invested in writing it.

---

## The GIST content objective

For every page, aim for this balance:

### Maximize
- intent coverage,
- decision usefulness,
- practical specificity,
- evidence density,
- edge-case handling,
- differentiated value,
- clarity of angle,
- non-replaceable insight.

### Minimize
- boilerplate intros,
- generic definitions,
- repeated FAQs,
- duplicated meaning across sections,
- “everyone says this” filler,
- safe but empty generalizations,
- bloated structure,
- competitor-shaped sameness.

---

## Mandatory editorial mindset

When using this skill, the LLM must think like:
- a selector, not a collector,
- a system designer, not a paraphraser,
- a decision architect, not a text expander,
- a redundancy cutter, not a content inflator.

The LLM must constantly ask:
- Does this block add useful value?
- Is this block already implied elsewhere?
- Is this block too similar to standard SERP content?
- What does this block contribute that a competitor likely does not?
- If removed, would the page materially weaken?
- If kept, should it be shorter, sharper, or moved higher?

---

## How to create content by GIST logic

## Step 1. Identify the real job of the page

Do not start by writing.
Start by defining the page’s job.

Determine:
- primary intent,
- secondary intents,
- expected format,
- user risk,
- required level of explanation,
- likely decision stage,
- what the page must help the user do.

Questions:
- What decision is the user trying to make?
- What uncertainty must be reduced?
- What wrong turn must the page prevent?
- What type of page best fits the query: guide, comparison, category, review, FAQ, landing page, tool page?

Rule:
The page must be designed around the job, not around the keyword alone.

---

## Step 2. Extract the topic core

Before adding differentiation, define the non-negotiable core of the topic.

The core includes:
- the facts or concepts required to satisfy intent,
- the essential distinctions the user expects,
- the minimum trusted structure without which the page feels incomplete.

Rule:
You cannot remove the core in the name of originality.

Bad approach:
- avoiding the basics just to be different.

Good approach:
- include the basics efficiently,
- then build advantage through missing semantic nodes.

---

## Step 3. Map competitor redundancy

Analyze the top competitors and identify:

### Shared core
What nearly all leaders include, and what is truly necessary.

### Shared redundancy
What nearly all leaders repeat but which adds little incremental value.

### Shared templates
Typical patterns such as:
- long definitional intro,
- standard benefits list,
- obvious bullet points,
- FAQ used as leftover storage,
- repetitive “how to choose” sections,
- generic trust phrases.

### Shared omissions
What most leaders fail to explain:
- limits,
- exceptions,
- decision edges,
- comparison frameworks,
- practical consequences,
- failure patterns.

Rule:
Do not imitate the average structure of the SERP just because it is common.

---

## Step 4. Score content ideas before writing

Every candidate section should be tested against 4 questions:

1. Utility  
Does this help the user decide, act, compare, or avoid mistakes?

2. Redundancy risk  
Would this likely overlap with standard competitor material?

3. Distinctiveness  
Does this add something specific, practical, or unusually clarifying?

4. Necessity  
Would the page weaken if this section were removed?

Simple decision model:

### Keep and emphasize
High utility + low/medium redundancy + high distinctiveness

### Keep but compress
High utility + high redundancy + necessary core

### Rewrite
Medium utility + high redundancy + potentially recoverable

### Remove
Low utility + high redundancy + low necessity

---

## Step 5. Build the page around non-replaceable value

A weak page places its best material too late.
A strong GIST-oriented page surfaces its differentiators early.

Move higher:
- decision frameworks,
- strong comparisons,
- exceptions,
- practical warnings,
- key limitations,
- real-world scenarios,
- uncommon but crucial insights.

Move lower or compress:
- generic definitions,
- standard trust padding,
- common-sense statements,
- repeated FAQ answers.

Rule:
The first meaningful blocks should already show why this page deserves to exist.

---

## Step 6. Write with compression discipline

GIST-style content is not minimal for the sake of minimalism.
It is compressed for signal quality.

Writing rules:
- one idea once,
- no repeated warnings across sections unless function changes,
- no restating the H2 in paragraph form without added meaning,
- no list where a sentence would do,
- no paragraph if a table or decision framework is stronger,
- no FAQ for leftovers.

Compression is good when:
- meaning stays intact,
- decision-support improves,
- redundancy drops,
- the unique angle becomes clearer.

Compression is bad when:
- important nuance disappears,
- edge cases vanish,
- the page loses trust-building evidence,
- core intent is no longer covered.

---

## Step 7. Add missing semantic nodes deliberately

A page becomes strong not by random originality, but by adding the right missing nodes.

Possible insertion patterns:

### Add an exceptions block
Use when advice only applies under certain conditions.

### Add a decision matrix
Use when users must choose between options with trade-offs.

### Add a “when not to do this” section
Use when misuse risk is high.

### Add an errors block
Use when users commonly misunderstand or misapply the topic.

### Add a segmentation block
Use when the right answer changes by:
- user level,
- device,
- geography,
- budget,
- legal context,
- urgency,
- experience.

### Add a scenario block
Use when understanding depends on context of use, not abstract explanation.

### Add proof blocks
Use:
- examples,
- data,
- source-backed constraints,
- observed patterns,
- process screenshots,
- comparisons,
- edge-case notes.

Rule:
Differentiation must increase usefulness, not just novelty.

---

## How not to do content by GIST logic

Do **not** do the following:

### 1. Do not confuse uniqueness with value
Bad:
- rewriting common facts with new wording,
- adding creative phrasing to generic points,
- thinking stylistic freshness equals content advantage.

### 2. Do not inflate the introduction
Bad:
- history,
- broad background,
- general “what is X” opening,
- motivational filler.

### 3. Do not repeat meaning in multiple wrappers
Bad:
- intro repeats overview,
- overview repeats comparison,
- comparison repeats FAQ,
- FAQ repeats conclusion.

### 4. Do not use FAQ as a garbage container
Bad FAQ signs:
- questions too obvious,
- answers duplicate section text,
- micro-questions created only for volume,
- no new distinctions.

### 5. Do not imitate SERP structure blindly
Bad:
- copying leader H2 patterns,
- using the same section order,
- reproducing the same comparison logic,
- mirroring the same “pros and cons” rhythm without new evidence.

### 6. Do not prioritize completeness over usefulness
A page can be “complete” and still weak if it mostly contains low-yield content.

### 7. Do not hide the best insight
Bad:
- unique criteria appear after 2000 words,
- limitations appear near the end,
- decisive comparison appears after generic filler.

### 8. Do not preserve weak text because it already exists
Existing text has no right to survive if it is semantically redundant.

### 9. Do not overpack every page
Not every query needs:
- giant FAQ,
- multiple tables,
- extensive glossary,
- case studies,
- deep historical context.

Only include what improves the page’s job.

### 10. Do not remove the topic core in pursuit of originality
If the basics are necessary, keep them.
Just compress and sharpen them.

---

## What good GIST-style content looks like

A strong page usually has these traits:

- the page angle is clear early,
- the page covers the essential core efficiently,
- the best distinctions appear near the top,
- repeated meaning is low,
- every major section has a clear job,
- the page helps the user choose, not just read,
- the page handles exceptions or failure cases,
- the page contains at least some non-generic insight,
- the FAQ is small or absent unless it genuinely adds value,
- the page feels tighter than competitors but more useful.

---

## What weak GIST-style content looks like

A weak page often has these traits:

- sounds polished but says little,
- repeats standard SERP content with minor rewording,
- has a long intro and a generic structure,
- uses many headings but low information gain,
- hides its only useful section too late,
- bloats FAQs,
- adds no meaningful decision advantage,
- lacks constraints, exceptions, trade-offs, or proof,
- could be replaced by any competent competitor page.

---

## Section-level evaluation framework

Evaluate each section using this grid.

### Utility score
- High: directly helps decision, action, comparison, or error prevention
- Medium: useful background but not decisive
- Low: generic, obvious, replaceable

### Redundancy score
- Low: uncommon and clearly additive
- Medium: common but still needed
- High: largely duplicated by competitors or other sections
- Critical: almost pure repetition or low-value filler

### Distinctiveness score
- High: contains unusual clarity, criteria, scenarios, evidence, or insight
- Medium: somewhat useful but still familiar
- Low: generic and predictable

### Action
- Keep
- Keep but compress
- Rewrite
- Merge
- Move higher
- Move lower
- Delete

---

## Recommended page architecture under GIST logic

The exact structure depends on query type, but the logic is usually:

1. Fast alignment with intent
2. Immediate value-bearing distinction
3. Core answer or framework
4. Decision-support blocks
5. Exceptions / limitations / errors
6. Evidence / examples / comparison
7. Secondary details
8. Small FAQ only if it adds real value

General rule:
- front-load value,
- mid-page handles complexity,
- back-end supports detail,
- no leftover dumping ground.

---

## Query-type adaptations

## Informational guide
Emphasize:
- clear explanation,
- decision consequences,
- exceptions,
- practical application.

Reduce:
- long broad intros,
- beginner filler if not needed,
- broad historical context.

## Comparison page
Emphasize:
- criteria matrix,
- trade-offs,
- scenario-based recommendations,
- disqualifiers,
- who should choose what.

Reduce:
- duplicated feature descriptions,
- repeated “pros and cons” blocks saying the same thing.

## Category page
Emphasize:
- segmentation,
- decision pathways,
- filtering logic,
- distinguishing traits,
- confidence-building structure.

Reduce:
- generic category intros,
- repeated product-card summaries.

## Review page
Emphasize:
- concrete evaluation criteria,
- actual strengths and limits,
- who it suits,
- when it fails,
- evidence or usage logic.

Reduce:
- manufacturer-style overview text,
- soft promotional filler.

## FAQ page
Only justify it if:
- the query is explicitly FAQ-driven,
- question format matches user intent,
- each answer adds new value.

Otherwise:
- a “FAQ page” easily becomes redundancy-heavy.

---

## Prompting rules for any LLM using this skill

When the LLM creates or audits content, it must follow these mandatory rules:

1. Never assume more text equals more value.
2. Never reward a section for sounding polished if it lacks informational gain.
3. Never preserve repeated meaning in multiple sections.
4. Always distinguish between:
   - required topic core,
   - useful additions,
   - redundant mass,
   - missing semantic nodes.
5. Always test replaceability:
   - Could this page be swapped with a leader?
   - Could this section be swapped with a standard competitor paragraph?
6. Prefer strong structure over exhaustive expansion.
7. Add differentiation through content substance, not clever wording.
8. Surface unique value early.
9. Shrink sections that are necessary but common.
10. Be willing to delete.

---

## Audit mode instructions

When auditing an existing page, do this:

### Phase 1. Reconstruct intent and page job
Identify:
- what the page is trying to do,
- whether the current structure fits the actual query.

### Phase 2. Split the page into blocks
For each block, label:
- purpose,
- utility,
- redundancy,
- distinctiveness,
- risk.

### Phase 3. Perform GIST selection
Assign each block to:
- keep,
- compress,
- rewrite,
- merge,
- delete.

### Phase 4. Detect missing nodes
Ask:
- What critical questions remain unanswered?
- What decisions still feel under-supported?
- What failure modes are missing?
- What edge cases are absent?
- What important comparison logic is missing?

### Phase 5. Reorder
Move high-value distinctions earlier.
Push background down.
Remove low-yield sections.

### Phase 6. Rewrite
Rebuild weak sections around:
- criteria,
- constraints,
- decisions,
- evidence,
- practical reality.

### Phase 7. Re-check replaceability
After rewriting, test:
- does the page now have visible non-generic value?
- would swapping it with a leader produce a meaningful loss?

---

## Creation mode instructions

When creating a page from scratch, do this:

### Phase 1. Define the job
- query,
- user intent,
- page type,
- conversion or information goal.

### Phase 2. Map the topic core
- what must be covered,
- what must not be bloated.

### Phase 3. Map competitive redundancy
- what everyone says,
- what everyone repeats,
- what is missing.

### Phase 4. Choose the page angle
The angle should make the page:
- sharper,
- more useful,
- less replaceable.

### Phase 5. Design the structure
Use:
- efficient core,
- distinctive middle,
- evidence and complexity in the right places.

### Phase 6. Draft with compression
Keep:
- clarity,
- density,
- decision value.

### Phase 7. Run a GIST self-audit
Before finalizing, ask:
- what can be removed?
- what is too common?
- what remains underdeveloped?
- what important node is still missing?
- is the best material too low on the page?

---

## Red-flag patterns

If any of these appear, the page likely violates GIST logic:

- long definitional opening,
- multiple sections saying the same thing,
- FAQ full of generic questions,
- lots of words but few distinctions,
- no scenario thinking,
- no “when not to” guidance,
- no practical criteria,
- weak first screen,
- generic trust language,
- copied competitor section rhythm,
- content that feels safe but unmemorable,
- too much “what it is,” not enough “how to decide.”

---

## Advanced GIST content heuristics

### 1. Core-compression heuristic
If a point is necessary but widely repeated:
- keep it short,
- make it accurate,
- do not let it dominate.

### 2. Early-differentiation heuristic
If a block is your strongest non-replaceable contribution:
- move it earlier.

### 3. Edge-case heuristic
If a topic has common exceptions:
- surface them before the user makes a wrong decision.

### 4. Scenario heuristic
If advice changes by user type or conditions:
- segment the answer.

### 5. Conflict heuristic
If two sections partially overlap:
- merge into one stronger block.

### 6. Replaceability heuristic
Ask of each major section:
- could a top-ranking competitor say this almost the same way?
If yes, either compress, enrich, or replace.

### 7. Evidence heuristic
If a strong claim lacks support:
- add examples, proof, observed pattern, or constraints.

### 8. Friction heuristic
If a section consumes attention but yields little decision value:
- cut it.

---

## Good vs bad patterns

## Good
- “Here are the three decision criteria that actually change the answer.”
- “This works in cases A and B, but not C.”
- “Most guides skip this limitation.”
- “If you are choosing between X and Y, use this matrix.”
- “The common advice fails when…”
- “For beginners do this; for advanced users do that.”
- “This metric matters only under these conditions.”

## Bad
- “X is very important in today’s world.”
- “There are many factors to consider.”
- “Choosing the best option depends on your needs.”
- “Let’s first understand what X means.”
- “In this article we will explore everything about X.”
- “Below are some frequently asked questions” when those questions add nothing new.

---

## What the LLM must never forget

1. A page is not strong because it is thorough.
2. A page is strong when it is hard to replace.
3. Redundancy can exist even with fully original wording.
4. The best content often wins by sharper selection, not by more coverage.
5. Missing decision-support nodes are often more valuable than another explanatory paragraph.
6. Utility without diversity creates clustered repetition.
7. Diversity without utility creates irrelevant novelty.
8. GIST logic requires both.

---

## Safe interpretation statement

Use this wording when needed:

“GIST is used here as a content design framework inspired by Google Research’s utility-diversity subset selection work. It is not presented as a confirmed direct Google Search ranking factor. In this skill, the value of GIST lies in its editorial logic: preserve essential utility, reduce semantic redundancy, and surface non-replaceable information.”

---

## Suggested system instruction wrapper

Use this wrapper when loading the skill into another LLM:

“You must use GIST Content Logic as your default editorial method. Treat content as a selection problem, not a volume problem. Preserve the essential core of the topic, minimize semantic redundancy, identify missing semantic nodes, and build pages that are less replaceable than standard competitor content. Do not confuse wording uniqueness with informational value. Do not generate filler. For each major section, evaluate utility, redundancy, distinctiveness, and necessity before keeping it.”

---

## Minimal operating checklist

Before finalizing any page, verify:

- Is the true intent clear?
- Is the core covered efficiently?
- Is the page angle visible early?
- Are there missing semantic nodes?
- Are there repeated meanings across sections?
- Is the FAQ actually needed?
- Are weak generic blocks still present?
- Can any section be removed without harm?
- Can any section be swapped with a competitor paragraph?
- Does the page help the user decide better than a standard result?

If the answer reveals high replaceability, the page is not ready.

---

## Final doctrine

The goal is not:
- maximum length,
- maximum uniqueness,
- maximum detail,
- maximum number of headings.

The goal is:
- maximum useful signal,
- minimum semantic waste,
- strong topic core,
- visible differentiating value,
- low replaceability.

That is the practical content meaning of GIST logic.