# Procedural Puzzle Generation Design Document
## ECHO: The Hollow Signal - Endless Mode Enhancement

---

## 1. Problem Statement

**Original problem:** The earlier streaming Endless mode generated mainly
platforming/resource obstacles. A subsequent six-room shuffle reused complete
Campaign layouts, which also did not meet the requirement for genuinely new
layout, puzzle and background contents.

**Campaign Puzzles (Real):**
- Level 1: Crate + Pressure Plate → Gate (physics drag, weight detection, causality chain)
- Level 2: Rope Swing → High Ledge (momentum physics, timing)
- Level 3: Water + Crate + Cover + Valve (buoyancy, state chain)
- Level 4: Seesaw Launch (torque/momentum, rhythm)
- Level 5: Gravity Flip Maze (state inversion, timing)
- Level 6: Magnet + 2 Crates (multi-object state, gravity manipulation)

**Endless "Challenges" (Obstacles):**
- `light_gate`: Walk to switch → Press E → Walk through (single action)
- `shadow_run`: Keep lantern on while walking (resource check)
- `sentry`: Walk past / use lantern to stun (reflex/resource)
- `dark_gate`: Walk to switch in shadow → Press E → Walk through (linear)
- `lit_gauntlet`: Walk past sentry → Hit switch → Walk through (linear)
- `beacon_charge`: Walk to cache (zero thought)

### Implemented system (2026-11-19)

`echo_game/rooms.py` now generates complete immutable `Level` configurations and
`PuzzleStage` sequences. `ProceduralRoomWorld` gives these to `World.__init__`
before spawning mechanisms. No frozen-level mutation, fake magnet state or
separate simplified water solver is involved. Public `EndlessRoomGenerator` /
`EndlessRoomWorld` names remain aliases for compatibility, not a template shuffle.

**Spatial grammar:** two to four stages; a seeded main-mechanic bag distributes
all six mechanics across each cycle, without adjacent main-mechanic repeats at
cycle boundaries. Push/pull crate relays can precede or follow the main mechanism.
Generated stage widths, targets, masses, sizes, water levels/rates, rope geometry,
bank elevations, beam lengths and gravity-wall geometry change the playable room.
Count increases from at most two stages initially to at most four from room ten.
Gaps have no continuous hidden floor; high banks and gravity walls require their
mechanisms rather than merely decorating a walkable base floor.

**Runtime:** relay gates latch only after their own crate is genuinely grabbed
and resting fully over the plate. The courier alone cannot activate them. Water,
cover, rope, seesaw and magnetic capture use Campaign's actual implementations.
Magnetic block indices isolate the two iron blocks from relay crates. A generated
gravity field accelerates the courier only, so remote relay crates cannot fly
away while another stage is played. This field scope is an explicit difference
from Campaign's whole-space gravity flip; both verifier and game use it.

**Verification:** `RoomPilot` emits only movement/jump/grab/action/climb controls.
`RoomVerifier` runs the whole room from spawn to exit at 120 Hz, matching
`Game.update`'s 60 Hz input sampling (jump on the first substep only). Acceptance
requires exit completion without death, every relay solved and the main mechanic
witnessed. Probes remove interactions, attempt walking/hopping, and disable the
main mechanic while solving surrounding stages normally. Each simulation has a
14,400-step cap; direct walking/hopping probes use at most 4,800 steps. There are
at most 16 candidates per request; exhaustion raises rather than quietly emitting
an unverified/empty room. These are bounded concrete witness/bypass checks, **not
an exhaustive solver, a proof against every exploit, or human difficulty testing**.

**Uniqueness/replay:** independent SHA-256 signatures cover actual terrain,
puzzle-stage/object configuration and visual parameters. Previously accepted
signatures are rejected, excluding titles/room numbers from layout and puzzle
identity. Room content is derived from the run seed and room number; a separate
visual RNG is unaffected by rejected geometry candidates. Retry reuses the same
room object without consuming RNG. Room history holds 32 entries; compact seen
signature sets grow with accepted room count.

