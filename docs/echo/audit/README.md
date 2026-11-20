# Procedural world and challenge generation audit

**Historical pre-repair audit.** Its measurements and source references describe
the code before the approved repairs. Baseline JSON/JSONL/test artifacts remain
unchanged. Current results are in `docs/echo/verification/generation-repair/`.

**Status at audit delivery: audit complete; gameplay repairs not started.** The existing structural
generator, challenge generator, and streaming world should be retained. The audit
does not support replacing the entire procedural system.

## 1. Executive findings

The reported symptoms have different causes:

1. **Environmental variety is missing at runtime.** Trees and grass are primarily
   pre-generated, fixed-seed artwork, not segment-owned environmental entities.
   There is no runtime tree/bamboo/wood/rock placement pipeline to vary or register.
2. **Repeated scenery is real; repeated structural world X is not.** Background
   textures tile; endless mode always uses chapter-0 art. Generated platforms
   advance in world X, but height sampling and reachability rejection concentrate
   surfaces near the bottom vertical bound. Challenge templates also use fixed
   relative anchors.
3. **The puzzle generator executes and spawning works in endless mode.** Five live
   runs produced 86 accepted challenges, including 37 interactive puzzles. The
   universal claim that puzzles never spawn was not reproduced.
4. **Challenge frequency increases overall, but complexity scaling is broken or
   incomplete.** Two saws require widths the structural generator never supplies;
   the combined gauntlet loses its usable width range as difficulty rises. Several
   configuration fields have no effect. Puzzles and non-puzzle challenges compete
   for one selection slot rather than having independent density controls.
5. **Validation suppresses candidates for both legitimate and avoidable reasons.**
   Saw clearance/overlap restrictions are important safety rules, not something to
   remove. Inconsistent minimum-width metadata and unconstrained combo sampling
   waste otherwise usable opportunities.
6. **Fairness validation is not complete.** Enemy validation bounds disagree with
   runtime/render bounds, moving patrols are not swept for overlap validation, and
   standalone saw placement ignores the resource context used by challenge rules.

The user's actual launch command, selected mode, and run duration are unknown.
Campaign mode, same-seed restarts, and short/idle runs are possible explanations
for their observation, not established causes of that particular session.

## 2. Actual execution pipeline

### Launch and controller

- `play_echo.py:3-7` imports and invokes `echo_game.game.main`.
- `echo_game/game.py:625-675`, `main`: creates `Game`, processes real events,
  calls `Game.update`, calls `Game.draw`, and presents the canvas.
- `Game.__init__` (`game.py:36-71`) creates authored `World(chapter)` by default.
  `--play` skips the title; it does **not** enable procedural generation.
- `main` enables endless only with `--endless` (`game.py:649-650`), or title/ending
  input E calls `Game.start_endless` (`game.py:129-142`).
- `Game.start_endless` (`game.py:93-106`) constructs `EndlessWorld(seed)`; restart
  and automatic restart reuse that seed. A new RNG per new run is intentional
  deterministic replay, not reseeding each segment.
- `Game.update` (`game.py:166-213`) converts keyboard/pilot input into `Input`
  and advances the actual world in fixed `DT = 1/120` steps. Menu, pause, and help
  do not advance gameplay. `World.step` (`physics.py:389-479`) owns movement,
  jump/contact physics, and saw-contact checks.
- `EndlessWorld.step` (`procedural.py:710-728`) delegates to that controller,
  updates progress/difficulty, updates challenge state, ensures generation ahead,
  and cleans behind. There is no alternate controller used only by the generator.

### Generation to spawning

```text
EndlessWorld.__init__ / EndlessWorld.step
  -> _ensure_generated (frontier < player.x + generation_distance)
  -> ProceduralGenerator.generate_next(distance, challenge_context)
     -> DifficultyManager.calculate -> GenerationProfile.create
     -> _candidate -> validate_platform (bounded structural retries)
     -> _hazards (except recovery platforms)
     -> PuzzleGenerator.generate (except recovery/disabled paths)
        -> probability gate -> PuzzleRules.eligible
        -> weighted definition selection
        -> PuzzleComposer.compose -> PuzzleValidator.validate
        -> accepted Challenge or safe no-challenge fallback
     -> validate_segment
        -> discard invalid optional challenge, not its reachable platform
     -> _accept (advance previous platform, index, and statistics)
  -> EndlessWorld._spawn_segment
     -> static platform Pymunk body/shape and platform registry
     -> saw list
     -> _spawn_challenge: challenge list, barrier shapes, enemy states
```

