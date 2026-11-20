# Visual Differences: Campaign vs Endless/Procedural Mode

## Executive Summary
**This is a confirmed bug.** The visual presentation between Campaign (hand-authored) and Endless (procedural) modes is **fundamentally different** — different rendering pipelines, different art assets, different color schemes, and different parallax systems. Players experience two visually distinct games.

---

## Root Cause: Two Separate Rendering Pipelines

### Campaign Mode (`art.py` + `game.py:_terrain()`, `_environment()`, etc.)
- **Art style:** Colored, atmospheric, hand-painted Cairo landscapes per chapter
- **Background:** `Art.draw_background()` → chapter-specific PNGs (far/mid/works/fog/foliage)
- **Terrain:** `game.py:_terrain()` → hand-coded procedural terrain with ink lines, roots, grass
- **Environment:** `game.py:_environment()` → colored trees, bamboo, wood, rocks, grass, dirt blocks
- **Water:** `game.py:_water()` → animated water with sine-wave surface, underwater rays
- **Player:** `Art.draw_player()` → courier sprite with lantern glow, gravity flip support
- **HUD:** `game.py:_campaign_hud()` → colored chapter title, hints, mechanic status
- **Color palette:** INK (9,14,17), PAPER (214,223,216), ACCENT (157,204,195)

### Endless/Procedural Mode (`forest.py` + `game.py` endless branches)
- **Art style:** Monochrome forest, seeded deterministic generation
- **Background:** `ForestRenderer.draw_background()` → pre-rendered layer strips (distant/mist/trunks)
- **Terrain:** `ForestRenderer.draw_terrain()` → Cairo-rendered eroded platforms with grass/roots
- **Environment:** `ForestRenderer.draw_environment()` → monochrome props (trees/bamboo/wood/rock/grass/dirt)
- **Water:** **NONE** — no water system in endless mode
- **Player:** `ForestRenderer.draw_player()` → procedural stick-figure courier, no lantern glow
- **HUD:** `game.py:_forest_hud()` → monochrome health/lantern bars, distance/seed/difficulty
- **Color palette:** INK (4,4,4), LIGHT (219,219,219) — **grayscale only**

---

## Detailed Visual Differences

### 1. Background & Parallax
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Layers | 4 (far, works, mid, fog) + foliage foreground | 3 (distant, mist, trunks) + canopy + floor + fringe |
| Parallax factors | 0.075, 0.18, 0.32, 0.10 (fog) | 0.12, 0.29, 0.62 |
| Chapter variation | 6 unique chapter backgrounds | Single seed-generated forest |
| Animation | Fog scrolls (time * 7), dust motes | Static pre-rendered strips |
| Beacon/tower | Chapter-specific beacon at BEACON_X | None |

### 2. Terrain Rendering
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Base color | INK (9,14,17) with highlight line (49,59,59) | Pure INK (4,4,4) with eroded edges |
| Surface detail | Deterministic "broken surface" lines every 19px | Per-platform Cairo erosion with grass/clumps |
| Roots/hanging | Deterministic lines every 45px on deep platforms | Overhanging roots + grass nap on every platform |
| Water interaction | Water overlay with animated surface | **No water at all** |

### 3. Environment Objects (Trees, Rocks, Grass)
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Trees | Colored trunks (39-55 range), 5 branch layers | Monochrome trunks (4-26 gray), irregular boles |
| Bamboo | Green stalks (52,75+,60) with nodes | Monochrome trunks layer |
| Wood | Brown crates (64,57,44) with highlights | Monochrome polygons |
| Rocks | Colored polygons (61,72+,70) | Monochrome polygons |
| Grass | Green blades (68,88,68) | Monochrome blades on terrain surface only |
| Dirt blocks | Brown rectangles (39+,43,35) | Same but monochrome |

### 4. Player Rendering
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Sprite | 12-frame courier with hood, scarf, lantern | 12-frame stick figure (procedural Cairo) |
| Lantern glow | **Yes** - `Art.draw_player()` adds glow + `game.py:_lantern()` | **Only** `ForestRenderer.draw_lantern()` (halo) |
| Gravity flip | Sprite flips vertically (`gravity` param) | Stick figure flips |
| Animation | Walk cycle (frames 2-9), jump (10-11), idle (0-1) | Same frame logic but procedural |

