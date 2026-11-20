# Modular rockets

Greyscale rockets assembled from independent parts on one horizontal axis
(nose on the left, exhaust on the right). Every part is a separate PNG, every
shape variant has a different silhouette, and each part is built from several
primitives. The greyscale pixels are meant to be multiplied with a seeded
colour at runtime (`pygame.BLEND_MULT`), the same trick the block library uses,
so one part set yields any palette.

```
rockets/
  parts/
    nose/     cone, blunt cone, dome, stepped cone, pentagon, spearhead
    collar/   trapezoid, pill, pentagon, double ring, hexagon, notched plate
    body/     straight plank barrel, long barrel, chamfered panel,
              bulged panel, waisted drum, tapered ribbed shell
    strap/    riveted, twin band, slim ring, studded, chevron clamp
    fin/      swept, straight, notched split, rounded, leaf, stepped
    nozzle/   bell, ribbed bell, straight pipe, converging cone, stepped flare
    flame/    single, triple, forked, twin
  variants/   24 seeded sample rockets, 512x176
  parts.json  part index (shape, tone, length, half height, axis)
  variants.json  which parts each sample used
  preview.png contact sheet
```

Counts: 18 noses, 18 collars, 6 bodies, 10 straps, 12 fins, 10 nozzles and
4 flames — 78 parts, combining into millions of rockets. Most families also
come in `dark`, `mid` and `light` tones.

## How a part is built

Each part is a composite, not a single outline:

- **nose**: cone/trapezoid/pentagon silhouette + base plate + rivets + light
  and shadow facets;
- **collar**: flared or rounded band + lip rectangles + centre groove + dots;
- **body**: barrel profile + plank seams or panel lines + end caps + rivets;
- **strap**: band + raised edges + rivets or studs or chevrons;
- **fin**: plate polygon + inner lighter plate + root strip, mirrored on both
  sides;
- **nozzle**: flared trapezoid + two ellipses for the mouth + ribs;
- **flame**: layered bezier tongues with a bright core and a thin outline.

## Assembling / randomizing

`echo_game.generate_rockets.random_choice(rng)` holds the composition rules
(one part per family, optional second strap at 52–64% of the body, optional
flame). Parts attach at `x = 0` on their own PNG with the rocket axis through
the vertical centre, so placing them left to right is all that is needed.
`variants.json` records the exact files for each sample so an AI or algorithm
can propose new combinations in the same format.

## Regenerate

```bash
.venv-echo/bin/python -m echo_game.generate_rockets --force
.venv-echo/bin/python -m echo_game.generate_rockets --variants 48 --seed demo
```

Parts are only redrawn when missing unless `--force` is used; stale part files
are removed automatically. Variants are deterministic for a given seed.
