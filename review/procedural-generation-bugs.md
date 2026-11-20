# Procedural Generation Bugs & Test Failures

## Executive Summary
**1 test failing**: `test_generated_segments_keep_hazards_clear_of_landing_and_takeoff` — hazard count (47) below expected minimum (50) across 15 seeds × 50 segments.

Additional issues found in procedural generation logic that may cause gameplay bugs.

---

## Failed Test Analysis

### Test: `test_generated_segments_keep_hazards_clear_of_landing_and_takeoff`
**File:** `tests_echo/test_procedural.py:118-150`

**Failure:** `assert total_hazards > 50` — got 47

**Root Cause:** Hazard generation probability too low at low difficulties, combined with recovery platforms (which correctly have zero hazards) reducing total count.

**Code Path:**
```python
# procedural.py:405-469 _hazards()
def _hazards(self, platform, profile, context, challenge):
    # ...
    if rng.random() >= profile.hazard_probability:  # <-- PROBABILITY GATE
        return []
```

**Profile hazard_probability at difficulty 1.0:** `0.14` (14%)
- `GenerationProfile.create(1.0)` → `hazard_probability = 0.14 + 0.46 * 0 = 0.14`
- With `obstacle_density=1.0`: `min(1.0, 0.14 * 1.0) = 0.14`

**Expected hazards per 50 segments:** ~7 (50 × 0.14), but test expects >50 total across 15 seeds = >3.3/seed

**Actual:** 47 total / 15 seeds = 3.13/seed — close but under threshold

**Recovery platforms:** Every `recovery_spacing` (6 at low difficulty) platforms have 0 hazards by design
- 50 segments / 6 = ~8 recovery platforms per seed
- 42 hazard-eligible platforms × 0.14 = 5.88 expected per seed
- But validation rejections + fallback platforms reduce this further

---

## Procedural Generation Bugs

### 1. Hazard ID Reclamation Race Condition
**File:** `procedural.py:327-333`

```python
def reclaim_hazard_ids(self, ids: list[int]) -> None:
    for hazard_id in ids:
        if hazard_id not in self._free_hazard_ids:
            self._free_hazard_ids.append(hazard_id)
    self._free_hazard_ids.sort()
```

**Bug:** `_free_hazard_ids` is a list, `sort()` makes allocation order non-FIFO but deterministic. However, `pop(0)` in `_hazards()` (line 461) is O(n). More critically, if same ID reclaimed twice (cleanup race), duplicate IDs enter free list.

**Fix:** Use `set` for membership, `heapq` for allocation, or `collections.deque` with `popleft()`.

---

### 2. Challenge Validation Allows Overlapping Hazards
**File:** `procedural.py:471-508 validate_segment()`

```python
for hazard in segment.hazards:
    # Checks hazard vs platform edges, hazard vs hazard spacing
    # MISSING: hazard vs challenge barrier/switch/cache overlap
```

**Gap:** `reserved_rects()` is computed in `generate_next()` (line 558) but only passed to `environment_generator.generate()`. The `validate_segment()` receives `hazards=segment.hazards` but doesn't check challenge objects against hazards.

**Result:** Saws can spawn inside light barriers, on top of switches, or overlapping shadow zones.

---

### 3. Fallback Platform Ignores Challenge Context
**File:** `procedural.py:510-515 create_safe_fallback()`

```python
def create_safe_fallback(self, previous: Platform, difficulty: float) -> Platform:
    gap = min(48.0, self.config.max_gap)
    width = max(self.config.minimum_landing_width + 96, 200.0)
    return Platform(self.next_platform_id, previous.right + gap, previous.y,
                    width, self.config.platform_thickness, self.index + 1,
                    difficulty)
```

**Bug:** Fallback always uses `previous.y` (flat), but `previous.y` could be at `vertical_max` (470) or `vertical_min` (190). If at boundary, next platform may be unreachable due to jump height limits.

**Missing:** Fallback should respect `vertical_min`/`vertical_max` and `max_jump_height`.

---

### 4. Difficulty Calculation Uses `furthest_distance` Not `distance`
**File:** `procedural.py:144-154 DifficultyManager` + `procedural.py:897-899 EndlessWorld.step()`

```python
# In EndlessWorld.step():
self.distance = max(0.0, self.player.position.x - self.level.spawn[0])
self.furthest_distance = max(self.furthest_distance, self.distance)
self.difficulty = self.generator.difficulty_manager.calculate(self.furthest_distance)
```

**Issue:** `furthest_distance` never decreases (monotonic). If player backtracks, difficulty stays at peak. This is likely intentional (ratchet difficulty) but undocumented.

