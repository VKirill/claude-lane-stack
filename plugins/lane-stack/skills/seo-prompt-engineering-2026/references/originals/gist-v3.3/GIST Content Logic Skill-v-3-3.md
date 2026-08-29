# GIST Content Logic Skill v3.3
<!-- 
Автор: DrMax
https://drmax.su
https://t.me/drmaxseo
-->
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
- a meta title and meta description construction framework,
- a safeguard against "good but replaceable" content.

Do **not** use this skill to claim:
- that GIST is a confirmed Google ranking factor,
- that Google Search directly scores pages with the same formula as the paper,
- that "unique wording" alone satisfies GIST logic,
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
   - Local "best next item" selection can still create poor overall sets.
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
- "when this advice does not apply,"
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
- "everyone says this" filler,
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
Start by defining the page's job.

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
- repetitive "how to choose" sections,
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

### Add a "when not to do this" section
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

## Step 8. Apply GIST logic to meta titles and meta descriptions

Meta titles and meta descriptions are treated as their own selection problem, not as a shrunken summary of the page. The same tension applies: maximize utility (a genuine reason to click, grounded in fact) while minimizing redundancy (the title/description must not read like the hundreds of near-identical competitor tags for the same query). This is a deliberate inversion of the conventional approach, where meta tags are written as a compressed paraphrase of the page content — here, the field is treated as an independent selection task with its own candidate pool, its own filters, and its own conflict checks.

**Cross-level dependency note:** If the page was built using this skill's page-level workflow (Steps 1–7), the candidate pool for meta fields does not need to be generated from scratch. The page's angle (chosen in Step 4) and the missing semantic nodes added in Step 7 are high-utility candidates by construction — they have already passed the skill's utility and distinctiveness tests at the page level. Extract them as the first entries in the candidate list (Step 8.2) before running the five-heuristic search (Step 8.3). This ensures that the meta fields reflect the page's actual differentiators rather than surface-level features, and prevents a semantic split between what the page is actually built around and what the title/description promise.

### Why this matters

Structural fields (title, meta description, headings) are the primary mechanism through which a page becomes visible and citable in both classic search and generative/AI-driven search surfaces. Optimizing structural fields alone has been shown to meaningfully improve retrieval and citation likelihood, while body-text-only optimization can even hurt visibility. This makes the title/description not a cosmetic afterthought, but a high-leverage GIST selection target in its own right.

Important framing:
- Google rewrites a large share of meta descriptions (roughly 60–70% in various observations) when it judges the existing one as low-value or mismatched to the query.
- The practical implication: the goal is not "force Google to show my exact text," it is "supply a structural field so specific and useful that it is the best available material to show."
- This reframes meta tag writing from a copywriting exercise into a GIST selection exercise: pick the single fact with the highest utility-to-redundancy ratio.

### The core problem GIST solves here

A generic formula such as `[Product/Topic name] + [Generic feature] | [Brand]` produces a title that is nearly identical to hundreds of competitor titles for the same query. This is a textbook case of semantic redundancy and high replaceability at the level of a single field. GIST logic replaces the generic feature slot with a single, concrete, verifiable differentiator selected through an explicit filter, not through free improvisation.

### GIST Meta Filter: four selection tests

Every candidate fact competing for the title or description slot must pass these four tests, each grounded in the working definitions already established in this skill.

**1. Concreteness test (Utility check)**  
Is the fact a specific, named detail (a technology, material, mechanism, number, or process) rather than an abstract quality word ("high quality," "best," "reliable")? Abstract quality words have near-zero utility because they cannot be verified and say nothing a competitor could not also claim.

**2. Decision-relevance test (Utility check)**  
Does the fact resolve a real uncertainty or remove a real friction point for the user at the moment of scanning search results (a cost, a risk, a common inconvenience, a missing option)? If the fact would not change what the user expects or decides, it has low utility regardless of how specific it sounds.

**3. Replaceability test (Redundancy / Replaceability check)**  
Could a competitor selling or writing about the same thing use this exact fact almost word for word? If yes, the fact is semantically redundant at the field level and should not occupy the scarce title/description space. This test must be applied twice: once when selecting the candidate fact (before writing), and once again on the finished title/description (before publishing).