**Scenery:** `echo_game/room_art.py` draws new seeded Cairo sky and three parallax
silhouette layers per room, not six fixed background images. Structure positions,
counts, construction, heights, terrain contours, sky tint, light position,
time-of-day brightness, fog and particle types vary. Campaign player/prop/HUD
styling is retained. Only two room panoramas are cached, and evicted scenery
regenerates identically. Palette does not select collision or mechanic rules.

**Legacy boundary:** lower-level streaming `EndlessWorld`, challenge generation,
and its verified crate–plate slice remain for regression tests. Generic water,
seesaw, rope, gravity and magnet `PuzzleInstance` builders in
`puzzle_archetypes.py` are not admitted by that streaming verifier; full rooms
use the independently integrated `rooms.py` system instead.

Reproduce:

```bash
.venv-echo/bin/python -m pytest tests_echo/test_endless_rooms.py -q
.venv-echo/bin/python -m pytest --tb=short
.venv-echo/bin/python play_echo.py --endless --seed 7 --demo --headless \
  --frames 3600 --show-hud --no-save \
  --report /tmp/opencode/procedural-rooms.json \
  --screenshot /tmp/opencode/procedural-rooms.png
```

Cold generation includes real physics verification and takes seconds, not the
millisecond/platform target from the original proposal. Six mechanism families
are reusable rules, not infinitely many novel mechanics. Human playtesting and
background variety beyond this finite grammar remain separate quality checks.

### Historical proposal below (not a description of current implementation)

Sections 2–13 retain the original speculative architecture, roadmap and targets.
Their placeholder interfaces, difficulty tables, obstacle fallback and performance
targets must not be mistaken for implemented features or measured results.

---

## 2. Architecture Overview

### 2.1 Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProceduralPuzzleGenerator                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Archetype   │  │   Composer   │  │      Verifier        │  │
│  │  Registry    │──▶│  (places    │──▶│  (simulates player   │  │
│  │  (templates) │  │   objects)   │  │   physics to verify  │  │
│  └──────────────┘  └──────────────┘  │   solvability)       │  │
│        ▲              │             └──────────┬─────────────┘  │
│        │              ▼                      │                │
│        │  ┌──────────────────┐              │                │
│        └──│  Constraint      │◀─────────────┘                │
│           │  Solver          │                               │
│           │  (positions,     │                               │
│           │   dimensions)    │                               │
│           └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EndlessWorld Integration                    │
├─────────────────────────────────────────────────────────────────┤
│  • Spawns physics bodies (crates, plates, gates, water, etc.)  │
│  • Registers with PuzzleVerifier for runtime validation         │
│  • Tracks puzzle state machines                                 │
│  • Handles cleanup/streaming                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
Platform Generated
       │
       ▼
PuzzleGenerator.generate(platform, context)
       │
       ├──▶ Select Archetype (weighted by difficulty, resources, tags)
       │
       ├──▶ Composer.place(archetype, platform, caps, rng)
       │       │
       │       ├──▶ ConstraintSolver.solve(archetype.constraints)
       │       │
       │       └──▶ Returns PuzzleSpec (positions, dimensions, physics params)
       │
       ├──▶ Verifier.simulate(PuzzleSpec, caps)
       │       │
       │       ├──▶ PhysicsSimulator.run(puzzle, "perfect_player")
       │       │
       │       ├──▶ Checks: solvable, non-trivial, fair
       │       │
       │       └──▶ Returns VerificationResult
       │
       └──▶ If verified: Spawn in EndlessWorld
           If failed: Retry with different params / fallback to obstacle
```

---

## 3. Archetype Definitions

### 3.1 CratePlateArchetype (Port from Level 1)

```python
@dataclass(frozen=True)
class CratePlateSpec:
    """Crate must be dragged to pressure plate to open gate."""
    # Platform-relative positions
    crate_spawn_x: float      # Where crate spawns (left side)
    plate_x: float            # Pressure plate center x
    plate_width: float        # Plate width
    gate_x: float             # Gate position (blocks exit)
    gate_width: float
    gate_height: float
    
    # Physics params
    crate_mass: float = 6.0
    crate_size: tuple[float, float] = (54, 54)
    
    # Constraints (validated by ConstraintSolver)
    # 1. Crate must be pushable from spawn to plate
    # 2. Plate must be before gate
    # 3. Gate must block exit path
    # 4. Player must reach crate from platform left edge

