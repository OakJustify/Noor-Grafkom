# Procedural Creature Generation — Module Spec

**Target:** Rain World–style procedural creatures untuk game Noor (2D side-scroller)
**Integrasi:** `src/procedural-generation/prc-animation/` (procedural animation), `noor/systems/director.py` (spawn), `noor/audio/recipes.py` (procedural audio)
**Deterministic seed:** 42 (shared dengan semua sistem)

---

## 1. ARSITEKTUR — Creature Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   CREATURE ARCHETYPE DEFINITION                  │
│  (JSON: body_plan, behavior_archetype, size_class, stage_affinity)│
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MORPHOLOGY GENERATOR                          │
│  - Body plan → limb config (count, type, segments, proportions) │
│  - Size class → scale, mass, segment lengths                    │
│  - Variation params → asymmetry, mutation, sanity corruption    │
│  - Output: CreatureDefinition (compatible dengan prc-animation) │
└─────────────────────────────┬───────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────┐ ┌─────────────────────┐
│ BEHAVIOR GENERATOR  │ │ AUDIO GEN   │ │ VISUAL TRAITS GEN   │
│ - State machine     │ │ - Vocalizations│ │ - Color palette     │
│ - Transition rules  │ │   from morphology│ │ - Pattern/procedural │
│ - Sanity modulation │ │ - Footsteps   │ │   texture (pycairo) │
│ - Ecology params    │ │ - Breath/heart│ │ - Glitch variants   │
└─────────────────────┘ └─────────────┘ └─────────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CREATURE INSTANCE (Runtime)                   │
│  - SpawnDirector integration                                     │
│  - ProceduralAnimationController (prc-animation)                │
│  - AudioManager integration                                      │
│  - SanitySystem reactivity                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. BODY PLANS (Morphology Archetypes)

| Body Plan | Limb Config | Locomotion | Contoh Creature |
|-----------|-------------|------------|-----------------|
| **QUADRUPED** | 4 legs (FL,FR,RL,RR), tail, neck, head | Walk/trot/gallop | Lizard, Scavenger, Dog-like |
| **BIPED** | 2 legs, 2 arms, torso, head | Walk/run, climb | Humanoid, Bird-like |
| **HEXAPOD** | 6 legs (3 pairs), optional tail | Wave gait, climb | Insect, Spider, Centipede |
| **SERPENTINE** | 0 legs, segmented body (8-20 seg), head | Lateral undulation, sidewind | Snake, Worm, Eel |
| **FLOATING** | 0 legs, core + tendrils/wisps, gas sac | Buoyancy + thrust | Jellyfish, Gasbag, Spirit |
| **MULTI-LIMBED** | 4-8 legs + 2-4 arms, heavy torso | Slow walk, climb, grab | Crab, Multi-armed horror |
| **WINGED** | 2 wings + 2 legs, light torso | Flight, glide, perch | Bat, Bird, Moth |
| **AMORPHOUS** | Pseudopods (3-6), no fixed skeleton | Flow, ooze, split/merge | Slime, Blob, Shadow |

### 2.1 Body Plan → Limb Mapping (Generator Rules)