References: `procedural.py:211-232,234-279,281-326,328-426,438-485,516-542`;
`challenges.py:117-133,291-394,403-498,504-575`.

Structural retries are bounded at 18. A failed structural sequence becomes a
close, flat, hazard-free platform (`create_safe_fallback`). Challenge attempts are
bounded at six, but each eligible definition is removed after one attempt. A
failed sampled position for a definition is **not** retried with a new position
for that same definition.

### Runtime, rendering, and cleanup

| Generated data | World registration / runtime | Actual drawing route |
| --- | --- | --- |
| Platform | `_spawn_segment`, `_platform_geometry`, `_static_rect` | `terrain_rects` -> `Game._terrain` |
| Saw | `generated_hazards`; `saw_positions` shared by contact checking and drawing | `Game._mechanisms` -> `Art.draw_saw` |
| Barrier | `_spawn_challenge` -> static Pymunk geometry; `activate_switch` removes it | `Game._challenges`, active-geometry check |
| Switch | Owned in `Challenge.switches`; `EndlessWorld.interact` checks distance/light | `Game._challenges` |
| Shadow / cache | Owned in challenge; `_update_challenges` checks logical overlap/distance | `Game._challenges` |
| Sentry | Owned in challenge; `enemy_states` holds moving X; `_update_challenges` checks damage | `Game._challenges` uses that same state X |
| Artwork trees/foliage | No world object, collider, or segment owner | `Art.draw_background` / `draw_foreground` tiles images |

References: `physics.py:133-144,382-389,463-479`; `procedural.py:501-531,590-625,663-706`;
`game.py:218-233,251-339,353-428,495-507`; `art.py:680-709`.

Not every interactive object needs a Pymunk shape: switches, shadows, caches, and
sentries deliberately use logical interaction/damage checks. Their absence from
the solid-shape registry is not a missing-registration bug.

All runtime structural and challenge positions are world pixels, with Y downward.
Rendering subtracts the camera; it does not feed screen coordinates back to
physics. Challenges carry `platform_id` and `generation_index`; the validator
checks both. Saws carry their platform owner. Artwork has a separate parallax
coordinate system and is not aligned to generated platform surfaces.

`_cleanup` / `_remove_challenge` (`procedural.py:544-581`) remove old platform
bodies/shapes, owned hazards/challenges, barrier geometry, enemy states, cache
state, and obsolete active-switch IDs. The current support body is retained.
The authored starting terrain remains; it is not one of the streamed platforms.

## 3. Root causes and classifications

### A. Environmental objects and apparent repetition

**Confirmed missing responsibility: runtime environment generation.**

`Segment` (`procedural.py:193-201`) has platform, hazards, enemies, and optional
challenge, but no environmental payload. `_spawn_segment` has no environmental
registry or spawn path, and `Game.draw` has no segment-owned environment pass.
Runtime searches for the requested object types led to artwork, not a live
environment generator. Campaign crates are authored props (`levels.py:35-36`,
`physics.py:46-132`), not an endless wood/environment spawning system.

**Confirmed visual repetition: fixed artwork seeds, anchors, and tiling.**

- `art.py:20-24` defines fixed artwork `SEED` and 1,920 px landscape width.
- `_landscape` (`art.py:145-169`) uses fixed chapter/layer seeds. Prominent mid-layer
  trees use tile X `[96, 352, 688, 1682, 1854]` rather than generated world positions.
- `_foliage` (`art.py:546-559`) uses another fixed seed and fixed branch anchors.
- `Art._tile` (`art.py:680-685`) wraps offsets modulo texture width.
- `Art.draw_background` / `draw_foreground` (`art.py:687-709`) use parallax.
  At the 960x540 game canvas, the mid-tree layer repeats every **6,000 camera px**;
  foliage repeats approximately every **3,147.54 camera px**.