@dataclass(frozen=True)
class CratePlateConstraints:
    min_crate_to_plate: float = 100.0      # Min push distance
    max_crate_to_plate: float = 400.0      # Max push distance (player stamina)
    min_plate_to_gate: float = 50.0        # Plate must be before gate
    gate_blocks_exit: bool = True          # Gate must block forward progress
```

### 3.2 WaterCrateArchetype (Port from Level 3)

```python
@dataclass(frozen=True)
class WaterCrateSpec:
    """Crate floats in raised water to reach high exit."""
    water_x: float
    water_width: float
    water_base_y: float
    water_raise: float          # How much water rises
    water_rate: float           # Rise speed
    cover_x: float              # Cover handle position
    valve_x: float              # Valve position
    crate_spawn_x: float
    exit_y: float               # High exit that requires floating crate
```

### 3.3 SeesawLaunchArchetype (Port from Level 4)

```python
@dataclass(frozen=True)
class SeesawLaunchSpec:
    """Run on seesaw to build momentum, launch to target platform."""
    pivot_x: float
    beam_length: float
    target_platform_x: float
    target_platform_y: float
    target_platform_width: float
```

### 3.4 GravityMazeArchetype (Port from Level 5)

```python
@dataclass(frozen=True)
class GravityMazeSpec:
    """Vertical corridor with saws, gravity flip switches."""
    corridor_x: float
    corridor_width: float
    flip_switches: list[float]   # Y positions of switches
    saw_positions: list[tuple[float, float, float]]  # x, y, radius
    ceiling_saw: tuple[float, float, float] | None
```

### 3.5 MagnetStairsArchetype (Port from Level 6)

```python
@dataclass(frozen=True)
class MagnetStairsSpec:
    """Lift crates with magnet, flip gravity to create stairs."""
    magnet_ceilings: list[float]      # Y positions of ceiling magnets
    magnet_switch_x: float
    gravity_switch_x: float
    crate_spawns: list[tuple[float, float, float, float]]  # x, y, w, h
    exit_y: float
```

### 3.6 RopePendulumArchetype (Port from Level 2)

```python
@dataclass(frozen=True)
class RopePendulumSpec:
    """Swing on rope to reach high platform."""
    anchor_x: float
    anchor_y: float
    rope_length: float
    segment_count: int
    target_platform_x: float
    target_platform_y: float
    target_platform_width: float
```

---

## 4. Constraint Solver

### 4.1 Purpose
Given an archetype template and a platform, solve for valid positions/dimensions that satisfy all constraints.

### 4.2 Interface

```python
class ConstraintSolver:
    def solve(self, archetype: Archetype, platform: Platform, 
              caps: PlayerCapabilities, rng: Random) -> PuzzleSpec | None:
        """
        Returns concrete PuzzleSpec with all positions filled,
        or None if constraints unsatisfiable on this platform.
        """
```

### 4.3 Constraint Types

| Type | Example | Validation |
|------|---------|------------|
| **Reachability** | Player can reach crate from platform edge | `caps.horizontal_reach()` |
| **Pushability** | Crate can be pushed to plate | `crate_mass * friction * distance < player_work` |
| **Physics Simulation** | Seesaw launches to target | `simulate_trajectory()` |
| **State Machine** | Water raise → crate floats → reaches exit | Step-by-step simulation |
| **Ordering** | Plate before gate, cover before valve | `x1 < x2` |
| **Bounds** | All objects on platform | `platform.x < obj.x < platform.right` |
| **Non-overlap** | Objects don't intersect | AABB checks |

---

## 5. Physics Verifier (Solver)

### 5.1 Purpose
Simulate a "perfect player" solving the puzzle to verify:
1. **Solvable**: Solution exists
2. **Non-trivial**: Requires >1 step, not just "walk right"
3. **Fair**: Doesn't require frame-perfect inputs
4. **Unique enough**: Not identical to recent puzzles

### 5.2 Interface

```python
class PuzzleVerifier:
    def verify(self, spec: PuzzleSpec, caps: PlayerCapabilities) -> VerificationResult:
        """
        Runs physics simulation with automated solver.
        Returns: SOLVABLE | UNSOLVABLE | TRIVIAL | UNFAIR
        """
