# Physics & Gameplay Mechanics Review

## Executive Summary
The physics system (Pymunk-based) is well-structured but has several edge cases and inconsistencies between campaign and endless modes that affect gameplay feel.

---

## Critical Physics Issues

### 1. Gravity Flip Preserves Vertical Velocity (Intentional but Risky)
**File:** `physics.py:330-338 flip_gravity()`

```python
def flip_gravity(self, direction: int):
    self._release()
    self.gravity = direction
    self.space.gravity = (0, GRAVITY * direction)
    # A field changes acceleration, not existing momentum. Resetting vy
    # removed the mid-air timing described in the reference walkthrough.
    # Preserve coyote and jump_buffer across gravity flip (C5).
    self.grounded = False
    self.events.append("gravity")
```

**Comment admits:** "Resetting vy removed the mid-air timing described in the reference walkthrough."

**Risk:** Player keeps upward velocity when gravity flips downward → launches higher than intended. Can sequence flips for infinite height gain.

**Campaign Level 5** uses gravity flips — this is a designed mechanic but undocumented for players.

---

### 2. Coyote Time & Jump Buffer Asymmetry
**File:** `physics.py:182-197 _ground()` + `physics.py:406-411 step()`

```python
# _ground() - grounded detection
if self.player.velocity.y * self.gravity < -70:  # Rising fast? Not grounded
    return

# step() - coyote & jump buffer
self.coyote = 0.10 if self.grounded else max(0, self.coyote - dt)
self.jump_buffer = max(0, self.jump_buffer - dt)
if control.jump:
    self.jump_buffer = 0.12
if self.jump_buffer and self.coyote:
    self.player.velocity = (self.player.velocity.x, -self.gravity * JUMP_SPEED)
```

**Issue:** `coyote = 0.10s` (12 physics frames), `jump_buffer = 0.12s` (14 frames). Buffer > coyote means you can press jump *before* landing and it triggers on landing — good. But if you press jump *after* leaving ground, coyote expires first.

**Endless mode** uses same constants — but procedural platforms have varying gaps, making timing feel inconsistent.

---

### 3. Move Acceleration Differs Grounded vs Airborne
**File:** `physics.py:434-440`

```python
target = move * (135 if self.grab_kind == "crate" else MOVE_SPEED)  # 190
accel = 4500 if self.grounded else 620  # 7.25x difference!
dv = max(-accel * dt, min(accel * dt, target - vx))
self.player.velocity = (vx + dv, vy)
```

**Grounded:** 4500 px/s² → reaches 190 px/s in ~0.042s (5 frames)
**Airborne:** 620 px/s² → reaches 190 px/s in ~0.31s (37 frames)

**Impact:** Air control feels "floaty" — intentional for physics realism but makes precise platforming harder in endless mode where gaps are tighter at higher difficulties.

---

### 4. Rope Climbing Uses Hand Constraint Sliding (Complex)
**File:** `physics.py:239-262 _climb_rope()`

```python
def _climb_rope(self, direction: float, dt: float):
    # Moves the PivotJoint anchor along rope segments
    distance = max(40, min(len(self.ropes) * length - 2,
                          self.rope_distance - max(-1, min(1, direction)) * 85 * dt))
```

**Climb speed:** 85 px/s along rope. At 12 segment rope (28px each = 336px), full climb ~4s.

**Bug potential:** `max(-1, min(1, direction))` clamps to ±1, but `control.climb` is already -1/0/1 from `Input` dataclass. Double-clamping harmless but confusing.

---

### 5. Water Buoyancy Applies Force Every Frame (Expensive)
**File:** `physics.py:283-299 _buoyancy()`

```python
for prop in self.crates:
    if water.x - prop.size[0] / 2 < b.position.x < water.x + water.w + prop.size[0] / 2:
        # ... calculates ratio, applies force_at_world_point, modifies force/torque directly
        b.force += (-b.velocity.x * b.mass * 4 * ratio, -b.velocity.y * b.mass * 6 * ratio)
        b.torque -= b.angular_velocity * b.moment * 3 * ratio
        b.torque -= math.sin(b.angle) * b.moment * 30 * ratio
```

