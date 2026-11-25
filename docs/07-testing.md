# NUR v4 · verification after the visual/hazard revision

The earlier NPC/dissolving-scenery delivery is **superseded**. Its 50/437-test
figures and old campaign screenshots do not verify this revision. The linked
reports below are regenerated for the standalone, NPC-free controller.
All pilots disable persistence. Save tests use pytest temporary paths, never the
player's actual `saves/nur-v4.json`.

## Full input-only routes

| Route | Simulated elapsed | Active inputs | Milestones | Q shifts | Deaths / blackout recoveries |
|---|---:|---:|---:|---:|---:|
| Sprint bursts | 20:04.51 | 19:41.59 | 144 | 88 | 0 / 0 |
| Walking | 21:41.53 | 21:30.17 | 144 | 88 | 0 / 0 |

Both routes enter the ending, visit all 29 wick stations and preserve the original
Pymunk space through all 28 region changes. They exceed 15 minutes even counting
only active inputs. [Sprint report](verification/campaign-sprint.json) ·
[Walking report](verification/campaign-walk.json).

`src/scripts/playtest_continuum.py` supplies movement, sprint, jump, E and Q inputs.
It does **not** assign player positions, charge, solved flags, trap state, or
remove collision bodies/gates. It reads the visible regular machines to wait or
jump around them, and translates the retained known-solution puzzle pilot.
It aborts on death/stall; there is no idle padding to manufacture campaign length.
The corrected connector route stays below optional lookouts, rather than arriving
at a ground-timed pendulum crossing from above.

Reports record cumulative monster unlocks, forms observed in the camera's view,
maximum on-screen population, elapsed/active time, physics identity and source
hashes. The fresh sprint route observed **all eight forms** and reached **eight
monsters in the camera view** late in the journey; the linked dense frame was
inspected at full size. [Sprint visual sheet](verification/campaign-sprint/campaign.png) ·
[Walking visual sheet](verification/campaign-walk/campaign.png) ·
[Dense encounter frame](verification/campaign-sprint/dense-encounters.png).

These are **accelerated known-solution simulations**, not real-time human
playtests or speedrun proofs. They verify a feasible route and technical duration,
not enjoyment, intuitive puzzle solutions or an optimal completion time.

## Actual-input visual review

[Fourteen-image preview](verification/captures/preview.png) ·
[State/source records](verification/captures/captures.json).
`src/scripts/capture_v4.py` starts new games and uses normal inputs to show:

1. Different walking/running animation and stamina states.
2. E interaction at an unattended wick station, without an NPC/dialogue state.
3. Walking onto the real presser button, its warning, an intentional lethal slam,
   and automatic retry **inside the same world**.
4. Bright → uncertain → fractured → near-dark grading, from holding F until the
   real light budget reaches each threshold; full blackout and E recovery.
5. Actual jumps onto a lookout, E ribbon pickup, crossing the connector and E
   deposit at the next wick station.

Inspected full-size frames include [button warning](verification/captures/04-button-warning.png),
[presser death](verification/captures/05-presser-death.png),
[lookout pickup](verification/captures/13-ribbon-on-lookout.png) and
[deposit](verification/captures/14-ribbon-deposited.png). The foreground genuinely
occludes objects; it does not erase itself around the player. Small prop interiors
are solid, with transparency only in empty space/antialiased contours. Large
building and forest masses are confined to the distant plane.

Campaign folders also contain `hazard-01.png` through `hazard-05.png` with state
records: actual-input approaches and successful passage, not staged positions.
The [eight-form sheet](verification/bestiary-fixture.png) is explicitly an
**art inspection fixture** made from renderer sprites, not eight simultaneous
monsters photographed during a campaign. The campaign reports separately record
actual on-screen observations.

## Tests and source checks

[Full NUR/v4 test log](verification/tests.txt) contains both `tests/v4/` and
the retained `tests/nur/`: **228 passed** at the time it was captured, without
deselecting historical tests from a removed package. After the folder cleanup and
modularization, `.venv-nur/bin/python -m pytest -q` from the v4 root reports
**254 passed** with the same two test trees. The default `pytest -q` targets the
live v4 suite.
Checks cover:

- Intact translated puzzle plans, persistent gates/backtracking and Q edges.
- Stable foreground without player cutout; unchanged scenery across an address
  boundary; measured layer-3 connected silhouettes ≤120 px and opaque interiors.
- All five lethal machinery types, warning before slam, real spike-clearing jump,
  quiet steam window, rendered pendulum position, persistent progress on retry.
- Eight cumulative monster forms, one tested warning/attack cycle for **each**,
  carried-lantern cancellation and zero-charge immunity, placed-radius protection.
- One-use wick stations, actual ribbon inventory, stamina/glide, gradual darkness,
  complete world blackout and non-softlocking recovery.
- Save/load round trips, monster unlock persistence, finite/range/type checks,
  no-save launcher behaviour, final encounter, audio/mute and six action sets.
- A complete input-only campaign, all eight observed forms and ≥15 active minutes.

The old game's package/assets/tests/dependency file are absent from v4. Required
physics lives under NUR; retained NUR regression tests are **not** evidence that
the removed game is still packaged. The runtime report checks unwanted paths.
[Targeted Ruff checks](verification/lint.txt) passed for the revised controller, standalone engine/geometry,
depth, machines, stations, encounters, current pilots and live tests; this is not
a claim that every inherited reference module is lint-clean.

```bash
.venv-nur/bin/python -m pytest -q tests_v4 tests_nur
PYTHONPATH=src .venv-nur/bin/python src/scripts/playtest_continuum.py --output docs/verification/campaign-sprint.json --captures docs/verification/campaign-sprint
PYTHONPATH=src .venv-nur/bin/python src/scripts/playtest_continuum.py --walk --output docs/verification/campaign-walk.json --captures docs/verification/campaign-walk
PYTHONPATH=src .venv-nur/bin/python src/scripts/capture_v4.py
```

## Launcher, rendering and sound

[Smoke report](verification/smoke.json) · [Smoke frame](verification/smoke.png)
come from 120 live headless launcher frames with `--no-save --mute`.
[Runtime probe](verification/runtime.json) records bright/dim cached update/draw
timings and cold generation at four debug-spawn regions. Those are **timing
fixtures, not traversal evidence**. Dummy SDL and this machine do not establish
performance on other hardware. Cold procedural scenery can hitch; no locked
60 fps claim is made. The final idle-machine probe recorded maximum cached p95
**19.19 ms** and maximum first draw **92.43 ms**. An earlier concurrent run was
slower (43.62 ms cached p95), demonstrating why these are machine/load-specific
measurements rather than a frame-rate guarantee.

[Bright](verification/sound-bed-bright.wav) and
[dim](verification/sound-bed-dim.wav) excerpts are offline mixes of the original
live wind/drone/breath stems at target gains, not recordings of mixer output.
Tests cover PCM headroom/endpoints and gain/mute changes. They do not establish
subjective quality or headphone/speaker balance.

## What this does not prove

- Studio-quality illustration, animation or engaging human pacing. The art is
  still procedural vector work, with repeated motifs and room for art direction.
- Human readability/avoidability under very low light, accessibility or narrative
  impact. Known-solution machine timing is not a substitute for a fresh player.
- A free-roaming map: this is one continuous platforming road with optional
  lookouts and backtracking, retaining authored perception puzzles.
- GPU lighting: all grading/compositing is CPU-side Pygame/NumPy.

The revision fixes specific contracts and documents inspected gameplay evidence;
it is **not declared artistically finished**.