```

### 5.3 Solver Strategies per Archetype

| Archetype | Solver Strategy |
|-----------|-----------------|
| CratePlate | 1. Walk to crate 2. Grab 3. Push to plate 4. Release 5. Walk through gate |
| WaterCrate | 1. Open cover 2. Push crate in 3. Turn valve 4. Wait for water 5. Climb crate |
| SeesawLaunch | 1. Run back/forth N times 2. Jump at peak velocity |
| GravityMaze | 1. Flip at switch 1 2. Navigate 3. Flip at switch 2 4. Exit |
| MagnetStairs | 1. Power magnet 2. Lift crate A 3. Flip B gravity 4. Climb A 5. Flip A 6. Climb B |
| RopePendulum | 1. Catch rope 2. Climb to height H 3. Swing 4. Release at angle θ |

### 5.4 Simulation Parameters

```python
@dataclass(frozen=True)
class SolverConfig:
    max_simulation_steps: int = 12000  # 100 seconds at 120Hz
    max_solution_length: int = 50      # Max action sequence
    allow_suboptimal: bool = True      # Accept non-perfect play
    coyote_time: float = 0.10
    jump_buffer: float = 0.12
```

---

## 6. Integration with EndlessWorld

### 6.1 New Physics Bodies Needed

```python
# In EndlessWorld.__init__():
self.puzzle_geometry: dict[int, PuzzlePhysicsData] = {}

# PuzzlePhysicsData contains:
# - Pymunk bodies/shapes for crates, plates, gates, water, seesaws, magnets, ropes
# - State machines for multi-step puzzles
# - Cleanup logic
```

### 6.2 Puzzle Spawning

```python
def _spawn_puzzle(self, puzzle: PuzzleSpec):
    """Create Pymunk bodies for puzzle elements."""
    if puzzle.kind == "crate_plate":
        # Crate body
        crate_body = self._prop((puzzle.crate_spawn_x, platform.y), 
                               puzzle.crate_size, puzzle.crate_mass)
        # Plate sensor
        plate_body = self._static_sensor(puzzle.plate_x, platform.y, 
                                        puzzle.plate_width, 10)
        # Gate kinematic body
        gate_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        # ... register callback: when plate.pressed and crate.on_plate → open_gate
```

### 6.3 Puzzle State Machine

```python
@dataclass
class PuzzleState:
    puzzle_id: int
    kind: str
    state: str  # "waiting", "crate_on_plate", "gate_opening", "solved"
    progress: dict  # e.g., {"crate_on_plate": True, "gate_open": 0.5}
    
    def update(self, dt, world_state):
        # State transitions based on physics
        pass
```

---

## 7. Difficulty Scaling

### 7.1 Archetype Unlock by Difficulty

| Difficulty | Available Archetypes |
|------------|---------------------|
| 1.0 - 1.5 | `crate_plate` (simple), `rope_pendulum` |
| 1.5 - 2.5 | `water_crate`, `seesaw_launch` |
| 2.5 - 4.0 | `gravity_maze`, `magnet_stairs` |
| 4.0+ | Combos, variants, tighter constraints |

### 7.2 Constraint Tightening

```python
def get_constraints_for_difficulty(base: Constraints, difficulty: float) -> Constraints:
    t = min(1.0, (difficulty - 1.0) / 9.0)
    return Constraints(
        min_crate_to_plate=base.min_crate_to_plate * (1 + 0.5 * t),
        max_crate_to_plate=base.max_crate_to_plate * (1 - 0.3 * t),
        # ... tighter tolerances at higher difficulty
    )
