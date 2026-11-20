# ECHO: The Hollow Signal

An original six-room physics puzzle-platformer inspired by the **mechanical
ideas** of LIMBO, not a copy of its levels, character, artwork, or soundtrack.

This standalone project lives at `~/Projects/03-projects/02-games/noor-grafkom/v3`.
Launch it with `.venv-echo/bin/python play_echo.py` from that directory.

## Run

The isolated environment created for this task is ready to use:

```bash
.venv-echo/bin/python play_echo.py
```

For a fresh environment:

```bash
python3 -m venv --system-site-packages .venv-echo
.venv-echo/bin/python -m pip install -r requirements-echo.txt
.venv-echo/bin/python -m echo_game.generate_assets
.venv-echo/bin/python play_echo.py
```

Pycairo requires Cairo development headers if no wheel/system installation is
available. On this host Pygame, Cairo and NumPy were already installed;
Pymunk and pytest were installed **only in `.venv-echo`**.

Assets are generated automatically if absent. Regeneration is deterministic:
`python -m echo_game.generate_assets --force`. No LIMBO files are needed to play.

## Controls

| Key | Action |
|---|---|
| A/D or left/right | Walk; swing a held rope |
| Space | Jump; release a held rope |
| W/S or up/down while holding rope | Climb up/down |
| W or up otherwise | Jump |
| Hold E or Ctrl | Pull a nearby crate; catch a rope |
| Tap E or Ctrl | Operate covers, valves, timed gravity, magnet power or block gravity |
| F1 (endless) | Show/hide extended run details |
| R | Retry the current Campaign or generated Endless room |
| Esc | Pause/resume; quit from title |
| H or Tab | Show/hide controls; pauses simulation while reading |
| M | Mute/unmute |
| F3 | Physics diagnostics |
| Enter at title | Begin/continue |
| E at title | Start a new endless run |
| N at title | Start a new journey |

Room checkpoints are written to `saves/echo.json`. Existing game saves and
the original campaign are not touched. `--no-save` disables persistence.
The game letterboxes a 960 × 540 logical view into a resizable window.

## Endless signal

Endless composes **new room contents**, rather than shuffling six fixed Campaign
layouts. Rooms contain two to four stages, with generated widths, elevations,
crate sizes/masses, push/pull targets and mechanism positions. A main water lift,
rope crossing, seesaw bridge, gravity corridor or magnetic stair can occur before
or after the crate relays. Each six-room cycle visits all six main mechanics,
but their geometry and complete stage sequence are generated afresh.

Every accepted room has a spawn-to-exit witness using ordinary controls in the
same Pymunk physics as play. The generator rejects duplicate layout, puzzle and
scenery signatures within the run, failed solutions and detected simple bypasses.
This proves a demonstrated solution, not exhaustive impossibility of alternate
routes or human difficulty balance. Mechanics can recur; exact room contents do
not. Verification may take a few seconds when a room is first loaded.

Campaign's animated courier, props, lighting, terrain and HUD are retained.
Backgrounds are new seeded Cairo panoramas: varying structures/trees/caves,
sky tint, time of day, fog and particles, with layered parallax and a bounded
cache. The visual palette is independent of the room's physics mechanic.
**F1** (or `--show-hud`) shows the run seed and room ID. **R** or automatic death
recovery retries the same room without changing scenery or consuming the next
room's RNG. Reaching its signal loads the next generated room:

```bash
.venv-echo/bin/python play_echo.py --endless --seed 7
.venv-echo/bin/python play_echo.py --endless --seed 7 --show-hud
.venv-echo/bin/python play_echo.py --endless --demo --seed 7 --headless \
  --frames 1800 --show-hud --no-save --report /tmp/opencode/endless.json
```

In `--demo` mode, a geometry-relative `RoomPilot` controls the generated stages
and continues into the next room. The Campaign pilot is unchanged for Campaign.
The older streaming platform/health/lantern implementation is retained internally
for regression coverage; it is no longer the game's default Endless experience.

See [procedural room design](../procedural_puzzle_design.md) for the generator,
verification boundaries and reproduction commands.

## Six original physics puzzles

