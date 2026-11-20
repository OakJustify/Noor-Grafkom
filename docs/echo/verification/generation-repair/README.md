# Approved procedural generation repairs

This implementation follows the [pre-repair audit](../../audit/README.md).
The original audit artifacts are retained as historical evidence; current
verification writes to this directory instead of overwriting that baseline.

## What changed

- **Structural generation remains `ProceduralGenerator`.** Ordinary width/gap
  profiles, real-controller reachability validation, bounded retries, and safe
  fallback remain. Periodic wider challenge platforms become more frequent and
  wider with difficulty. Height samples come from feasible intervals instead of
  being repeatedly clamped to the lower boundary.
- **Puzzle generation remains the existing catalog/composer/rules/validator.**
  Eligibility uses the composer's geometry-derived minimum width. Combined gate
  switch intervals reserve the required shadow or patrol space before sampling.
  Layout retries are bounded both globally and per definition.
- **Puzzles and obstacles have independent density controls.** A puzzle request
  has priority when both categories request an encounter. A combined encounter
  additionally requires an obstacle request and the difficulty-dependent combo
  probability. Safe caches use a separate recovery policy, not puzzle density.
  Saws are placed after challenges, in remaining free intervals, without removing
  landing/takeoff reserves. Damaging challenges reserve that segment's obstacle
  space; standalone saws never stack onto them.
- **Fairness checks cover all damaging segment objects.** Low health or depleted
  lantern suppresses standalone saw generation. The damage budget is an exposure
  budget: saw count plus the challenge's damage cost. It is not a formal bound on
  damage from repeatedly touching an enemy. Two saws require space for separate
  hops and at least 120 px clear between moving sweeps. Disabled sentries are
  filtered even when stored inside combined challenges.
- **Enemy bounds have one center-based definition.** Validation uses full patrol
  sweeps; runtime damage and drawing use `EnemySpec.rect_at(state.x)`.
- **Runtime scenery is now segment-owned.** `echo_game/environment.py` provides
  typed, supported, spaced decorations with its own persistent RNG. It receives
  reserved challenge/hazard footprints after geometry and challenges validate.
  `Segment.environment` is forwarded to `EndlessWorld.environment_objects`,
  drawn in rear/terrain/front passes, and released by existing owner cleanup.
- **Difficulty uses furthest progress.** Current displacement still drives
  position-based streaming. Backtracking no longer reduces difficulty or
  reshuffles already generated content.

## Procedural forest presentation

Endless mode no longer reuses campaign parallax or its HUD palette. A dedicated
renderer (`echo_game/forest.py`) draws a seeded monochrome forest that follows
the collision terrain:

- **Layered world-space scenery.** Three deterministic trunk layers (distant
  needles, misted midground, monumental foreground boles), a wrapping leaf
  canopy, fog banks, floating leaf litter, and a near-black grass fringe frame
  the silver light. Scenery uses its own renderer RNG and never consumes a
  gameplay RNG or registers collision geometry.
- **Terrain-derived silhouettes.** Platform tops reuse the exact collision
  surface. Eroded shoulders, hanging roots, strata, and dense verge grass make
  platforms read as rising forest floor instead of floating bars. A separate
  non-colliding floor silhouette closes the gaps behind platforms.
- **Monochrome gameplay objects.** The courier, saws, sentries, seals, switches,
  caches, environmental props, shadows, and damage effects are drawn in
  grayscale. Context prompts sit above the courier on a dark plate instead of
  rendering underneath them.
- **Seeded, cached composition.** The camera zooms to `1.6` and tracks vertical
  platform changes so the collision ground stays on the `73.5%` frame line.
  World chunks and terrain/prop/saw surfaces are lazily cached; Cairo runs only
  on cache misses.
- **Quiet status by default.** The default endless frame has no persistent HUD.
  **F1** (or `--show-hud`) reveals distance/seed/difficulty, health dots,
  lantern charge, and controls. Damaged health or lantern charge below `20%`
  automatically reveals the health/lantern portion with a short
  `L · rest the light` hint.
