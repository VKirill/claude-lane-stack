---
name: design-md-standard
description: |
  Google-labs DESIGN.md format spec — YAML front matter for machine-readable tokens + Markdown
  body for prose. Includes full template, OKLCH color guidance, WCAG AA contrast checklist,
  and the `npx @google/design.md` CLI workflow (spec / lint / diff / export). Use whenever
  generating or auditing a design system document.
license: MIT
---

# DESIGN.md Standard

## Why DESIGN.md Exists

DESIGN.md is a **two-layer** plain-text document that serves as the living source of truth for a design system:

- **Layer 1 — YAML front matter (machine tokens):** Structured, typed design tokens that AI agents and tools can parse, validate, and convert. Tokens are the normative values.
- **Layer 2 — Markdown body (human prose):** Rationale, brand personality, visual intent, and design decisions. Prose may use descriptive color names ("Midnight Forest Green") that correspond to systematic token names (`primary`). Prose provides context; tokens provide precision.

Both layers together allow an AI agent to understand *what* the design is (tokens) and *why* it looks that way (prose), producing consistent outputs across tools and sessions.

---

## Required vs Optional Elements

**Required:**
- `name` field in YAML front matter
- At least one token category (`colors`, `typography`, `rounded`, `spacing`, or `components`)

**Optional sections** — when present, they MUST appear in this order:

1. **Overview** (also: "Brand & Style") — brand personality, target audience, emotional tone
2. **Colors** — palettes with semantic roles
3. **Typography** — type scale with font properties
4. **Layout** (also: "Layout & Spacing") — grid system, spacing scale
5. **Elevation & Depth** (also: "Elevation") — shadow, tonal layer, or flat strategy
6. **Shapes** — corner radius language
7. **Components** — atom-level style tokens (buttons, inputs, chips, etc.)
8. **Do's and Don'ts** — practical guardrails

All sections use `##` headings. An optional `#` heading may appear for document titling but is not parsed as a section.

---

## Token Schema (Full Type Reference)

