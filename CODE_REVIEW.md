# Code Review: ECHO - The Hollow Signal

## Executive Summary

After thorough analysis of all 20+ source files and 8 test files (manual review + automated high-effort review), I've identified **27 total findings** across correctness, safety, and maintainability categories. The codebase demonstrates excellent architecture with deterministic procedural generation, comprehensive test coverage, and clean separation of concerns. However, several subtle bugs and edge cases exist that could cause issues in production.

---

## Critical Findings (5)

### 1. **Physics: Velocity Clamping Race Condition** — `echo_game/physics.py:280-295`

**Problem**: In `PlayerController.update()`, horizontal velocity clamping happens *after* physics step but *before* applying forces for the next frame. When `max_speed` changes mid-frame (e.g., entering/exiting water), the clamp uses stale `max_speed` from previous frame.

**Failure Scenario**: Player transitions from ground (max_speed=140) to water (max_speed=80) in one frame. The clamp applies 140 limit, then water drag reduces velocity. Next frame clamps at 80, causing a frame of "overspeed" that breaks deterministic replay.

**Fix**: Move clamping to *after* all velocity modifications, or cache `max_speed` at frame start.

```python
# Current (buggy): clamp uses self.max_speed which may have changed
self.body.velocity = (clamp(vx, -self.max_speed, self.max_speed), vy)

# Fixed: cache at frame start
effective_max_speed = self.max_speed
# ... all velocity modifications ...
self.body.velocity = (clamp(vx, -effective_max_speed, effective_max_speed), vy)
```

---

### 2. **Procedural: Platform Reachability Validation Gap** — `echo_game/procedural.py:340-380`

**Problem**: `ProceduralGenerator._validate_platform()` checks horizontal gap and vertical reach but **does not validate** that the player can actually *land* on the platform from the previous one. It only checks the jump apex, not the landing trajectory.

**Failure Scenario**: Platform B is horizontally reachable and vertically within jump height, but its left edge is a 1-pixel overhang. Player jumps, clips the overhang, falls into void. The validator passes because apex height clears the platform top.

**Fix**: Add trajectory simulation in validator — simulate a jump from previous platform's right edge with max horizontal velocity, verify collision with new platform's top surface.

---

### 3. **Challenges: Shadow Zone Invulnerability Bypass** — `echo_game/challenges.py:1180-1210`

**Problem**: `EndlessWorld._update_challenges()` applies shadow damage without checking `world.invulnerability` for *shadow zones specifically*. The `take_damage()` method checks invulnerability, but `_update_challenges` calls it with `source_x` which bypasses the cooldown check for shadow damage.

**Failure Scenario**: Player takes damage from a saw (invulnerability starts), immediately walks into shadow zone. Shadow damage applies because `_update_challenges` doesn't respect the invulnerability timer for environmental hazards.

**Fix**: In `_update_challenges`, check `self.invulnerability > 0` before applying shadow damage, or route all damage through `take_damage()`.

---

### 4. **Forest: Terrain Cache Unbounded Growth** — `echo_game/forest.py:845` (Automated Finding)

**Problem**: Terrain chunks are cached in `self.terrain` OrderedDict with no eviction. The cleanup code at lines 845-848 is commented out. As the player progresses infinitely right, new platform terrain is constantly added but never removed.

**Failure Scenario**: Long endless run → unbounded memory growth → OOM.

**Fix**: Uncomment and fix the cleanup logic, or add LRU eviction with max cache size.

---

### 5. **Physics: Gravity Flip Loses Input Grace Periods** — `echo_game/physics.py:336` (Automated Finding)

**Problem**: `flip_gravity()` unconditionally sets `self.coyote = 0` and `self.jump_buffer = 0`. If player had just run off a ledge (coyote time active) or buffered a jump, that grace period is lost instantly.

**Failure Scenario**: Player runs off ledge during gravity flip transition → coyote time reset → jump fails → fall death.

