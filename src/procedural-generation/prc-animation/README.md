# Procedural Animation System — Creature Module

**Target:** Rain World–style procedural creature animation untuk game Noor (2D side-scroller, Python + Pygame + Pymunk)

**Deterministic seed:** 42 (semua sistem: physics, spawn, audio, art, shaders, animation)

**Aksesibilitas:** Hargai flag `reduce_motion`, `reduce_flash`, `reduce_shake` dari `config.DEFAULT_ACCESSIBILITY`

---

## 1. ARSITEKTUR SISTEM (Pipeline Per Frame)

```
AI INTENT (desired_vel, look_target, gait_type)
       │
       ▼
GAIT GENERATOR  ── phase-based, duty cycle, footfall timing
       │              output: foot_targets_world[leg_name]
       ▼
FOOT PLACEMENT  ── raycast terrain, search valid foothold, compliance spring
       │              output: ik_targets_world[leg_name]
       ▼
IK SOLVER (FABRIK)  ── per leg chain (2-4 segments), joint limits, ground lock
       │              output: joint_angles[leg_name], joint_positions[leg_name]
       ▼
SPINE / TAIL / NECK IK  ── secondary chains, counter-balance, look-at
       │              output: spine_angles, tail_angles, neck_angle, head_angle
       ▼
PHYSICS INTEGRATION (Pymunk)  ── body rigidbody, leg forces → torque, COM check
       │              output: body_pos, body_vel, body_angle, contact_forces
       ▼
SECONDARY MOTION  ── squash/stretch, breathing, tail sway, head stabilization
       │              output: sprite_transforms (pos, rot, scale, z-order per piece)
       ▼
RENDER (pycairo → sprite atlas)  ── modular pieces, flip by facing, depth sort
```

---

## 2. DATA DEFINITION — `CreatureDefinition` (JSON / Python dataclass)

```python
@dataclass
class SegmentDef:
    length: float
    angle_limit: tuple[float, float] | None = None   # degrees, relative to parent
    sprite: str | None = None                        # key ke asset atlas
    radius: float = 4                                # collision capsule radius

@dataclass
class LimbDef:
    name: str
    type: Literal["leg", "arm", "tail", "neck", "head", "wing"]
    anchor: Vec2                                     # relative to body center
    segments: list[SegmentDef]
    # Leg-specific:
    nominal_offset: Vec2 | None = None               # default foot pos relative to body
    gait_phase_offset: float = 0.0                   # 0-1 dalam cycle

@dataclass
class GaitDef:
    name: str
    pattern: Literal["lateral_sequence", "diagonal_pairs", "rotary", "pace", "bound"]
    phase_offsets: list[float]                       # per leg (order: FL, FR, RL, RR)
    duty_cycle: float                                # 0.35-0.75
    speed_range: tuple[float, float]                 # (min_speed, max_speed) px/s
    max_step_length: float
    step_height: float

@dataclass
class CreatureDefinition:
    name: str
    body: dict                                        # mass, width, height, com, sprites
    limbs: list[LimbDef]
    gaits: dict[str, GaitDef]                         # "walk", "trot", "gallop", "climb"
    ik: dict                                          # solver, iterations, tolerance, foot_radius
    behavior_weights: dict                            # head_look_at, tail_balance, body_lean
    physics: dict                                     # friction, restitution, collision_layers
    visual: dict                                      # squash_stretch_enabled, breathing_enabled
```

**Contoh minimal (Lizard-like):**
- Body: 1 torso sprite, mass 15, COM (0, -4)
- 4 legs × 3 segments (thigh, shin, foot) = 12 IK chains
- 1 tail × 4 segments (tapered)
- 1 neck × 2 segments + head
- Gaits: walk, trot, gallop, climb

---

## 3. GAIT GENERATOR — Phase-Based Footfall Timing

### 3.1 Phase Offsets per Gait (4 kaki: FL, FR, RL, RR)