```python
BODY_PLAN_LIMBS = {
    "quadruped": {
        "legs": 4, "leg_segments": 3, "leg_type": "leg",
        "tail": True, "tail_segments": 4,
        "neck": True, "neck_segments": 2,
        "head": True,
        "gaits": ["walk", "trot", "gallop", "climb"]
    },
    "biped": {
        "legs": 2, "leg_segments": 3, "leg_type": "leg",
        "arms": 2, "arm_segments": 3, "arm_type": "arm",
        "tail": False,
        "neck": True, "neck_segments": 2,
        "head": True,
        "gaits": ["walk", "run", "climb", "crouch"]
    },
    "hexapod": {
        "legs": 6, "leg_segments": 3, "leg_type": "leg",
        "tail": True, "tail_segments": 3,
        "neck": False,
        "head": True,
        "gaits": ["wave", "tripod", "ripple", "climb"]
    },
    "serpentine": {
        "legs": 0,
        "body_segments": (8, 20),  # range
        "head": True,
        "gaits": ["undulate", "sidewind", "concertina", "swim"]
    },
    "floating": {
        "legs": 0,
        "tendrils": (3, 8), "tendril_segments": (2, 5),
        "core": True,
        "gaits": ["drift", "pulse", "jet", "tether"]
    },
    "multi_limbed": {
        "legs": (4, 8), "leg_segments": 3,
        "arms": (2, 4), "arm_segments": 3,
        "tail": True, "tail_segments": 3,
        "neck": True, "neck_segments": 2,
        "head": True,
        "gaits": ["walk", "scuttle", "climb", "grapple"]
    },
    "winged": {
        "legs": 2, "leg_segments": 2,
        "wings": 2, "wing_segments": 3,
        "tail": True, "tail_segments": 3,
        "neck": True, "neck_segments": 2,
        "head": True,
        "gaits": ["walk", "hop", "flight", "glide", "perch"]
    },
    "amorphous": {
        "pseudopods": (3, 6), "pod_segments": (2, 4),
        "core": True,
        "gaits": ["flow", "ooze", "split", "merge", "extend"]
    }
}
```

---

## 3. SIZE CLASSES (Scaling Parameters)

| Size Class | Mass Range | Body Length | Leg Length Mult | Step Height | Speed Mult | Audio Pitch |
|------------|------------|-------------|-----------------|-------------|------------|-------------|
| **TINY** | 0.5-2 kg | 20-40 px | 0.3-0.5× | 4-8 px | 0.5-0.8× | +2 octaves |
| **SMALL** | 2-10 kg | 40-80 px | 0.5-0.8× | 8-16 px | 0.8-1.2× | +1 octave |
| **MEDIUM** | 10-40 kg | 80-160 px | 0.8-1.2× | 16-32 px | 1.0× | base |
| **LARGE** | 40-150 kg | 160-300 px | 1.2-1.8× | 32-60 px | 0.7-1.0× | -1 octave |
| **HUGE** | 150-500 kg | 300-500 px | 1.5-2.5× | 50-100 px | 0.4-0.7× | -2 octaves |

**Scaling Formulas:**
```python
def scale_creature(base_def, size_class):
    scale = SIZE_SCALE[size_class]  # 0.5, 0.75, 1.0, 1.5, 2.5
    base_def.body["mass"] *= scale ** 3
    base_def.body["width"] *= scale
    base_def.body["height"] *= scale
    for limb in base_def.limbs:
        for seg in limb.segments:
            seg.length *= scale
        limb.anchor *= scale
        if limb.nominal_offset:
            limb.nominal_offset *= scale
    # Gait params
    for gait in base_def.gaits.values():
        gait.max_step_length *= scale
        gait.step_height *= scale
        gait.speed_range = (gait.speed_range[0]*scale, gait.speed_range[1]*scale)
    # Audio
    base_def.audio["base_pitch"] *= 2 ** SIZE_PITCH_SHIFT[size_class]
    return base_def
```

---

## 4. BEHAVIORAL ARCHETYPES (AI Personality)

| Archetype | Core Drive | State Priority | Social | Sanity Reaction |
|-----------|------------|----------------|--------|-----------------|
| **PREDATOR** | Hunt/eat | chase > patrol > investigate > feed | Solitary/territorial | Lebih agresif, chase longer |
| **PREY** | Survive | flee > hide > feed > patrol | Herd/flock | Panik lebih cepat, flock tighter |
| **SCAVENGER** | Opportunistic | investigate > feed > patrol > flee | Loose groups | Bold saat sanity rendah, steal fragments |
| **TERRITORIAL** | Defend area | patrol > threaten > chase > return | Solitary/pair | Territory expands saat sanity rendah |
| **CURIOUS** | Investigate | investigate > follow > play > flee | Social | Approach player, mimic sounds |
| **PARASITIC** | Attach/feed | attach > feed > detach > hide | Host-dependent | Attach ke player (sanity drain) |
| **GUARDIAN** | Protect | patrol > intercept > defend > return | Pack | Protect fragments/areas |
| **AMBUSH** | Wait/strike | hide > wait > strike > retreat | Solitary | Lebih lama hide, strike harder |

