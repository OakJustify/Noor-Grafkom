# Current ECHO verification

These results cover the six-room campaign — pressure gates, climbing, rising
water, temporary gravity, an oscillatory seesaw, and magnetic ceiling capture
with separate block gravity — plus the endless mode's monochrome forest
presentation. They do **not** measure LIMBO's native runtime or establish full
behavioral equivalence. See
[`../REFERENCE_COMPARISON.md`](../REFERENCE_COMPARISON.md) for reference sources,
chosen models and omitted sequences.

## Results

- **216 tests passed, 1 optional installation test skipped** in the latest full
  portable suite (**57.54 s**). The current
  [JUnit evidence](generation-repair/tests.xml) records **217 tests**, zero
  failures, and zero errors. This includes **16 procedural tests** covering the
  real **445 px/s** takeoff speed, seed reproducibility, rejection of impossible
  gaps and heights, safe fallback platforms, hazard landing/takeoff clearance,
  streaming cleanup, six independent 6,000-frame endless traversals, and
  menu/restart/update/draw integration. A further **23 puzzle/obstacle tests**
  cover the challenge catalog, deterministic composition, bounded retries,
  geometric/state/fairness validation, real measured jump-height checks,
  multi-seed and multi-difficulty valid generation rates, low-health/low-lantern
  recovery choices, damage invulnerability, lantern drain/recharge, translucent
  lantern rendering, shadow light rules, seal activation, sentry retreat, cache
  restoration, challenge cleanup, live streamed-challenge validity and long
  sessions. `tests.xml` in this directory retains the earlier 176-test campaign
  snapshot; the current full-suite JUnit is linked above.
- **47 package-decoder tests passed** with `LIMBO_REFERENCE_ROOT` explicitly
  selecting the supplied installation. `reference-package-tests.xml` records
  this separate run, including the otherwise skipped package-identity check.
  This does not constitute a new installation-selected full-suite run.
- `verification.json`: continuous `Game.update` at 60 Hz with fixed 120 Hz
  physics reaches all six signals and the ending in **4,282 frames** without
  deaths or teleports. Room simulation times are **7.258, 6.883, 13.025, 17.175,
  8.792, and 7.292 seconds**; frame count also includes transitions.
- Recorded causal witnesses: climb-height choice; separately opened cover and
  filling valve; box carrying the courier upward; gravity expiring without a
  second relay; alternating seesaw motion followed by crest departure; a
  magnetically retained first block and a returned second block supporting the
  player. Magnetic tests also cover early/late switching, momentum overshoot,
  unpowered contact, release, replay, and 60/120 Hz input sampling.
- **47 asset files** validated: **30 PNGs, 15 WAVs**, the art philosophy, and
  the authorship manifest. Every WAV is non-silent and below PCM clipping;
  two original music/ambience loops are 32 seconds each. This is data validation,
  not a human listening review.
- **14 campaign/UI captures** and their contact sheet regenerated. The refreshed
  contact sheet, both full-resolution magnetic captures, ending, pause, and
  failure captures were visually inspected. Magnetic state labels sit beside
  the rails, below the subtitle, and are hidden during UI overlays. Screenshots
  alone do not establish motion.
- `rendered-campaign.json`: an independent **4,800-frame** CLI run renders
  continuously and reaches the six-room ending. `rendered-ending.png` is its
  final image.
- `endless-seed7.json` / `.png`: a **3,600-frame** headless endless run with the
  input-only pilot reaches **11,340.61 px** (difficulty **4.976**) with **8 active
  platforms**, **1 active hazard**, **34 generations**, **0 platform
  fallbacks**, **5/5 health**, **45.3% lantern** and no death. The challenge
  generator requested **28** challenges, emitted **17** validated ones
  (**5 light seals, 5 shadow runs, 6 sentries, 1 lantern cache**), skipped
  **11** candidates and made **0** safe fallbacks. This is a streaming
  render/soak witness, not a claim of human difficulty balance. The refreshed
  screenshot uses the current monochrome forest and the opt-in status overlay.