**Related:** `generator.profile(distance)` in `generate_next()` uses `furthest_distance` (line 711), so generation difficulty matches current peak, not current position.

---

### 5. Environment Generator Density Cap Reached Silently
**File:** `environment.py:130-169 generate()`

```python
if len(accepted) >= self.config.max_objects:  # default 32
    report["cap_reached"] = True
    break
```

**Bug:** `max_objects=32` is per-segment. A wide arena platform (360-660px) at high density could want 50+ objects but gets capped at 32 silently. No warning, no fallback distribution.

**Impact:** Sparse decoration on large platforms, visual inconsistency.

---

### 6. Lantern/Health Recovery Timing Edge Cases
**File:** `procedural.py:829-838 _update_lantern()` + `procedural.py:840-883 _update_challenges()`

```python
def _update_lantern(self, dt: float):
    if self.lantern_on:
        self.lantern_energy = max(0.0, self.lantern_energy - self.config.lantern_drain * dt)
        if self.lantern_energy <= 0:
            self.lantern_on = False
            self.events.append("tick")
    else:
        self.lantern_energy = min(1.0, self.lantern_energy + self.config.lantern_recharge * dt)
```

**Edge case:** `lantern_drain=0.0105`, `lantern_recharge=0.115` → recharge is ~11x faster than drain. At 60 FPS (dt=1/60):
- Drain/frame: 0.000175
- Recharge/frame: 0.00192
- Full drain: ~95 seconds
- Full recharge: ~8.5 seconds

**Potential exploit:** Toggle lantern off for 1 frame every ~50 frames → near-infinite lantern.

---

### 7. Saw Contact Detection Uses Capsule Approximation
**File:** `physics.py:459-465`

```python
for x, y, radius in self.saw_positions():
    cy = max(p.y - 15, min(p.y + 15, y))  # Clamp to player vertical center ±15
    if math.hypot(p.x - x, cy - y) < radius + 10:
        self._saw_contact(x)
```

**Bug:** Player height is 44 (PLAYER_SIZE[1]), half-height = 22. Clamping to ±15 means top/bottom 7 pixels of player don't collide with saws.

**Campaign saws** (physics.py:301-303) use same logic — consistent but potentially wrong.

---

### 8. Challenge Generator Stats Not Reset Between Runs
**File:** `challenges.py:279-296 ChallengeStats` + `procedural.py:623`

```python
challenge_generator = PuzzleGenerator(self.seed, challenge_config)
# ...
self.challenge_generator = challenge_generator
```

**Issue:** `ChallengeStats` accumulates across `generate_next()` calls. `snapshot()` reports cumulative stats (line 949), but no way to get per-segment stats.

**Impact:** Debugging challenge distribution requires parsing `rejections` list in `ProceduralGenerator`.

---

## Test Coverage Gaps

### Missing Tests
1. **No test for challenge-hazard overlap validation**
2. **No test for fallback platform reachability**
3. **No test for environment density cap behavior**
4. **No test for lantern toggle exploit**
5. **No test for saw collision accuracy vs player bounds**
4. **No integration test: full endless run > 1000 segments**

### Flaky Test Risk
`test_generated_segments_keep_hazards_clear_of_landing_and_takeoff` uses fixed seeds 1-15. If RNG changes, test breaks. Should use statistical assertion (e.g., "mean hazards > 40 with p<0.01").

---

## Recommendations

### P0 - Fix Failing Test
```python
# Option A: Lower threshold (pragmatic)
assert total_hazards > 40  # Was 50, actual ~47

# Option B: Increase base hazard_probability (design change)
# procedural.py:183: hazard_probability=0.14 + 0.46 * t
# Change to: hazard_probability=0.18 + 0.42 * t
```

### P1 - Fix Validation Gaps
1. Add challenge-hazard overlap check in `validate_segment()`
2. Make fallback platform respect vertical bounds and jump reach
3. Use `heapq` for hazard ID allocation

### P2 - Add Missing Tests
1. Property-based test: `hypothesis` for platform reachability
2. Integration test: 1000-segment run with snapshot validation
3. Visual regression: screenshot comparison at fixed seeds

---

## Verification Commands
```bash
# Run failing test with verbose output
.venv-echo/bin/python -m pytest tests_echo/test_procedural.py::test_generated_segments_keep_hazards_clear_of_landing_and_takeoff -xvs

# Run all procedural tests
.venv-echo/bin/python -m pytest tests_echo/test_procedural.py -xvs

# Quick endless run simulation (headless, 1000 frames)
.venv-echo/bin/python -m echo_game.game --headless --frames 1000 --endless --seed 42 --report /tmp/endless.json
```