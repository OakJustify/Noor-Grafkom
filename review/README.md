# Code Review Index — ECHO: The Hollow Signal

## Project Overview
- **Game:** ECHO — The Hollow Signal (physics platformer)
- **Language:** Python 3.14 + Pygame + Pymunk + Cairo + NumPy
- **Architecture:** Deterministic simulation (120Hz) + rendered presentation (60Hz)
- **Modes:** Campaign (6 hand-authored levels) + Endless (procedural generation)

---

## Review Files Created

| File | Focus | Priority |
|------|-------|----------|
| `performance-fps.md` | FPS bottlenecks, rendering pipeline | **P0** |
| `visual-differences-campaign-vs-endless.md` | Two different visual games | **P0** |
| `procedural-generation-bugs.md` | Test failures, generation logic bugs | **P1** |
| `physics-gameplay.md` | Physics edge cases, mechanic parity | **P1** |
| `asset-npc.md` | Asset pipeline, enemy variety | **P2** |

---

## Critical Findings Summary

### 🔴 P0 — Must Fix Before Release

1. **FPS Drops in Endless Mode** (`performance-fps.md`)
   - Cairo→PNG→Pygame round-trip on chunk cache misses
   - Per-frame surface allocation for shadows
   - Saw re-render every frame (rotation cache key includes frame-varying degree)
   - 15-20 blits/frame for background layers

2. **Campaign ≠ Endless Visually** (`visual-differences-campaign-vs-endless.md`)
   - **Different rendering pipelines** (Art vs ForestRenderer)
   - **Different color schemes** (full color vs forced grayscale)
   - **Different mechanics** (water/magnet/seesaw/rope missing in endless)
   - **Different player art** (courier sprite vs stick figure)
   - This is a **bug**, not a feature — no design doc supports it

3. **Failing Test** (`procedural-generation-bugs.md`)
   - `test_generated_segments_keep_hazards_clear_of_landing_and_takeoff`
   - Expected >50 hazards, got 47 across 15 seeds
   - Root cause: low hazard_probability (0.14) at difficulty 1.0

---

### 🟠 P1 — Fix Soon

4. **Procedural Validation Gaps** (`procedural-generation-bugs.md`)
   - Challenge-hazard overlap not checked
   - Fallback platforms ignore jump reachability
   - Hazard ID reclamation uses O(n) list operations

5. **Physics Inconsistencies** (`physics-gameplay.md`)
   - Gravity flip preserves vertical velocity (can exploit for height)
   - Saw collision misses top/bottom 7px of player hitbox
   - Air control 7.25x weaker than ground — feels floaty in endless
   - Regrab delay 0.3s feels unresponsive

6. **Single Enemy Type** (`asset-npc.md`)
   - Only "Sentry" implemented
   - Campaign has **zero enemies** — no combat tutorial
   - Rocket/crane/watertower generators exist but unused

---

### 🟡 P2 — Technical Debt

7. **Asset Pipeline** (`asset-npc.md`)
   - No stale asset cleanup on generator changes
   - Two player art styles (campaign vs endless)
   - Moth guide hardcoded per chapter

8. **Code Organization**
   - `game.py` = 844 lines (god class)
   - `forest.py` = 1173 lines (rendering + generation + caching)
   - `procedural.py` = 1109 lines (generation + world + pilot)
   - No interface separation for renderers

---

## Quick Wins (Can Fix Today)

| Fix | File | Effort |
|-----|------|--------|
| Increase `hazard_probability` base from 0.14→0.18 | `procedural.py:183` | 1 min |
| Pre-render saw rotations (60 angles) | `forest.py:1030-1048` | 30 min |
| Pool shadow zone surfaces | `forest.py:1053-1063` | 1 hour |
| Remove forced grayscale in endless text() | `game.py:81-83` | 5 min |
| Add saw collision for full player height | `physics.py:461` | 10 min |

---

## Architecture Refactor (If Time Permits)

### Renderer Interface
```python
# New: echo_game/renderer.py
class IRenderer(Protocol):
    def draw_background(self, canvas, camera_x, camera_y, time): ...
    def draw_terrain(self, canvas, world, camera): ...
    def draw_player(self, canvas, player, time): ...
    def draw_hud(self, canvas, world): ...

# CampaignRenderer wraps Art + game.py campaign draw methods
# ForestRenderer already implements most — add color support
```

### Unified Color Palette
```python
# Both modes use same constants
INK = (9, 14, 17)
PAPER = (214, 223, 216)
ACCENT = (157, 204, 195)
# Endless: remove INK=(4,4,4), LIGHT=(219,219,219)
```

### Mechanics Parity
| Mechanic | Campaign | Endless | Action |
|----------|----------|---------|--------|
| Water | ✓ | ✗ | Add procedural water segments |
| Magnet | ✓ | ✗ | Add magnetic ceiling challenges |
| Seesaw | ✓ | ✗ | Add seesaw platform variant |
| Rope | ✓ | ✗ | Add rope swing challenges |
| Lantern | ✗ | ✓ | Add to campaign (optional) |

---

## Test Commands

```bash
# Full test suite
cd /home/podistrict/Projects/03-projects/02-games/noor-grafkom/v3
.venv-echo/bin/python -m pytest --tb=short

# Performance benchmark (headless, 30 sec target)
.venv-echo/bin/python -m echo_game.game --headless --frames 1800 --endless --seed 1 --report /tmp/perf.json

# Visual regression (screenshots)
.venv-echo/bin/python -m echo_game.game --frames 1 --screenshot /tmp/campaign.png --chapter 1
.venv-echo/bin/python -m echo_game.game --frames 1 --screenshot /tmp/endless.png --endless --seed 1
```

---

## Review Metadata
- **Reviewer:** Hermes Agent (automated code review)
- **Date:** 2026-11-17
- **Commit:** (run `git rev-parse HEAD` to record)
- **Branch:** (run `git branch --show-current`)