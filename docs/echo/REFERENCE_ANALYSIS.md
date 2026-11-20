# What was learned from the supplied LIMBO installation

## Scope and limits

Reference: `/home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO`.
Inspection was read-only. No executable was launched, DRM altered, resource
reused, or original audio/art copied. This is a **mechanical recreation with
original content**, not a complete port of LIMBO or a claim to its source code.

The available REA connection had no configured Ghidra, IDA, or Kuna engine;
Wine was also absent. Therefore the exact native routines and runtime physics
could not be recovered or measured. No exact original timestep, coefficients,
physical units, animation rig, or collision algorithm is claimed.

## Evidence ledger

| Finding | Evidence | Scope / interpretation |
|---|---|---|
| `limbo.exe` is a 32-bit x86 Windows PE; 5,074,432 bytes | REA `ev_f9ed430c671f90104de7970e5ec46f2e1a352e5a0c2fb0f0dbffb104aa5c2f6f`, retained in `rea-evidence.json` | Observed static headers/import tables |
| Direct3D 9, shader compilation and DirectInput declarations | Same Evidence; 12 DLL descriptors, 234 imports, complete import-table coverage | Declared imports, **not observed calls** |
| `PhysicsWorld2D::Update`, `PhysicsCoreStep`, `PhysicsIntegrate`, `PhysicsPostIntegrate`, `PhysicsCollisionManager`, `PhysicsJoint2D` | `local-artifact-findings.json`, executable literal byte offsets | Suggest a staged 2D physics subsystem; strings alone do not establish implementation or reachability |
| `JointPin2D`, `JointSlider2D`, `JointSpring2D`, `JointWind2D` | Same local inventory | Joint-family names, not recovered equations |
| `BoyRopeState`, `BoyGrabState`, `ropeVelocityLimit`, `ropeSlopePenalty` | Executable and boot package literals | Supports separate grab/rope control states |
| `PhysicsTriggerWater`, `PhysicsTriggerImpact`, `collisionfriction` | Executable literals | Water/impact hooks and friction vocabulary, not proof of a particular buoyancy model |
| `worldgravity`, `boygravity`, `gravityshift`, `gravityZone` | Executable and package literals | Multiple gravity-related settings/control paths; actual behavior unmeasured |
| Runtime package contains `worldgravity = "0.000000,-10.000000"` | Literal inventory and offset | A serialized value in that package, **not a universal/default measured gravitational acceleration** |
| Package table candidate: a count plus 12-byte identifier/offset/size records | `reference.py`; 1,641 boot and 455 runtime entries; every range fits and final range reaches EOF | Validated structural hypothesis; no filenames or object decoder inferred |
| Controls use directions and Ctrl/action; configured backbuffer 720 | Read of supplied `settings.txt` | Observed configuration, not measured rendering resolution |

Exact artifact SHA-256 values:

```text
limbo.exe         acea5e50330ac0356540cdcebd46fe5692b02528cac9dd3ae670a65b4d7bc4a4
limbo_boot.pkg    e7b5128c8ea5251959f6af78f418f89ceb188d8dc2145e3a17afb5ecb8ebbf5f
limbo_runtime.pkg e5cdd74fb89130f7dd3a5e61e949ad9e38f2962c6d03abaa6b5af09babcb14ff
```

### Structured follow-up (not just strings)

The initial inventory above has now been complemented by a bounded structural
decoder: [`PACKAGE_DECODING.md`](PACKAGE_DECODING.md) and
[`packaged-obstacle-data.json`](packaged-obstacle-data.json). It reads both
declaration lists and count/list function extensions in six selected boot
members: **211 declarations / 12,825 bytes**, leaving **3,166 bytes explicitly
undecoded**. Runtime members 0–102 decode completely into 39 chapter mappings
and 102 six-field checkpoint records. Among those records, `boygravity` is
literally zero in all 102; this does **not** establish zero net player force.

[`REFERENCE_GAMEPLAY.md`](REFERENCE_GAMEPLAY.md) separates explicit gameplay
guide instructions from twenty inspected stills; no video or native runtime
was observed. [`REFERENCE_COMPARISON.md`](REFERENCE_COMPARISON.md) maps those
concrete behaviors to the current recreation and its acceptance tests.

Reproduce the byte inventory:

```bash
.venv-echo/bin/python -m echo_game.reference \
  /home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO \
  --output docs/echo/local-artifact-findings.json
```

## Puzzle-design context (external, not binary evidence)