### 4.1 State Machine per Archetype (Base States + Archetype-Specific)

```
BASE STATES (all creatures):
  IDLE → PATROL → INVESTIGATE → CHASE → FLEE → FEED → REST → SLEEP
  ↓         ↓           ↓           ↓       ↓      ↓      ↓      ↓
  |         |           |           |       |      |      |      |
  └─────────┴───────────┴───────────┴───────┴──────┴──────┴──────┘
                    │
                    ▼
         ARCHETYPE-SPECIFIC STATES:
         PREDATOR: STALK, AMBUSH, KILL, DRAG
         PREY:     HIDE, HERD, ALARM, STAMPEDE
         SCAVENGER: STEAL, HOARD, BARTER, SCRAP
         TERRITORIAL: MARK, THREATEN, ESCORT, SIEGE
         CURIOUS:  MIMIC, PLAY, FOLLOW, GIFT
         PARASITIC: ATTACH, DRAIN, LAY_EGGS, DETACH
         GUARDIAN: INTERCEPT, SHIELD, CALL, RALLY
         AMBUSH:   CAMOUFLAGE, LURE, STRIKE, RETREAT
```

### 4.2 Transition Rules (Utility-Based)

```python
@dataclass
class TransitionRule:
    from_state: str
    to_state: str
    condition: Callable[[Creature, World], bool]
    priority: int
    cooldown: float = 0.0

# Example: Predator
PREDATOR_TRANSITIONS = [
    TransitionRule("patrol", "stalk", lambda c,w: w.player_in_sight(c) and c.hunger > 0.5, 10),
    TransitionRule("stalk", "chase", lambda c,w: w.player_detected(c) and c.distance_to_player < 200, 20),
    TransitionRule("chase", "pounce", lambda c,w: c.distance_to_player < 50 and c.can_pounce, 30),
    TransitionRule("chase", "patrol", lambda c,w: c.distance_to_player > 500 or c.stamina < 0.2, 5),
    TransitionRule("feed", "rest", lambda c,w: c.hunger < 0.2, 10),
    # Sanity-modulated
    TransitionRule("patrol", "investigate", lambda c,w: w.sanity < 40 and random() < 0.01, 3),
]
```

### 4.3 Sanity Modulation (Critical untuk Noor)

```python
SANITY_BEHAVIOR_MODS = {
    # sanity_threshold: {archetype: {stat_modifiers}}
    75: {  # Early stage - subtle
        "predator": {"aggression": 1.1, "patrol_range": 1.2},
        "prey":     {"skittishness": 1.1, "herd_cohesion": 1.2},
        "scavenger": {"boldness": 1.1},
    },
    50: {  # Mid stage - noticeable
        "predator": {"aggression": 1.5, "chase_duration": 2.0, "pack_hunt": True},
        "prey":     {"panic_threshold": 0.5, "flee_distance": 2.0},
        "scavenger": {"steal_fragments": True, "approach_player": 0.3},
        "territorial": {"territory_size": 2.0, "threaten_player": True},
    },
    25: {  # Late stage - extreme
        "predator": {"aggression": 3.0, "ignore_stun": True, "spawn_minions": True},
        "prey":     {"mutate": True, "become_predator": 0.1},
        "curious":  {"mimic_player": True, "hallucinate": True},
        "parasitic": {"attach_player": True, "sanity_drain": 5},
    },
    0: {   # Zero sanity - nightmare
        "all": {"visual_corruption": True, "audio_distortion": True,
                "physics_glitch": True, "reality_break": True}
    }
}
```

---

## 5. PROCEDURAL AUDIO GENERATION (Per Creature)

Menggunakan `noor/audio/synth.py` + `recipes.py` sebagai base. Setiap creature generate suara unik dari morfologi.

### 5.1 Vocalization Parameters dari Morphology

