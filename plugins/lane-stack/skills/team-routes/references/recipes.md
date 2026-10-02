# Route recipes

Starting points, not scripts. `∥` = parallel, `→` = after. Drop a step whose
output is already on disk; add one the goal needs.

| Goal looks like | Route | Deliverable |
|---|---|---|
| Prototype / wireframe of a site page | seo ∥ design-lead UX read (only if a page or competitor exists) → copy-lead → design-lead `prototype` → design-lead `audit` of the prototype | `.agents/prototypes/site/<slug>/` |
| Prototype of an app screen or flow (no search traffic) | design-lead UX read → copy-lead (microcopy, labels) → design-lead `prototype` | `.agents/prototypes/app/<slug>/` |
| Branded mockup | prototype route if no prototype yet → design-lead `extract/seed` if no DESIGN.md → design-lead `mockup` | page `visual/` folder |
| New landing or page in code | prototype route → WRITE Loop (`read_first`: copy page, SEO brief, prototype, DESIGN.md) → browser-qa | merged code + QA report |
| Rewrite copy of an existing page | seo (if the page gets search traffic) → copy-lead → browser-qa only if the text is shipped | `.agents/copy/pages/<slug>.md` |
| Article / SEO content | seo-specialist (owns the whole content pipeline) | article under `.agents/seo/` |
| Redesign / «проверь дизайн» | browser-qa ∥ design-lead `audit` → fixes via WRITE Loop after «делай» | audit report, then code |
| Product feature with new UI | Explore → design-lead `prototype` (if the screen is new) → copy-lead (labels, errors, empty states) → WRITE Loop | merged code |
| Product feature without new UI, bug, refactor | WRITE Loop only | merged code |
| Market or competitor question | tavily | `.agents/research/<slug>.md` |