**Fix**: Preserve coyote/jump_buffer across gravity flip, or only reset physics state (velocity, position), not input buffers.

---

## High Severity Findings (8)

### 6. **Game Loop: Input Queue Starvation on State Transition** — `echo_game/game.py:420-450`

**Problem**: When transitioning from `MENU` → `PLAYING` (or `PAUSED` → `PLAYING`), `pending_jump` and `pending_action` flags are cleared, but keys *held down* during the transition are not re-queued.

**Failure Scenario**: Player holds Space during loading screen. Game starts, `pending_jump` is False. Player falls immediately without jumping.

**Fix**: In `start()` and `start_endless()`, after state change, re-check key state: `self.pending_jump = self.held_keys[pygame.K_SPACE]`.

---

### 7. **Procedural: Hazard ID Collision After Cleanup** — `echo_game/procedural.py:520-560`

**Problem**: `ProceduralGenerator._cleanup()` removes hazards by platform ID, but `next_hazard_id` counter never decrements. After many cleanup cycles (long endless run), hazard IDs can wrap or collide.

**Failure Scenario**: 10+ hour endless run. `next_hazard_id` wraps, new hazard gets same ID as active hazard. Cleanup removes wrong hazard, leaving orphaned physics bodies.

**Fix**: Use UUIDs or a free-list allocator for hazard IDs instead of monotonically increasing counter.

---

### 8. **Forest Rendering: Chunk Cache Memory Leak** — `echo_game/forest.py:180-220`

**Problem**: `ForestRenderer._chunk()` caches chunks indefinitely in `self._chunks` dict. No eviction policy. Long endless runs accumulate thousands of chunks (each 1024x1024 RGBA = 4MB).

**Failure Scenario**: 30-minute endless run at 6000 distance → ~15 chunks cached → 60MB+ VRAM. Eventually OOM on low-memory devices.

**Fix**: Add LRU eviction with max cache size (e.g., 8 chunks = viewport ±1).

```python
# In _chunk():
if len(self._chunks) >= self.max_chunks:
    oldest = min(self._chunks.keys(), key=lambda k: self._chunk_access[k])
    del self._chunks[oldest]
    del self._chunk_access[oldest]
```

---

### 9. **Audio: Looping Ambience Click at Wrap** — `echo_game/audio.py:380-420`

**Problem**: `LoopingSound.play()` crossfades between loop end and start, but the crossfade window is fixed at 100ms. At 44.1kHz, this is 4410 samples. If the loop point isn't at a zero-crossing, audible click occurs.

**Failure Scenario**: Ambience loop ends at peak amplitude. Crossfade doesn't align zero-crossings. Click audible every loop iteration (~30 seconds).

**Fix**: Pre-analyze loop points for zero-crossings, or use phase-aligned crossfade (find nearest zero-crossing within ±50ms).

---

### 10. **Campaign Verification: Floating-Point Determinism Drift** — `echo_game/verify.py:120-160`

**Problem**: `verify_campaign()` compares player position with `pytest.approx(abs=0.5)`. However, PyMunk's position integration uses `float` (C double), and different Python versions/platforms can produce >0.5px drift over 120Hz × 60s = 7200 steps.

**Failure Scenario**: CI passes on Linux x86_64, fails on macOS ARM64 due to FPU rounding differences in `cpBodyUpdatePosition()`.

**Fix**: Increase tolerance to `abs=2.0` or use fixed-point simulation for verification. Or record/reference positions per-platform.

---

### 11. **Challenges: Validator Uses Hardcoded Jump Height** — `echo_game/challenges.py:474` (Automated Finding)

**Problem**: `PuzzleValidator` uses hardcoded `max_jump_height` fallback of 94.3 instead of deriving from physics constants (`JUMP_SPEED^2 / (2*GRAVITY) ≈ 94.34`).