| Gait | Phase Offsets | Duty Cycle | Use Case |
|------|---------------|------------|----------|
| Walk (lateral sequence) | [0.0, 0.5, 0.75, 0.25] | 0.70 | Slow, careful, uneven terrain |
| Trot (diagonal pairs) | [0.0, 0.5, 0.5, 0.0] | 0.55 | Medium speed, efficient |
| Pace (lateral pairs) | [0.0, 0.5, 0.0, 0.5] | 0.55 | Wide body, amphibian |
| Gallop (rotary) | [0.0, 0.25, 0.5, 0.75] | 0.40 | Fast, fleeing, chase |
| Bound (synchronous) | [0.0, 0.0, 0.5, 0.5] | 0.40 | Small mammals, hop |
| Climb (custom) | [0.0, 0.33, 0.66, 0.33] | 0.80 | Vertical, 3+ contact points |

### 3.2 Per-Frame Calculation

```python
def gait_step(dt, speed, gait_def, current_phase):
    # Frequency dari speed (Hz)
    freq = lerp(gait_def.speed_range[0], gait_def.speed_range[1],
                clamp(speed / max_speed, 0, 1))
    new_phase = (current_phase + freq * dt) % 1.0
    
    targets = {}
    for i, leg_name in enumerate(LEG_ORDER):  # [FL, FR, RL, RR]
        leg_phase = (new_phase + gait_def.phase_offsets[i]) % 1.0
        in_stance = leg_phase < gait_def.duty_cycle
        
        if in_stance:
            # Stance: foot LOCKED to world (no slip)
            targets[leg_name] = stance_positions[leg_name]
        else:
            # Swing: parabolic arc ke landing target
            swing_t = (leg_phase - gait_def.duty_cycle) / (1 - gait_def.duty_cycle)
            landing = compute_landing_position(leg_name, body_vel, terrain)
            targets[leg_name] = swing_arc(stance_positions[leg_name], landing, swing_t)
    
    return targets, new_phase
```

### 3.3 Swing Arc (Visual Polish)

```python
def swing_arc(start, end, t):
    # Bezier: start → peak (mid + height) → end
    mid = (start + end) * 0.5
    peak = mid + Vec2(0, -step_height * sin(pi * t))
    return lerp2(lerp2(start, peak, t), lerp2(peak, end, t), t)
```

---

## 4. FOOT PLACEMENT — Terrain Adaptation & Compliance

### 4.1 Raycast Search (Priority Order)

1. **Nominal position** (dari gait generator)
2. **Spiral search** around nominal: radius 0, 8, 16, 24, 32 px; angles 0°, ±45°, ±90°, ±135°, 180°
3. **Score each hit:** `score = 100 - distance - slope_penalty*50 - height_diff*10`
4. **Pick best valid** (ground layer, not too steep, within max_step_height)

### 4.2 Compliance Spring (Soft IK Target)

```python
# Foot target TIDAK snap ke foothold — spring-damper
ik_target += (foothold - ik_target) * compliance_stiffness * dt
ik_target_vel = (ik_target_vel + (foothold - ik_target) * compliance_stiffness) * compliance_damping
```

**Why:** Menghindari "IK pop" saat foot placement berubah mendadak; kaki "merenggang" natural.

### 4.3 Stance Lock (Critical untuk Weight Feel)

```python
# Saat in_stance: foot world position DI-KUNCI
stance_positions[leg_name] = ik_target_at_stance_start
# Body bergerak ATAS kaki yang terkunci (bukan kaki ikut body)
```

---

## 5. IK SOLVER — FABRIK (Forward And Backward Reaching IK)

### 5.1 Why FABRIK over CCD?

| Factor | FABRIK | CCD |
|--------|--------|-----|
| Singularity (straight limb) | ✅ Stable | ❌ Stuck |
| Convergence (3-bone) | 5-10 iter | 20+ iter |
| Joint limits | Easy clamp | Tricky |
| Deterministic | ✅ | ⚠️ |
| Implementation | Simple | Simple |

### 5.2 Algorithm (Per Leg Chain)

