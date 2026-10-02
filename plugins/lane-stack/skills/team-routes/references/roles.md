# Role cards

What each role needs to start and what it hands to the next step. The spawn
rules and «never a writer lane» limits live in `dev-orchestrator.md`, not here.

| Role | Needs (READ) | Hands over (WRITE) | Ask it to DECIDE | Cost note |
|---|---|---|---|---|
| **tavily** | question, market/region | `.agents/research/<slug>.md` with URLs | competitors, market facts, sources | cheap; use when a later role would otherwise guess facts |
| **seo-specialist** | slug, page goal, region, existing `.agents/seo/` | page brief under `.agents/seo/` (path in its `DONE`) | search intents, required blocks and their order, headings and keys, what competitors cover | expensive full harness; ask for a page-scoped brief, not a full passport cycle, unless the project has no SEO passport and the goal is SEO traffic |
| **copy-lead** | SEO brief, research, audience notes in `.agents/copy/` | `.agents/copy/pages/<slug>.md` | audience and offer, H1, block texts, CTA and button labels, UI microcopy, names of interface elements | marks unknown facts `[unknown]`; never writes SEO keys itself |
| **design-lead** `MODE=audit` (UX read) | goal, existing screens/URL, DESIGN.md | `.agents/session-log/DESIGN-AUDIT-*.md` | user job, primary action, hierarchy, engagement patterns, states | use before a prototype only when there is an existing page or competitor to read |
| **design-lead** `MODE=prototype` | SEO brief, copy page, UX notes | `.agents/prototypes/site/<slug>/` (or `app/`, `flows/`) | layout of blocks, interactions, empty/error states | gray kit only; pulls real text from the copy page |
| **design-lead** `MODE=mockup` | prototype, DESIGN.md, copy page | page `visual/` folder under `.agents/prototypes/` | brand look of the approved structure | after the prototype is accepted, not instead of it |
| **design-lead** `MODE=extract/seed` | app source or brief | `docs/DESIGN.md` packs | tokens, components | once per project, before the first mockup or UI run |
| **browser-qa** | URL, viewports, click path | `.agents/qa/<slug>/` report + shots | what breaks on 375/1440, broken flows | needs a live URL or a published prototype |
| **Explore / Plan** | codebase question | answer in chat or `.agents/plans/` | where code lives, how to split work | read-only; cheap |
| **run-supervisor** (WRITE Loop) | task YAMLs with `read_first` = specialist outputs | accepted code on main | — | only after specialist steps are done |