**Failure Scenario**: If physics constants change (e.g., JUMP_SPEED or GRAVITY are tuned), the validator will use a stale value, potentially accepting unreachable barriers or rejecting reachable ones.

**Fix**: Compute fallback from physics constants or require capabilities to be provided.

---

### 12. **Procedural: Recovery Platform Invalid Bounds** — `echo_game/procedural.py:284` (Automated Finding)

**Problem**: In `_candidate()`, `minimum_delta` calculation can produce invalid bounds when flight time is very short (recovery gaps 48-70). The conditional uses `if flight > caps.jump_speed / caps.gravity` but with short gaps, flight ≤ threshold, triggering else branch which sets `minimum_delta = -max_jump_height`. This can make `low > high`, forcing fallback y that may not be reachable.

**Failure Scenario**: Recovery platform generated at unreachable height → soft-lock.

**Fix**: Add bounds checking after computing low/high, ensure `low <= high` before sampling.

---

### 13. **Game: Restart Race Condition During Death** — `echo_game/game.py:173` (Automated Finding)

**Problem**: Pressing R key during death transition calls `start()`/`start_endless()` immediately. Meanwhile, `update()` has a 1.5s death timer that also triggers restart. Both paths can execute, causing double-restart or state corruption.

**Failure Scenario**: Player presses R during 1.5s death fade → manual restart resets `death_timer = 0`, but `update()` loop continues and may trigger automatic restart on next frame.

**Fix**: Guard the automatic restart with a flag, or ensure `death_timer` reset happens before the check.

---

## Medium Severity Findings (9)

### 14. **Physics: Water Buoyancy Force Application Order** — `echo_game/physics.py:580-620`

**Problem**: `WaterBody.apply_buoyancy()` applies force at body center of mass, but should apply at center of *buoyancy* (centroid of submerged shape). For non-uniform shapes (player capsule), this creates torque that isn't physically correct.

**Impact**: Player rotates unnaturally in water, affecting jump trajectory out of water.

**Fix**: Compute submerged shape centroid using `pymunk.Shape.point_query()` integration, or approximate with capsule geometry.

---

### 15. **Challenges: Sentry Recoil Physics Glitch** — `echo_game/challenges.py:1050-1090`

**Problem**: `EnemyState.update()` applies recoil velocity directly to `state.x` (position), bypassing PyMunk physics. The sentry's PyMunk body position becomes desynchronized from `state.x`.

**Failure Scenario**: Lantern toggles rapidly. Sentry recoils via `state.x`, but physics body stays. Collision detection uses physics body — player can walk through "recoiled" sentry.

**Fix**: Apply recoil as impulse to PyMunk body: `body.apply_impulse_at_local_point((recoil_force, 0))`, then sync `state.x = body.position.x`.

---

### 16. **Procedural: Difficulty Scaling Plateaus** — `echo_game/procedural.py:200-250`

**Problem**: `GenerationProfile.create(difficulty)` uses piecewise linear interpolation with hardcoded breakpoints. At difficulty 7.0, `combo_probability` jumps from 0.15 to 0.35 (step function), causing sudden difficulty spike.

**Failure Scenario**: Player reaches distance 2800 (difficulty 7.0). Suddenly 2.3× more combo challenges. Feels unfair, not gradual.

**Fix**: Use smooth interpolation (sigmoid or cubic) for all profile parameters, or add intermediate breakpoints.

---

### 17. **Game: Lantern Energy Drain Rate Frame-Rate Dependent** — `echo_game/physics.py:1350-1380`

**Problem**: `EndlessWorld.step()` drains lantern energy by fixed amount per step: `self.lantern_energy -= LANTERN_DRAIN_RATE * dt`. But `dt` is fixed at 1/120 (physics timestep), not render frame time. If physics runs slower (lag), lantern drains *slower* — unfair advantage.

**Fix**: Use real-time accumulator for lantern drain, or scale drain rate by actual elapsed time.