**Issues:**
- Modifies `b.force` and `b.torque` directly (bypasses Pymunk's force accumulation)
- Runs every physics step (120Hz) for every crate in water
- Magic numbers (4, 6, 3, 30) not exposed as config

**Campaign only** — endless has no water.

---

### 6. Gate Descent Crushes Crates (Handled but Complex)
**File:** `physics.py:340-372 _gate()`

```python
if delta < 0:  # Gate descending
    # Kinematic body has infinite mass — bound sweep before integration
    next_bottom = bottom - delta * (gate.h + 20)
    for prop in self.crates:
        if crate in gate path:
            clearance = max(0, bb.bottom - bottom)
            delta = max(delta, -clearance / (gate.h + 20))  # Slow/stop descent
```

**Correctness:** Prevents crate crushing by limiting gate velocity. Good.

**Risk:** If player stands under descending gate, no protection — gate passes through player (kinematic). Player death only from `gate_body` contact check in `step()` (line 476-478).

---

### 7. Saw Collision Uses Capsule Approximation (Inaccurate)
**File:** `physics.py:459-465`

```python
for x, y, radius in self.saw_positions():
    cy = max(p.y - 15, min(p.y + 15, y))  # Clamp to player center ±15
    if math.hypot(p.x - x, cy - y) < radius + 10:
        self._saw_contact(x)
```

**Player half-height:** 22px. **Clamp:** ±15px. **Misses:** Top 7px and bottom 7px of player hitbox.

**Saw radius:** 31-34px (campaign). **Collision radius:** saw_radius + 10 = 41-44px.

**Result:** Can "thread the needle" through saw gaps that visually overlap player sprite.

---

### 8. Magnet System Complexity (Campaign Chapter 6 Only)
**File:** `magnet.py` + `physics.py:107-109, 452-456`

```python
# physics.py
if self.level.magnet:
    self.magnet = MagneticCeiling(self.space, self.crates, self.level.magnet, ...)
# step()
if self.magnet:
    self.magnet.prepare_step()
self.space.step(dt)
if self.magnet:
    self.magnet.finish_step(self.time)
```

**Two-phase step** required for magnet constraint updates. Not used in endless.

**Risk:** If `magnet.prepare_step()` or `finish_step()` throws, physics state inconsistent.

---

## Campaign vs Endless Physics Differences

| Mechanic | Campaign | Endless |
|----------|----------|---------|
| Gravity flip | Yes (Level 5) | No |
| Water | Yes (Levels 3, 4) | No |
| Magnet | Yes (Level 6) | No |
| Seesaw | Yes (Level 4) | No |
| Rope | Yes (Level 2) | No |
| Plate/gate | Yes (Level 1) | Light barriers only |
| Cover/valve | Yes (Level 3) | Light switches only |
| Saws | Instant death | 1 damage + knockback |
| Health | 1 life | 5 health (configurable) |
| Invulnerability | None | 0.95s after damage |
| Lantern | No | Yes (resource + combat) |

**Design smell:** Endless mode is a *subset* of campaign mechanics, not a superset or variant. Missing mechanics reduce variety.

---

## Input Handling Issues

### 1. Jump Buffer Consumed on Rope Release
**File:** `physics.py:427-432`

```python
if control.jump:
    vx, vy = self.player.velocity
    self._release()
    self.player.velocity = (vx + move * 75, vy - self.gravity * 130)
    self.regrab_delay = 0.3
    self.jump_buffer = 0  # <-- CONSUMES BUFFER
```

**Issue:** Jumping off rope clears jump buffer. If player hits jump *during* release frames, no coyote jump on landing.

---

### 2. Regrab Delay Blocks All Grabs
**File:** `physics.py:206-208 _release()` + `physics.py:417-420 step()`

```python
self.regrab_delay = max(0, self.regrab_delay - dt)
if not control.grab:
    self._release()
elif self.grab_joint is None and self.regrab_delay <= 0:  # <-- BLOCKS
    self._grab()
```

**0.3s delay** after rope release. During this, can't grab crate or rope. Feels unresponsive.

---

## Performance Physics Concerns

### 1. Space.iterations = 30 (High)
**File:** `physics.py:57`

```python
self.space.iterations = 30  # Default is 10
```

**Cost:** 3x more solver iterations per step. Needed for stable rope/seesaw/magnet but impacts CPU.

**Endless** inherits this but has no rope/seesaw/magnet — could lower to 15-20.

---

### 2. Segment Query for Ground Detection (3 Raycasts/Frame)
**File:** `physics.py:182-197 _ground()`

```python
for dx in (-7, 0, 7):
    hits = self.space.segment_query((p.x + dx, foot - self.gravity * 3),
                                    (p.x + dx, foot + self.gravity * 7), 1,
                                    pymunk.ShapeFilter(mask=SOLID))
```

**3 segment queries per physics step** (120Hz) = 360 queries/sec. Acceptable but measurable.

---

## Recommendations

### P0 - Fix Gameplay Feel
1. **Document gravity flip mechanic** — add to help screen
2. **Expose air/ground accel ratio as config** — tune for endless difficulty
3. **Fix saw collision to use full player AABB** — or document as feature
4. **Reduce regrab_delay** from 0.3s to 0.15s

### P1 - Physics Parity
5. **Add water/magnet/seesaw/rope to endless** with procedural placement
6. **Unify saw damage model** — campaign instant death vs endless 1 damage
7. **Lower space.iterations for endless** (no complex constraints)

### P2 - Code Quality
8. **Extract physics constants to config** — buoyancy multipliers, gate speeds, etc.
9. **Add physics debug visualization** (F3 already shows snapshot)
10. **Property-based tests for jump reachability** across all platform configs

---

## Verification Commands
```bash
# Run physics tests
.venv-echo/bin/python -m pytest tests_echo/test_physics.py -xvs

# Test gravity flip behavior
.venv-echo/bin/python -c "
from echo_game.physics import World, Input, DT
w = World(4)  # Level 5 has gravity flip
w.step(Input(action=True))  # Flip gravity
print('Gravity:', w.gravity, 'VY:', w.player.velocity.y)
"

# Profile physics step
.venv-echo/bin/python -m cProfile -o /tmp/phys.prof -c "
from echo_game.physics import World, Input, DT
import time
w = World(0)
start = time.perf_counter()
for _ in range(12000):  # 100 seconds at 120Hz
    w.step(Input(move=1))
print('Time:', time.perf_counter() - start)
"
```