```python
def fabrik_solve(root_pos, target_pos, segments, root_angle=0, max_iter=10, tol=0.5):
    # segments: [{"length": L, "angle_limit": (min,max)}, ...]
    
    # 1. Initial positions (forward)
    positions = [root_pos]
    angles = [root_angle]
    for seg in segments:
        positions.append(positions[-1] + Vec2.from_angle(angles[-1]) * seg["length"])
        angles.append(angles[-1])
    
    total_len = sum(s["length"] for s in segments)
    if (target_pos - root_pos).length() > total_len:
        # Unreachable → stretch straight
        dir = (target_pos - root_pos).normalize()
        for i, seg in enumerate(segments):
            positions[i+1] = positions[i] + dir * seg["length"]
        return extract_angles(positions, root_angle)
    
    # 2. FABRIK iterations
    for _ in range(max_iter):
        # Backward: pull end to target
        positions[-1] = target_pos
        for i in reversed(range(len(segments))):
            dir = (positions[i] - positions[i+1]).normalize()
            positions[i] = positions[i+1] + dir * segments[i]["length"]
        
        # Forward: anchor root
        positions[0] = root_pos
        for i in range(len(segments)):
            dir = (positions[i+1] - positions[i]).normalize()
            positions[i+1] = positions[i] + dir * segments[i]["length"]
        
        if (positions[-1] - target_pos).length() < tol:
            break
    
    # 3. Apply joint limits & re-project
    angles = extract_angles(positions, root_angle)
    for i, seg in enumerate(segments):
        if seg.get("angle_limit"):
            angles[i+1] = clamp(angles[i+1], seg["angle_limit"][0], seg["angle_limit"][1])
            positions[i+1] = positions[i] + Vec2.from_angle(angles[i+1]) * seg["length"]
    
    return angles, positions
```

### 5.3 Leg-Specific Constraints

| Joint | Typical Limit (deg) | Note |
|-------|---------------------|------|
| Hip (body-thigh) | -45° to +45° | Relative to body forward |
| Knee (thigh-shin) | -90° to 0° | Hanya bend backward |
| Ankle (shin-foot) | -30° to +30° | Terrain adaptation |

---

## 6. SPINE / TAIL / NECK / HEAD — Secondary Chains

### 6.1 Spine (Body Curve)
- 2-3 segments dari tail base ke neck base
- **Driver:** Body velocity + angular velocity → curve toward turn direction
- **Formula:** `spine_angle[i] = body_angular_vel * stiffness[i] - body_vel.x * lean_factor[i]`

### 6.2 Tail (Counter-Balance Pendulum)
```python
# Physics-driven pendulum, bukan IK target
tail_torque = -body_accel.x * tail_mass * tail_length * 0.5
tail_angle += (tail_torque - tail_angle * stiffness - tail_vel * damping) * dt
# Clamp to joint limits per segment
```

### 6.3 Neck + Head (Look-At + Stabilization)
```python
# Target: AI look_target (player, threat, food) atau body_vel direction
desired_head_angle = (look_target - neck_base).angle()
# Spring to target, damped by body motion
head_angle = spring_damper(head_angle, desired_head_angle, k=15, c=3, dt)
# Neck follows head dengan offset (head leads, neck supports)
neck_angle = spring_damper(neck_angle, head_angle * 0.6, k=10, c=2, dt)
```

### 6.4 Eye / Gaze (Micro Detail)
- Pupil offset dalam head sprite: `pupil_pos = gaze_dir * pupil_range`
- Blink: random interval 2-6s, duration 0.15s (respect `reduce_motion`)

---

## 7. PHYSICS INTEGRATION (Pymunk)

### 7.1 Body Setup
```python
body = pymunk.Body(mass, moment)
body.position = start_pos
body.velocity_func = custom_velocity_func  # untuk gravity scale, damping

# Collision shape: capsule atau polygon mengikuti body sprite
shape = pymunk.Poly(body, vertices)
shape.friction = 0.7
shape.collision_type = COLLISION_CREATURE
```

### 7.2 Leg Forces → Body Torque (Stance Phase)

```python
for leg_name in stance_legs:
    foot_world = stance_positions[leg_name]
    leg_force = (body.position - foot_world).normalize() * leg_push_force
    # Apply di foot position → torque otomatis
    body.apply_force_at_world_point(leg_force, foot_world)
```

### 7.3 Support Polygon Check (Fall Over)
```python
# Convex hull dari stance foot positions
support_poly = convex_hull([stance_positions[l] for l in stance_legs])
com_proj = body.position + body.rotation_vector * com_offset
if not point_in_polygon(com_proj, support_poly):
    # Creature tipping → trigger stumble/recovery behavior
    ai.request_state("stumble")
```