```python
@dataclass
class VocalParams:
    # Source characteristics
    fundamental_freq: float      # Hz, dari mass & size
    formant_ratios: list[float]  # Resonance peaks (shape of vocal tract)
    breathiness: float           # 0-1, noise mix
    roughness: float             # 0-1, amplitude modulation
    # Behavioral
    call_types: dict[str, CallDef]  # "idle", "alert", "aggressive", "pain", "death"
    # Sanity corruption
    corruption_factor: float = 0.0  # 0-1, increases with low sanity

class CallDef:
    pattern: Literal["pulse", "trill", "scream", "chirp", "drone", "click"]
    duration_range: tuple[float, float]
    pitch_range: tuple[float, float]  # semitone offset from fundamental
    rhythm: Literal["regular", "irregular", "burst", "continuous"]
    harmonicity: float  # 0-1, how tonal vs noisy
```

### 5.2 Morphology → Vocal Mapping

| Morphology Trait | Audio Effect |
|------------------|--------------|
| Large mass + long neck | Low fundamental (40-80 Hz), rich formants |
| Small mass + short neck | High fundamental (400-1000 Hz), pure tone |
| Hollow body (floating) | Resonant, reverb-heavy, breathy |
| Rigid exoskeleton (hexapod) | Click/stridulation, rhythmic, percussive |
| Amorphous | Wet, squelchy, continuous texture |
| Multiple heads/necks | Polyphonic, chords, dissonance |

### 5.3 Footstep / Movement Audio

```python
def generate_footstep_sound(creature_def, gait, surface_type):
    # Mass → impact force → low freq thump
    mass = creature_def.body["mass"]
    leg_count = len([l for l in creature_def.limbs if l.type == "leg"])
    
    # Base thump
    thump_freq = 40 * (mass / 10) ** 0.33  # cube root scaling
    thump_dur = 0.05 * (mass / 10) ** 0.25
    
    # Surface modulation
    surface_params = {
        "stone": {"noise_amp": 0.4, "cutoff": 800, "decay": 0.08},
        "dirt":  {"noise_amp": 0.6, "cutoff": 400, "decay": 0.12},
        "metal": {"noise_amp": 0.3, "cutoff": 2000, "decay": 0.05, "ring": True},
        "flesh": {"noise_amp": 0.5, "cutoff": 300, "decay": 0.15, "wet": True},
        "void":  {"noise_amp": 0.2, "cutoff": 150, "decay": 0.3, "reverb": 3.0}
    }
    
    # Gait rhythm → step interval
    step_interval = 1.0 / gait.frequency  # dari gait generator
    
    return procedural_hit(thump_freq, thump_dur, surface_params[surface_type])
```

### 5.4 Breathing / Heartbeat / Idle Loops

```python
def generate_idle_loop(creature_def, sanity_level):
    # Breathing rate dari metabolic rate (mass^-0.25)
    breath_rate = 0.5 * (creature_def.body["mass"] / 10) ** -0.25
    # Heart rate ~ 60-180 BPM scaled
    heart_rate = 120 * (creature_def.body["mass"] / 10) ** -0.25
    
    # Sanity corruption: irregular rhythm, added harmonics
    if sanity_level < 50:
        breath_rate *= 1.0 + (50 - sanity_level) / 100 * 0.5
        # Add subharmonic "wheeze"
    
    return mix(
        generate_breathing(breath_rate, creature_def.vocal.breathiness),
        generate_heartbeat(heart_rate / 60, creature_def.vocal.roughness),
        generate_micro_vocalizations(creature_def.vocal.call_types["idle"])
    )
```

### 5.5 Audio Cache Strategy (Generate Once on Spawn)