- **Unchanged gameplay.** Platform geometry, generation repairs, challenge
  validation, hazards, physics, and the separate six-room campaign are
  untouched.

### Procedural forest evidence

The [contact sheet](forest/contact-sheet.png) compares seeds, distances, and
object states. Full-resolution captures and raw metrics:

| Evidence | Artifact |
| --- | --- |
| Seed 7, frame 150 (464 px) | [screenshot](forest/seed-7-frame-150.png) |
| Seed 7, frame 400 (1,254 px) | [screenshot](forest/seed-7-frame-400.png) |
| Seed 7, frame 900 (2,831 px) | [screenshot](forest/seed-7-frame-900.png) |
| Seed 11, frame 400 | [screenshot](forest/seed-11-frame-400.png) |
| Seed 23, frame 400 | [screenshot](forest/seed-23-frame-400.png) |
| Light-gate challenge | [screenshot](forest/challenge-light-gate.png) |
| Saw hazard and sentry | [screenshot](forest/hazard-saw.png) |
| `F1` status overlay | [screenshot](forest/hud-on.png) |
| Automatic low-resource warning, HUD off | [screenshot](forest/warning-auto.png) |
| Launcher smoke test with `--show-hud` | [screenshot](forest/cli-show-hud.png), [report](forest/cli-report.json) |
| Capture definitions and timings | [capture.json](forest/capture.json) |

The captures use the real application, real `EndlessPilot` input, and real
seeded generation. Challenge/hazard shots only move the camera and courier for
inspection; no platform, hazard, or challenge geometry is fabricated.

Measured on this machine, headless:

- A 900-frame launcher run (`--endless --seed 7 --demo --headless --show-hud`)
  completed in **20.108 s**, about **22.3 ms per rendered application frame**
  including update, draw, and display scaling. Its report recorded 16 chunk
  builds, 12 cached chunks, 6 cached terrain surfaces, and 19 cached props.
- The direct capture run for the same 900 frames took **19.528 s**, about
  **21.7 ms/frame**.
- A cold distant/mist/trunk chunk built in **0.042 / 0.043 / 0.049 s**; a cold
  platform terrain surface built in **0.151 s**. Warm chunks are surface-cache
  hits and perform no Cairo work.

The four presentation tests in `tests_echo/test_forest.py` cover seeded chunk
determinism and cache reuse, ground/camera alignment, non-blank forest drawing,
HUD opt-in versus automatic warnings, and terrain/environment render routes.

## Environmental rules and limits

| Type | Placement / drawing |
| --- | --- |
| Tree | Broad supported footprint, larger edge/neighbor clearance, rear-layer branches |
| Bamboo | Narrower supported cluster footprint, rear-layer stalk variants |
| Wood | Supported low debris/log footprint, front layer, moderate clearance |
| Rock | Supported small footprint, front layer, smaller spacing |
| Grass | High-density small surface patches, short blades, smaller edge clearance |
| Dirt patch | Inside the supporting terrain thickness, terrain-material pass rather than floating surface scatter |

Every environmental object carries a unique environment ID, world-space bounds,
type, layer, variant, platform owner, and generation index. Validation rejects
unsupported placement, out-of-bounds dimensions, spacing overlap, and obscured
reserved challenge/hazard footprints. Generation logs candidates and rejection
reasons, with bounded attempts and at most 32 accepted objects per platform.

**These objects are non-solid decorations.** Existing platform bodies remain the
collision terrain. Solid wood/rock props are intentionally not introduced without
controller-path validation. Campaign parallax artwork remains as atmosphere in
the six rooms; endless mode replaces it with the dedicated forest renderer. The
decorations are not relabeled as runtime entities or removed.

## Configuration and determinism