### 7.4 Ground Reaction (Compliance)
- Setiap stance leg = `DampedSpring` antara body (at anchor) dan world (foot pos)
- Stiffness/damping dari `creature_def.physics.leg_spring`

---

## 8. SECONDARY MOTION — Visual Juice (Respect `reduce_motion`)

| Effect | Driver | Formula | Accessibility |
|--------|--------|---------|---------------|
| **Body squash/stretch** | Vertical velocity | `scale_y = 1 - clamp(vel.y * 0.001, -0.15, 0.1)`; `scale_x = 1/scale_y` | Disable jika `reduce_motion` |
| **Breathing idle** | Time (saat speed < 0.1) | `scale_y += sin(time * 0.5) * 0.02` | Disable |
| **Tail sway** | Body accel + angular vel | Pendulum sim (see 6.2) | Reduce amplitude |
| **Head bob (walk)** | Gait phase | `head_offset_y = sin(phase * 2π) * 1.5` | Disable |
| **Impact flash** | Damage/landing | White overlay 0.1s | Disable jika `reduce_flash` |
| **Screen shake** | Large impact | Camera offset noise | Disable jika `reduce_shake` |

---

## 9. RENDER — Modular Sprite System (pycairo → Atlas)

### 9.1 Sprite Piece Definition
```python
sprite_pieces = {
    "torso": {"atlas_key": "lizard_body", "z": 10, "pivot": (0, 0)},
    "head": {"atlas_key": "lizard_head", "z": 20, "pivot": (0, -4)},
    "thigh_FL": {"atlas_key": "lizard_thigh", "z": 5, "pivot": (0, 8)},
    "shin_FL": {"atlas_key": "lizard_shin", "z": 5, "pivot": (0, 16)},
    "foot_FL": {"atlas_key": "lizard_foot", "z": 5, "pivot": (0, 24)},
    # ... per limb
}
```

### 9.2 Per-Frame Transform Calculation
```python
def compute_sprite_transforms(body_pos, body_angle, joint_angles, secondary):
    transforms = {}
    # Body
    transforms["torso"] = Transform(body_pos, body_angle, 
                                     scale=secondary.body_scale)
    # Limbs (FK dari joint_angles)
    for limb_name, angles in joint_angles.items():
        pos = body_pos + limb_anchor_rotated
        for i, (seg_name, angle) in enumerate(zip(limb_segments, angles)):
            transforms[f"{seg_name}_{limb_name}"] = Transform(
                pos, angle, scale=secondary.limb_scale)
            pos += Vec2.from_angle(angle) * segment_lengths[i]
    # Head/neck/tail dari secondary chains
    ...
    return transforms
```

### 9.3 Z-Sort & Facing Flip
- Sort by `z` + `body_pos.y` (back to front)
- Flip horizontal jika `body_vel.x < 0` (atau `facing_dir`)
- Pivot point per piece dari atlas definition

---

## 10. GAIT TRANSITIONS (Smooth Blending)

```python
def blend_gaits(current_gait, target_gait, blend_factor):
    # Blend phase offsets & duty cycle
    phase_offsets = lerp_array(current.phase_offsets, target.phase_offsets, blend_factor)
    duty_cycle = lerp(current.duty_cycle, target.duty_cycle, blend_factor)
    # Blend frequency
    freq = lerp(current_freq, target_freq, blend_factor)
    # Maintain phase continuity: adjust target phase to match current
    return BlendedGait(phase_offsets, duty_cycle, freq)
```

**Transition Triggers:**
- Speed crosses gait `speed_range` threshold → blend over 0.5-1.0s
- Terrain change (flat → climb) → immediate switch + 0.3s blend
- Panic/flee → instant gallop (no blend, emergency)

---

## 11. STUMBLE / RECOVERY / FALL (Procedural Vulnerability)

### 11.1 Stumble Trigger
- COM outside support polygon > 0.2s
- Large external impulse (explosion, hit)
- Leg IK fail (target unreachable 3+ frames)

