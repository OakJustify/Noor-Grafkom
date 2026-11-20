# LIMBO behavior → ECHO implementation

## What the evidence actually establishes

This comparison uses two complementary sources:

1. **Read-only packaged data from the supplied installation.**
   [`PACKAGE_DECODING.md`](PACKAGE_DECODING.md) documents the parser and
   [`packaged-obstacle-data.json`](packaged-obstacle-data.json) retains
   identities, half-open byte ranges, raw fields and coverage. Both tables were
   validated; six selected boot members yield **211 declarations**. Runtime
   members 0–102 yield **39 chapter mappings and 102 checkpoint records**.
   Script execution bodies and most other members remain undecoded.
2. **Explicit gameplay instructions and inspected stills.**
   [`REFERENCE_GAMEPLAY.md`](REFERENCE_GAMEPLAY.md) and
   [`reference-gameplay.json`](reference-gameplay.json) retain 26 source
   records, nine findings and 20 inspected image identities. GameSpy/IGN's
   chapter pages and Matt Hughes's independent GamesRadar guide also support
   the contracts in [`reference-contracts.json`](reference-contracts.json).
   Text reports actions and sequences; stills establish visible placement,
   not motion or timing measurements.

**No native LIMBO session or gameplay video was observed.** Guides cover
published releases, not a controlled replay of the supplied Windows build.
Publisher chapter numbering differs from the package map. The following is a
qualitative mechanical adaptation with original geometry, characters, art and
audio, **not a recovered solver or a checkpoint-by-checkpoint port**.

## Reference-to-implementation matrix