- **Endless forest presentation** is captured across seeds/distances and object
  states in the [forest contact sheet](generation-repair/forest/contact-sheet.png).
  A 900-frame launcher smoke test with `--show-hud` completed in **20.108 s**
  (about **22.3 ms/frame**) and reported 16 chunk builds, 12 cached chunks, 6
  cached terrain surfaces, and 19 cached props. Cold chunk/terrain builds measured
  **0.042-0.049 s** and **0.151 s**; see the
  [forest section](generation-repair/README.md#procedural-forest-presentation)
  and [capture.json](generation-repair/forest/capture.json).
- `challenge-generation.json`: measured generation sweep over **1,000 synthetic
  platforms at each difficulty 1, 4, 7 and 10**, fed through the same composer,
  validator and real controller constants. Valid generation rates were
  **22.3%, 32.5%, 44.2% and 51.9%**; candidate rejections were **0, 55, 79 and
  89**; challenge fallbacks were **0** at every difficulty. A separate
  low-resource sweep (10% health, 10% lantern) produced **816 recovery caches
  out of 1,000 requests** and no damaging challenge. Same-seed output was
  identical and a different seed differed.
- A separate 30-seed, 6,000-frame physics soak produced **223 validated
  challenges**, **75 rejected candidates**, **8 safe no-challenge fallbacks**,
  **0 platform fallbacks** and no death; minimum distance was **9,146.7 px**,
  minimum health **4/5**, and minimum lantern energy **47.5%**. Long-session
  evidence therefore exercises real traversal, not only synthetic generation.
- `native-window.json` / `.png`: refreshed **180-frame, room-6** ECHO
  desktop-window smoke test. Its image is the game canvas from that run;
  wall-clock timing and live keyboard input are not a deterministic witness.
  This is ECHO desktop execution, not execution of the LIMBO reference.

## Magnetic witness

`06-first-magnetic-contact.png` records the first block caught while the second
is still rising. At campaign frame **4,013**, the split-height witness records
the first block held at centre Y=**306.85** and the second at Y=**418.15**, with
the courier supported by the second block and both gravity directions normal.
The first capture occurred **2.158333 s** into the room. These are ECHO
measurements in its own geometry and units.

`held_blocks: [1]` and `support_block: 2` in the witness use human-facing block
numbers. Physics snapshots and contact history use zero-based indices, so
`captured: [0]` refers to that same first block.

Campaign and CLI reports retain SHA-256 identities for the current
`echo_game/*.py` sources. `verification.json` also hashes the captures and assets.
The final consistency audit matched all 18 source hashes across the three
reports, all 14 capture hashes, all 47 asset hashes, and the manifest's 46
entries (which exclude the manifest itself). All 10 local Markdown link targets
in the root/player/research documentation existed.
The current ending, pause, and failure captures are `07-ending.png`,
`08-pause.png`, and `09-fall-and-retry.png`. Older five-room names have been
retired.

## Reproduce from the project root

```bash
TMPDIR=/tmp/opencode \
  .venv-echo/bin/python -m pytest tests_echo -q \
  --junitxml=docs/echo/verification/tests.xml

TMPDIR=/tmp/opencode \
  .venv-echo/bin/python -m pytest \
  tests_echo/test_game.py::test_render_all_rooms_and_ui_states -q \
  --junitxml=docs/echo/verification/presentation-tests.xml

.venv-echo/bin/python -m echo_game.verify

.venv-echo/bin/python -m echo_game.verify_challenges

.venv-echo/bin/python play_echo.py --endless --seed 7 --demo --headless \
  --frames 3600 --show-hud --no-save \
  --report docs/echo/verification/endless-seed7.json \
  --screenshot docs/echo/verification/endless-seed7.png

.venv-echo/bin/python play_echo.py --demo --headless --chapter 1 \
  --frames 4800 --no-save \
  --screenshot docs/echo/verification/rendered-ending.png \
  --report docs/echo/verification/rendered-campaign.json

# Run only where a desktop display is available; no headless driver.
.venv-echo/bin/python play_echo.py --play --chapter 6 --frames 180 --no-save \
  --screenshot docs/echo/verification/native-window.png \
  --report docs/echo/verification/native-window.json
```

To include the optional read-only comparison with the supplied installation:

```bash
TMPDIR=/tmp/opencode \
  LIMBO_REFERENCE_ROOT=/home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO \
  .venv-echo/bin/python -m pytest tests_echo/test_package_data.py -q \
  --junitxml=docs/echo/verification/reference-package-tests.xml
```

The game, campaign witness and portable tests work without proprietary
packages. Decoder tests validate preserved metadata and bounds; they do not
recover compiled execution bodies or prove that declaration defaults are
level-instance coefficients.
