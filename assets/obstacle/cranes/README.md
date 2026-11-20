# Modular tower cranes

Greyscale tower cranes assembled from independent parts the way a real crane is
bolted together: footing, lattice mast sections, slewing unit, operator cab,
tower head, jib, counter-jib, counterweight and hoist block. Every part is a
separate PNG, every shape variant has a different silhouette, and each part is
a composite of several primitives. The greyscale pixels are meant to be
multiplied with a seeded colour at runtime (`pygame.BLEND_MULT`), the same
trick the block and rocket libraries use, so one part set yields any palette.

```
cranes/
  parts/
    base/           concrete slab, four pads, steel grillage, stepped plinth
    mast/           square lattice, X-braced, diamond-braced, ladder, tubular
    slew/           slewing ring, machined box, toothed gear ring
    cab/            box, rounded, slanted glass, hut with roof overhang
    apex/           pyramid truss, cage, spike with sheave, tripod
    jib/            lattice truss, tapered truss, parallel-chord truss,
                    plate girder
    counterjib/     lattice arm, railed walkway, boxed arm
    counterweight/  cast slab, stack of three, ribbed block, hollow frame
    hoist/          single sheave block, double sheave, open hook,
                    spreader beam
  variants/   24 seeded sample cranes, 660x640
  parts.json  part index (shape, tone, size, origin)
  variants.json  which parts each sample used, plus section count,
                 hoist position/drop and pendant style
  preview.png contact sheet
```

Counts: 8 footings, 10 mast sections, 6 slew units, 8 cabs, 8 tower heads,
8 jibs, 6 counter-jibs, 8 counterweights and 8 hoists — 70 parts, combining
into far more cranes than the 24 seeded samples. Every family comes in two
tones (`mid`/`dark` or `mid`/`light`).

## How a part is built

Each part is a composite, not a single outline:

- **base**: tapered slab / four pads / crossed grillage / three stacked plinths,
  plus a top plate, skirt lines and anchor bolts;
- **mast**: two vertical chords, four lattice cells per section (rungs and/or
  X or diamond braces), end bolt plates — or a bolted tube column with flanges,
  a weld seam, a ladder strip and bolt rows;
- **slew**: ring or box band with a highlight lip, panel lines and a tooth row;
- **cab**: body polygon (or rounded) + front glass band + mullion + dark lower
  panel + roof plate + optional second roof;
- **apex**: pyramid / cage / spike / tripod truss, filled with cross-braces and
  rungs, crowned with a sheave wheel and pin;
- **jib**: two flanges + diagonal web + vertical posts + mid chord + end plate,
  or a plate girder with stiffeners;
- **counter-jib**: lattice arm, or a railed walkway with posts and handrail;
- **counterweight**: cast block with ribs, bolt eyes or a lifting eye arc, or a
  stack of three slabs, or a hollow frame with cross bracing;
- **hoist**: cheek plate + one or two sheaves + shackle + hook, or a spreader
  beam with two hanging hooks.

## Attaching / randomizing

`echo_game.generate_cranes.random_choice(rng)` holds the composition rules:
one part per family, 3–4 mast sections, mast section height 92–108 px, optional
cab (85%), hoist at 28–72% along the jib with a 52–150 px drop, and one of
three pendant styles (`single`, `double`, `truss`).

`parts.json` stores the attachment `origin` in pixels relative to each part's
own top-left corner, so a composer only needs one anchor point per part:

| part | origin |
| --- | --- |
| base | top centre |
| mast, slew, apex | bottom centre |
| cab, jib | top-left / bottom-left |
| counterjib | bottom right |
| counterweight, hoist | top centre |

Two things are drawn by the composer rather than baked into a PNG, because
their geometry changes per variant: the hoist rope plus its trolley on the jib,
and the pendant tie bars from the tower head to the jib/counter-jib.

## Regenerate

```bash
.venv-echo/bin/python -m echo_game.generate_cranes --force
.venv-echo/bin/python -m echo_game.generate_cranes --variants 48 --seed demo
```

Parts are only redrawn when missing unless `--force` is used; stale part files
are removed automatically. Variants are deterministic for a given seed.