DESIGN.md tokens follow a subset of the [Design Token JSON spec](https://www.designtokens.org/tr/2025.10/format/).

### Primitive Types

| Type | Format | Examples |
|------|--------|---------|
| **Color** | `"#RRGGBB"` hex, sRGB | `"#1A1C1E"`, `"#B8422E"` |
| **Dimension** | string with unit | `"48px"`, `"0.5rem"`, `"1.5em"` |
| **Token Reference** | `"{path.to.token}"` | `"{colors.primary}"`, `"{rounded.md}"` |

Valid units for Dimension: `px`, `em`, `rem`.

### Full Schema

```yaml
version: <string>          # optional, current: "alpha"
name: <string>             # REQUIRED — brand/product name
description: <string>      # optional free-text description

colors:
  <token-name>: <Color>    # e.g. primary: "#1A1C1E"

typography:
  <token-name>:
    fontFamily: <string>           # e.g. "Inter"
    fontSize: <Dimension>          # e.g. "48px"
    fontWeight: <number>           # 100–900, e.g. 600
    lineHeight: <Dimension|number> # unitless preferred, e.g. 1.5
    letterSpacing: <Dimension>     # e.g. "-0.02em"
    fontFeature: <string>          # font-feature-settings value
    fontVariation: <string>        # font-variation-settings value

rounded:
  <scale-level>: <Dimension>  # sm/md/lg/xl/full common

spacing:
  <scale-level>: <Dimension|number>  # base/xs/sm/md/lg/xl common

components:
  <component-name>:
    backgroundColor: <Color|TokenRef>
    textColor: <Color|TokenRef>
    typography: <TokenRef>
    rounded: <Dimension|TokenRef>
    padding: <Dimension|TokenRef>
    size: <Dimension>
    height: <Dimension>
    width: <Dimension>
  <component-name-variant>:  # e.g. button-primary-hover
    backgroundColor: <Color|TokenRef>
```

**Token References** use `{path.to.token}` syntax. In most sections, references must point to primitive values (e.g., `{colors.primary-60}`). Inside `components`, references to composite values (e.g., `{typography.label-md}`) are also permitted.

**Scale levels** for `rounded` and `spacing`: any descriptive string key is valid. Recommended: `xs`, `sm`, `md`, `lg`, `xl`, `full`.

---

## CLI Workflow — `@google/design.md`

Tool is installed globally as `@google/design.md` v0.1.1.

### Commands

```bash
# 1. Inject the latest canonical spec into context (call FIRST)
npx @google/design.md spec

# 2. Validate a DESIGN.md file against the spec
npx @google/design.md lint path/to/DESIGN.md

# 3. Compare two versions (diff for design review)
npx @google/design.md diff DESIGN.md DESIGN-v2.md

# 4. Export tokens to Tailwind JSON format
npx @google/design.md export --format json-tailwind DESIGN.md

# 5. Export tokens to DTCG (Design Token Community Group) format
npx @google/design.md export --format dtcg DESIGN.md
```

### Agent Workflow (Mandatory Order)

1. **Call `npx @google/design.md spec` FIRST** — injects the up-to-date spec into the agent's context window. Do not skip this step; the spec evolves and your training data may be stale.
2. **Write `DESIGN.md`** using the spec as reference.
3. **Call `npx @google/design.md lint <path>`** to verify the output is valid.
4. Fix any lint errors, re-lint, confirm green.

---

## Full Copy-Pasteable Template

Replace all placeholder values with brand-specific content.

```markdown
---
version: alpha
name: Lumora Studio
description: A bold, editorial creative agency platform with warm ink tones and deliberate whitespace.

colors:
  primary: "#1C1917"
  primary-light: "#44403C"
  secondary: "#C84B31"
  secondary-light: "#E07B64"
  neutral: "#FAF9F7"
  neutral-mid: "#E7E5E4"
  surface: "#FFFFFF"
  on-surface: "#1C1917"
  error: "#B91C1C"
  success: "#15803D"

typography:
  display:
    fontFamily: Playfair Display
    fontSize: 72px
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.03em
  h1:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -0.02em
  h2:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.7
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1
    letterSpacing: 0.06em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4

rounded:
  none: 0px
  sm: 2px
  md: 6px
  lg: 12px
  xl: 20px
  full: 9999px

spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  xxl: 96px
  gutter: 32px
  section: 80px

components:
  button-primary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
    typography: "{typography.label-md}"
  button-primary-hover:
    backgroundColor: "{colors.secondary-light}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "11px 23px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: "10px 14px"
    typography: "{typography.body-md}"
---

# Lumora Studio Design System

## Overview

Lumora Studio serves high-end creative agencies and independent directors who need a digital presence that matches the weight of their work. The visual identity is rooted in **editorial restraint** — rich ink blacks, a single fiery accent, and generous off-white breathing room.

Personality: ambitious, editorial, precise. Not playful. Not corporate. The UI should feel like a beautifully typeset book held together by one bold thread of color.

Target audience: creative directors aged 28–45, portfolio-first, critically aware of design quality.

## Colors

The palette is built on deep ink neutrals anchored by a single, unmistakable accent.

- **Primary (#1C1917):** Near-black warm ink. Used for all headline text, navigation, and high-contrast UI chrome. Conveys permanence and craft.
- **Primary-light (#44403C):** Warm charcoal for secondary text, icons, and borders.
- **Secondary (#C84B31):** A volcanic terracotta-red. The sole driver of interaction — every CTA, active state, and brand highlight uses only this color.
- **Secondary-light (#E07B64):** Hover and focus state of the accent. Warmer, approachable.
- **Neutral (#FAF9F7):** Warm limestone page background. Softer than pure white.
- **Surface (#FFFFFF):** Pure white for cards, modals, and elevated containers.
- **Error (#B91C1C):** Standard semantic red for destructive actions and validation.

## Typography

Two typefaces carry the full system — **Playfair Display** for editorial authority, **Inter** for functional clarity.

- **Display / Headlines:** Playfair Display at tight tracking (-0.02em to -0.03em) creates a tension that reads as premium.
- **Body:** Inter Regular, generous line-height (1.6–1.7). Long-form readability without feeling airy.
- **Labels:** Inter Medium, loose tracking (+0.06em), uppercase-ready for UI chrome.
- **Caption:** Inter Regular, 12px — metadata only.

## Layout

The layout follows a **Fixed-Max-Width Grid** (max 1280px) with a 12-column system for desktop. Mobile collapses to a 4-column grid.

An 8px base spacing scale governs all internal rhythm. Section separators use 80px vertical spacing to create editorial breath. Cards carry 24px internal padding.

## Elevation & Depth

Depth is achieved through **Tonal Layers**, not shadows. Elevation reads as:

1. Page background (neutral/limestone)
2. Surface cards (white) — no shadow, just tonal contrast
3. Modals and dropdowns — a single `box-shadow: 0 4px 24px rgba(28,25,23,0.12)` at the top layer only

The system deliberately avoids heavy shadows that compete with the photography and editorial content.

## Shapes

**Architectural Minimalism**: nearly all corners are sharp or minimally rounded (2–6px). This maintains the engineered, editorial feel. Rounded `full` (pill) is reserved exclusively for status badges and avatar containers.

## Components

Buttons use the secondary (terracotta) accent as the only filled variant. The secondary button is an outlined ghost — never a filled neutral color. Input fields match card rounding (6px) and carry a 1.5px border in neutral-mid, activating to secondary on focus.

## Do's and Don'ts

- Do use `secondary` (#C84B31) only for the single most important action per screen
- Don't mix the Playfair editorial headlines with any sans-serif in the same visual hierarchy level
- Do maintain WCAG AA contrast (4.5:1 for body, 3:1 for large text/UI)
- Don't use more than two font weights on a single screen
- Do rely on whitespace and type scale to establish hierarchy — resist adding color variety
- Don't apply rounded corners larger than 12px on any interactive element except badges
```

---

## OKLCH Color Guidance

Modern design systems use **OKLCH** for perceptually uniform color manipulation (P3 wide gamut). DESIGN.md tokens require sRGB hex, but your design process should start in OKLCH.

### Why OKLCH

- Perceptually uniform: equal lightness steps look visually equal (unlike HSL)
- P3 wide gamut: richer reds, greens, blues on modern displays
- Predictable tonal palettes: change L to lighten/darken without hue shift

### Two-Format Pattern

Generate your palette in OKLCH, then provide sRGB hex fallbacks in DESIGN.md tokens.

```css
/* In CSS (for browsers that support P3) */
:root {
  --color-secondary: oklch(52% 0.18 28);          /* P3 wide gamut */
  --color-secondary-srgb: #C84B31;                 /* sRGB fallback */
}

/* Progressive enhancement */
.button-primary {
  background-color: var(--color-secondary-srgb);   /* sRGB fallback first */
  background-color: oklch(52% 0.18 28);            /* P3 override */
}
```

```yaml
# In DESIGN.md — use the sRGB hex (spec requirement)
colors:
  secondary: "#C84B31"   # oklch(52% 0.18 28) in P3 — sRGB approximation stored here
```

### OKLCH Parameters

| Parameter | Range | Meaning |
|-----------|-------|---------|
| L (Lightness) | 0–100% | Perceptual brightness |
| C (Chroma) | 0–0.4+ | Saturation / colorfulness |
| H (Hue) | 0–360° | Color angle (28 = red-orange) |

### Tonal Palette Generation (Semantic Tokens)

```
primary base:    oklch(15% 0.01 50)   → #1C1917
primary-40:      oklch(40% 0.02 50)   → #44403C
secondary base:  oklch(52% 0.18 28)   → #C84B31
secondary-60:    oklch(62% 0.16 28)   → #E07B64
neutral-95:      oklch(97% 0.005 70)  → #FAF9F7
```

---

## WCAG AA Contrast Guidance

WCAG 2.1 Level AA requirements:

| Text Type | Minimum Contrast Ratio |
|-----------|----------------------|
| Normal text (< 18px regular, < 14px bold) | 4.5:1 |
| Large text (≥ 18px regular, ≥ 14px bold) | 3:1 |
| UI components and graphical objects | 3:1 |

### Color Pairs Matrix — Lumora Studio

All ratios calculated against WCAG relative luminance formula.

| Foreground | Background | Hex Pair | Approx. Ratio | AA Normal | AA Large |
|-----------|-----------|----------|---------------|-----------|----------|
| primary (#1C1917) | neutral (#FAF9F7) | dark on light | **16.8:1** | PASS | PASS |
| primary (#1C1917) | surface (#FFFFFF) | dark on white | **18.1:1** | PASS | PASS |
| neutral (#FAF9F7) | primary (#1C1917) | light on dark | **16.8:1** | PASS | PASS |
| neutral (#FAF9F7) | secondary (#C84B31) | light on accent | **4.7:1** | PASS | PASS |
| surface (#FFFFFF) | secondary (#C84B31) | white on red | **4.9:1** | PASS | PASS |
| primary-light (#44403C) | neutral (#FAF9F7) | mid on light | **8.2:1** | PASS | PASS |
| secondary (#C84B31) | neutral (#FAF9F7) | accent on light | **4.7:1** | PASS | PASS |
| secondary (#C84B31) | surface (#FFFFFF) | accent on white | **4.9:1** | PASS | PASS |
| neutral-mid (#E7E5E4) | surface (#FFFFFF) | border only | **1.3:1** | FAIL | FAIL (border/decoration only — not text) |

### Validation Checklist

- [ ] `primary` text on `neutral` background: minimum 4.5:1
- [ ] `on-surface` text on `surface`: minimum 4.5:1
- [ ] CTA button label on `secondary` fill: minimum 4.5:1
- [ ] Placeholder text (60% opacity): still meets 4.5:1 against its background
- [ ] Error color on white background: minimum 4.5:1
- [ ] Focus ring has 3:1 contrast against adjacent colors
- [ ] Disabled state: intentionally exempt from contrast requirements (but document this)

---

## Reference Snippets — Token Naming Conventions

### Material Design 3 (Google)

```yaml
# Material 3 uses role-based semantic naming
colors:
  primary: "#6750A4"
  on-primary: "#FFFFFF"
  primary-container: "#EADDFF"
  on-primary-container: "#21005D"
  secondary: "#625B71"
  on-secondary: "#FFFFFF"
  surface: "#FFFBFE"
  on-surface: "#1C1B1F"
  error: "#B3261E"
  on-error: "#FFFFFF"
```

Key lesson: Material 3 pairs each color with its `on-*` counterpart, ensuring all text/icon combos are pre-validated.

### IBM Carbon Design System

```yaml
# Carbon uses numeric tonal scales per palette
colors:
  gray-10: "#F4F4F4"
  gray-20: "#E0E0E0"
  gray-70: "#525252"
  gray-100: "#161616"
  blue-60: "#0F62FE"
  blue-70: "#0043CE"
  red-60: "#DA1E28"
  green-50: "#198038"
```

Key lesson: Carbon's numeric scale (10–100) makes tonal relationships explicit and machine-parseable.

### Tailwind CSS Tokens

```yaml
# Tailwind semantic layer (v4 CSS variables pattern)
colors:
  background: "#FFFFFF"
  foreground: "#09090B"
  card: "#FFFFFF"
  card-foreground: "#09090B"
  primary: "#18181B"
  primary-foreground: "#FAFAFA"
  secondary: "#F4F4F5"
  secondary-foreground: "#18181B"
  muted: "#F4F4F5"
  muted-foreground: "#71717A"
  accent: "#F4F4F5"
  destructive: "#EF4444"
  border: "#E4E4E7"
  ring: "#18181B"
```

Key lesson: Tailwind v4 uses `foreground` as the canonical `on-*` naming variant — consistent with CSS custom property ergonomics.

---

## Validation Checklist

Run through this checklist before calling `npx @google/design.md lint`:

### Schema Validation
- [ ] YAML front matter opens and closes with exactly `---` on its own line
- [ ] `name` field is present in front matter
- [ ] At least one of: `colors`, `typography`, `rounded`, `spacing`, `components`
- [ ] All Color values start with `#` and are valid sRGB hex
- [ ] All Dimension values have valid units: `px`, `em`, or `rem`
- [ ] `fontWeight` values are numeric (400, not "regular")
- [ ] No duplicate `##` section headings in the Markdown body

### Token Integrity
- [ ] Broken token refs: every `{path.to.token}` resolves to an existing key
- [ ] No orphaned tokens: every defined token is referenced in at least prose or components
- [ ] `primary` color is defined (required by WCAG guidance)
- [ ] Typography includes at least one body-level style

### Section Order
- [ ] If Overview present: appears before Colors
- [ ] If Colors present: appears before Typography
- [ ] If Typography present: appears before Layout
- [ ] If Layout present: appears before Elevation & Depth
- [ ] If Elevation & Depth present: appears before Shapes
- [ ] If Shapes present: appears before Components
- [ ] If Components present: appears before Do's and Don'ts

### Accessibility
- [ ] Primary text on background meets WCAG AA 4.5:1
- [ ] CTA (accent) on its button background meets WCAG AA 4.5:1
- [ ] Error color meets WCAG AA on white/surface
- [ ] All interactive component states (hover, focus, active) are defined

### Completeness
- [ ] prose in each section explains *why*, not just *what*
- [ ] Component tokens reference upstream color/typography/rounded tokens (no hardcoded duplicates)
- [ ] Do's and Don'ts covers at least: color usage, typography mixing, contrast

---

## How an Agent Should Use This Skill

### Step-by-step protocol for `worker-brand-token-designer`

**Step 1 — Always call spec first**

```bash
npx @google/design.md spec
```

This injects the canonical, up-to-date spec into context. Your training data may reflect an older version. Do not skip this.

**Step 2 — Build tokens from brand inputs**

Inputs available: brief, audience portrait, competitor analysis, strategy doc. Extract:
- Key colors from brand personality (use OKLCH internally, convert to sRGB hex for tokens)
- Typography from tone: editorial = serif display + sans body; tech = geometric mono; friendly = rounded sans
- Spacing from density: dense (data apps) vs. airy (marketing sites)

**Step 3 — Write DESIGN.md using the template above**

Follow section order. Write prose FIRST (rationale, decisions), then ensure YAML tokens match the prose.

**Step 4 — Lint immediately**

```bash
npx @google/design.md lint path/to/DESIGN.md
```

Fix every error. Common issues:
- Token reference typo: `{colors.prmary}` instead of `{colors.primary}`
- Invalid Dimension unit: `"1.5"` instead of `"1.5rem"`
- fontWeight as string: `"bold"` instead of `700`
- Missing `---` closing delimiter

**Step 5 — Verify contrast pairs**

Check the WCAG AA matrix manually or with a contrast checker before finalizing. Document which pairs you intentionally left low-contrast (disabled states, decorative elements) in Do's and Don'ts.

**Step 6 — Export if needed**

```bash
# Tailwind integration
npx @google/design.md export --format json-tailwind DESIGN.md > tokens.json

# Design tool integration (Figma, Penpot)
npx @google/design.md export --format dtcg DESIGN.md > tokens.dtcg.json
```

### Anti-patterns to avoid

- Do not generate DESIGN.md without running `npx @google/design.md spec` first
- Do not hardcode color values in `components` — always reference `{colors.token-name}`
- Do not invent section names — use only the 8 canonical sections listed in the spec
- Do not use HSL or RGB notation in token values — hex sRGB only
- Do not skip linting — a DESIGN.md that fails lint is not deliverable