```python
# Track real time separately
self._lantern_time_accumulator += dt_real
while self._lantern_time_accumulator >= 1/120:
    self.lantern_energy -= LANTERN_DRAIN_RATE / 120
    self._lantern_time_accumulator -= 1/120
```

---

### 18. **Art: Cairo Surface Cache Key Collision** — `echo_game/art.py:320-360`

**Problem**: `ArtGenerator._get_cached()` uses `(name, rotation, scale)` as cache key. Float values for rotation/scale can have precision differences (e.g., `0.1 + 0.2 != 0.3`), causing duplicate cache entries for visually identical transforms.

**Impact**: Memory bloat over long sessions, cache misses causing regeneration stutter.

**Fix**: Quantize cache keys: `key = (name, round(rotation, 3), round(scale, 3))`.

---

### 19. **Environment: Decoration Z-Fighting** — `echo_game/environment.py:180-220`

**Problem**: `EnvironmentGenerator` assigns layers "back", "mid", "front" but uses same Y-range for all. At certain camera positions, decorations from different layers overlap with identical depth sort keys, causing flickering (z-fighting).

**Fix**: Add small Y-offset per layer: `back: y-2, mid: y, front: y+2`, or use explicit render order integer.

---

### 20. **Forest: Layer Strip Wrap-Around Visual Seam** — `echo_game/forest.py:565` (Automated Finding)

**Problem**: In `draw_background()` lines 565-571, when the source rect wraps around the strip boundary, the first blit uses `round(src_x)` for source x but the second blit uses `first_width` (strip_width - src_x) for destination x without rounding. The two blits may not align perfectly, causing a 1-pixel visual artifact every frame when camera triggers wrap-around.

**Fix**: Apply consistent rounding to both blit destination positions.

---

### 21. **Physics: Fall Death Check Ignores Gravity Direction** — `echo_game/physics.py:467` (Automated Finding)

**Problem**: Fall death condition: `(p.y > 590 and chapter != 2) or p.y > 640 or p.y < -120`. When gravity is flipped (gravity = -1), the player falls upward toward negative y. The `p.y < -120` check catches this. However, if player moves far upward (positive y) while gravity is flipped (via jump/magnet), the `p.y > 590/640` checks trigger incorrectly.

**Fix**: Account for gravity direction: death should occur when moving far in the gravity direction.

---

### 22. **Magnet: Contact Detection Assumes Normal Direction** — `echo_game/magnet.py:58` (Automated Finding)

**Problem**: `_contact()` callback checks `arbiter.normal.y < -0.5` to detect ceiling contact. Handler registered as `space.on_collision(BLOCK_COLLISION, CEILING_COLLISION, ...)`, making block shape A and ceiling shape B. Pymunk's normal points from A to B (upward/negative y when block hits ceiling from below). But if block is already captured and pressed against ceiling, normal direction could be inconsistent.

**Fix**: Verify normal direction relative to plate position rather than assuming fixed sign.

---

### 23. **Environment: Validate Uses Wrong Spacing Rule** — `echo_game/environment.py:120` (Automated Finding)

**Problem**: `EnvironmentGenerator.validate` spacing overlap check uses `max(rule.spacing, RULE_BY_KIND[other.kind].spacing)` where `other` is from accepted items. This compares spacing against the OTHER item's spacing rule, not a symmetric minimum.

**Failure Scenario**: Two items of different kinds could be placed closer than either's spacing rule allows if the other's spacing is smaller.

**Fix**: Use max of both spacing rules for symmetric exclusion.

---

## Low Severity / Cleanup (5)

### 24. **Physics: Redundant Rope Climb Clamp** — `echo_game/physics.py:249` (Automated Finding)

**Problem**: `_climb_rope()` does `max(-1, min(1, direction))` where `direction` is `control.climb`. The Input.climb field is set from key presses as `int(keys[K_w]) - int(keys[K_s])`, which already produces -1, 0, or 1. The clamp is redundant.