- `EndlessWorld.__init__` (`procedural.py:452`) always initializes chapter 0.
  Changing the world seed does not change these artwork textures.

This is intentional asset/render behavior, but it does not meet the requested
runtime environmental-generation responsibility. The asset RNG is not proof of
a faulty per-segment RNG; asset creation is a different pipeline.

**Confirmed vertical concentration, not a missing X offset.**

`_candidate` (`procedural.py:234-251`) samples `x = previous.right + gap` and clamps
Y to 190-470. The asymmetric height ranges include substantial downward motion;
upward movement also faces stricter reachability rejection in `validate_platform`.
The clamp makes many downward samples land on exactly Y=470.

All **287** live-generated platform world X coordinates were unique. **141/287**
live surfaces were exactly Y=470. In the difficulty-10 real-width sweep,
**743/1,000** were at that bound. Similar Y is measurable; a repeated-local-X or
missing-world-offset bug was not found.

**Confirmed template anchors.**

`PuzzleComposer.compose` (`challenges.py:304-381`) anchors barriers to
`platform.right - 20`, starts sentries at patrol centers, and centers caches on
platforms. Every recorded barrier had that same 20 px relative offset. Switches
and shadow starts are sampled in world-space intervals. These are repeated
relative templates, not identical absolute world coordinates.

**Intentional bounded streaming.**

`_ensure_generated` maintains 1,500 px ahead; `_cleanup` releases platforms more
than 1,100 px behind (`procedural.py:535-581`, `GenerationConfig:120-121`). Only
8-9 generated platforms remained active at the end of the live runs, despite
57-58 generated over each run's lifetime. The 24-iteration generation guard was
never reached in these runs. A small current registry is not a small lifetime
spawn count.

### B. Puzzle and obstacle absence

**Confirmed working endless call/spawn/render path.**

The audit observed `PuzzleGenerator.generate`, actual candidate composition and
validation, forwarding into `_spawn_segment` / `_spawn_challenge`, barrier shape
registration, sentry runtime state, `Game._challenges` calls, and switch activation
removing barrier geometry. No live registration discrepancy was found.

**Intentional opportunities that can yield no puzzle.**

- Recovery platforms omit both hazards and challenges (`generate_next:368-386`).
- Healthy challenge probability is 0.22 at difficulty 1 and 0.52 at difficulty 10.
  Not every segment should contain a challenge.
- One slot mixes interactive puzzles, sentries, shadows, and safe caches. An
  accepted challenge is not necessarily an interactive puzzle.
- At low resources, damaging/light-dependent challenge types are filtered and
  caches are preferred (`PuzzleRules.reasons`, `PuzzleGenerator.generate`).
- Generation is spatial, not a timer. Seed 7 remained at distance zero with three
  generated platforms and zero challenges over 600 idle application updates.
- Seed 7's first accepted light gate was segment 6, generated at approximately
  911 px player progress, on a platform beginning at X=2,605.91. Objects generated
  ahead may not yet be visible. A short start can legitimately show no puzzle.
- The longest challenge-free generated runs in the five live seeds were
  8, 6, 5, 8, and 4 segments respectively. There is no maximum-absence guarantee.

**Confirmed avoidable rejection: eligibility does not match composition.**

`shadow_run.min_width = 215` (`challenges.py:70-72`), but its half-platform span
and two 62 px margins (`compose:348-356`) need width **at least 248**. Metadata
admits candidates that cannot compose.

`dark_gate` and `lit_gauntlet` call the generic gate sampler before checking the
space needed for a shadow or enemy patrol (`compose:362-377`). Many switch samples
leave too little room. The remaining feasible interval could instead be computed
before sampling. The generator then removes that definition, so the six-attempt
budget is not six layout retries for a promising definition.

**Confirmed geometric competition: saws precede challenges.**

`generate_next:381-386` reserves saws first. `PuzzleValidator.validate:490-497`
rejects challenge objects overlapping the saw's full travel sweep plus padding.
Those rejections are often correct, but narrow platforms plus independent choices
leave little free space. Raising raw spawn probabilities cannot solve that conflict.

