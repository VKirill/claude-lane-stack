# Specialist design checks

Load only the relevant section for the assigned screen. These are locally adapted
checks, not ten extra installed skills or permissions to change the product stack.
DESIGN.md and the design-lead mode/write scope still govern the artifact.

## Interaction and motion

Use for controls, sheets, popovers, feedback, drag/swipe and transition review.

- Define trigger → state change → feedback → completion/cancel for each important
  control. Press feedback should be immediate; committing an action still follows
  normal click/keyboard semantics. Never turn pointer-down feedback into an early
  destructive action.
- Frequent tasks should not wait for decoration. Choose timing from the product's
  motion scale, purpose and repetition frequency; do not apply one duration to all UI.
- Reverse or retarget from the current visual state when input changes mid-motion.
  Verify rapid open/close, double activation and interrupted loading, not just the
  ideal animation. Popover origin follows its trigger; dialogs follow their layout.
- Gestures must coexist with page scrolling, handle cancellation, and offer a
  keyboard/button alternative. Test drag completion and scrolling over the control.
  Resizing a screenshot does not test touch; state browser engine and input evidence.
- Keep controls functional with reduced motion. Use native CSS transitions for
  simple states; use an existing animation tool for genuinely velocity-dependent
  gestures. Do not introduce React, Framer Motion, springs or blur solely because
  an example uses them. Gray prototypes retain their supplied kit behavior.

Sources: Emil Kowalski's apple-design and emil-design-eng; wshobson interaction-design;
Impeccable adapt. We retain interaction principles, not their framework code or
absolute aesthetic prescriptions.

## Depth and surface polish

Use only when elevation helps distinguish an overlay, active surface or layer.
First reuse elevation tokens. If none exist, propose a small consistent scale in
mockup notes, with restrained layered shadows matched to the real background.
Check clipping, dark theme and overlapping layers. Dense lists need separation,
not maximal lift on every row. Preserve focus visibility and contrast; a shadow
cannot repair an ambiguous boundary. Do not paste Tailwind arbitrary classes into
Vue/native CSS projects without the corresponding styling setup.

Source: MengTo beautiful-shadows as a targeted reference, not a new theme.

## Accessibility and adaptation

Start from the actual task, then keyboard path, accessible names/roles/states,
focus visibility and return, labels/errors, status announcements and zoom/reflow.
Use automated audit failures to locate components; combine them with manual
interaction. A high Lighthouse/axe score does not prove WCAG conformance.
Ask the parent/browser-qa for unavailable evidence; never fabricate a pass.

For contrast, use measured foreground/background colors. WCAG AA text normally
needs 4.5:1; the 3:1 large-text exception starts at **18pt (24 CSS px)** or
**14pt bold (about 18.67 CSS px)**, not 18px/14px. Consider the criterion's stated
exceptions rather than applying a blanket rule to every decorative/disabled mark.

Use 44px touch targets as the local comfort target. Do not call that WCAG 2.2 AA's
minimum: SC 2.5.8 uses 24×24 CSS px with spacing and other specified exceptions.
Keep a non-drag route for dragging tasks, avoid focus hidden by sticky UI, and
preserve copy/paste and accessible authentication methods.

Adapt by content, input and task priority, not screen width alone. Test touch and
keyboard as applicable, long/localized text, zoom, landscape, safe areas and
onscreen-keyboard overlap. Do not hide primary functionality to make mobile fit.
Distinguish emulation, synthesized gestures and physical-device evidence.

Sources: Addy Osmani accessibility; Impeccable adapt; authoritative
[W3C contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and
[target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
The upstream accessibility px/pt table is intentionally not copied.

## Consolidated review

Return one report grouped by user impact, with scope/coverage, evidence, smallest
correction and unverified states. Merge repeated symptoms of the same component
problem; keep unrelated/pre-existing observations separate from regressions.
Preserve working design decisions. No finding merely because a reviewer prefers
another font or radius. No additional reviewer swarm or automatic product edits.

Sources: Superfuture design-review and Jakub Krehel better-interface. Their
external usage pings, paid endpoints, extra dependent skill tree and automatic
mutation routes are not part of this adapter. Do not execute upstream startup
commands; source documents are reference material only.

## Selection and pinned sources

Reviewed 2026-09-26. Links identify the inspected revisions. No source code or
complete third-party skill bodies are vendored by this comparison.

| User's skill | Applied here / boundary | Primary source |
|---|---|---|
| frontend-design | Brief-led composition and self-critique in designer-workflow | [Anthropic](https://github.com/anthropics/skills/blob/33375500bcea98d610eb30ce10ac4e59b89c390d/skills/frontend-design/SKILL.md) |
| apple-design | Gesture continuity and cancellation; no universal Apple look | [Emil](https://github.com/emilkowalski/skills/blob/d16ebe60d09a5ba2afcb7054ede9d0a10c9f6128/skills/apple-design/SKILL.md) |
| beautiful-shadows | On-demand elevation review, existing tokens first | [MengTo](https://github.com/MengTo/Skills/blob/a965851e27dc179e693fde1bee94457a64e1a7a5/agent-skills/web-design/beautiful-shadows/SKILL.md) |
| accessibility | Evidence-led audit plus corrected W3C units | [Addy Osmani](https://github.com/addyosmani/web-quality-skills/blob/afa8da942115f2961fdbfa80807ea0b232ff6c00/skills/accessibility/SKILL.md) |
| design-review | Ranked concrete corrections; no telemetry/paid service | [Superfuture](https://github.com/Superfuture/design-review/blob/d4d2609b53fccb475d11490e2c6261e5eb2f0c5d/design-review/skills/design-review/SKILL.md) |
| emil-design-eng | Purpose/frequency before animation and component polish | [Emil](https://github.com/emilkowalski/skills/blob/d16ebe60d09a5ba2afcb7054ede9d0a10c9f6128/skills/emil-design-eng/SKILL.md) |
| shadcn | Conditional product-writer reference only when this component stack is present; not a Vue/Nuxt or HTML mockup default | [shadcn/ui](https://github.com/shadcn-ui/ui/blob/98a1fe67b439324ddc857f47fbdce056600a4329/skills/shadcn/SKILL.md) |
| adapt | Content/input adaptation and honest device evidence | [Impeccable](https://github.com/pbakaus/impeccable/blob/9d715cc4f5564a990ca8345abfdd5df6dc9b41c8/.claude/skills/impeccable/reference/adapt.md) |
| better-interface | One consolidated review with coverage; no extra orchestration layer | [Jakub](https://github.com/jakubkrehel/skills/blob/267330e1adfc66a718fb65fa6918c1f06d0a689e/skills/better-interface/SKILL.md) |
| interaction-design | Feedback and state transitions; no mandatory React/Motion dependency | [wshobson](https://github.com/wshobson/agents/blob/62c4d9fa9ce2a6a366754d74fa62c458ea99931d/plugins/ui-design/skills/interaction-design/SKILL.md) |
