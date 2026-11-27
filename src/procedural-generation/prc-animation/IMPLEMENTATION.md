# Implementation Status

The README is the target blueprint. This file records what the current module
actually implements, how to call it, and what is still deferred.

## Implemented

| Blueprint area | Status |
|---|---|
| Data | `CreatureSpec` (Python) for biped/quadruped/floating; JSON loader not yet needed |
| Gait | Phase-based generator with duty cycle, phase offsets, speed-driven frequency; walk/run for biped, walk/trot/gallop for quadruped |
| Foot placement | Vertical raycast through `ground_height(x)`, candidate search around the nominal foothold, slope/height rejection |
| Stance lock | Planted feet keep their world x while the body moves over them |
| IK | FABRIK solver (2-4 bones, joint limits) used by the legs; closed-form seed keeps the knee side stable |
| Compliance | Spring-smoothed IK target on planted feet, so terrain changes do not pop |
| Secondary motion | Squash/stretch from vertical velocity, idle breathing scale, head bob, tail pendulum, blink |
| Head | Damped look-at with clamping and partial body-lean compensation |
| Render | Depth-sorted modular pieces (back limbs, torso, front limbs, head, eye) drawn as placeholders |
| Determinism | Per-creature `random.Random(seed)` for phase, breath and blink; same seed gives identical poses |
| Accessibility | `reduce_motion=True` disables squash/stretch, breathing, head bob, tail sway and blink |
| Tests | `tests/test_animation.py` inside this folder |

## API

```python
from creature_anim import CreatureAnimator, make_spec
from creature_draw import draw_creature

anim = CreatureAnimator(make_spec("quadruped", scale=0.9), x=400, y=640, seed=7)
anim.update(
    dt,
    x=400, y=640,              # ground anchor (feet) or core centre for floating
    vx=80, vy=0,
    facing=1,
    state="walk",              # idle/walk/run/jump/fall/attack/hit/dead
    on_ground=True,
    ground_height=lambda gx: 640,   # None over a gap
    head_target=(player_x, player_y),
    gait=None,                 # optional: walk/run/trot/gallop
    reduce_motion=False,
)
draw_creature(surface, anim, offset=(-camera.x, -camera.y))
```

`find_foothold` and `solve_fabrik` are public helpers for future creature
variants. `solve_ik` remains as the closed-form 2-bone seed.

## Still deferred

- Pymunk body/leg forces, support polygon, stumble/recovery. The game still
  moves entities kinematically; adding a physics body is a gameplay change, not
  an animation-only change.
- Spine/neck chains, gaze pupil, eye contact. Tail is a single pendulum link.
- Sprite atlas/modular art. The depth-sorted piece list is ready for atlas
  keys, but assets are still placeholder shapes.
- Gait blending, LOD tiers, debug draw, footstep audio sync.
- Creature JSON definitions and `data/creatures/`; current presets are
  `make_spec` presets.

## Performance

Measured on this machine: ~85 µs update and ~128 µs draw per creature
(10 creatures, 600 frames). The blueprint budget is ~800 µs per creature.

## Tests

```bash
python -m pytest -q
```

Animation tests live in `src/procedural-generation/prc-animation/tests/`.
Gameplay integration tests remain in the repository `tests/` folder.
