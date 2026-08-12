---
version: alpha
name: REPLACE_ME
description: REPLACE_ME — extract tokens from code (tokens.css / @theme / tokens.json). Do not invent brand colors without // hypothesis.

# Google Labs DESIGN.md format (@google/design.md). Full canon:
# skills/project-onboard/references/design-md-standard.md
# Validate: npx @google/design.md lint docs/DESIGN.md

colors:
  # primary: "#000000"
  # surface: "#FFFFFF"

typography:
  # body-md:
  #   fontFamily: Inter
  #   fontSize: 16px
  #   fontWeight: 400
  #   lineHeight: 1.5

rounded:
  # md: 8px

spacing:
  # md: 16px

components: {}
---

# REPLACE_ME Design System

> Filled by project-onboarder when `has_ui: 1`.  
> **Layer 1 (YAML above)** = machine tokens for agents.  
> **Layer 2 (sections below)** = rationale.  
> Runtime CSS remains source for shipping UI — keep front matter in sync with code.

## Overview

Brand personality, audience, emotional tone. (Edit from evidence.)

## Colors

Semantic roles and how they map to tokens above. Cite token file paths.

## Typography

Type scale / pairings used in the product. Link font loading code if any.

## Layout

Grid, spacing rhythm, breakpoints (from real CSS/Tailwind config).

## Elevation & Depth

Shadow vs tonal layer strategy (from code).

## Shapes

Corner radius language.

## Components

Atom-level notes (button/input/card) referencing `{colors.*}` / `{typography.*}` tokens.

## Do's and Don'ts

- Do: …
- Don't: invent colors outside tokens; bypass primitives; …

## Code pointers

- Tokens: `path/to/tokens`
- UI kit: `path/to/components`
- Architecture: `docs/ARCHITECTURE.md`