Saw feasibility is also substantially stricter than the nominal 205 px minimum:
150 px landing clearance + 90 px takeoff clearance + two radii + an 8 px center
interval require **282-296 px**, depending on the sampled 17-24 px radius
(`procedural.py:281-295`). At difficulty 10, 383 saw requests failed this geometric
slot test. Do not fix this by removing landing/takeoff safety clearances.

### C. Difficulty, complexity, and fairness

**Working progression, with a progress-semantics mismatch.**

`EndlessWorld.step:722-723` updates difficulty from player X minus spawn X using
`DifficultyManager.calculate` (`procedural.py:72-83`). Difficulty rose to
5.859-5.877 during forward live play. It is not stuck at its initial value.

`distance` is current displacement, not maximum achieved displacement.
Backtracking lowers difficulty. Already accepted segments are not regenerated,
and no new generation is normally needed while backtracking through the buffer.
If progression means cumulative achievement, a separate furthest-progress value
is needed; that expectation should be made explicit.

**Confirmed unreachable two-saw scaling branch.**

`GenerationProfile.create:106` gives ordinary platform widths at most 335 px,
shrinking to 310. `_hazards:297-299` requires width >=380 for two saws. Recovery
platforms do not generate hazards. `max_hazards` increasing to two cannot affect
normal generated segments under these defaults.

**Confirmed loss of combo geometry at high difficulty.**

`lit_gauntlet.min_width = 315` (`challenges.py:85-87`). Structural upper width
is 315 at difficulty 8.2, leaving no positive-width sampling interval meeting
the minimum, and is strictly below the minimum above 8.2. At difficulty 10 it
is 310. The gauntlet is very rare before that point and unavailable afterward.
Fixed catalog weights do not create increasing combo frequency on their own.

**Confirmed ineffective/incomplete controls.**

| Control | Evidence / effect |
| --- | --- |
| `GenerationProfile.combo_probability` | Defined in `procedural.py:99,114`; never consumed by selection |
| `GenerationProfile.challenge_damage_cap` | Defined at `procedural.py:98,113`; never consumed by validation/composition |
| `GenerationConfig.challenge_min_width` | Defined at `procedural.py:138`; generator instead uses catalog minima |
| `GenerationConfig.enemy_types` | Check at `procedural.py:332` inspects `Segment.enemies`, always empty in `generate_next`; sentries inside `Challenge.enemies` bypass it |
| Independent environmental/puzzle/obstacle density | No environment configuration; interactive and non-interactive definitions share one challenge probability/slot; standalone saw probability is separate from challenge obstacles |

The enemy configuration bypass is demonstrated by a characterization test:
`enemy_types=()` still generates challenge sentries.

**Confirmed bounds mismatch; dynamic fairness remains a validation gap.**

`EnemySpec.rect` (`challenges.py:220-223`) uses `y - height`, while runtime damage
(`procedural.py:698-700`) and rendering (`game.py:419-421`) use `y - height/2`.
With a 36 px enemy, validator bounds are **18 px too high**. This is not a general
world/camera coordinate error; it is a local anchor disagreement.

The validator tests the initial enemy rectangle, not its full moving patrol
rectangle, against other objects and saws (`challenges.py:466-497`). No overlapping
enemy/saw patrol sweep was found in the recorded live events; the missing check
must not be represented as a reproduced live collision or proof of unsolvability.
It becomes especially important when wider challenge platforms are introduced.

**Confirmed standalone saw resource-context omission.**

`_hazards(platform, profile)` receives no health/lantern context. Challenge
recovery rules therefore do not cover standalone saws. At difficulty 4 with both
resource fractions at 0.1, the real-width sweep still generated **86 saws**, alongside
617 caches and 68 cache-overlap fallbacks. This violates a shared resource-fairness
policy if that policy is intended to cover all damaging obstacles; it does not
prove every saw encounter is impossible to jump.

## 4. Measured verification

### Live application-update runs

Seeds `[1, 2, 7, 13, 21]`, 6,000 updates each at 60 Hz, through actual
`Game.update` and the real controller. Rendering was sampled at generation
events and endpoints, not captured at every frame. Each run advanced approximately
18,639-18,820 world px. The pilot sends inputs, not generation-position teleports.