### 11.2 Stumble Behavior
1. **Freeze gait** (all legs swing phase)
2. **Spawn recovery limbs** — IK target = wide base, low COM
3. **Body physics takes over** (ragdoll-lite: increased drag, reduced push force)
4. **Recovery:** Setelah 0.5-1.5s, gait resumes dari current phase

### 11.3 Fall (Complete Failure)
- Body rotation > 60° dari upright
- Trigger "fall" state → procedural tumble (physics-driven)
- Recovery: roll to upright, stand up sequence (IK + physics)

---

## 12. CREATURE VARIATIONS (Data-Driven)

| Parameter | Range | Effect |
|-----------|-------|--------|
| Leg count | 2, 4, 6, 8 | Gait pattern changes |
| Leg length ratio | 0.5-2.0 | Step height, speed |
| Body width/length | 0.5-3.0 | Stability, turn radius |
| Tail length | 0-1.5×body | Balance authority |
| Neck length | 0-1.0×body | Look-at range |
| Mass | 5-50 | Inertia, gravity response |
| Gait preferences | dict | Walk-heavy vs gallop-heavy |

**Semua dari `CreatureDefinition` — zero code change untuk species baru.**

---

## 13. PERFORMANCE BUDGET (Target 60 FPS, 10+ creatures)

| Operation | Cost per Creature | Optimization |
|-----------|-------------------|--------------|
| FABRIK (4 legs × 3 bones × 8 iter) | ~200 μs | Early exit if converged; LOD: far=4 iter |
| Foot placement raycast (4 legs × 8 rays) | ~150 μs | Cache terrain heightmap; spatial hash |
| Physics step (Pymunk) | ~300 μs | Fixed timestep; sleep inactive bodies |
| Secondary motion | ~50 μs | Simple spring math |
| Render transform calc | ~100 μs | Precompute static offsets |
| **Total** | **~800 μs** | **OK untuk 10 creatures @ 60 FPS (8ms)** |

**LOD System:**
- Distance > 800px: IK iter=4, no secondary motion, no foot placement search
- Distance > 1600px: Frozen pose, only body transform
- Off-screen: Physics sleep, no IK

---

## 14. DEBUG / VISUALIZATION TOOLS (Wajib untuk Development)

```python
# Debug draw flags (toggle via key)
DEBUG_DRAW = {
    "ik_targets": True,           # Red crosses di foot targets
    "stance_locks": True,         # Green circles di locked feet
    "support_polygon": True,      # Yellow polygon
    "com_projection": True,       # Blue dot
    "joint_angles": True,         # Angle values di joints
    "gait_phase": True,           # Phase bars per leg
    "raycasts": True,             # Foot placement rays
    "physics_forces": True,       # Force vectors di body
}
```

---

## 15. INTEGRATION POINTS (Noor v7 Codebase)

| System | File | Integration |
|--------|------|-------------|
| Config | `noor/config.py` | Tambah `CREATURE_*` constants, accessibility flags |
| Physics | `noor/systems/physics.py` | Extend `PhysicsSystem` dengan creature bodies |
| Entities | `noor/entities/monster.py` | Base class `ProceduralCreature` extends `Monster` |
| AI | `noor/systems/director.py` | Spawn dengan `CreatureDefinition` |
| Render | `noor/gfx/cairo_utils.py` | Sprite atlas loading, modular render |
| RNG | `noor/core/rng.py` | Deterministic seed untuk gait phase, variation |
| Audio | `noor/audio/recipes.py` | Footstep sounds synced ke stance events |

---

## 16. ACCEPTANCE CRITERIA (Definition of Done)

### Minimum Viable (Phase 1-2)
- [ ] `CreatureDefinition` load dari JSON
- [ ] FABRIK solver works untuk 2-4 bone chain
- [ ] Gait generator: walk + trot, phase offsets correct
- [ ] Foot placement raycast di flat ground
- [ ] Stance lock — foot tidak slide
- [ ] Body physics movement (Pymunk) dengan leg forces
- [ ] Modular sprite render (torso + 4 legs)
- [ ] Deterministic: same seed = identical animation