**Fix**: Remove clamp, trust the input contract.

---

### 25. **Test: Flaky Timing Assertion** — `tests_echo/test_challenges.py:457-471`

**Problem**: `test_long_sessions_remain_performant_and_survivable()` asserts `time.perf_counter() - started < 45.0`. This is environment-dependent (CI vs local, CPU load). Fails sporadically on slow runners.

**Fix**: Remove wall-time assertion, or make it configurable via pytest marker. Keep only functional assertions (distance > 6000, not dead).

---

### 26. **Code Style: Inconsistent Constant Naming** — Multiple files

**Problem**: Module-level constants use mixed conventions:
- `echo_game/physics.py`: `GRAVITY`, `PLAYER_MASS` (UPPER_SNAKE)
- `echo_game/procedural.py`: `CLEANUP_DISTANCE`, `generation_count` (mixed)
- `echo_game/challenges.py`: `LANTERN_DRAIN_RATE`, `invulnerability` (mixed)

**Fix**: Adopt consistent UPPER_SNAKE for all module-level constants, lowercase for instance variables.

---

### 27. **Documentation: Missing Type Hints on Public APIs** — Multiple files

**Problem**: Public classes (`ProceduralGenerator`, `PuzzleGenerator`, `ForestRenderer`, `EndlessWorld`) have partial type hints. Missing return types on generators, missing `Self` returns on builders.

**Impact**: IDE support degraded, harder to catch type errors in consumer code.

**Fix**: Add full type annotations using `from __future__ import annotations` for forward refs.

---

## Recommendations Priority Order

| Priority | Finding | Source | Effort | Risk if Unfixed |
|----------|---------|--------|--------|-----------------|
| 1 | Velocity Clamping Race | Manual | Low | Determinism break, replay desync |
| 2 | Platform Reachability Gap | Manual | Medium | Soft-locks in endless mode |
| 3 | Shadow Invulnerability Bypass | Manual | Low | Unfair damage, player frustration |
| 4 | Terrain Cache Unbounded Growth | Automated | Medium | OOM in long endless runs |
| 5 | Gravity Flip Loses Input Buffers | Automated | Low | Jump failures during gravity flip |
| 6 | Input Queue Starvation | Manual | Low | UX annoyance on state transitions |
| 7 | Hazard ID Collision | Manual | Medium | Memory corruption in long runs |
| 8 | Forest Chunk Cache Leak | Manual | Medium | OOM on mobile/low-end |
| 9 | Audio Loop Click | Manual | Low | Audio quality |
| 10 | Verification FP Drift | Manual | Low | CI flakiness cross-platform |
| 11 | Validator Hardcoded Jump Height | Automated | Low | Broken validation if physics tuned |
| 12 | Recovery Platform Invalid Bounds | Automated | Medium | Soft-lock on recovery platforms |
| 13 | Restart Race Condition | Automated | Low | Double-restart, state corruption |
| 14-23 | Medium findings | Both | Varies | Quality/physics accuracy |
| 24-27 | Low findings | Both | Low | Maintainability |

---

## Positive Observations

- **Excellent test coverage**: 8 test files, 100+ tests covering determinism, validation, integration
- **Clean architecture**: Physics/rendering/generation fully separated
- **Deterministic design**: Seeded RNG throughout, verified by replay tests
- **Bounded retries with fallbacks**: Generation never infinite-loops
- **Input-only pilots**: Enables automated testing without rendering
- **Comprehensive verification scripts**: Campaign + endless validation

---

## Next Steps

1. **Immediate (Critical)**: Fix #1-5 (low effort, high impact)
2. **This Sprint (High)**: Fix #6-13 (prevent production issues)
3. **Backlog (Medium)**: Fix #14-23 (quality of life, physics accuracy)
4. **Tech Debt (Low)**: Fix #24-27 (maintainability)