| Seed | Generated platforms | Challenge requests | Accepted challenges | Interactive puzzles | Obstacle entities | Final active platforms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 58 | 48 | 16 | 8 | 10 | 8 |
| 2 | 58 | 48 | 21 | 11 | 12 | 8 |
| 7 | 57 | 47 | 17 | 9 | 15 | 8 |
| 13 | 57 | 47 | 16 | 3 | 15 | 8 |
| 21 | 57 | 47 | 16 | 6 | 14 | 9 |
| **Total** | **287** | **237** | **86** | **37** | **66** | **41** |

Interactive puzzles count challenges with switches. Obstacle entities count saws,
shadows, and sentries; barriers belong to the puzzle count and are not counted
again. Accepted challenge totals also include caches. Logical spawned/cleaned
object totals exclude the starting terrain and challenge containers, and include
platforms plus their owned entities.

Across these runs: 437 logical objects spawned, 372 cleaned, 246 streamed platforms
removed, and 34 switch activations observed. There were zero deaths, platform
fallbacks, registration discrepancies, or generation-guard hits. No live run
accepted a dark gate or gauntlet; accepted diversity was limited to four kinds.

Generation-event windows grouped by **player progress when requested**:

| Progress window (px) | Segments | Accepted challenges | Interactive puzzles | Obstacle entities |
| --- | ---: | ---: | ---: | ---: |
| 0-4,000 | 72 | 19 | 5 | 12 |
| 4,000-8,000 | 59 | 15 | 8 | 12 |
| 8,000-12,000 | 58 | 24 | 13 | 13 |
| 12,000-16,000 | 59 | 17 | 7 | 13 |
| 16,000-20,000 | 39 | 11 | 4 | 16 |

The initial window includes the startup prefetch; the last window is incomplete.
Small random samples and unequal exposure do not establish monotonic rates.
Existing segments retain the profile used when generated, even as the player
later reaches them at a different difficulty.

### Real structural-width sweeps

1,000 segments at each difficulty (200 per seed), passing real generated platform
geometry and saws into the existing challenge generator. These use a fixed
progress/resource context per sweep; they are **not live high-difficulty traversals**.

| Difficulty | Accepted challenges / 1,000 | Interactive puzzles | Gauntlets | Accepted saws | Saw slot skips | Platform fallbacks | Challenge fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 200 | 159 | 0 | 52 | 65 | 0 | 6 |
| 4 | 290 | 117 | 2 | 86 | 156 | 0 | 9 |
| 7 | 351 | 161 | 0 | 117 | 282 | 0 | 22 |
| 8.2 | 398 | 182 | 0 | 110 | 309 | 0 | 20 |
| 10 | 454 | 212 | 0 | 125 | 383 | 3 | 24 |

Accepted total challenge frequency rises from 20.0% to 45.4%, but puzzle counts
initially fall when new non-interactive types enter the shared pool. Complexity
does not track that frequency increase. Difficulty-10 generation represents
approximately 160,231 px progress under the current logarithmic curve; the live
100-second runs do not reach it.

Earlier verification (`echo_game/verify_challenges.py:29-37,60-84`) used **fixed
340 px synthetic platforms** for the rate sweeps. Its prior 22.3% / 32.5% / 44.2% /
51.9% figures describe that fixture, not actual width/profile compatibility. Those
tests remain useful unit checks but missed the narrowing-platform integration
constraints and cannot establish live high-progress combo availability.

### Evidence and limitations

- `audit-summary.json`: live runs, per-kind totals, progress windows, healthy and
  low-resource structural sweeps, render samples, source/instrumentation hashes.
- `audit-events.jsonl`: 570 live/idle events: 290 generation, 246 cleanup, 34 switch
  activations. Sweep candidate events are aggregated in the summary, not retained
  in this JSONL file.
- `audit-endless-seed7.png`: real sampled game rendering; visible terrain, saw,
  scenery, and sentry. The HUD's challenge label is not by itself proof that its
  gate is currently in the viewport.
