# Designer workflow

Use for design-lead prototype/mockup work and implementation handoffs. Existing
brand, product constraints, and the requested deliverable govern the choices.

## Brief before visuals

Record a compact brief in the artifact's notes: audience and context, user's job,
primary action and success condition, required content, surface/viewport, existing
brand/components, constraints, evidence and open assumptions. Reuse supplied
copy/SEO briefs. Never invent demand, research participants, metrics or claims.

For a flow, map entry → action → feedback → next step, including back/cancel and
failure recovery. For an individual page, order content around the decision the
visitor needs to make. Show a second direction only when a real unresolved tradeoff
warrants comparison; recommend one and explain the cost/benefit.

## Choose the right artifact

- Gray structure/click path: design-lead `MODE=prototype`, apply `page-prototype`
  and its shared kit exactly. Brand assets are labels/placeholders in this mode.
- Styled mockup: `MODE=mockup`. Create `.agents/prototypes/site/<slug>/visual/`,
  `.agents/prototypes/app/<app>/<slug>/visual/`, or
  `.agents/prototypes/flows/<flow>/visual/`. Use `index.html`, local `style.css`
  and optional `script.js`; flow screens link locally from index. Keep the gray
  prototype intact and register the visual entry in `.agents/prototypes/INDEX.md`.
- Product implementation: give the parent a handoff for a writer run. Never copy
  the mockup into product directories or claim that static controls save real data.

Mockups use semantic HTML and native CSS/JS, with no package install or CDN.
Reuse tokens from the relevant DESIGN.md and supplied licensed/local assets.
If no brand exists, mark a provisional direction in `visual/README.md`; do not
silently make it the canonical brand. Preserve the product's typography and
icon family. No missing remote stock images, invented testimonials or fake logos.
Forms and state controls simulate their effects locally, with no data submission.

Keep styling in the visual folder; never modify `_kit/proto.css` or `proto.js`.
The gray kit is optional for a styled mockup and must not constrain its visual
language. Use realistic content lengths, including the target language's glyphs.

## Evidence and usability pass

Inspect the rendered artifact when browser evidence is available. Ask the parent
for browser-qa with the local artifact path or already running URL and concrete
cases; do not launch a server or a child agent yourself. Record unverified checks
when browser tools/screenshots are unavailable, without claiming visual success.

Check the requested sizes; absent specifics, use 375 / 768 / 1280 px as samples:

- Main task and content order remain clear; primary action describes its outcome.
- Long titles, localized text, empty lists and validation errors fit. No accidental
  overflow, clipped controls or unreadable images; tables keep deliberate scrolling.
- Keyboard navigation, visible/unobscured focus, labels and semantic controls;
  dialogs return focus, state changes communicate feedback, motion has a reduced mode.
- Loading, success, empty, error, disabled and hover/focus states where relevant.
  Critical information is not available only on hover or represented only by color.
- Verify contrast from actual colors; do not infer a pass from a screenshot alone.
  Distinguish functional accessibility issues from visual preferences.

Publishing is optional and only on request. For an approved public preview, use
page-prototype's `references/publish.py --bundle <visual/index.html>` only when
the page is self-contained HTML with sibling CSS/JS. That publisher does not
bundle local images, fonts, or additional HTML screens. For such artifacts,
keep local delivery and report the preview limitation to the parent; do not
publish a broken flow or silently remove assets. For supported pages, include
only non-sensitive content, check the returned URL and report upload failure.
Local delivery remains valid without an external preview.

## Handoff to implementation

In `visual/README.md` (or the audit report), give the parent:

1. Artifact path, user job, primary flow, assumptions and chosen direction.
2. Existing components/tokens to reuse; proposed additions explicitly marked.
3. Responsive layout and state behavior, including keyboard/error recovery.
4. Asset/copy provenance and missing inputs; simulated behavior versus real needs.
5. Acceptance criteria with observed evidence and pending checks. No claim that a
   polished mockup proves a conversion lift, user validation or production readiness.

## Sources and adaptation

- [Anthropic frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design):
  subject-specific direction, coherent composition and critique against the brief.
- [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines):
  concrete checks for navigation, forms, focus, content and responsive behavior.
- [Impeccable](https://github.com/pbakaus/impeccable): existing local `impeccable-ui`
  provides structural review; no additional CLI/hooks installation is needed.
- [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): existing
  local search provides design candidates; evaluate their fit before adoption.

These are a curated methodology comparison, not a popularity ranking or a full
upstream mirror. Local scope and existing product decisions take precedence.

Reviewed upstream revisions (2026-09-26): Anthropic `33375500bcea98d610eb30ce10ac4e59b89c390d`,
Vercel `e3d624baaf29dc1fc645aff3e38f03e564d2d6b1`, Impeccable
`9d715cc4f5564a990ca8345abfdd5df6dc9b41c8`, UI/UX Pro Max
`dcc40ff5133ef78276117db0cc34e7b83cc8aeba`. These identify research sources,
not a claim that the vendored search datasets or tools were upgraded.
