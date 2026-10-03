# Typeset (impeccable)

Upstream: [pbakaus/impeccable typeset](https://github.com/pbakaus/impeccable/blob/main/plugin/skills/impeccable/reference/typeset.md) + typography rhythm. `DESIGN.md` of the surface wins on faces and tokens.

Do **not** install the impeccable binary or hooks. This file is the check we actually run.

## Roles

Name jobs, not pixel values: display, heading, subhead, body, caption/meta.
Adjacent roles must be distinguishable at a glance — size **and** weight **and** space. If two sizes are within ~15–20%, they are the same role; merge or pull them apart.

Body floor: 16px. Headings: line-height 1.05–1.2. Body: 1.5–1.7. Measure 45–75ch (this site: 62ch on leads).

## Vertical rhythm

Body line-height is the unit. Here body is 16px × 1.5 → **24px**. Margins and gaps are 12 / 24 / 48 / 72, not 16+20+28 stacked at random.

**A heading belongs to what follows.** More space above it than below it. Tight group: heading + first paragraph. Wide gap: end of one section → next heading.

Do not combine flex `gap` and extra `mt-*` on the same children — it double-marks the beat.

Paragraph rhythm: space between paragraphs **or** first-line indent, not both.

## Verify (answer with a selector, not “yes”)

1. H1 / H2 / body / meta — can you tell them without reading?
2. Space above each H2 > space below it?
3. H1→lead tighter than lead→next section?
4. Caption sits on its parent line (4–8px), not on a new “block”?
5. Long Cyrillic headings wrap without colliding the next block?

Then fix the page. Do not restyle the brand.