- `audit-tests.xml`: **187 passed, 1 skipped** across `tests_echo`.
- `tests_echo/test_generation_audit.py`: 12 tests covering tracing preservation,
  hook restoration, actual update/spawn/cleanup integration, idle generation,
  seed/art repetition, ineffective controls, width incompatibility, enemy bounds,
  resource-independent saw selection, and current-vs-furthest progress.

The diagnostics preserve segment output, both generator RNG states, and actual
application-update results. All production `echo_game/*.py` hashes match the
pre-audit `docs/echo/verification/verification.json` baseline. Only diagnostics,
audit tests, and report artifacts were added during this audit.

Passing traversal/registration tests demonstrates playable sampled paths and
actual integration, not exhaustive puzzle solvability. Render sampling verifies
that actual routes execute and world data is available; it is not automated
pixel-by-pixel visibility or collision parity proof for every object. Dynamic
patrol validation and high-difficulty real-controller traversal remain required
before declaring all generated encounters fair.

## 5. Minimal repair plan — proposed, not implemented

### Step 1: Make policy explicit and controls effective

- Keep `ProceduralGenerator`, `PuzzleGenerator`, composer, validator, and
  `EndlessWorld`. Do not unify everything into a replacement generator.
- Introduce independently configurable **environment density**, **obstacle
  density**, and **interactive-puzzle density**, with documented units and
  progress-dependent profiles. Measure accepted objects per eligible segment and
  per world-distance window; a probability alone is not a realized density.
- Treat shadows/sentries/standalone saws as obstacles under the same obstacle
  budget. Interactive combined encounters consume both puzzle and obstacle
  budgets. Keep recovery-cache policy separate from puzzle density.
- Wire combo probability, enemy allowlists, and damage budgets into the existing
  rules/selection/validation. Replace or wire the unused minimum-width setting so
  eligibility has one authoritative meaning.
- Expose validated settings through constructors/configuration and usable launch
  controls in `game.py`; retain reproducible explicit seeds and existing defaults
  unless deliberately changed. Show active mode/seed/profile in diagnostics.
- Separate current displacement from furthest progress. Use furthest progress for
  achievement-based scaling if approved; retain current position for streaming.

### Step 2: Correct compatibility without weakening safety