| Family | Concrete reference behavior and evidence | Previous ECHO limitation | Current implementation / acceptance |
|---|---|---|---|
| Rope traversal | [GameSpy/IGN chapter 2](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_8.html) describes swinging from a vine; [chapter 8](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_14.html) describes climbing a sinking rope and transferring. PortForward chapters 2, 10 and 15 independently describe up/down climbing and release. Boot 1620 declares segment count, density, drag and usability; 1518 declares rope/door signals. | Swing/release only; no vertical movement or meaningful height choice. | A held hand constraint travels along linked rigid segments. Up/down changes attachment height without setting player position. The elevated destination makes the pilot's climb-height choice consequential. Tests check segment traversal, detachment/momentum and paired climb/no-climb input witnesses. Sinking-rope gate and rope-to-rope transfer remain unimplemented. |
| Water and cover | [Chapter 10](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_16.html) reports positioning a box beneath a covered opening, exposing the gap, operating a flood lever and riding the rising box. Chapter 9 reports positioned wood and pipe-controlled filling. Boot 1574/1575 declare water targets, area rate and start/stop signals; runtime map names rain/water-machine and sewer-flooding resources. | A/D automatically propelled a raft and kept the player centered, without source support for on-deck rowing. | Open the sliding cover, position the hollow box, activate the separate valve, board and rise with the water, then jump out. The cover physically blocks ascent if closed. Ordinary movement can walk off the box. Tests check bounded fill area, valve start/stop, loaded flotation, blocked cover, missing water/support and the removal of rowing. Ball-assisted flotation and balancing multiple reservoirs remain unimplemented. |
| Pressure door | IGN chapter 16 and PortForward chapter 26 report pressure activation and placing a box in a closing doorway to jam it; a different two-box mechanism lifts a ledge. | Centre-band sensing could activate with a hovering body; an infinite-mass closing gate could pass through/crush a box. | Shape-bottom contact activates the plate. The gate's descending sweep stops at a box in its opening; removal allows closure. Tests assert contact, opening, jamming, intact box and later closure. The campaign is still a reduced crate/plate/door arrangement, not the original wheel track or two-box elevator. |
| Temporary gravity | [Chapter 23](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_29.html) reports repeated activation of an expiring field to relocate a box. [GamesRadar page 4](https://www.gamesradar.com/limbo-walkthrough-and-achievement-guide/4/) independently describes timing gravity shifts while crossing saws. Boot 1566/1569 declare gravity controls, separate boy/world settings and rotation/strength metadata. | Second relay permanently latched an exit and reset vertical velocity on every flip; no named reference dependency. | One temporary switch reverses player/box acceleration, preserves existing velocity, and expires without a second relay. The player crosses above a floor saw and waits before the ceiling blade. Tests check expiry with held action, airborne reactivation and preservation of both player and box velocity. Five seconds is ECHO tuning, not a measured original timer. |
| Gravity warning | [Chapter 24](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_30.html) explicitly reports accelerating beeps before reversals; PortForward chapter 37 confirms repeated automatic changes. | No timing cue; gravity was manually latched. | Original synthesized beeps accelerate toward temporary-field expiry, accompanied by a visible countdown. Tests check decreasing intervals and cessation after expiry. Room 5 adapts the temporary sequence; the autonomous periodic-gravity/magnet/gun sequence remains unimplemented. |
| Pivoted platform | [Chapter 13](http://xbox360.gamespy.com/xbox-360/limbo/guide/page_19.html) and PortForward chapter 22 describe running/jumping between edges, building oscillation and leaving at a useful phase. Runtime chapter24 names `crane_and_seesaw.branch`. | Heavy crate made permanent inclined stairs; this is not the reported pumping sequence. | The crate is removed. A passive pivot/restoring spring responds to alternating player runs and endpoint jumps; the pilot departs near the raised right-end crest. Tests compare alternating motion to standing, direct walking/jumping and a locked-flat beam, at both 60/120 Hz input sampling. Original solver/joint type and repetition count are not recovered. |
| Magnetic ceiling / box field | [IGN chapter 22](https://www.ign.com/wikis/limbo/Chapter_22) and [PortForward chapter 34](https://portforward.com/games/walkthroughs/Limbo/Chapter-34.htm) describe holding the first contacted block high and returning the second low with independent controls. PortForward chapter 33 separately reports a box-only field. | Both variants were documented but unimplemented. | Room 6 combines these ideas: separate magnet power and manual block-gravity switches, capture after actual solver contact, preserved velocity, and a lower block used to reach the exit. Early, late, unpowered, release, replay and 60/120 Hz witnesses cover the causal dependencies. The original guide's tram/rope route and magnetic force law are not reconstructed. |

### Not every gravity control is the same

The research distinguishes **manual box-only**, **manual player-inclusive**,
**temporary**, and **autonomous periodic** gravity. It also establishes an
**independent magnetic capture control**: capture one contacted block, restore
gravity before the other arrives, and leave a split-height route. Manual
switching itself was therefore not an error in ECHO; the unsupported permanent
exit latch and lack of a concrete causal sequence were the errors.

Room 5 selects the temporary variant. Room 6 adds a manual box-only field and
independent ceiling capture, combining two documented variants in original
geometry. Separate gravity
vectors in packaged declarations/checkpoints support further investigation,
but do not recover their execution semantics or establish how a zero stored
`boygravity` contributes to net force. The new implementation is grounded in
the explicit guide sequences, not inferred from those declarations alone.

### Passive drift is not input-driven rowing

PortForward chapter 2 reports a boat beginning to float across after boarding
breaks its chain. That supports passive travel for that boat. It does **not**
establish that walking on any floating box drives a hidden motor. ECHO removes
that invented input mapping without claiming LIMBO never contains drifting
water vehicles.

### Oscillation and useful departure phase

`echo_game/seesaw.py` configures a passive beam and provides an input-only
witness. The courier reverses between the ends with ordinary jumps, briefly
unloading the support while its momentum continues. Departure is allowed by
the witness only at a right-end arrival with angle below −0.26 rad and angular
speed below 0.08 rad/s, while grounded or within the normal coyote window.
These are **pilot/tuning choices**, not hidden gameplay permission checks.
A human can attempt any jump at any phase.

The nominal standalone witness completes in about 17 seconds with four
reversals and five jumps. Its angular range is about 0.678 rad versus 0.527 rad
of total transient motion for an endpoint-standing comparison; standing then
settles and cannot reach the exit. The successful input trace replays
deterministically but fails when the beam is locked horizontal. These are ECHO
measurements, not the original guide's approximate repetition count.

### Magnetic capture and timing

`echo_game/magnet.py` gives each iron block a vertical groove constraint and
an independently contactable ceiling plate. Enabling the magnet alone does
not move a block. The field adds a force only to the blocks, leaving the courier
under ordinary gravity. A real upward-facing block/plate collision is recorded
by Pymunk's `post_solve` callback. Only then is a finite-force pivot added to hold
the contacted block. Turning off the magnet removes that constraint.

The first block lifts about 76 px before contact; the second must travel about
236 px. The input-only pilot restores gravity on the first contact cue. The
second continues upward briefly, then falls and becomes a usable step while
the first leaves a passable opening below. No exit permission flag checks the
split: the physical route and ordinary jumps determine success.

The natural-spawn witness completes in **7.267 s at 120 Hz input** or **7.292 s
at 60 Hz input**. Early reversal captures neither block; late reversal captures
both. A further witness reverses before the second contact but still captures
both because the second block has too much upward momentum. These are ECHO
measurements of specified attempts, not exact LIMBO timing or an exhaustive
proof that every other player strategy fails. See `tests_echo/test_magnet.py`.

## Chosen models, not recovered constants

- Pymunk/Chipmunk rigid bodies and constraints, fixed **120 Hz**, **30 solver
  iterations**; pixels and downward-positive Y.
- Upright 2 kg courier; **1,050 px/s²** normal gravity, 190 px/s walking target,
  445 px/s ground jump, chosen coyote/jump-buffer windows.
- Twelve rope segments; **85 px/s** sliding hand coordinate; force-limited
  attachment and a small intentional jump-release impulse.
- One 280 px wide basin; **170 px** maximum rise at **20 px/s**. Water area
  increases by width × rise. Buoyancy is a chosen submerged-fraction force,
  with velocity/angular drag and restoring torque—not LIMBO's water solver.
- Five-second temporary field; accelerating original beep schedule. Field
  changes preserve momentum; no original timer or beep-count equivalence.
- A 440 px, 70 kg seesaw with ±0.36 rad limits, restoring stiffness 1,000,000
  and damping 20,000. Its angle, velocity and torque are not scripted.
- Surface-contact plate and bounded kinematic-door sweep. These implement the
  documented causal behavior without recovering the reference's machinery.
- Guided 150 px / 36 kg and 80 px / 20 kg iron blocks, with ceiling undersides
  at Y=230 / 140 and floor Y=460. Capture-force limits are 12 × block weight;
  block orientation is locked. These are contact restraints, not a simulated
  electromagnetic field or recovered material-eligibility rule.

Observed declaration annotations (for example rope count default 6, length
default 4, water area rate default 5) remain in the evidence ledger. They are
**not** assumed to be level-instance values or imported as ECHO coefficients.

## Verification boundary

`tests_echo/test_package_data.py` checks decoder structure, bounds, function
extensions, coverage and saved observations with synthetic/portable fixtures;
an optional explicitly selected installation test reproduces the source
hashes and all selected decoded data.

`tests_echo/test_reference_mechanics.py` checks the source-linked qualitative
contracts. Staged collision fixtures are explicitly labeled and are **not**
campaign solutions. Negative witnesses test a specified input/fixture, not the
impossibility of every hypothetical strategy.

`tests_echo/test_seesaw.py` uses the actual production room/constraints, with
comparison worlds changing only declared damping or the rotary lock. It
checks phase departure, robust 60/120 Hz controls, standing/direct-walk
failures and deterministic successful-trace replay.

`python -m echo_game.verify` drives the real application continuously using
only ordinary inputs and saves scene captures, completion states, source
hashes and `mechanics_witness` records. That demonstrates ECHO's transitions,
climb-height choice, exposed cover/filling, player rise on a box and automatic
gravity expiry, oscillation and crest departure, and a captured high block
paired with a low block supporting the player. **Solvability alone does
not establish fidelity to LIMBO.**

Remaining unimplemented sequences include sinking-rope gates and transfers,
movable jaw traps/spider baiting, rolling boulders/falling logs, ball-assisted
flotation, box momentum through a sloped gap, guns, the tram/rope sequence, and
autonomous periodic gravity. Exact native integration/collision/controller/water
behavior remains unresolved.
