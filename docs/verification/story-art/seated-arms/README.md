# Seated-figure arms: defect, cause, fix

## Reported symptom

The seated family shots read as a *floating torso*: the two women appear to have
no arms, and in the `tea`/`cloth` poses only a detached mitten-like hand was
visible on the tabletop.

## Reproduction (measured, not only visual)

`CS08/real_seated` rendered **1565 skin pixels above y=316 and 0 below it**.
`figure_layout()` places seated palms at world y≈346-355; the room table's top
plank spans y=316-369. Because the scene branch called `_table(art)` *after*
the figures, the table plank painted over every forearm and palm.

Affected shots (13): `CS02/mug_drawing`, `CS05/recipe_read`, `CS05/recipe_stir`,
`CS05/recipe_tea`, `CS06/cloth_wait`, `CS06/cloth_seated`, `CS06/cloth_door`,
`CS08/real_seated`, `CS08/real_tea`, `CS08/real_hands`, `CS08/real_cloth`,
`CS08/real_wide`, `CS08/real_faces`, `CS08/real_arrival`.

## Fix

Depth order is now explicit: **torso → table → props → arms**.

- `portraits.paint_arms()` holds the limb pass; `paint_figure(..., arms=)`
  accepts `True` (default, unchanged behaviour), `False` (torso only) and
  `'only'` (limbs alone).
- `renderer._seated_arms(art, x, y, scale, ...)` re-paints the limbs with the
  exact brush position, scale and facing of the original figure, after the
  table and its props.

`test_splitting_arms_into_two_passes_is_pixel_identical` proves the refactor is
pixel-identical to the single-pass render for 8 age/pose combinations, so
already-correct shots could not drift.

## Verification

- 58 tests in `tests/v4/test_story_seated_arms.py` pass; they were written
  first and failed against the old renderer.
- Each seated palm area must contain skin, not table colour.
- Each arm must be skin-continuous across the table's far edge.
- Table close-ups (`photo_print`, `photo_fading`, `mug_detail`, `real_mug`,
  `stitch_hands`) keep their table-foreground framing.
- Pixel inspection of `CS08/real_seated`, `CS05/recipe_read` and
  `CS05/recipe_tea` at 2x zoom confirms a continuous shoulder → elbow → hand
  limb with hands resting on the tabletop.

Captures: `after/*.png` (full frames) and `after/*-zoom.png` (2x crop of the
seat-to-table band). The `before/` folder holds the pre-fix story-art set.

Scene art, subtitles, timings and shot order were not changed.