```python
@dataclass
class AudioCache:
    vocalizations: dict[str, np.ndarray]      # "idle", "alert", "aggressive", "pain", "death"
    footsteps: dict[str, np.ndarray]          # per surface type
    idle_loop: np.ndarray                     # breathing + heartbeat + micro-vocal
    metadata: dict                            # seed, archetype, size_class, stage, duration

def generate_creature_audio(creature_def: CreatureDefinition, stage: int) -> AudioCache:
    \"\"\"Generate all audio for a creature instance. Called ONCE on spawn.\"\"\"
    cache_key = (creature_def.seed, creature_def.archetype, creature_def.size_class, stage)
    
    if cache_key in GLOBAL_AUDIO_CACHE:
        return GLOBAL_AUDIO_CACHE[cache_key]
    
    # Generate all variants
    vocalizations = {}
    for call_type, call_def in creature_def.vocal.call_types.items():
        vocalizations[call_type] = synthesize_vocalization(creature_def.vocal, call_def, stage)
    
    footsteps = {}
    for surface in ["stone", "dirt", "metal", "flesh", "void"]:
        footsteps[surface] = generate_footstep_sound(creature_def, creature_def.gaits["walk"], surface)
    
    idle_loop = generate_idle_loop(creature_def, get_sanity_level(stage))
    
    cache = AudioCache(
        vocalizations=vocalizations,
        footsteps=footsteps,
        idle_loop=idle_loop,
        metadata={"seed": creature_def.seed, "archetype": creature_def.archetype,
                  "size_class": creature_def.size_class, "stage": stage}
    )
    
    GLOBAL_AUDIO_CACHE[cache_key] = cache
    return cache
```

**Runtime usage:**
```python
# Spawn time (once)
creature.audio_cache = generate_creature_audio(creature.morphology, current_stage)

# Every frame (near-zero cost)
if creature.state == "idle" and not audio_playing:
    audio_play(creature.audio_cache.idle_loop, loop=True)
if creature.animation.just_stepped:
    audio_play_one_shot(creature.audio_cache.footsteps[current_surface])
if creature.state == "alert" and just_transitioned:
    audio_play_one_shot(random_choice(creature.audio_cache.vocalizations["alert"]))
```

**Memory estimate:** ~500KB-2MB per unique creature type (cached), shared across instances.

---

## 6. VISUAL TRAITS GENERATION (pycairo)

### 6.1 Color Palette dari Archetype + Stage

```python
ARCHETYPE_PALETTES = {
    "predator":     {"base": (0.0, 0.1, 0.05), "accent": (0.9, 0.1, 0.1)},      # Dark green/red
    "prey":         {"base": (0.6, 0.5, 0.4), "accent": (0.3, 0.6, 0.9)},      # Tan/blue
    "scavenger":    {"base": (0.4, 0.3, 0.2), "accent": (0.8, 0.7, 0.2)},      # Brown/gold
    "territorial":  {"base": (0.2, 0.1, 0.3), "accent": (0.9, 0.4, 0.1)},      # Purple/orange
    "curious":      {"base": (0.5, 0.3, 0.6), "accent": (0.2, 0.8, 0.7)},      # Magenta/teal
    "parasitic":    {"base": (0.1, 0.05, 0.15), "accent": (0.6, 0.9, 0.3)},    # Dark/green
    "guardian":     {"base": (0.2, 0.4, 0.2), "accent": (1.0, 0.9, 0.3)},      # Green/gold
    "ambush":       {"base": (0.05, 0.05, 0.1), "accent": (0.7, 0.1, 0.5)},    # Near black/magenta
}

STAGE_PALETTE_SHIFT = {
    1: {"saturation": 0.8, "value": 0.9, "hue_shift": 0.0},      # Normal
    2: {"saturation": 0.6, "value": 0.7, "hue_shift": 0.02},     # Desaturated, slight shift
    3: {"saturation": 0.4, "value": 0.5, "hue_shift": 0.05},     # Muted, shifted
    4: {"saturation": 0.2, "value": 0.3, "hue_shift": 0.1},      # Near grayscale, heavy shift
}
```

### 6.2 Procedural Patterns (pycairo shaders)

```python
def generate_body_texture(creature_def, stage, seed):
    rng = Random(seed)
    pattern_type = rng.choice(["scales", "fur", "skin", "chitin", "slime", "feathers", "shadow"])
    
    if pattern_type == "scales":
        return cairo_scale_pattern(creature_def, rng)
    elif pattern_type == "fur":
        return cairo_fur_pattern(creature_def, rng)
    # ... etc
    
    # Sanity corruption overlay
    if stage >= 3:
        return apply_glitch_overlay(base_texture, stage, rng)
```

### 6.3 Glitch Variants (Sanity-Dependent)