### 5. Mechanisms & Hazards
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Saws | `Art.draw_saw()` - pre-rendered rotating sprite | `ForestRenderer.draw_saws()` - Cairo-rendered per-frame |
| Gates | Plate + gate with chain visual | Light barriers (monochrome monoliths) |
| Magnet | `Art.sprite("magnet")` - colored ceiling clamp | **Not in endless** |
| Seesaw | Beam + pivot rendered in `_mechanisms()` | **Not in endless** |
| Water valve/cover | Animated cover + valve pipe | Light switches only |
| Rope | Segmented rope physics + render | **Not in endless** |

### 6. Challenges (Endless Only)
- Shadow zones (animated diagonal stripes)
- Light caches (halo + beam)
- Light barriers (monochrome sealed monoliths with vertical seam)
- Light switches (pole + circle indicator)
- Hollow sentries (ellipse + eyes)

### 7. HUD & UI
| Aspect | Campaign | Endless |
|--------|----------|---------|
| Title | Chapter title + subtitle (fades) | None during play |
| Hint | Level-specific hint at bottom | None |
| Health | Not shown (single life) | 5 health circles |
| Lantern | Not shown | Energy bar + toggle hint |
| Debug | F3 shows physics snapshot | Same + F1 shows seed/distance/difficulty |
| Pause menu | "THE WORLD CAN WAIT" | Same + "F1 / STATUS" |
| Death screen | "Returning to the last signal…" | "The signal rebuilds ahead…" |

### 8. Color Grading (Critical Difference)
```python
# game.py:text() - FORCES GRAYSCALE IN ENDLESS
def text(self, text, x, y, size=18, color=PAPER, center=False, alpha=255):
    if self.endless:
        value = round(sum(color[:3]) / 3)
        color = (value, value, value)  # CONVERTS ALL TEXT TO GRAYSCALE
```

**Campaign:** Full color (PAPER, ACCENT, INK, custom colors per object)
**Endless:** Forced grayscale for ALL text rendering

---

## Why This Is a Bug (Not a Feature)

1. **No design document** indicates intentional visual divergence
2. **Shared code paths** suggest unified vision (same `Game` class, same physics)
3. **Player confusion** - skills don't transfer visually (lantern, saws, movement feel different)
4. **Asset waste** - Campaign art assets unused in endless; endless art not in campaign
5. **Testing gap** - Visual regression tests don't exist for either mode

---

## Evidence of Incomplete Integration

### Water System Missing in Endless
```python
# game.py:335-349 - _water() only runs for campaign
def _water(self):
    r = self.world.level.water
    if not r:
        return
    # ... water rendering
# EndlessWorld has no water attribute (procedural.py:605-613)
```

### Magnet/Seesaw/Rope Missing in Endless
```python
# procedural.py Level definition has NO magnet, seesaw, rope, water, valve, cover
level = Level(
    "ENDLESS / THE UNENDING SIGNAL", ...,
    terrain=(Rect(-80, 460, base_width + 80, 180),),  # Only base terrain
)
```

### Environment Generator Only Used in Endless
```python
# procedural.py:622-623 - EnvironmentGenerator only created for endless
self.environment_generator = EnvironmentGenerator(...)
# Campaign uses hand-placed environment_objects in World.__init__ (physics.py:93-107)
```

---

## Recommendations

### Option A: Unify Visual Pipeline (Recommended)
1. **Extract common rendering interfaces** - `IRenderer` with `draw_background`, `draw_terrain`, `draw_player`, etc.
2. **Make ForestRenderer a drop-in replacement** for Art in endless mode, but allow color
3. **Port campaign mechanics to endless** (water, magnet, seesaw, rope) with procedural placement
4. **Unify color scheme** - Endless should use campaign palette, not forced grayscale

### Option B: Document as Intentional (If Design Choice)
1. Add `VISUAL_DESIGN.md` explaining the two distinct art directions
2. Rename modes: "Campaign (Colored)" vs "Endless (Monochrome Forest)"
3. Add transition screen when switching modes

### Option C: Minimal Fix - Color Parity
1. Remove forced grayscale in `game.py:text()` for endless
2. Add color to `ForestRenderer` constants (INK→campaign INK, LIGHT→PAPER)
3. Port lantern glow to endless player rendering
4. Add water visual (even if no gameplay water)

---

## Verification Checklist
- [ ] Run both modes side-by-side, compare screenshots
- [ ] Verify all campaign mechanics have endless equivalents
- [ ] Check color consistency for shared UI elements (menus, HUD, text)
- [ ] Test gravity flip visual in both modes
- [ ] Verify lantern behavior matches (glow, radius, energy drain)