```sh
.venv-echo/bin/python play_echo.py --endless --seed 7 --environment-density 2 --obstacle-density 1 --puzzle-density 1.5
```

- Density values are finite multipliers in `[0, 3]`; defaults are all `1`.
- `--environment-density 0`: no runtime environmental objects.
- `--obstacle-density 0`: no saws, shadows, sentries, or damaging combinations.
- `--puzzle-density 0`: no interactive gates; safe caches remain available.
- `--no-enemies`: no sentries, including inside combined puzzles.
- Restart preserves the explicit seed and configuration.
- `GenerationConfig.challenge_min_width` now gates real challenge requests.
- Profile combo probability and damage caps are consumed, not decorative fields.

Structural, standalone-hazard, challenge, and environment RNG streams are
separate. Environment density does not change platform/challenge/hazard output.
Changing puzzle/obstacle settings does not consume structural randomness.
Placement reservations can couple realized densities: the controls do not promise
an exact number of accepted objects or identical obstacle counts after changing
puzzle density. Same seed **and settings** deterministically replay the new
algorithm; old pre-repair layouts are not promised to remain identical.

The launcher still defaults to the six-room campaign. Use `--endless` or E on the
title screen. Campaign geometry, checkpoint behavior, and instant-fatal campaign
saws are unchanged.

## Verification artifacts and commands

### Measured results

The final full regression suite passed **216 tests, with 1 skipped**, in 57.54
seconds. [JUnit evidence](tests.xml) records 217 tests, zero failures, and zero
errors. The skipped test requires an optional caller-selected local reference.
This total includes the four new procedural forest presentation gates.

Five ordinary live seeds (`1, 2, 7, 13, 21`), each using 6,000 real application
updates at 60 Hz, produced **267 platforms, 131 challenges, 66 interactive puzzles,
78 obstacle entities, and 1,058 environmental objects**. The environment included
65 trees, 89 bamboo clusters, 104 wood pieces, 124 rocks, 534 grass patches, and
142 dirt patches. All five runs survived, with no registration discrepancies,
platform/challenge fallbacks, or generation-guard hits. These shorter runs reached
approximately 18,748-18,846 px; the additional wider platforms explain the lower
segment count compared with the pre-repair audit, not a new generation cap.

Real structural-width sweeps used 1,000 segments per difficulty, across the same
five seeds, with healthy/full-lantern contexts:

| Difficulty | Accepted challenges | Interactive puzzles | Combined challenges | Obstacle entities | Maximum saws per segment |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 237 | 193 | 0 | 55 | 1 |
| 4 | 458 | 261 | 13 | 263 | 1 |
| 7 | 587 | 357 | 26 | 344 | 2 |
| 8.2 | 614 | 382 | 27 | 362 | 2 |
| 10 | 653 | 479 | 69 | 406 | 2 |

Combined challenges count dark gates plus lit gauntlets. Obstacle entities count
saws, shadows, and sentries, not puzzle barriers. These are fixed-context sweeps
on real generated geometry, not controller traversals. No healthy sweep used a
platform/challenge fallback, and no sampled platform was clamped to exactly Y=470.
Geometrically unsuitable saw slots are still skipped; their safety constraints
have not been removed to raise spawn counts.

At difficulty 4 with health and lantern fractions both 0.1, the 1,000-segment
sweep generated **676 recovery caches and zero damaging obstacles**, with zero
cache-overlap fallbacks. The original audit generated 86 standalone saws under
that same resource context.

Two **60,000-update** application runs followed normal progress from zero, rather
than a difficulty floor or a position teleport:

| Seed | Final progress (px) | Difficulty | Platforms generated | Interactive puzzles | Gauntlets | Environment spawned / cleaned | Final health |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 187,198.06 | 10 | 469 | 173 | 8 | 1,922 / 1,901 | 5/5 |
| 7 | 186,989.92 | 10 | 470 | 173 | 2 | 1,914 / 1,885 | 5/5 |