| Sanity Stage | Visual Corruption |
|--------------|-------------------|
| 75-100 | Normal |
| 50-75 | Occasional sprite flicker, color shift |
| 25-50 | Texture tearing, extra limbs flicker, eye multiplication |
| 0-25 | Geometry distortion, vertex displacement, reality tears |
| 0 | Complete visual breakdown, placeholder shapes |

---

## 7. ECOLOGY & SPAWN SYSTEM (Integration dengan SpawnDirector)

### 7.1 Population Dynamics

```python
@dataclass
class PopulationParams:
    carrying_capacity: int           # Max per region
    reproduction_rate: float         # Offspring per cycle
    mortality_rate: float            # Natural death
    territory_size: float            # px radius
    food_preference: list[str]       # "player", "prey", "fragments", "plants"
    social_structure: Literal["solitary", "pair", "pack", "herd", "swarm", "colony"]
    activity_cycle: Literal["diurnal", "nocturnal", "crepuscular", "random"]
```

### 7.2 Spawn Director Integration

```python
class ProceduralSpawnDirector(SpawnDirector):
    def __init__(self, stage, sanity, seed, region_ecology):
        super().__init__(stage, sanity, seed)
        self.ecology = region_ecology
        self.populations = {archetype: PopulationParams(...) for archetype in ARCHETYPES}
    
    def request_spawn(self, x, player_x, archetype_hint=None):
        # 1. Check population caps per archetype
        # 2. Select archetype based on ecology weights + sanity
        # 3. Generate creature instance (morphology + behavior + audio)
        # 4. Validate spawn position (territory, food sources, player distance)
        # 5. Return CreatureInstance dengan all systems wired
```

### 7.3 Sanity-Driven Ecology Shifts

| Sanity | Ecology Change |
|--------|----------------|
| >75 | Normal distribution, stable populations |
| 50-75 | Predators increase, prey decrease, scavengers bold |
| 25-50 | Territorial expand, parasitic appear, curious→aggressive |
| <25 | Mass mutation, impossible hybrids, reality-glitched spawns |
| 0 | Only "Void" archetype spawns, infinite variations |

---

## 8. CREATURE INSTANCE — Runtime Object

```python
@dataclass
class CreatureInstance:
    # Identity
    id: str
    seed: int                    # Deterministic per instance
    archetype: str
    body_plan: str
    size_class: str
    stage_spawned: int
    
    # Generated Definitions (immutable after spawn)
    morphology: CreatureDefinition      # → prc-animation
    behavior: BehaviorDefinition        # State machine, transitions
    audio: AudioDefinition              # Vocal, footsteps, idle loops
    visual: VisualDefinition            # Palette, pattern, glitch params
    
    # Runtime State (mutable)
    position: Vec2
    velocity: Vec2
    state: str                       # Current behavior state
    state_timer: float
    health: float
    stamina: float
    hunger: float
    sanity_corruption: float         # 0-1, increases over time at low sanity
    
    # System References
    animation_controller: ProceduralAnimationController
    audio_sources: dict[str, AudioSource]
    
    # Ecology
    territory_center: Vec2
    known_entities: set[str]         # Other creature IDs
    memory: dict                     # Fragment locations, player sightings
```

---

## 9. INTEGRATION POINTS (Noor v7 Codebase)

| System | File | Integration Method |
|--------|------|-------------------|
| **Animation** | `src/procedural-generation/prc-animation/` | `CreatureDefinition` output → `ProceduralAnimationController` |
| **Spawn** | `noor/systems/director.py` | Extend `SpawnDirector` → `ProceduralSpawnDirector` |
| **Entities** | `noor/entities/monster.py` | Replace `Monster` dengan `CreatureInstance` wrapper |
| **Audio** | `noor/audio/recipes.py`, `synth.py` | Add `generate_creature_audio()` functions |
| **Visuals** | `noor/gfx/cairo_utils.py`, `assets.py` | Add procedural texture generation |
| **Sanity** | `noor/systems/sanity.py` | Hook `sanity_corruption` updates per creature |
| **Glitch** | `noor/systems/glitch.py` | Creature visual/audio glitch tied to global glitch system |
| **Fragments** | `noor/systems/fragments.py` | Creatures drop/guard fragments based on archetype |
| **Levels** | `data/levels/*.json` | Region ecology definitions per level |
| **RNG** | `noor/core/rng.py` | Deterministic seeds per creature instance |

