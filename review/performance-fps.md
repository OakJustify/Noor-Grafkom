# Performance & FPS Review

## Executive Summary
The game suffers from significant FPS drops, especially in Endless/Procedural mode. The root causes are concentrated in `echo_game/forest.py` (procedural rendering) and the Cairo/Pygame interop pipeline.

---

## Critical Performance Bottlenecks

### 1. Cairo → Pygame Round-Trip on Every Chunk Build (`forest.py`)
**Location:** `forest.py:_canvas()`, `_image()`, `_surface_image()`, `_mask_image()`

**Problem:**
- Every new chunk triggers: Cairo surface → PNG encode → BytesIO → pygame.image.load() → convert_alpha()
- This happens on **cache miss** during gameplay when new chunks enter view
- `_mask_image()` does additional: surfarray pixel manipulation → smoothscale → blit → BLEND_RGBA_MULT

**Evidence:**
```python
# forest.py lines 34-61
def _canvas(width, height, scale=1):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, math.ceil(width * scale), ...)
    # ...

def _image(surface):
    encoded = io.BytesIO()
    surface.write_to_png(encoded)  # PNG ENCODE - SLOW
    encoded.seek(0)
    return pygame.image.load(encoded).convert_alpha()  # PNG DECODE - SLOW
```

**Impact:** Frame hitches when new chunks generate (visible as stutter during horizontal movement)

---

### 2. NumPy Operations in Hot Path (`forest.py:_atmosphere()`)
**Location:** `forest.py:_atmosphere()` called once at init, but creates large arrays

**Problem:**
- Creates `np.mgrid[0:h, 0:w]` for 960x540 = 518,400 elements
- Multiple `np.exp()`, `np.clip()`, `np.repeat()` operations
- `pygame.surfarray.make_surface()` and `pygame.surfarray.array3d()` conversions

**Impact:** Slow startup, memory pressure

---

### 3. Excessive Blitting in `draw_background()` (`forest.py:549-576`)
**Current (optimized but still heavy):**
```python
for index, layer in enumerate(LAYERS):  # 3 layers
    # wrap-around handling with 2 blits per layer = up to 6 blits/frame
screen.blit(self._atmosphere_overlay, (0, 0))  # 1 blit
self.draw_canopy(game)  # 1-2 blits with wrap
self._draw_forest_floor(game)  # 1-2 blits with wrap
# Total: ~10-12 blits/frame just for background
```

**Plus foreground:**
```python
# draw_foreground() - another 1-2 blits + vignette
game.canvas.blit(self._vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
```

---

### 4. Per-Frame Surface Creation in `draw_challenges()` (`forest.py:1050-1135`)
**Problem:** Creates new `pygame.Surface` every frame for shadows:
```python
for shadow in challenge.shadows:
    field = pygame.Surface((width, height), pygame.SRCALPHA)  # ALLOCATION!
    for n in range(0, width, 5):  # per-pixel drawing loop
        pygame.draw.line(field, ..., 3)
    screen.blit(field, (x, y))
```

**Impact:** Memory allocation + GC pressure every frame with active challenges

---

### 5. Saw Rendering Cache Misses (`forest.py:1024-1048`)
**Problem:** Cache key includes `degree` which changes every frame:
```python
degree = round(game.visual_time * 240 / 6) * 6 % 360  # Changes ~40x/second
key = (r, degree)  # New key every frame → cache miss → Cairo render
```

**Impact:** 20 teeth × 4 offsets = 80 curve_to operations per saw per frame when not cached

---

### 6. Campaign Mode Also Has Blitting Overhead (`art.py:687-712`)
```python
def draw_background(self, screen, camera_x, time, chapter):
    screen.blit(self._sky_surface, (0, 0))
    self._tile(screen, f"chapter_{chapter}_far", camera_x * .075)   # multiple blits
    self._tile(screen, f"chapter_{chapter}_works", camera_x * .18)  # multiple blits
    self._tile(screen, f"chapter_{chapter}_mid", camera_x * .32)    # multiple blits
    self._tile(screen, "fog", camera_x * .10 + time * 7)            # multiple blits
    # 17 dust motes drawn individually with pygame.draw.circle
```

---

## Measured/Estimated Costs

| Operation | Est. Cost | Frequency |
|-----------|-----------|-----------|
| Cairo PNG encode/decode | ~2-5ms | Per new chunk (cache miss) |
| NumPy mgrid + surfarray | ~10-20ms | Once at init |
| Shadow Surface alloc + draw | ~1-3ms | Per shadow zone/frame |
| Saw Cairo re-render | ~1-2ms | Per saw/frame (when cache miss) |
| Blit (960x540) | ~0.1-0.3ms | 15-20x/frame |

---

## Recommendations (Priority Order)

### P0 - Immediate Fixes
1. **Pre-warm all chunks at startup** - `warm_chunks()` exists but only called in `start_endless()`. Call it for a wider camera range.
2. **Cache saw rotation at fixed angles** - Pre-render 60 angles (6° steps) instead of computing per-frame degree
3. **Reuse shadow surfaces** - Pool/cache shadow zone surfaces instead of allocating per frame

### P1 - Structural Improvements
4. **Replace Cairo→PNG→Pygame with direct buffer copy** - Already partially done in `_surface_image()` but not used everywhere
5. **Batch blits** - Combine layer strips into single atlas textures
6. **Move per-pixel loops to shaders** - Shadow stripes, fog bands, dust motes

### P2 - Architecture
7. **Separate render thread** - Decouple physics (120Hz) from rendering (60Hz) with interpolation
8. **Level-of-detail for distant chunks** - Lower resolution/less detail for far parallax layers

---

## Verification Steps
```bash
# Run headless benchmark
cd /home/podistrict/Projects/03-projects/02-games/noor-grafkom/v3
.venv-echo/bin/python -m echo_game.game --headless --frames 1800 --endless --seed 1 --report /tmp/perf.json

# Check frame times in report
cat /tmp/perf.json | jq '.wall_seconds, .frames'
# Target: 1800 frames in ≤ 30 seconds (60 FPS sustained)
```