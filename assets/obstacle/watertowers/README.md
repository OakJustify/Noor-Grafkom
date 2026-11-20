# Modular water towers

Greyscale elevated steel water towers assembled from independent parts the way
one is really built: a concrete footing, stacked leg bays with bracing panels
between them, a catwalk deck with railing, the riveted tank, its roof, roof
fittings and a riser pipe at the base. Every part is a separate PNG, every
shape variant has a different silhouette, and each part is a composite of
several primitives. The greyscale pixels are meant to be multiplied with a
seeded colour at runtime (`pygame.BLEND_MULT`), the same trick the block,
rocket and crane libraries use, so one part set yields any palette.

```
watertowers/
  parts/
    base/       wide slab, four footings, stepped plinth, ring beam
    leg/        square post, tapered post, round tube, H-section
    brace/      X-brace bay, single diagonal, K-brace, zigzag
    platform/   ring truss, solid deck, plate girder frame
    railing/    two rails with posts, mesh fence, pickets with kick plate
    tank/       riveted cylinder, bulged barrel, tapered shell, spheroid
    roof/       cone, shallow cone, dome, flat deck - wide and narrow spans
    vent/       vent pipe, finial ball, antenna, roof hatch
    riser/      elbow, valve stack, straight run, conduit with junction box
  variants/   24 seeded sample towers, 560x720
  parts.json  part index (shape, tone, size, origin, roof span)
  variants.json  which parts each sample used, plus leg bays and sides
  preview.png contact sheet
```

Counts: 8 footings, 8 legs, 8 bracing panels, 6 platforms, 6 railings,
8 tanks, 16 roofs, 8 roof fittings and 8 risers — 76 parts. Roofs come in two
spans (`wide` 182 px, `narrow` 132 px) because a spheroid is cut flat where its
cap lands, so a wide cone would overhang it.

## How a part is built

Each part is a composite, not a single outline:

- **base**: tapered slab with anchor bolts, four separate footings under one
  cap, three stacked plinths, or a ring beam with expansion joints;
- **leg**: end flange plates + bolt rows + a bolted gusset halfway, or a tube
  with collars and a highlight strip, or an H-section with a visible web;
- **brace**: two ties, plus X, single diagonal, K-brace or zigzag members with
  gusset plates and bolts at the corners;
- **platform**: top and bottom chords with an X-truss between them, a solid
  plate deck with skirt and bolts, or a plate girder frame with stiffeners;
- **railing**: two rails, post caps and either a diagonal mesh, pickets with a
  kick plate, or plain posts;
- **tank**: shell gradient + vertical plate seams with rivet rows + three hoop
  bands + top rim and base ring (or a spheroid with weld bands, skirt and
  collar);
- **roof**: cone/shallow cone/dome/flat deck with radial seams, rim band and a
  finial knob, or a parapet and expansion joints on the flat version;
- **vent**: pipe with cap and flange, stem with a ball finial, antenna mast
  with crossbars, or a hinged hatch box;
- **riser**: pipe elbow with flanges, two valve bodies with handwheels, a
  ribbed straight run with clamps, or a conduit with a junction box.

## Attaching / randomizing

`echo_game.generate_watertowers.random_choice(rng)` holds the composition
rules: one part per family, a footing, a leg and brace pair repeated for the
bays, one platform, railing, tank, roof, vent and riser, a left/right side for
the riser and for the ladder. Each family has two tones.

`parts.json` stores the attachment `origin` in pixels relative to each part's
own top-left corner, so a composer only needs one anchor point per part:

| part | origin |
| --- | --- |
| base | top centre |
| leg | bottom centre |
| brace | bottom left |
| platform | top centre |
| railing | bottom left |
| tank, roof, vent, riser | bottom centre |

Fixed layout numbers (also in `parts.json`): bay height 80 px, clear span
between the front legs 96 px, deck width 210 px, canvas 560×720 with the ground
line at y = 694. `_fit_sections` computes how many bays a tank + roof + vent
stack needs so the tower fills the canvas, so a tall spheroid gets fewer bays
than a shallow shell with a flat roof.

Two things are drawn by the composer rather than baked into a PNG, because
their length changes per variant: the caged service ladder up the inside of a
bay, and the riser feed pipe that runs up the outside of a leg and elbows into
the tank.

## Regenerate

```bash
.venv-echo/bin/python -m echo_game.generate_watertowers --force
.venv-echo/bin/python -m echo_game.generate_watertowers --variants 48 --seed demo
```

Parts are only redrawn when missing unless `--force` is used; stale part files
are removed automatically. Variants are deterministic for a given seed.