---

## 10. DATA FILES (JSON Definitions)

### 10.1 Creature Archetypes: `data/creatures/archetypes.json`
```json
{
  "predator": {
    "base_drives": ["hunt", "territory", "dominance"],
    "state_priorities": ["chase", "stalk", "patrol", "feed", "rest"],
    "social": "solitary",
    "sanity_mods": { "50": {"aggression": 1.5}, "25": {"aggression": 3.0} },
    "palette": "predator",
    "vocal_profile": "deep_terrestrial",
    "population": { "carrying_capacity": 3, "territory_size": 800 },
    "is_cutscene": false
  },
  ...
}
```

### 10.2 Body Plans: `data/creatures/body_plans.json`
```json
{
  "quadruped": {
    "limbs": { "legs": 4, "leg_segments": 3, "tail_segments": 4, "neck_segments": 2 },
    "gaits": ["walk", "trot", "gallop", "climb"],
    "size_range": ["tiny", "small", "medium", "large"],
    "archetype_affinity": ["predator", "prey", "territorial", "guardian"]
  },
  ...
}
```

### 10.3 Region Ecology: Extend `data/levels/*.json` (existing files)
Tambahkan field `ecology` ke level JSON yang sudah ada (contoh `prolog.json`):

```json
{
  "id": "prolog",
  "stage": 1,
  "...": "...",
  "ecology": {
    "biome": "ruined_hospital",
    "archetype_weights": { "scavenger": 0.4, "predator": 0.2, "curious": 0.2, "parasitic": 0.2 },
    "population_caps": { "total": 8, "per_archetype": { "predator": 2 } },
    "food_sources": ["fragments", "rats", "mold"],
    "sanity_modifiers": { "predator_aggression": 1.2 },
    "activity_cycle": "nocturnal"
  }
}
```

---

## 11. ACCEPTANCE CRITERIA

### Phase 1: Core Generation (Data-Driven)
- [ ] `CreatureArchetype`, `BodyPlan`, `SizeClass` dataclasses + JSON loader
- [ ] `MorphologyGenerator` → outputs valid `CreatureDefinition` (prc-animation compatible)
- [ ] All 8 body plans generate correct limb configs
- [ ] Size scaling works (mass, dimensions, gait params, audio pitch)
- [ ] Deterministic: same seed = identical creature definition

### Phase 2: Behavior System
- [ ] `BehaviorDefinition` with utility-based state machine
- [ ] 8 archetypes with distinct transition rules
- [ ] Sanity modulation hooks functional
- [ ] Integration dengan `SpawnDirector` (spawn archetype-appropriate creatures)

### Phase 3: Audio Generation
- [ ] `VocalParams` dari morphology (mass, size, body plan)
- [ ] Procedural vocalizations per call type (idle, alert, aggressive, pain, death)
- [ ] Footstep sounds dari gait + mass + surface
- [ ] Idle loops (breathing, heartbeat, micro-vocalizations)
- [ ] **Audio cache on spawn** — generate once, reuse untuk session
- [ ] Sanity corruption on audio (pitch drift, added noise, rhythm break)

### Phase 4: Visual Traits
- [ ] Palette generation dari archetype + stage
- [ ] Procedural texture patterns (pycairo) per body plan
- [ ] Glitch variants per sanity stage
- [ ] Integration dengan `prc-animation` render system

### Phase 5: Ecology & Polish
- [ ] Population dynamics per region
- [ ] Territory, social structure, activity cycles
- [ ] Sanity-driven ecology shifts
- [ ] Fragment interaction (guard, drop, steal)
- [ ] **LOD System:**
  - Near (< 500px): Full animation, behavior, audio, visual
  - Mid (500-1500px): Simplified animation, behavior active, audio low-fi, visual reduced
  - Far (> 1500px): Position only, no animation, no audio, sprite billboard
  - Off-screen (> 2000px): Frozen state, despawn setelah timeout