```

---

## 8. Fallback Strategy

If no puzzle verifies within `max_attempts`:
1. Try simpler archetype
2. Relax constraints slightly
3. Fall back to obstacle (light_gate, shadow_run, sentry)
4. Log for analysis

---

## 9. Testing Strategy

### 9.1 Unit Tests
- ConstraintSolver returns valid specs for known-good platforms
- Verifier correctly identifies solvable/unsolvable
- Archetype constraints are complete

### 9.2 Integration Tests
- Endless run with puzzles: 1000 segments, no unsolvable puzzles
- Visual regression: puzzles render correctly
- Performance: puzzle verification < 10ms per platform

### 9.3 Property-Based Tests (Hypothesis)
- Random platforms + archetypes → always verifiable or correctly rejected
- Difficulty scaling monotonic

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] Port `crate` + `plate` + `gate` physics to endless
- [x] Implement constrained crate-plate composition and fixed-step Pymunk verification
- [x] Integrate with `EndlessWorld` spawning, pilot controls, rendering, and cleanup
- [x] Test solvability, no-grab bypass rejection, deterministic generation, runtime, and cleanup

### Phase 2: Architecture (Week 1-2)
- [ ] Abstract `Archetype` base class
- [ ] `ArchetypeRegistry` with difficulty gating
- [ ] `ProceduralPuzzleGenerator` orchestrator
- [ ] Config system for tuning

### Phase 3: Additional Archetypes (Week 2-3)
- [ ] `WaterCrateArchetype` (needs water physics port)
- [ ] `SeesawLaunchArchetype` (needs seesaw physics port)
- [ ] `RopePendulumArchetype` (needs rope physics port)

### Phase 4: Advanced (Week 3-4)
- [ ] `GravityMazeArchetype` (needs gravity flip port)
- [ ] `MagnetStairsArchetype` (needs magnet physics port)
- [ ] Combo puzzles (multiple archetypes on one platform)
- [ ] Visual variety (different crate types, plate styles)

---

## 11. Target File Structure (Future Extraction)

The current vertical slice is intentionally implemented in the existing
`echo_game/puzzle_archetypes.py` and `echo_game/procedural.py` rather than
creating empty modules for every future archetype. Extract modules when a
second fully verified archetype exists.

```
echo_game/
├── puzzles/
│   ├── __init__.py
│   ├── archetypes.py          # Archetype definitions & specs
│   ├── constraints.py         # ConstraintSolver
│   ├── verifier.py            # PuzzleVerifier + solvers
│   ├── generator.py           # ProceduralPuzzleGenerator
│   ├── registry.py            # ArchetypeRegistry
│   └── state.py               # PuzzleState, state machines
├── physics.py                 # Add puzzle physics bodies
├── procedural.py              # Integrate puzzle generator
└── challenges.py              # Deprecate/integrate with puzzles
```

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Verifier too slow | Cache results, run async, limit attempts |
| False negatives (solvable but verifier says no) | Conservative solver, allow suboptimal play |
| False positives (verifier says yes but human can't) | Add human-playable margins, test with pilot |
| Physics non-determinism | Fixed timestep, seeded RNG, snapshot comparison |
| Puzzle repetition | Track recent archetypes, enforce variety |
| Streaming cleanup bugs | Reference counting, comprehensive cleanup tests |

---

## 13. Success Metrics

- **Solvability rate**: >99% of generated puzzles verified solvable
- **Human solvability**: Pilot completes >95% of puzzles in test runs
- **Variety**: >5 archetypes active at difficulty 5+, no repeat within 10 platforms
- **Performance**: Puzzle generation + verification < 5ms/platform
- **Player feedback**: "Puzzles feel hand-designed, not random"

---

*Document Version: 2.0 (implemented room system + historical proposal)*
*Author: Procedural Puzzle System Design*
*Date: 2026-11-19*