**4. Verifiability test (Missing semantic node / proof check)**  
Can the user or the search system confirm this fact is true by opening the page (a number, a named technology, a certification, a count of reviews, a concrete policy)? Facts that pass verifiability behave like a proof block: they build trust before the click, not just curiosity.

A fact should not enter the title unless it clears all four tests. A fact that passes only "sounds interesting" but fails Replaceability or Verifiability is stylistic decoration, not a GIST factor.

### Step-by-step algorithm for meta title/description construction

**Step 8.1 — Define the field's job**  
Before selecting any fact, state what this specific title/description must do: which single intent it serves, and what wrong click it must prevent (irrelevant traffic, mismatched expectation).

**Step 8.2 — List 3–5 candidate facts about the entity**  
Write down concrete facts about the product, service, or topic: a technology/material detail, a measurable outcome or benefit, a friction point it removes, and a piece of verifiable proof. If the page was already built using Steps 1–7, start this list with the page angle and the missing semantic nodes added in Step 7 (see Cross-level dependency note above), then continue over-generating. Do not filter yet.

**Step 8.3 — Search for missing semantic nodes as candidate facts**  
Before filtering, run the page through five search heuristics designed to surface facts that competitors systematically miss. Each heuristic targets a type of missing semantic node from this skill's working definitions:

- **Failure mode heuristic:** What can go wrong with this product or decision? (→ "подрезка рулона под размер" снимает боль "останутся обрезки")
- **Hidden information heuristic:** What does the user typically learn only after purchasing or deeper reading? (→ "сборка включена" — пользователь узнает об этом только в корзине)
- **Limitation heuristic:** Under what conditions does this NOT work, or for whom is it NOT suitable? (→ "не подходит для помещений без отопления")
- **Disqualifier heuristic:** What would make the user explicitly NOT choose this option? (→ "не подходит для крупноформатной плитки")
- **Quantifiable heuristic:** What is measurable about this entity that the user cannot easily infer from the category name? (→ "расход 1.5 кг/м²", "800+ отзывов", "гарантия 5 лет")

Each of these searches is designed to produce a candidate fact with high initial utility that is unlikely to be semantically redundant with competitor meta fields, because competitors rarely include failure modes, hidden information, or disqualifiers in their titles and descriptions. Not every heuristic produces a usable fact for every page, but running all five ensures the search space is not limited to the surface-level features of the entity.

**Step 8.4 — Map what competitors already say (redundancy check on the SERP)**  
Look at the top-ranking titles/descriptions for the same query. Identify the shared generic pattern (the "template everyone uses"). Any candidate fact that matches this shared pattern is disqualified at this stage — this is the first Replaceability pass.

**Step 8.5 — Run each surviving candidate through the GIST Meta Filter**  
Apply all four tests (Concreteness, Decision-relevance, Replaceability, Verifiability) to each remaining candidate. Discard any fact that fails more than one test.

**Step 8.5b — Fallback when no candidate passes all four tests**  
If every candidate fact fails at least one filter, do not default to abstract quality words. Instead, use the following forced-choice sequence, attempting each option before moving to the next:

1. **Escalate to a super-category fact.** If the entity itself has no passing fact, check whether the category, brand, or product line has a verifiable characteristic that the entity inherits (e.g., "все ламинаты Praktik имеют защиту Aqua Stop" — факт верен для всей линейки, но не для конкретной модели). This fact passes Replaceability only if most competitors in the same category cannot truthfully claim it.
2. **Relax Verifiability as a requirement.** If after escalation no candidate passes all four tests, admit the weakest filter — Verifiability — and allow a candidate that passes the other three (Concreteness, Decision-relevance, Replaceability) but is not verifiable from the page alone. The title must then be paired with a description that supplies the verifiable proof (a number, a named technology, a customer count) that the title lacks. If the description also cannot supply verifiable proof, escalate to option 3.
3. **Use a structural or operational fact.** If both options above fail, use a fact about how the entity is sold, shipped, or supported rather than about the entity itself (e.g., "доставка за 2 часа," "бесплатный замер," "подрезка в подарок"). These are not product features but they pass Concreteness and Decision-relevance because they remove a real friction point. They must still pass the Replaceability and Verifiability tests — a structural fact that every competitor already claims ("доставка за 2 часа" when all competitors also deliver in 2 hours) fails Replaceability and should not be used.
4. **If all three fallbacks fail, escalate to the human editor.** The skill must not hallucinate a GIST factor. Output a clear statement: "This entity has no fact that passes the GIST Meta Filter through any fallback path. Manual review required."