- [ ] **Creature Limits:**
  - `GLOBAL_ENTITY_CAP` (config): 20 active entities
  - Simultaneous rendered: 20-30 dengan LOD
  - Total alive in level: 50-100 (banyak frozen off-screen)
- [ ] Performance: 20+ creatures @ 60 FPS dengan LOD
- [ ] **Cutscene creatures:** `is_cutscene` flag di archetype, spawn via trigger, scripted behavior

---

## 12. FILE STRUCTURE (Target)

```
src/procedural-generation/prc-creature/
├── README.md                          # This file
├── archetype_definition.py            # Archetype, BodyPlan, SizeClass dataclasses
├── morphology_generator.py            # Body plan → CreatureDefinition
├── behavior_generator.py              # Archetype → BehaviorDefinition (state machine)
├── audio_generator.py                 # Morphology → AudioDefinition (vocal, footsteps, idle)
├── visual_generator.py                # Archetype+Stage → VisualDefinition (palette, pattern)
├── ecology.py                         # Population, territory, spawn logic
├── creature_instance.py               # Runtime CreatureInstance class
├── spawn_director.py                  # ProceduralSpawnDirector extends SpawnDirector
├── sanity_integration.py              # Sanity modulation hooks
├── data_loader.py                     # Load archetypes, body_plans, ecology from JSON
├── variations.py                      # Mutation, hybrid, glitch variant generators
└── tests/
    ├── test_morphology.py
    ├── test_behavior.py
    ├── test_audio.py
    ├── test_visual.py
    └── test_integration.py
```

---

## 13. REFERENSI TEKNIS

| Topic | Source |
|-------|--------|
| Rain World Creature Design | "The Ecology of Rain World" — James Primate (blog/video) |
| Utility AI for Creatures | "Behavior Trees vs Utility AI" — Game AI Pro |
| Procedural Audio Synthesis | "Real Sound Synthesis for Interactive Applications" — Perry Cook |
| Morphology-Locomotion Coupling | "Evolving Virtual Creatures" — Karl Sims (SIGGRAPH 1994) |
| Pycairo Procedural Textures | Cairo docs: mesh gradients, patterns, surface sampling |
| Deterministic Procgen | "Procedural Generation in Spelunky" — Derek Yu |

---

## 14. CATATAN KHUSUS UNTUK NOOR

1. **Sanity as Core Driver:** Creature behavior, appearance, audio **semua** bereaksi ke sanity global & lokal. Ini bukan cosmetic — itu *mechanic*.

2. **Fragment Economy:** Creatures bukan cuma enemy — mereka *part of fragment loop*. Scavengers steal, Guardians protect, Parasites drain sanity via fragments.

3. **No Combat System:** Player tidak "fight" creatures. Interactions: avoid, distract, lure, hide, use flare, close lantern. Creature AI designed untuk *interaction possibilities*, bukan combat balance.

4. **Cutscene Creatures:** Beberapa creature hand-authored untuk narrative beats (prologue, chapter transitions, ending). Generator dipakai untuk *ambient/emergent* population.

5. **Accessibility:** `reduce_motion` → simpler visual patterns, no glitch overlay. `reduce_loud` → creature audio volume capped, no sudden screams.

---

## 15. NEXT STEPS UNTUK OPENCODE

1. **Phase 1 Start:** `archetype_definition.py` + `morphology_generator.py` + JSON data files
2. **Verify:** Generated `CreatureDefinition` loads di `prc-animation` test
3. **Phase 2:** `behavior_generator.py` + `spawn_director.py` integration
4. **Phase 3:** `audio_generator.py` — test dengan `noor/audio/synth.py`
5. **Phase 4:** `visual_generator.py` — pycairo patterns
6. **Iterate** full integration di `GameplayScene`

**Pertanyaan sebelum mulai:**
- Region ecology per level: `data/levels/*/ecology.json` baru atau extend level JSON existing?
- Creature instance limit simultaneous untuk perf? (target 20?)
- Cutscene creature definitions: separate file atau flag di archetype?
- Audio streaming vs pre-generated: creatures generate audio on-spawn (cached) atau pre-bake?

---

**End of Spec — Procedural Creature Generation Ready for Implementation**