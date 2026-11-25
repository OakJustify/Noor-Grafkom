# Cloaked wisp — player sprite sets

Six original, transparent RGBA sprite sheets, **8 frames each / 48 total**.
The wisp has a glowing, hollow hood, a fluttering cloak, floating spirit ribbons
instead of legs, and the existing brass lantern.

| Action | Sheet | Frames | Playback |
|---|---|---:|---|
| Idle | `wisp_idle.png` | 8 | 7 fps loop: hover, breathing glow, cloth and lantern sway |
| Walk | `wisp_walk.png` | 8 | 10 fps loop: soft glide, shorter cloth wake |
| Run | `wisp_run.png` | 8 | 16 fps loop: forward lean, streaming cape and scarf |
| Jump | `wisp_jump.png` | 8 | Non-looping takeoff → ascent → apex → descent → landing |
| Glide | `wisp_glide.png` | 8 | 10 fps loop: open cloak, outstretched ribbons |
| Focus | `wisp_focus.png` | 8 | 8 fps loop: braced lantern, subtle breathing |

![All 48 frames](preview.png)

Each sheet is **832 × 104 px**, one horizontal row of **104 × 104 px** cells,
facing right. `manifest.json` supplies each frame rectangle, timings and pivots.
The pivot is `(52, 68)`; after horizontal mirroring it is `(51, 68)`. The fixed
pivot prevents direction changes or pose changes from shifting the player.

The live game and these exports use the same deterministic, cached vector
frames from `src/nur_game/wisp.py`, supersampled at 2× for clean edges. PNGs are
exports for inspection/reuse, not a second independently maintained source.

Regenerate from `v4`:

```bash
.venv-nur/bin/python -m nur_game.generate_wisp
```

Normal movement now selects **walk at 190 px/s**, including slower crate pulling.
Hold **Shift + direction** to sprint at **300 px/s** and select run: a stronger
forward lean with a longer, faster cape/scarf wake. Sprint consumes the separate
NAPAS stamina meter; exhaustion returns to walk until recovery. Jump frames
follow actual vertical velocity and never loop in midair. Playback pauses with
the game and resets on retry/new game. The fixed pivot/collision size and
lantern protection remain unchanged. Updated run frames are exported here.

V4 renders the same frames at a larger on-screen scale. Talking to a refuge
companion unlocks glide: hold jump while descending to limit fall speed, spending
stamina. F selects focus while standing still and brightens the local light at
the cost of faster drain. If G leaves the lantern behind, live frames omit the
hand lantern; these inspection sheets show the carried variant.