### Polish (Phase 3-4)
- [ ] Gallop + climb gait
- [ ] Terrain adaptation (slopes, gaps, walls)
- [ ] Spine IK (body curve)
- [ ] Tail pendulum physics
- [ ] Neck/head look-at + stabilization
- [ ] Squash/stretch, breathing idle
- [ ] Gait transitions (blend 0.5s)
- [ ] Stumble/recovery behavior
- [ ] LOD system (3 tiers)
- [ ] Accessibility flags respected

### Visual Quality (Subjective — "Alive Feel")
- [ ] Weight transfer terlihat (body compress/extend per step)
- [ ] Head stays stable saat body bergerak (stabilization)
- [ ] Tail counter-balance saat turn/stop
- [ ] Feet "search" terrain sebelum commit (compliance spring)
- [ ] No IK pop saat gait transition
- [ ] Creature reacts to push/impulse (physics-driven)
- [ ] Idle breathing + occasional blink + weight shift

---

## 17. FILE STRUCTURE (Target)

```
src/procedural-generation/prc-animation/
├── README.md                    # This file
├── creature_definition.py       # Dataclasses + JSON loader
├── gait_generator.py            # Phase-based gait + transitions
├── foot_placement.py            # Raycast search + compliance spring
├── ik_solver.py                 # FABRIK + joint limits
├── secondary_chains.py          # Spine, tail, neck, head IK
├── physics_integration.py       # Pymunk body + leg forces
├── secondary_motion.py          # Squash/stretch, breathing, sway
├── render_system.py             # Modular sprite transforms + z-sort
├── creature_controller.py       # Main update loop, ties all together
├── debug_draw.py                # Visualization tools
├── lod_system.py                # Distance-based simplification
├── variations.py                # Species presets (lizard, scavenger, vulture, etc.)
└── tests/
    ├── test_ik_solver.py
    ├── test_gait_generator.py
    ├── test_foot_placement.py
    └── test_integration.py
```

---

## 18. REFERENSI TEKNIS (Untuk Implementasi)

| Topic | Source |
|-------|--------|
| Rain World Animation GDC | "Procedural Animation in Rain World" — James Primate (YouTube) |
| FABRIK Paper | Aristidou & Lasenby, "FABRIK: A fast, iterative solver for IK" (2011) |
| Quadruped Gait | Van de Panne, "Procedural Animation for Quadrupeds" (SIGGRAPH) |
| Spring-Damper IK | Robotics literature: "Compliant IK via Virtual Springs" |
| Pymunk Constraints | `DampedSpring`, `PivotJoint`, `SlideJoint` docs |
| Modular 2D Animation | Spine/Unity 2D Animation workflow (sprite pieces + bone hierarchy) |

---

## 19. CATATAN KHUSUS UNTUK NOOR

1. **Sanity System Integration:** Sanity level → creature behavior weight
   - Low sanity: creature lebih agresif, gait lebih erratic (phase jitter), visual glitch (sprite corruption)
   - High sanity: creature lebih passive, gait smooth

2. **Fragment Collection:** Creature drop fragment saat "defeated" (bukan killed — Noor tidak punya combat tradisional)

3. **Cutscene Creatures:** Beberapa creature scripted (prologue, ending) — pakai `CreatureDefinition` tapi `AIController` diganti `CutsceneController`

4. **Determinism:** Semua random (variation, blink, breath phase) pakai `noor.core.rng.RNG` dengan seed per-creature

5. **Accessibility:** `reduce_motion` → disable squash/stretch, breathing, tail sway, head bob, gait blend smoothing

---

## 20. NEXT STEPS UNTUK OPENCODE

1. **Start Phase 1:** `creature_definition.py` + `ik_solver.py` (FABRIK) + basic test
2. **Verify:** Debug draw IK targets, joint angles, convergence
3. **Phase 2:** `gait_generator.py` + `foot_placement.py` di flat ground
4. **Verify:** Creature berjalan di flat terrain, stance lock works, no foot slide
5. **Iterate** ke Phase 3-4 sesuai acceptance criteria

**Pertanyaan sebelum mulai:**
- Sprite atlas format sudah ditentukan? (pycairo vector → rasterize at load?)
- `noor/systems/physics.py` sudah wrapper Pymunk — extend atau buat baru?
- Creature definition JSON location: `data/creatures/`?
- Max creature count simultaneous untuk perf budget?

---

**End of Spec — Ready for Implementation**