1. **The Weight of Silence** — leave a crate on a pressure plate to hold a gate.
2. **A Thread Across the Dark** — catch, climb and swing a multi-segment rope to a high ledge.
3. **What the Water Carries** — open a cover, position a box, activate the valve, and ride the rising water.
4. **The Returning Tide** — alternate runs and jumps to build seesaw motion, then leave at the raised-end crest.
5. **The Hollow Signal** — use temporary inverted gravity to cross a saw, then time the return before the ceiling blade. Accelerating original beeps warn of expiry.
6. **What the Ceiling Keeps** — power the magnet, lift the iron blocks, then return block gravity as the first catches. The first stays high while the second falls to form a step. Magnet power and gravity have separate switches; the courier stays on the ground.

To try the new magnetic room directly:

```bash
.venv-echo/bin/python play_echo.py --chapter 6 --play --no-save
```

If both blocks catch, turn block gravity downward and switch the magnet off to
release them. Switching downward just before contact can still be too late:
upward momentum survives the reversal. The clack and **FIRST CAUGHT** cue mark
the useful window. The blocks are guided vertically; they are not pushable crates.

The player is an original hooded courier carrying a small chest lantern; a
moth-like guide and the signal beacons provide visual direction. The art uses
layered, foggy silhouettes, vector-drawn scenery, animation, grain and vignette.
Audio includes original synthesized ambience, a sparse instrumental motif,
footsteps and mechanical/interaction effects. Existing OFL-licensed project
fonts retain their license files in `assets/fonts/`.

## Verify / watch

```bash
# Watch a real-time scripted playthrough (ordinary controls, no teleports)
.venv-echo/bin/python play_echo.py --demo --no-save

# Full physics, checkpoint and application regression tests
.venv-echo/bin/python -m pytest tests_echo -q

# Procedural generation only (reachability, seeds, hazards, streaming)
.venv-echo/bin/python -m pytest tests_echo/test_procedural.py -q

# Generated multi-stage rooms, six mechanics, uniqueness and live input replay
.venv-echo/bin/python -m pytest tests_echo/test_endless_rooms.py -q

# Puzzle/obstacle catalog, composition, fairness, health and lantern runtime
.venv-echo/bin/python -m pytest tests_echo/test_challenges.py -q

# Deterministic endless traversal without a window
.venv-echo/bin/python play_echo.py --endless --demo --seed 7 --headless \
  --frames 1800 --no-save --report /tmp/opencode/endless.json

# Optional read-only reproduction against the supplied reference packages
LIMBO_REFERENCE_ROOT=/home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO \
  .venv-echo/bin/python -m pytest tests_echo/test_package_data.py -q

# Complete campaign witness, asset validation and screenshots
.venv-echo/bin/python -m echo_game.verify

# Reproducible standalone launch / render smoke test
.venv-echo/bin/python play_echo.py --headless --play --frames 120 \
  --no-save --screenshot docs/echo/verification/launch.png \
  --report docs/echo/verification/launch.json
```

`--chapter 1` through `--chapter 6` select a room for testing. `--mute` starts
silently. `--demo --headless --frames 4800 --no-save` runs a rendered campaign
without a desktop window. `--headless` requires a finite `--frames` value.

### Evidence

- `REFERENCE_ANALYSIS.md`: reference findings, physics explanations and unknowns.
- `REFERENCE_COMPARISON.md`: concrete reference-to-implementation matrix and test boundaries.
- `REFERENCE_GAMEPLAY.md` and `reference-gameplay.json`: fetched walkthroughs, inspected stills and explicit source coverage.
- `PACKAGE_DECODING.md` and `packaged-obstacle-data.json`: 211 structured declarations, 39 chapter mappings, 102 checkpoints, offsets/hashes and undecoded regions.
- `reference-contracts.json`: source-linked qualitative behavior contracts and named regression tests.
- `rea-evidence.json`: complete portable REA import-table Evidence.
- `rea-package-evidence.json`: complete REA package-identity Evidence from the follow-up investigation.
- `local-artifact-findings.json`: identities, selected literal offsets and validated
  package-table hypothesis; generated by the read-only `reference.py`.
- `verification/verification.json`: full campaign trace, per-room completion,
  screenshot identities, library versions and audio/asset validation.
- `verification/challenge-generation.json`: difficulty sweep, valid generation
  rates, low-resource behavior, deterministic-seed check and a 30-seed physics
  soak for the puzzle/obstacle layer.
- `verification/contact-sheet.png`: title, controls, all six physics scenes,
  ending, pause and failure recovery.
- `verification/README.md`: current test results, reproduction commands and visual-review limits.

This is a complete small original campaign, **not a port of LIMBO's entire
campaign**. The exact LIMBO native physics implementation remains unverified
because a native analysis engine and Windows runtime were unavailable here.
