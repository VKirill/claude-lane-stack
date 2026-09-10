# Layout rules (writer)

Match the app stack. SelfyStudio is Vue/Nuxt, not React/Next.
`DESIGN.md` of **this** surface wins over any default below.

## Structure

- Page: one `max-width` container (token or ~1200–1440px), not edge-to-edge body text.
- Grid over percentage flex math. One radius scale per surface.
- More space **above** a heading than below it. Tight groups, wide gaps between groups.
- Body measure ~65–75ch. Display tracking floor `-0.04em`.
- Full-height hero: `min-height: 100dvh`, never `100vh`.
- Touch targets ≥44px. Focus ring visible. Theme selection / caret / scrollbar from the palette.

## Hierarchy

- One primary CTA intent per view. Duplicate “contact us” / “get started” labels are a fail.
- Cards only when elevation is the hierarchy. No card-in-card. No 3 equal icon+title+text columns as the page spine.
- No eyebrow/kicker above every heading.
- Align shared baselines in card rows (title, price, CTA).

## Motion

- One authored moment, not a fade-in on every section.
- Animate `transform` / `opacity` (and materials if they stay smooth). Not `top`/`left`/`width`/`height`.
- Honor `prefers-reduced-motion`. No bounce/elastic easing unless `DESIGN.md` asks.

## States

Ship hover, active, disabled, loading (skeleton in the real layout), empty, error.
CTA text stays one line on desktop. Contrast AA: body 4.5:1, large 3:1. No gray-on-color.

## Stack

- Do not add a design-system package the repo does not already use.
- Do not swap Inter/purple-gradient “because taste said so” if `DESIGN.md` named the brand face and accent.
- Icons: one family already in the app. No hand-rolled SVG glyphs, no emoji-as-icon.