**Step 8.6 — Score and rank surviving candidates**  
When multiple candidate facts pass all four tests, use a simple scoring system to break ties before selecting the single strongest fact for the title. Score each candidate on a 0–2 scale for each dimension:

| Dimension | 0 points | 1 point | 2 points |
|---|---|---|---|
| Surprise value | The fact is expected for this category | The fact is uncommon but not unique | The fact is genuinely surprising or rarely mentioned |
| Verification cost | The user must scroll or click to verify | The user can verify from the SERP preview | The user can verify from the title alone |
| Intent specificity | The fact is true of many pages | The fact is true of this subcategory | The fact is uniquely true of this specific entity |

The candidate with the highest total score is the default selection for the title. Ties are broken by Intent specificity first, then Surprise value. This scoring is not a substitute for the four-filter pass — no candidate that failed a filter may be reinstated through scoring, regardless of score.

**Step 8.7 — Select the single strongest fact for the title**  
The candidate with the highest total score from Step 8.6 is the default selection for the title. Within a tie, break first by Intent specificity, then by Surprise value. The scoring dimensions already encode Replaceability (Intent specificity) and Decision-relevance (Verification cost), so no separate prioritization is needed — the highest-scoring candidate is the best selection by construction. Place it as close to the front of the title as the format allows, because front-loading is the same principle used for page structure in Step 5.

**Step 8.8 — Build the description around a compact sequence, not a list of adjectives**  
Use a short sequence that mirrors the page-level logic of "core answer, then proof, then action": lead fact → concrete specification or number → verifiable credibility marker → soft call to action. Each part must earn its place using the same Utility/Redundancy logic as any page section — do not include a part just because "descriptions usually have a CTA."

**Step 8.9 — Check for Title-Description semantic conflict**  
Apply this skill's conflict heuristic at field scale: the title and description must not perform the same informational job with overlapping meaning. Read the pair as a two-field system and flag if:

- The description restates the title's GIST factor in different words without adding a new fact (this is the field-level equivalent of a section that restates its own heading).
- The description's hook fact is the same as the title's GIST factor, differing only in phrasing (merge into one stronger field — move the proof or CTA, not a second restatement of the same fact).
- The description uses the same credibility marker or number as the title without adding a separate dimension of proof.

When conflict is detected, the description must be rebuilt around a different fact from the candidate pool, keeping the original GIST factor in the title. If the pool has no remaining candidate that passes the GIST Meta Filter, the title's GIST factor may be moved to the description and the title rebuilt around the next strongest candidate.

This conflict check is a general rule. It has one explicit, narrow exception — see the Standalone context note below.

**Step 8.10 — Re-run the Replaceability test on the finished pair**  
Read the finished title and description together and ask the mandatory question from this skill's general audit process: could a competitor swap in their own brand name and reuse this almost unchanged? If yes, the selection failed and Step 8.6–8.8 must be repeated with a different candidate fact.

**Step 8.11 — Template-level GIST for catalog pages (optional, scale-dependent)**  
This step applies only when constructing meta fields at catalog scale (hundreds or thousands of similar entities), where manual per-page GIST selection through Steps 8.1–8.10 is impractical. It does not apply to individually authored pages. In that case, the GIST logic must be embedded at the template level rather than the instance level:

1. **Identify the single attribute that varies most usefully across the catalog.** For a clothing catalog, this may be the material technology (Gore-Tex, Merino, Coolmax). For a building materials catalog, it may be the certification or class (НГ, КМ1, Е1). For a SaaS directory, it may be the integration count or compliance certification.
2. **Build the template around that attribute as the slot, not around a generic feature.** A template like `[Product Name] + [Material Technology] | [Brand]` preserves GIST logic at scale because the slot is filled with a concrete, verifiable fact, even if the slot itself is repeated. A template like `[Product Name] + High Quality | [Brand]` does not — the slot is an abstract quality word.
3. **Validate the template with a single GIST Meta Filter pass before deployment.** Run the template with three different slot fillers through the four tests. If any of the three passes fail, the template is too weak and must be redesigned.
4. **Monitor for template-level semantic conflict.** If the same GIST factor appears in a large majority of the catalog's titles, evaluate whether this reflects a genuine shared attribute (all products legitimately share the technology) or template laziness (the slot filler is being copied rather than selected per entity). As a diagnostic heuristic: if the factor is present in more than 70% of titles and is not a genuinely shared attribute of the entire catalog, the template likely needs a second slot or a secondary attribute to restore diversity. This is a diagnostic signal, not a hard rule — a catalog where 100% of products genuinely share the same technology is fine.

### Length and pixel discipline (Cyrillic-aware)

Character-count targets are a rough proxy; actual truncation is pixel-width-based. Google's practical limits are approximately 600px for the title on desktop and approximately 920px (desktop) / 680px (mobile) for the meta description. Cyrillic characters are generally wider than Latin characters at the same font size, which means Russian-language titles and descriptions reach the visual truncation point at a lower character count than English-language equivalents.

Estimated Cyrillic-safe ranges (these are approximations, not measured guarantees, and should be verified with a pixel-width preview tool before publishing):

| Field | Latin safe range | Cyrillic safe range (estimated) | Note |
|---|---|---|---|
| Title (desktop, ~600px) | 50–60 chars | 40–50 chars | Cyrillic "ш", "щ", "ж", "ю", "м" are estimated 1.3–1.5× wider than average Latin characters |
| Meta description (desktop, ~920px) | 150–160 chars | 130–145 chars | The 920px ceiling is reached faster with Cyrillic text |
| Meta description (mobile, ~680px) | 110–120 chars | 90–105 chars | The mobile limit is especially tight for Russian-language descriptions |

Practical adjustment:
- Treat standard English-language length guidance as an upper ceiling, not a target, when writing in Russian.
- Front-load the selected GIST fact so that if truncation occurs, the differentiator is not the part that gets cut. As a safe default, place the GIST factor within the first 35 characters of a Cyrillic title and within the first 90 characters of a Cyrillic description.
- Test visually where possible rather than relying on character counts alone, because bold/wide Cyrillic letterforms consume more pixel width than narrow Latin letters.

**Standalone context note:** The meta description is treated as part of a two-field system in this skill (see Step 8.9), but it also appears in standalone contexts where the title is not visible: social media previews (when og:description is absent — note that setting og:description independently reduces this dependency and should be preferred when social sharing is a primary distribution channel), AI-generated answer summaries, voice search results, and link previews in messaging apps. When there is a specific, known reason to expect standalone exposure — the page is designed for active social sharing, or the page is a likely citation source for generative/AI answers — the GIST factor should be placed at the very start of the description, within the first 90 Cyrillic characters, even if this means the title and description share the same GIST factor, overriding the conflict check in Step 8.9 for this specific case. This override is a narrow, deliberate exception triggered by a known distribution context, not a default fallback — for pages without a specific standalone-exposure reason, Step 8.9 applies in full.

**Temporal stability note:** When selecting a GIST factor, distinguish between facts that are stable (material, technology, certification, mechanism, dimension) and facts that are time-bound (price, discount percentage, stock status, promotional deadline). A time-bound fact may score higher on Surprise value and Intent specificity, but it creates a maintenance obligation: the meta field must be updated when the fact changes. As a rule of thumb:

- Use a stable GIST factor for the title (which is expensive to change and indexed for longer).
- Use a time-bound GIST factor for the description (which is cheaper to update and often rewritten by Google anyway).
- If a time-bound fact is the only fact that passes all four filters, flag it in the output as "temporary GIST factor — set a review date."

### Anti-patterns specific to meta fields

Do not do the following when applying GIST logic to titles and descriptions:

1. Do not use abstract quality words as the selected differentiator ("высокое качество," "лучший выбор," "надежный поставщик," "выгодные цены," "широкий ассортимент," "индивидуальный подход") — these fail the Concreteness test.
2. Do not select a fact that is true of the entire category rather than this specific entity ("класс 33," "сертифицированный продукт" when every competitor's product is also certified) — this fails the Replaceability test.
3. Do not stack multiple candidate facts into one title hoping one will land — this recreates the "accumulation over selection" mistake this skill rejects at the page level, just at field scale.
4. Do not use the brand name as the differentiator inside the description if it already appears in the title — this is a redundant field-to-field repeat, not a new fact.
5. Do not treat "add a number" as automatically sufficient — a number must still pass Decision-relevance (a review count only matters if the user cares about social proof for this type of decision; a random spec number that does not affect the decision is filler with digits).
6. Do not copy the CTA phrasing pattern from every competitor ("узнать больше," "подробнее здесь") — a soft CTA should reflect what actually happens next on this specific page.
7. Do not let the title and description restate the same fact in different words unless the narrow standalone-exposure exception applies — this is a Title-Description semantic conflict (see Step 8.9) and wastes half the available field space.
8. Do not default to an abstract quality word when no candidate passes the GIST Meta Filter — run the fallback sequence in Step 8.5b first, and escalate to human review only if all fallbacks fail.
9. Do not leave a time-bound fact (a discount, a deadline, a stock claim) in the title without flagging it for review — this risks a false promise once the fact expires (see Temporal stability note).
10. Do not treat a structural or operational fact (Step 8.5b, option 3) as automatically safe — it must still pass Replaceability and Verifiability, not just Concreteness and Decision-relevance.

### Niche-calibrated GIST fact types

The type of fact most likely to pass the GIST Meta Filter differs by page type. Use this as a starting search space, not a rigid template. The third column gives a productive search question to run against the entity — use it together with the five heuristics in Step 8.3.

| Page type | Where the strongest GIST fact usually hides | Productive search questions |
|---|---|---|
| Product / e-commerce card | A named material, mechanism, or included service detail competitors do not mention | What service is included that competitors charge extra for? What material or mechanism has a specific name? What dimension is critical but rarely listed? |
| Category page | A segmentation or filtering capability that removes a real shopping friction | What filter do users most need but most stores lack? What is the range (brands, sizes, price) that sets expectations? |
| Local service page | A hyperlocal qualifier plus an operational fact | What is the specific response time? What certification or license is unusual for this trade? What is the exact service radius? |
| SaaS / B2B page | A measurable outcome range plus a friction-removal fact | What is the measurable result range (%, time, money)? What objection is most commonly raised and how is it removed? |
| Blog / informational page | The single most decisive distinction the article makes | What is the one thing this article says that most others do not? What exception or limitation does this article surface? |
| Comparison / "vs" page | The specific dimension where the two options actually diverge | On what specific criterion do the two options produce opposite recommendations? What disqualifier cleanly separates the choices? |
| Landing page | A concrete constraint the user cares about at the point of conversion | What is the turnaround time? What is absent that the user expects to be a problem? What is the specific output? |
| FAQ / Q&A page | The exact question re-stated with the specific number or boundary that answers it | What is the most common misconception this question addresses? What number or condition changes the default answer? |
| News / research page | The specific date and the specific magnitude of change | What is the exact date of the event? What is the percentage or count that measures the impact? |

### Pre-publish checklist for meta fields

Before finalizing any title/meta description pair, verify:

- Does the title contain at least one fact that passed the Concreteness test?
- Does that fact also pass Decision-relevance for this specific query and page type?
- Was the missing-semantic-node search (Step 8.3, five heuristics) actually run before filtering, not skipped?
- If the page was built with Steps 1–7, was the page angle and Step 7 additions pulled into the candidate pool first (Cross-level dependency note)?
- Has the Replaceability test been run twice — once on the candidate fact, once on the finished pair?
- If multiple candidates passed all four filters, was the GIST score used to select among them rather than an arbitrary choice?
- If no candidate passed all four filters, was the Step 8.5b fallback sequence run before falling back to abstract quality words?
- If a structural/operational fact (Step 8.5b, option 3) was used, was it also checked against Replaceability and Verifiability, not just Concreteness and Decision-relevance?
- Can the user verify this fact is true within the first screen of the page (Verifiability)?
- Is the strongest fact placed early enough to survive pixel-width truncation, accounting for Cyrillic width?
- Does the description avoid repeating the brand or the exact phrase already used in the title, unless the standalone-exposure exception applies?
- Is any time-bound fact in the title flagged for review (Temporal stability note)?
- Would a competitor selling the same category of thing be able to reuse this pair almost unchanged?

If the last question is answered "yes," the pair has not yet cleared GIST logic and must be revised.

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
- general "what is X" opening,
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
- mirroring the same "pros and cons" rhythm without new evidence.

### 6. Do not prioritize completeness over usefulness
A page can be "complete" and still weak if it mostly contains low-yield content.

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

Only include what improves the page's job.

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
- repeated "pros and cons" blocks saying the same thing.

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
- a "FAQ page" easily becomes redundancy-heavy.

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
   - Could this title/description be reused by a competitor almost unchanged?
6. Prefer strong structure over exhaustive expansion.
7. Add differentiation through content substance, not clever wording.
8. Surface unique value early.
9. Shrink sections that are necessary but common.
10. Be willing to delete.
11. Never hallucinate a GIST factor for meta fields — if no candidate fact passes the filter even after the Step 8.5b fallback sequence, say so explicitly rather than defaulting to abstract quality language.

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

### Phase 8. Audit the title and meta description
Apply the GIST Meta Filter (Step 8.1–8.11) to the existing title and description as if they were new candidates:
- does the current title contain a fact that passes Concreteness, Decision-relevance, Replaceability, and Verifiability, or does it rely on abstract quality words?
- was the missing-semantic-node search (Step 8.3) applied, or does the pair only reflect surface-level features?
- was the page's own angle and Step 7 additions considered as candidates (Cross-level dependency note), or were the meta fields written independently of the page's actual differentiators?
- do the title and description conflict semantically (Step 8.9), restating the same fact in different words, without a valid standalone-exposure justification?
- does the title rely on a time-bound fact (price, discount, stock) that is not flagged for review?
- if a structural/operational fact is used, does it actually pass Replaceability and Verifiability, or is it just as replaceable as any competitor's claim?
- would a competitor be able to reuse the current pair almost unchanged?
- if the answer to the last question is yes, the pair must be rebuilt using Step 8.1–8.11, not merely reworded.

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

### Phase 8. Construct the title and meta description
Run Step 8.1–8.11 on the finished page to select and validate the title and meta description as a dedicated GIST selection task, not as an afterthought summary of the body text. Start the candidate pool with the page angle and Step 7 additions (Cross-level dependency note) rather than generating meta candidates in isolation. For catalog-scale projects, use Step 8.11 to embed GIST logic at the template level instead of running the full per-page algorithm on every entity.

---

## Red-flag patterns

If any of these appear, the page likely violates GIST logic:

- long definitional opening,
- multiple sections saying the same thing,
- FAQ full of generic questions,
- lots of words but few distinctions,
- no scenario thinking,
- no "when not to" guidance,
- no practical criteria,
- weak first screen,
- generic trust language,
- copied competitor section rhythm,
- content that feels safe but unmemorable,
- too much "what it is," not enough "how to decide,"
- a title or description built from abstract quality words instead of a verifiable fact,
- a title and description that restate the same fact in different words without a standalone-exposure justification,
- a catalog template built around a generic feature slot instead of a concrete, verifiable attribute,
- a time-bound fact left in a title with no review date flagged,
- a structural/operational fallback fact used without checking Replaceability or Verifiability.

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

### 9. Meta-field selection heuristic
If a title/description candidate fact only makes the field sound different but not more decision-relevant:
- discard it and search for a fact that changes what the user expects, not just how it is phrased.

### 10. Fallback-before-filler heuristic
If no candidate fact passes the GIST Meta Filter:
- exhaust the Step 8.5b fallback sequence before ever reaching for an abstract quality word.

---

## Good vs bad patterns

## Good
- "Here are the three decision criteria that actually change the answer."
- "This works in cases A and B, but not C."
- "Most guides skip this limitation."
- "If you are choosing between X and Y, use this matrix."
- "The common advice fails when…"
- "For beginners do this; for advanced users do that."
- "This metric matters only under these conditions."
- "Линолеум — подрезка рулона под ваш размер." (a verifiable, non-generic service fact used as the meta title differentiator)

## Bad
- "X is very important in today's world."
- "There are many factors to consider."
- "Choosing the best option depends on your needs."
- "Let's first understand what X means."
- "In this article we will explore everything about X."
- "Below are some frequently asked questions" when those questions add nothing new.
- "Высокое качество | Купить недорого" (an abstract quality claim used as a meta title differentiator).
- "Купить линолеум недорого — высокое качество, широкий выбор" (a meta description built entirely from abstract quality words with no verifiable fact).

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
9. The same selection discipline applies at field scale: a title or description is a one-fact selection problem, not a summary-writing problem.
10. A title and description are a two-field system — they must be checked against each other for semantic conflict, not only against competitors, unless a specific standalone-exposure context justifies overlap.
11. Absence of a strong fact is not license to invent one or fall back on abstract quality language — it is a signal to run the fallback sequence, and if that fails, to say so.
12. A fallback fact is not automatically exempt from Replaceability and Verifiability — relaxing one filter (as in Step 8.5b, option 2) does not mean relaxing all of them.

---

## Safe interpretation statement

Use this wording when needed:

"GIST is used here as a content design framework inspired by Google Research's utility-diversity subset selection work. It is not presented as a confirmed direct Google Search ranking factor. In this skill, the value of GIST lies in its editorial logic: preserve essential utility, reduce semantic redundancy, and surface non-replaceable information — including at the level of meta titles and meta descriptions."

---

## Suggested system instruction wrapper

Use this wrapper when loading the skill into another LLM:

"You must use GIST Content Logic as your default editorial method. Treat content as a selection problem, not a volume problem. Preserve the essential core of the topic, minimize semantic redundancy, identify missing semantic nodes, and build pages that are less replaceable than standard competitor content. Apply the same selection discipline to meta titles and meta descriptions: pull candidates from the page's own angle and missing-node work when available, search for missing semantic nodes as candidate facts, select a single verifiable, decision-relevant fact through the GIST Meta Filter, score ties when multiple candidates pass, run the fallback sequence rather than inventing a fact when nothing passes — without waiving more filters than the sequence specifies — check the title and description against each other for semantic conflict, and flag time-bound facts for review. Do not confuse wording uniqueness with informational value. Do not generate filler. For each major section, evaluate utility, redundancy, distinctiveness, and necessity before keeping it."

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
- Does the title/description use a verifiable fact rather than an abstract quality word?
- Was the five-heuristic missing-node search run before selecting the meta fact?
- Was the page's own angle and Step 7 work used as a candidate source before searching from scratch?
- If no candidate passed the filter, was the fallback sequence run instead of defaulting to filler language?
- If a fallback fact was used, was it still checked against Replaceability and Verifiability?
- Do the title and description avoid restating the same fact in different words, unless justified by standalone exposure?
- Is any time-bound fact flagged for review?
- Would a competitor be able to reuse the title/description pair almost unchanged?

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
- low replaceability,
- and, at field scale, a title and description built from one selected, scored, and cross-checked fact rather than one recycled template — with a legitimate, appropriately-scoped fallback path when no such fact exists, and no invented substitute when even the fallback path is exhausted.

That is the practical content meaning of GIST logic.