Both accepted all six challenge types and two-saw segments, with **zero deaths,
registration discrepancies, fallbacks, or generation-guard hits**. Together they
activated 344 switches and cleaned 926 platforms. Final active environmental
counts were only 21 and 29, with no orphan owner IDs. The active count remains
bounded by streaming; lifetime generation is not restricted to those counts.

There is still no guaranteed maximum puzzle-free distance: the longest
puzzle-free generated streaks in the five shorter seeds were 10/13/17/9/9
segments. Density increases are statistical and constrained by space/resources,
not promises of a puzzle in every viewport or monotonically increasing counts in
each small random window.

The summary and long-run audit artifacts are generation snapshots taken before
the presentation-only forest integration. Their generation results remain
applicable — the refreshed 1,200-frame launcher reproduced the same distance,
difficulty, environment counts, and challenge results — but their
`source_sha256` blocks predate `echo_game/forest.py` and differ for
`echo_game/game.py`. Do not treat those hashes as current without rerunning
`scripts.audit_generation`. The refreshed CLI reports above carry current source
hashes, and `tests.xml` records the current suite run. Current generation
reports are `audit-summary.json`, `audit-events.jsonl`, `audit-endless-seed7.png`,
and `long-run/` equivalents.
Baseline report files under `docs/echo/audit/` have not been overwritten.

An actual launcher smoke test also completed 1,200 headless demo updates with
environment/obstacle/puzzle densities of `2 / 0 / 1.5` and `--no-enemies`, without
death or fallback. Its [report](configured-cli.json) confirms the effective
configuration, and its [screenshot](configured-cli.png) captures the current
forest rendering with the opt-in status overlay. The refreshed run completed in
**28.531 s**; its simulation result matches the earlier run, confirming that the
presentation rewrite did not alter generated content.

```sh
TMPDIR=/tmp/opencode .venv-echo/bin/python -m pytest tests_echo -q --junitxml=docs/echo/verification/generation-repair/tests.xml
TMPDIR=/tmp/opencode .venv-echo/bin/python -m scripts.capture_forest_evidence
TMPDIR=/tmp/opencode .venv-echo/bin/python play_echo.py --endless --seed 7 --demo --headless --frames 900 --show-hud --screenshot docs/echo/verification/generation-repair/forest/cli-show-hud.png --report docs/echo/verification/generation-repair/forest/cli-report.json --no-save
TMPDIR=/tmp/opencode .venv-echo/bin/python -m scripts.audit_generation
TMPDIR=/tmp/opencode .venv-echo/bin/python -m scripts.audit_generation --frames 60000 --seeds 1 7 --output docs/echo/verification/generation-repair/long-run
```

The observer calls original methods exactly once and records existing RNG draws;
it is not imported by the game launcher and produces no per-frame log stream.
Reports include environmental candidates/accepted/rejected positions, profile,
progress, category requests, challenge candidates, validation/fallback outcomes,
spawn/cleanup counts, registrations, rendering samples, and source hashes.

`tests_echo/test_generation_repairs.py` covers real generated widths at
difficulties 1/4/7/8.2/10 across five seeds, all environment types, valid combined
layouts across sampled positions, zero-density/allowlist/minimum-width behavior,
RNG independence, spacing/reservations, render routes, complete-segment budgets,
configuration validation, and input-only high-profile traversal with cleanup.

The high-profile unit runs use a difficulty floor of 10 without teleporting the
player or supplying artificial platform widths. The separate long-run report
starts at ordinary difficulty/progress and follows the real progression curve.
The full regression suite includes all six authored campaign rooms and the
application transition to its ending.

Passing samples is not exhaustive solvability proof. Environmental solid props,
new puzzle catalogs, multi-segment puzzles, and guaranteed maximum puzzle-free
distance remain outside this repair. Statistical rates and absence lengths must
be interpreted over adequate exposure, not required to rise in every random
window.