- Derive feasible intervals from platform geometry, landing/takeoff reserves, and
  occupied obstacle sweeps **before** sampling. Align catalog eligibility with
  composer requirements (including the shadow's 248 px effective minimum).
- For dark gates, constrain the switch interval to leave the required shadow
  span; for gauntlets, constrain it to leave the required enemy patrol span.
- Allow a small bounded set of alternate layouts for a compatible definition,
  rather than exhausting definitions after one unlucky positional draw.
- Reserve obstacle/puzzle space jointly while retaining the existing generators.
  Do not simply disable saw-overlap validation to raise challenge counts.
- Supply occasional reachable, wider challenge platforms when complexity needs
  them. Preserve the ordinary structural profile and controller reachability
  checks. Two saws need a width compatible with both the >=380 trigger and actual
  clearance/spacing constraints, not merely a lower threshold.
- Use shared center-anchored enemy bounds for validation, rendering, and damage;
  validate full patrol sweeps. Pass resource context to standalone-hazard policy
  and validate the complete segment's damage/resource fairness, not only its
  optional challenge.
- Evaluate current Y concentration separately: sample feasible height intervals
  instead of repeatedly clamping/rejecting, but preserve the real controller's
  reachable path and bounded fallback. A cosmetic variety target must not weaken
  jump validation.

### Step 3: Add only the missing runtime environmental responsibility

- Add an isolated data-only environment module, e.g. `echo_game/environment.py`,
  receiving the already validated platform, reserved challenge areas, profile,
  and its own persistent derived-seed RNG stream. It must not consume structural
  or challenge RNG draws or recreate an RNG for every placement.
- Return typed specs with unique IDs, world positions/bounds, layer, and
  `platform_id` / `generation_index`; add an environmental payload to `Segment`.
- Spawn/store those specs in `EndlessWorld`, add a dedicated rendering pass, and
  remove specs/colliders through existing platform-owner cleanup.
- Keep decorative and solid roles explicit. Begin with non-blocking environment
  objects; opt-in collidable wood/rocks must enter complete path validation and
  real collision registration before spawning.
- Retain the existing atmospheric parallax artwork. Runtime objects supplement
  it; additional background themes are optional and do not substitute for world
  placement/ownership.

Proposed type-specific rules (not a universal placement function):

| Type | Placement and safety rules |
| --- | --- |
| Tree | Root on a supported surface; canopy/trunk footprint spacing; rear layer by default; preserve switch/gate visibility and landing edges |
| Bamboo | Small bounded clusters on suitable surface spans, with intra-cluster jitter and inter-cluster clearance; do not fill every narrow platform |
| Grass | Surface-edge scatter/patches at higher density; non-solid; exclude interaction footprints rather than using tree-scale spacing |
| Rock | Surface support plus slope/edge/neighbor checks; small decorative rocks distinct from opt-in solid obstacles |
| Wood | Supported log/debris orientation and footprint; solid props reserve controller-sized passage and affect reachability checks |
| Dirt | Terrain material/edge or supported structural addition, not arbitrary floating scatter; structural collidable dirt stays under platform geometry validation |

### Step 4: Verify each increment before expanding content

Keep the standalone audit command and turn current-deficiency characterization
expectations into corrected-behavior tests as repairs land. Run the campaign
suite after each increment. Broader puzzle catalogs and multi-segment puzzles are
optional future work; first restore reliable availability of existing mechanics.

## 6. Regression risks and required test gates

| Risk | Required verification |
| --- | --- |
| Density/configuration changes disturb unrelated output | Fixed-seed replay; separate RNG streams; zero environment density preserves structural/challenge output; independently vary each density and enemy allowlist |
| More props make paths blocked or unreadable | Type-specific support, edge/spacing, non-stacking, reserved landing/takeoff/interaction space; solid-prop path validation; screenshot checks for occlusion |
| Wider platforms invalidate structural bounds or streaming | Real-controller reachability over many seeds, actual profile geometry, bounded retries/fallbacks, frontier coverage, supported-body retention, cleanup of every owned registry |
| More combos increase unavoidable damage | Shared initial/render/damage bounds, full moving sweeps, low-health/low-lantern and arrival-resource cases, complete-segment damage budget, input-only solves for each accepted interactive type |
| Raw spawn chance does not deliver desired availability | Rates per eligible segment and per full distance window; many seeds; max challenge-free/puzzle-free runs; catalog diversity and combo availability at difficulties 1/4/7/8.2/10 |
| Backtracking changes difficulty or accesses deleted world | Explicit progress semantics, same-frontier/backtracking tests, no retroactive segment reshuffle, established cleanup-distance behavior |
| New art/object rendering diverges from collision | World-to-screen transforms, bounds/anchor equality, Pymunk registrations where solid, logical contact checks where non-solid, saved captures at known object positions |
| Campaign behavior regresses | All six authored rooms, ending traversal, checkpoint behavior, help/pause/input tests; campaign saws remain instantly fatal |

High-difficulty verification must include **real controller traversal on actual
generated widths**, not only wider synthetic puzzle fixtures. Include long
forward runs, resource-depleted runs, deterministic restarts, paused/idle cases,
and bounded active entity/memory checks. Statistical increases should be assessed
over adequate exposure and multiple seeds, not required in every random window.

## 7. Reproduction and approval boundary

From the repository root:

```sh
TMPDIR=/tmp/opencode .venv-echo/bin/python -m scripts.audit_generation
TMPDIR=/tmp/opencode .venv-echo/bin/python -m pytest tests_echo -q --junitxml=docs/echo/audit/audit-tests.xml
```

To inspect the actual procedural mode interactively:

```sh
.venv-echo/bin/python play_echo.py --endless --seed 7 --no-save
```

No gameplay repairs are included in this audit. The next action is approval of
the incremental plan and confirmation of the user's launch mode/session. If their
session still has no puzzles after substantial forward travel in endless mode,
capture that exact seed, progress, and command and reproduce it before asserting
the current measured runs explain it.