Brandon Sheffield's 2010 report of Jeppe Carlsen's GDC Europe talk explains
LIMBO's direction/jump/grab controls, visual and audio cues, low death penalty,
and the importance of making the correct solution easy to execute:
[Game Developer, August 16, 2010](https://www.gamedeveloper.com/game-platforms/gdc-europe-i-limbo-i-s-carlsen-on-making-players-your-worst-enemy-and-your-best-friend).
The article was fetched during this investigation. It is reporting about the
design, not source-level evidence for the supplied build.

ECHO deliberately adds optional controls/help and explicit room hints. Its
six geometries, courier with scarf/lantern, moth guide, signal story, art,
and score are original rather than recreating LIMBO's particular expression.

## How the recreation works

### Simulation and character

`physics.py` uses Pymunk/Chipmunk at **120 fixed steps per second** with 30 solver
iterations. These are our choices. Pixels use downward-positive Y. Gravity is
1,050 px/s²; the 2 kg upright character accelerates toward 190 px/s and jumps
at 445 px/s. Rotation is locked. Ground probes respect the gravity direction.
A 100 ms coyote window and 120 ms jump buffer make ledge jumps forgiving.

Crates remain genuine rigid bodies. The controller transfers horizontal
momentum through collision contacts, so mass and surface friction matter.
Holding a crate attaches a force-limited damped spring, permitting both pushing
and pulling without directly setting the crate's position.

### 1. Crate, pressure plate, gate

Leave the crate on the plate and jump over it. A shape-surface contact sensor
activates the pressure plate. A kinematic gate rises gradually while
the plate remains occupied, and descends otherwise. Walking through a closed
gate is blocked by a solver shape, not just by a visual effect.

The sensor checks the shape's bottom surface against the plate,
so a hovering object centre cannot activate it. A descending gate's sweep is
bounded by an obstructing box: it remains jammed until the box is removed. This
matches the documented physical door-jam behavior, though the wheel/door level
sequence itself is not reproduced.

### 2. Hanging rope

Twelve short rigid segments are joined with pivots and angular limits. Catching
a nearby segment adds a pivot between it and the courier. A/D applies force,
which builds swinging momentum. Space removes the joint and adds a small
release impulse; gravity then follows an ordinary ballistic trajectory.
W/S moves the hand constraint along the chain at a chosen 85 px/s; neither
character nor rope is teleported. The right ledge is elevated, and a paired
input-only regression demonstrates that this pilot needs its climb-height
choice before release.

### 3. Flood and buoyancy

The hollow crate receives `F_up = mass * g * 2.3 * submerged_fraction`.
Velocity-dependent drag damps bobbing; angular drag and restoring torque keep
the broad box stable. This is an intentionally simplified water model, not a
fluid simulation or LIMBO's recovered formula. A/D remains ordinary walking
even on the crate, **not rowing**. A separate handle slides away the
cover; the box otherwise cannot float through it. A nearby valve raises the
water by up to 170 px at a chosen 20 px/s, adding width × height to the recorded
water area. The box carries player load and rises with the water. The courier
cannot swim and drowns after sustained submersion. Passive boat travel exists
in the reference, but is different from the removed on-deck motor.

### 4. Oscillating seesaw

A 440 px, 70 kg beam rotates around its centre pivot with ±0.36 rad limits.
A passive restoring spring (chosen stiffness 1,000,000 and damping 20,000)
allows the courier's alternating runs and endpoint jumps to build oscillation.
The exit bank is raised; departure occurs near a raised right-end crest, not
after a hard-coded repetition count. The old parked iron weight has been
removed. Neither beam angle nor player position is scripted. Tests compare
motion with endpoint standing, direct walking/jumping and a locked-flat beam.

### 5. Temporary gravity and saws

A nearby switch activates five seconds of inverted space gravity, then expires
without a second relay. Grounding/jumping switch direction too; crates fall
toward the ceiling with the courier. Changing acceleration does not zero
existing velocity. Original synthesized beeps accelerate toward expiry. The
floor saw and ceiling blade make the window consequential. No permanent exit
latch remains. This room adapts the documented temporary-gravity sequence.

### 6. Magnetic ceiling and separate block gravity

The sixth room implements the previously documented ceiling-capture sequence:
enable magnetic power, raise the blocks, retain the first at contact, then
restore downward block gravity while the second is still far enough below its
plate to stop and fall. The retained block opens a passage; the returned block
forms a physical step. Original rails, coil artwork, capture/release cues and
on-screen state labels explain the independent controls.

The block-only field changes acceleration without changing player gravity or
erasing either block's velocity. A Pymunk contact callback adds a finite-force
holding constraint only at the powered ceiling. Turning magnet power off removes
the constraint. Early, late and momentum-overshoot witnesses fail the intended
split-height route; a normal-input witness succeeds at 60/120 Hz. Exact geometry,
rail constraints and capture-force limits are ECHO choices. The original
tram/rope sequence and autonomous periodic gravity remain unimplemented.

### Checkpoints and presentation

Each signal advances to a fresh room and atomically saves its index. Death
restarts the current room, including prop and constraint state. The campaign
ends after six signals. Pygame handles input/window/composition, Cairo
generates vector assets, and NumPy synthesizes the soundtrack and sound effects.

## Remaining limits

- Six original rooms, not LIMBO's complete campaign.
- No native decompilation or execution comparison was possible on this host.
- No exact original spider AI, animation IK, continuous-collision settings,
  water solver, or original asset/format reconstruction is claimed.
- Automated runs demonstrate input-only puzzle solvability and deterministic
  behavior in **ECHO**, not behavioral equivalence with the supplied LIMBO.
