# Floating hands: cause and fix

## Reported symptom

Several cutscenes showed hands hovering with no arm attached.

## Reproduced by recording the real draw calls

A colour-distance pixel mask was unreliable here — `Ink` supersamples, and wood
and skin are close in RGB — so the defect was measured by intercepting
`_hand()` / `Brush.line()` / `Brush.poly()` during a real render.

Five shots called `_hand()` with no limb attached:

| shot | hands | problem |
|---|---|---|
| `CS04/photo_print` | 2 | palms on the table, nothing attached |
| `CS04/photo_fading` | 2 | same |
| `CS05/recipe_stir` | 1 | stirring hand floating above the mug |
| `CS06/stitch_hands` | 2 | palms over the cloth, one with a ribbon at the wrist and no sleeve |
| `CS08/real_hands` | 2 (+2 overlay) | near two-hander plus the animated finger overlay |

`CS01/ribbon_hands` already drew thin skin strokes, but they stopped ~79 px short
of each wrist, so both hands still read as detached.

## Fix

`_forearm(brush, wrist, exit_point, thickness, cuff)` draws a **tapered quad**:
narrow at the wrist, widening toward the frame edge, plus a sleeve band with a
darker cuff opening. A constant-width stroke was rejected during review because
it read as a table leg.

- Each floating hand now starts its forearm a little behind the palm centre, so
  the limb emerges from under the fingers instead of covering them.
- Close-up palms in `photo_print` / `photo_fading` are scaled 1.9x: at scale 1
  the palm was the same width as its forearm and the whole limb looked like a
  rounded stick.
- `real_hands` gets one forearm per hand (NUR's from the left sleeve, DARA's from
  the right), and the animated `_gesture` overlay gets wrist stubs that run off
  its own edges.

## Verification

`tests/v4/test_story_floating_hands.py` — 26 tests, written first and failing
before the fix. They assert, per shot:

- the expected number of close-up hands is drawn;
- every palm has a skin limb within 55 px of its wrist;
- that limb reaches a frame edge, so an arm is never cut mid-air;
- the palm is at least 1.15x wider than the arm it joins;
- limbs are thick enough to read as arms.

Pixel slices through a repaired frame confirm the wrist narrowing (skin width
~21 px at the palm, 29-38 px along the forearm) with the cuff present.

## Honest limitations

- Hands are still stylised mitten-fists: no separated fingers. That matches the
  rest of the artwork but is not anatomical illustration.
- Close-up arms enter from the frame edge, so no shoulder connects them to a
  seated body. That is normal for this kind of cropped shot, not a defect.

## ribbon_hands: what changed and what did not

Both palms used to sit beside the ribbon — the left one was 131 px from its
left edge — so the shot read as two hands hovering near a prop. They now close
on the ribbon: each palm centre lands inside the ribbon's bounding box, the
palms overlap its edge without smothering the bow, and each wrist faces the
forearm that leaves the frame. `tests/v4/test_story_ribbon_grip.py` pins that
placement.

The *shape* of the grip is unresolved, and this is worth stating plainly.
Four attempts were built and rejected on visual review:

1. separate curled digits drawn as closed contours — read as berry clusters;
2. fingers as overlapping discs along an arc — same problem, lumpier;
3. fingers as tapered `_limb` beziers with nails — still read as fused tubes;
4. palm-plus-fingertip-scallops with an opposed thumb — the fingertips were
   geometrically inside the palm mass, so they were swallowed and it rendered
   as one blob.

`paint_grip` was removed rather than left in the tree unused. The shot now uses
the same mitten palm as every other close-up hand, which is stylistically
consistent and reads as "hands at the ribbon knot", but it does not depict a
grip with wrapping fingers. Producing that needs hand-drawn art, not another
procedural helper.

Captures: `before/` (defect), `after/` (current), plus
`CS01-ribbon-both-5x.png` and the per-hand 5x crops for direct inspection.
Full suite: **528 passed** — declared = collected = 528, zero
failures/errors/skips (`pytest.xml` in this folder), including 4 ribbon-grip
tests, 26 floating-hand tests, 58 seated-arm tests, 7 pause-menu tests and 5
launcher tests.