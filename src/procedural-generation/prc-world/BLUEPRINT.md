# prc-world — Procedural World Layout Blueprint

**Module**: `src/procedural-generation/prc-world/`  
**Seed**: 42 (deterministic across all subsystems)  
**Context**: 2D side-scroller "Noor" — horror/sanity decay, creature ecosystems, fragment collection  
**Cutscene arc** (asset names): `warmth` → `fractured` → `labyrinth` → `end`  

---

## 1. Arsitektur Tiga Lapisan (Three-Layer Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│ L3 — Presentation Layer                                     │
│   Parallax backgrounds  │  Color grading (biome + sanity)   │
│   Weather / fog / glitch overlay  │  Shader sanity effects  │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ L2 — Level / Terrain Layer (in-level generation)            │
│   Heightmap + platform layers  │  Biome decor & props       │
│   Cave / depth layer  │  Fragment placement  │  Spawn points │
│   Sanity corruption morph (stage 1→4)                       │
└─────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────┐
│ L1 — World / Zone Layer (overworld progression)             │
│   Ordered zones (left→right)  │  Biome per zone             │
│   Sanity threshold gates  │  Landmark placement              │
│   Faction / territory map  │  Progression unlock logic       │
└─────────────────────────────────────────────────────────────┘
```

**Data flow** (deterministic, single seed → derived seeds):
```
seed=42
  ├─ zone_seed      = hash(seed, "zone")      → L1 zone sequence
  ├─ terrain_seed   = hash(seed, "terrain")   → L2 heightmap per zone
  ├─ decor_seed     = hash(seed, "decor")     → L2 props/fragments
  ├─ palette_seed   = hash(seed, "palette")   → L3 color grading
  ├─ weather_seed   = hash(seed, "weather")   → L3 particles/fog
  └─ sanity_seed    = hash(seed, "sanity")    → sanity curve param
```

---

## 2. L1 — World / Zone Layer

### 2.1 Zone Definition

```python
@dataclass
class WorldZone:
    zone_id: str                    # e.g., "zone_01_warmth_entry"
    biome: BiomeType                # determines creature palette, decor, palette
    x_range: Tuple[float, float]    # world-space horizontal span (meters)
    sanity_threshold: float         # world_sanity must be ≤ this to unlock
    landmark: Optional[Landmark]    # hero moment (see §2.4)
    territory_center: Vec2          # for population_manager territory logic
    difficulty_tier: int            # 1–4, maps to creature archetype weighting
    fragment_density: float         # fragments per 100m
    connecting_zone_ids: List[str]  # for branching (future)
```

### 2.2 Biome Types (adapted for 2D side-scroller)

| BiomeType | Visual Theme | Base Temp | Base Moisture | Creature Affinity | Sanity Morph Target |
|-----------|-------------|-----------|---------------|-------------------|---------------------|
| `SAFE_HAVEN` | Warmth — soft light, gentle slopes | 22°C | 600mm | `gentle_light`, `prey`, `curious` | `FRACTURED_GROVE` |
| `TEMPERATE_GROVE` | Lush forest, dappled light | 18°C | 800mm | `prey`, `scavenger`, `territorial` | `FRACTURED_GROVE` |
| `ARID_CANYON` | Dry rock, harsh shadows | 28°C | 200mm | `predator`, `ambush`, `void_walker` | `FRACTURED_WASTE` |
| `SWAMP_MIRE` | Waterlogged, fog, slow movement | 20°C | 1500mm | `parasitic`, `scavenger`, `curious` | `LABYRINTH_MIRE` |
| `BOREAL_TAIGA` | Coniferous, cold, long shadows | 5°C | 700mm | `predator`, `guardian`, `territorial` | `LABYRINTH_TAIGA` |
| `VOID_RUINS` | Ancient geometry, floating debris | — | — | `void_walker`, `ambush`, `guardian` | `END_VOID` |
| `FRACTURED_GROVE` | (Stage 2) Cracked earth, bleeding light | — | — | `void_walker`, `parasitic` | `LABYRINTH_*` |
| `FRACTURED_WASTE` | (Stage 2) Shattered rock, void dust | — | — | `ambush`, `void_walker` | `LABYRINTH_*` |
| `LABYRINTH_MIRE` | (Stage 3) Impossible geometry, mirror water | — | — | `void_walker`, `parasitic` | `END_VOID` |
| `LABYRINTH_TAIGA` | (Stage 3) Frozen maze, inverted trees | — | — | `guardian`, `void_walker` | `END_VOID` |
| `END_VOID` | (Stage 4) Pure abstraction, cutscene arena | — | — | `gentle_light` (scripted) | — |

**Note**: Base biomes (rows 1–6) exist at world_sanity ≥ 75. At sanity thresholds 50, 25, 0 they morph to their `Sanity Morph Target` via L2 corruption (see §3.4).

### 2.3 Default Zone Sequence (seed=42)

```
Zone 01: SAFE_HAVEN           [0–800m]      sanity≤100  tier=1  landmark=WARMTH_ALTAR
Zone 02: TEMPERATE_GROVE      [800–2200m]   sanity≤100  tier=1  landmark=OLD_OAK
Zone 03: ARID_CANYON          [2200–3800m]  sanity≤75   tier=2  landmark=SUN_DIAL
Zone 04: SWAMP_MIRE           [3800–5000m]  sanity≤75   tier=2  landmark=WEEPING_WILLOW
Zone 05: BOREAL_TAIGA         [5000–6500m]  sanity≤50   tier=3  landmark=FROZEN_SPIRE
Zone 06: VOID_RUINS           [6500–8000m]  sanity≤25   tier=4  landmark=SHATTERED_GATE
Zone 07: END_VOID             [8000–9000m]  sanity≤0    tier=4  landmark=FINAL_THRESHOLD (cutscene)
```

- **Progression gate**: Player must lower `world_sanity` (via fragment collection, boss encounters, scripted events) to unlock next zone.
- **Landmark**: Hero moment per zone — hand-placed unique structure/visual anchor (not procedural). Serves as navigation beacon and screenshot moment.
- **Territory center**: Feeds `PopulationManager` for creature spawn density.

### 2.4 Landmark System

```python
@dataclass
class Landmark:
    landmark_id: str
    landmark_type: LandmarkType   # ALTAR, SPIRE, GATE, TREE, RUIN, THRESHOLD
    world_pos: Vec2               # exact position (not procedural)
    unlock_sanity: float          # world_sanity at which landmark "activates"
    visual_state_per_sanity: Dict[int, LandmarkVisualState]  # 4 stages
    associated_cutscene: Optional[str]  # e.g., "warmth", "fractured"
```

**LandmarkVisualState** includes: sprite/texture override, particle emission, shader params, audio ambience.

---

## 3. L2 — Level / Terrain Layer

### 3.1 Heightmap Generation (per zone)

**Pipeline** (all deterministic from `terrain_seed`):

```
1. Base elevation (fBm, 6 octaves, lacunarity=2.0, gain=0.5)
   → scaled to zone biome: GROVE=±15m, CANYON=±60m, MIRE=±8m, TAIGA=±25m, RUINS=±40m

2. Ridge lines (ridged multifractal, 4 octaves) → mountain ridges, canyon walls
   → masked by biome: strong in CANYON/TAIGA/RUINS, weak in GROVE/MIRE

3. River / water paths (drainage simulation)
   - Seed water sources at high elevation
   - Flow downhill using gradient descent on heightmap
   - Accumulate flow; where flow > threshold → river channel carved into heightmap
   - MIRE biome: multiple shallow channels, swamp pooling

4. Platform layer extraction (for 2D side-scroller gameplay)
   - Sample heightmap at gameplay resolution (e.g., every 2m)
   - Convert to layered platforms: GROUND, MID, HIGH, CEILING
   - Platform width ∝ local flatness; gaps ∝ slope
   - Ensure connectivity: A* path from zone start to end on GROUND layer

5. Cave / depth layer (separate noise, triggered by CAVE mutator tag)
   - 3D noise (x, y, depth) → cavern carving
   - Entrances placed on GROUND layer where heightmap allows
   - Depth layers: SHALLOW (0–50m), DEEP (50–200m), ABYSS (200m+)
```

**Output**: `LevelTerrain` object with:
- `heightmap: Array[float]` (world_x → elevation)
- `platforms: List[Platform]` (x, y, width, layer_type, biome_decor_hint)
- `water_bodies: List[WaterBody]` (x_range, depth, flow_dir, biome_type)
- `cave_entrances: List[CaveEntrance]` (x, depth_layer, biome_type)
- `spawn_anchors: List[SpawnAnchor]` (x, y, archetype_weights, territory_id)

### 3.2 Biome Decor & Props

Per biome, a **decor palette** (loaded from JSON, deterministic placement via `decor_seed`):

| Biome | Foreground Props | Midground Silhouettes | Background Parallax |
|-------|------------------|----------------------|---------------------|
| SAFE_HAVEN | glowing flowers, soft grass, stone markers | gentle hills, distant trees | warm gradient sky, slow clouds |
| TEMPERATE_GROVE | ferns, fallen logs, mushroom clusters | dense trunks, canopy gaps | dappled light shafts, birds |
| ARID_CANYON | cracked earth, bleached bones, cacti | layered mesas, distant cliffs | harsh sun, heat shimmer |
| SWAMP_MIRE | reeds, lily pads, submerged roots | twisted mangroves, hanging moss | thick fog, fireflies |
| BOREAL_TAIGA | pine needles, frost crystals, icicles | conifer wall, northern lights | snow drift, aurora |
| VOID_RUINS | floating glyphs, broken arches, void dust | impossible geometry, fractured sky | deep space stars, slow rotation |

**Placement rules**:
- Poisson-disc sampling per platform segment (min distance = prop_size × 1.5)
- Density modulated by `fragment_density` (higher fragments → fewer decor)
- Sanity stage overrides: Stage 2+ adds `corruption_props` (cracks, void tendrils, bleeding light)

### 3.3 Fragment Placement

```python
@dataclass
class FragmentPlacement:
    fragment_type: FragmentType   # MEMORY, ESSENCE, SHARD, CORE
    world_pos: Vec2
    guardian_archetype: Optional[ArchetypeType]  # creature guarding it
    sanity_reward: float          # world_sanity reduction on collect
    required_ability: Optional[str]  # e.g., "double_jump", "void_walk"
```

- **Distribution**: 1 CORE per zone (at landmark), 2–3 SHARD, 5–8 ESSENCE, 10+ MEMORY
- **Pacing**: Increasing `sanity_reward` per zone; early zones give small drops, late zones large
- **Guardian**: Spawns creature from `PopulationManager` with `territory_center` at fragment pos

### 3.4 Sanity Corruption Morph (L2 → L3 bridge)

At each sanity threshold, the **same heightmap/platforms** are visually morphed:

| Stage | World Sanity | Visual Morph (applied in shader + decor override) |
|-------|--------------|---------------------------------------------------|
| 1 (Warmth) | 100–76 | Base biome palette. Gentle. No corruption. |
| 2 (Fractured) | 75–51 | **Cracks** in ground textures. **Color shift**: desaturate −30%, hue rotate toward purple/red. **Void dust** particles. Decor → `FRACTURED_*` variants. |
| 3 (Labyrinth) | 50–26 | **Geometry distortion**: platform positions jitter (shader vertex offset). **Mirror/invert** midground. **Impossible connections** (platforms link non-Euclid). Heavy fog. Audio: low-pass + reverb. |
| 4 (End) | 25–0 | **Abstraction**: textures → solid color fields + noise. Platforms → floating glyphs. Background → void shader. Only `gentle_light` entities remain. Cutscene trigger. |

**Implementation**: Single heightmap + 4 palette/shader param sets. No geometry regeneration — pure visual morph. Deterministic via `sanity_seed`.

---

## 4. L3 — Presentation Layer

### 4.1 Parallax Layer Stack (per biome)

```
Layer 0 (farthest):  Sky gradient + celestial bodies     → speed 0.05×
Layer 1:             Distant mountains / horizon         → speed 0.15×
Layer 2:             Midground silhouettes (trees, ruins) → speed 0.35×
Layer 3:             Foreground props (grass, particles)  → speed 0.65×
Layer 4 (gameplay):  Platforms, creatures, player        → speed 1.0×
Layer 5 (overlay):   Sanity glitch, vignette, UI          → speed 1.0× (screen-space)
```

**Layer data** (generated offline via pycairo, loaded at runtime):
- Each layer = 1–3 seamless tiles (960×540 base, tiled horizontally)
- Biome + sanity stage = 6 biomes × 4 stages = 24 layer sets
- Generated by `art/cairo_renderer.py` (see FR-08) using `palette_seed`

### 4.2 Color Grading & Palette (per biome × sanity stage)

**Base palette per biome** (HSV ranges, deterministic from `palette_seed`):

| Biome | Hue Range | Saturation | Value | Accent Hue |
|-------|-----------|------------|-------|------------|
| SAFE_HAVEN | 45–65 (warm gold) | 0.4–0.6 | 0.7–0.9 | 330 (soft pink) |
| TEMPERATE_GROVE | 90–130 (green) | 0.5–0.7 | 0.4–0.7 | 30 (amber) |
| ARID_CANYON | 20–40 (orange) | 0.6–0.8 | 0.5–0.8 | 0 (red) |
| SWAMP_MIRE | 140–170 (teal) | 0.3–0.5 | 0.3–0.5 | 280 (purple) |
| BOREAL_TAIGA | 190–220 (blue) | 0.4–0.6 | 0.4–0.6 | 60 (yellow) |
| VOID_RUINS | 260–300 (violet) | 0.2–0.4 | 0.2–0.4 | 340 (magenta) |

**Sanity stage transforms** (applied in fragment shader):
- Stage 1: Identity
- Stage 2: `saturation *= 0.7; hue += 15°; contrast *= 1.2`
- Stage 3: `saturation *= 0.4; hue += 45°; contrast *= 1.5; add noise(uv×0.01)×0.1`
- Stage 4: `desaturate to 0.1; hue = 280°; add void_noise(uv, time)×0.3; vignette=0.8`

### 4.3 Weather / Atmosphere (per biome)

| Biome | Particle Type | Density | Wind | Audio Ambience |
|-------|---------------|---------|------|----------------|
| SAFE_HAVEN | pollen, soft motes | low | gentle | warm drone, distant chimes |
| TEMPERATE_GROVE | leaves, spores | med | variable | birds, wind in leaves |
| ARID_CANYON | sand, dust devils | med | strong | howling wind, heat crackle |
| SWAMP_MIRE | mist, fireflies, bubbles | high | still | dripping water, frog chorus |
| BOREAL_TAIGA | snow, ice crystals | med | cold gust | wind howl, creaking ice |
| VOID_RUINS | void motes, glyph fragments | low | none | low hum, reversed audio |

**Sanity overlay** (always active, intensity = 1.0 − world_sanity/100):
- `glitch_overlay`: RGB channel shift, scanlines, block corruption (from creature visual_renderer)
- `vignette`: radial darken
- `chromatic_aberration`: increases with sanity loss
- `audio_distortion`: low-pass + bit-crush + reverb (from creature audio_synthesizer)

### 4.4 Shader Sanity Effects (GPU)

Vertex shader (terrain morph):
```glsl
// Stage 3+ only
vec2 distort = hash(vec2(world_x, time)) * sanity_factor * 2.0;
position.x += distort.x;
position.y += distort.y * 0.5;
```

Fragment shader (palette + glitch):
```glsl
vec3 color = sample_parallax(uv);
color = apply_palette(color, biome_id, sanity_stage);
color = apply_sanity_glitch(color, uv, world_sanity, time);
return color;
```

---

## 5. Data Definitions (JSON)

### 5.1 `data/world/biomes.json`
```json
{
  "biomes": [
    {
      "id": "SAFE_HAVEN",
      "name": "Safe Haven",
      "base_temperature": 22,
      "base_rainfall": 600,
      "terrain_amplitude": 15,
      "ridge_strength": 0.2,
      "water_frequency": 0.1,
      "cave_chance": 0.05,
      "decor_palette": "haven",
      "creature_archetype_weights": {
        "gentle_light": 1,
        "prey": 15,
        "curious": 8,
        "scavenger": 5
      },
      "sanity_morph": "FRACTURED_GROVE",
      "palette_hue_range": [45, 65],
      "palette_saturation": [0.4, 0.6],
      "palette_value": [0.7, 0.9],
      "accent_hue": 330,
      "weather": "pollen",
      "parallax_layers": ["sky_warm", "hills_gentle", "trees_soft", "grass_glow"]
    }
    // ... 5 more base biomes + 4 morphed variants
  ]
}
```

### 5.2 `data/world/zones.json`
```json
{
  "zones": [
    {
      "zone_id": "zone_01_warmth_entry",
      "biome": "SAFE_HAVEN",
      "x_range": [0, 800],
      "sanity_threshold": 100,
      "landmark": "WARMTH_ALTAR",
      "territory_center": [400, 100],
      "difficulty_tier": 1,
      "fragment_density": 0.8,
      "connecting_zones": ["zone_02_temperate_grove"]
    }
    // ... 6 more zones
  ],
  "landmarks": {
    "WARMTH_ALTAR": {
      "type": "ALTAR",
      "world_pos": [400, 80],
      "unlock_sanity": 100,
      "visual_states": {
        "1": {"sprite": "altar_warm", "particles": "warm_motes", "audio": "chime_soft"},
        "2": {"sprite": "altar_cracked", "particles": "void_dust", "audio": "chime_distorted"},
        "3": {"sprite": "altar_fractured", "particles": "glitch_shards", "audio": "silence"},
        "4": {"sprite": "altar_transcended", "particles": "light_rays", "audio": "choir"}
      },
      "associated_cutscene": "warmth"
    }
    // ... 6 more landmarks
  }
}
```

### 5.3 `data/world/fragments.json`
```json
{
  "fragment_types": [
    {"id": "MEMORY", "sanity_reward": 0.5, "color": [255, 220, 180], "rarity": "common"},
    {"id": "ESSENCE", "sanity_reward": 2.0, "color": [200, 150, 255], "rarity": "uncommon"},
    {"id": "SHARD", "sanity_reward": 8.0, "color": [150, 100, 255], "rarity": "rare"},
    {"id": "CORE", "sanity_reward": 25.0, "color": [255, 100, 200], "rarity": "unique"}
  ]
}
```

---

## 6. API Design

### 6.1 Public Entry Point

```python
# src/procedural_generation/prc_world/__init__.py

from .world_generator import WorldGenerator
from .zone_definition import WorldZone, BiomeType, Landmark
from .terrain_generator import LevelTerrain, Platform, SpawnAnchor
from .palette import BiomePalette, SanityPalette
from .data_loader import load_biomes, load_zones, load_fragments

__all__ = [
    "WorldGenerator",
    "WorldZone", "BiomeType", "Landmark",
    "LevelTerrain", "Platform", "SpawnAnchor",
    "BiomePalette", "SanityPalette",
    "load_biomes", "load_zones", "load_fragments",
]
```

### 6.2 WorldGenerator

```python
class WorldGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._derive_seeds()
        self.biomes = load_biomes()
        self.zones = load_zones()
        self.fragments = load_fragments()
        self._build_zone_index()

    def _derive_seeds(self):
        # Deterministic derivation using splitmix64
        self.zone_seed     = splitmix64(self.seed, "zone")
        self.terrain_seed  = splitmix64(self.seed, "terrain")
        self.decor_seed    = splitmix64(self.seed, "decor")
        self.palette_seed  = splitmix64(self.seed, "palette")
        self.weather_seed  = splitmix64(self.seed, "weather")
        self.sanity_seed   = splitmix64(self.seed, "sanity")

    def generate_zone(self, zone_id: str, world_sanity: float) -> LevelTerrain:
        """Generate full L2 terrain for a zone at given sanity."""
        zone = self.zones[zone_id]
        biome = self._resolve_biome(zone.biome, world_sanity)
        terrain = self._generate_heightmap(zone, biome)
        terrain = self._extract_platforms(terrain, biome)
        terrain = self._place_decor(terrain, biome, world_sanity)
        terrain = self._place_fragments(terrain, zone, world_sanity)
        terrain = self._place_spawn_anchors(terrain, zone, biome)
        return terrain

    def _resolve_biome(self, base_biome: BiomeType, world_sanity: float) -> BiomeType:
        if world_sanity > 75: return base_biome
        if world_sanity > 50: return self.biomes[base_biome].sanity_morph_stage2
        if world_sanity > 25: return self.biomes[base_biome].sanity_morph_stage3
        return BiomeType.END_VOID

    def get_zone_sequence(self) -> List[WorldZone]:
        return [z for z in self.zones.values() if z.sanity_threshold >= 0]  # ordered

    def get_unlocked_zones(self, world_sanity: float) -> List[WorldZone]:
        return [z for z in self.get_zone_sequence() if world_sanity <= z.sanity_threshold]

    def get_parallax_layers(self, biome: BiomeType, sanity_stage: int) -> List[ParallaxLayer]:
        # Load pre-rendered pycairo assets from assets/nur/parallax/{biome}_{stage}/
        pass

    def get_palette(self, biome: BiomeType, sanity_stage: int) -> BiomePalette:
        base = self.biomes[biome].palette
        return apply_sanity_transform(base, sanity_stage, self.palette_seed)

    def get_sanity_shader_params(self, world_sanity: float) -> Dict[str, float]:
        # Returns uniforms for sanity glitch shader
        stage = sanity_stage(world_sanity)
        intensity = 1.0 - world_sanity / 100.0
        return {"stage": stage, "intensity": intensity, "time": 0.0, "seed": self.sanity_seed}
```

### 6.3 Terrain Generator (L2)

```python
class TerrainGenerator:
    def __init__(self, seed: int):
        self.seed = seed
        self.noise = FastNoiseLite(seed)

    def generate_heightmap(self, zone: WorldZone, biome: BiomeDef) -> np.ndarray:
        # Returns 1D array: world_x (meters) → elevation (meters)
        width = int(zone.x_range[1] - zone.x_range[0])
        hm = np.zeros(width, dtype=np.float32)
        for i in range(width):
            x = zone.x_range[0] + i
            hm[i] = self._fbm_2d(x * 0.01, 0, 6, 2.0, 0.5) * biome.terrain_amplitude
            hm[i] += self._ridged_2d(x * 0.005, 0, 4) * biome.ridge_strength * biome.terrain_amplitude
        return self._carve_rivers(hm, zone, biome)

    def extract_platforms(self, heightmap: np.ndarray, biome: BiomeDef) -> List[Platform]:
        # Sample every 2m, build platforms from flat segments
        platforms = []
        # ... algorithm: find contiguous flat runs, create platform per run
        # Ensure connectivity via A* on ground layer
        return platforms

    def place_decor(self, platforms: List[Platform], biome: BiomeDef,
                    world_sanity: float, decor_seed: int) -> List[DecorInstance]:
        # Poisson-disc per platform segment
        # Decor palette shifts at sanity thresholds
        pass

    def place_fragments(self, platforms: List[Platform], zone: WorldZone,
                        world_sanity: float) -> List[FragmentPlacement]:
        # Deterministic placement: hash(zone_id, fragment_index) → position
        # CORE always at landmark; others distributed with increasing reward
        pass

    def place_spawn_anchors(self, platforms: List[Platform], zone: WorldZone,
                            biome: BiomeDef) -> List[SpawnAnchor]:
        # One anchor per territory_center ± noise
        # Archetype weights from biome.creature_archetype_weights
        pass
```

---

## 7. Integration Points

| System | Integration |
|--------|-------------|
| `prc-creature.PopulationManager` | `SpawnAnchor` → `territory_center`, `creature_archetype_weights`; `PopulationManager.spawn_in_territory()` called per anchor |
| `prc-creature.BehaviorEngine` | `world_sanity` passed to `EnvironmentalContext`; sanity modifiers already implemented |
| `nur_game.art.cairo_renderer` | Generates parallax layer PNGs offline (FR-08); `WorldGenerator.get_parallax_layers()` loads them |
| `nur_game.shaders` | `get_sanity_shader_params()` → uniforms for terrain morph + palette + glitch |
| `nur_game.audio` | Weather ambience per biome; sanity distortion from `audio_synthesizer` |
| Save/Load | `WorldGenerator` state = seed + current `world_sanity` + unlocked zone index (fully deterministic replay) |

---

## 8. Sanity Stage Mapping (Critical)

| Stage | World Sanity | Biome Morph | Visual | Audio | Gameplay |
|-------|--------------|-------------|--------|-------|----------|
| 1 — Warmth | 100–76 | Base biomes | Identity | Clean | Normal creature behavior |
| 2 — Fractured | 75–51 | Stage 2 morphs | Desaturate, cracks, void dust | Low-pass, subtle reverb | Aggression×1.5, pack_hunt, new archetypes (`void_walker` weight↑) |
| 3 — Labyrinth | 50–26 | Stage 3 morphs | Geometry warp, mirror, heavy fog | Heavy reverb, pitch shift | Ignore_stun, spawn_minions, `guardian`→`void_walker` conversion |
| 4 — End | 25–0 | END_VOID only | Abstraction, void shader | Choir, silence | Only `gentle_light` (scripted), cutscene trigger |

---

## 9. Determinism Checklist

- [ ] Single `seed=42` → all derived seeds via `splitmix64(seed, domain)`
- [ ] `FastNoiseLite` (or equivalent) for all noise — no Python `random`
- [ ] JSON data loaded once, cached, never mutated
- [ ] Zone order fixed in `zones.json` (no runtime sorting by position)
- [ ] Fragment placement: `hash(zone_id, fragment_index, seed)` → position
- [ ] Parallax assets pre-rendered offline (pycairo, seed=42)
- [ ] Shader uniforms derived from `sanity_seed` + `world_sanity` only
- [ ] Creature spawns: `PopulationManager` uses same derived seed for RNG

---

## 10. Known Gaps / Future Work

| Gap | Description |
|-----|-------------|
| **Branching zones** | Current design is linear. `connecting_zone_ids` exists but not implemented. |
| **Dynamic weather events** | Weather is ambient only. Storms, void storms, sanity surges not designed. |
| **Player-built structures** | No integration for player-placed platforms/anchors. |
| **Multiplayer sync** | Deterministic seed works, but runtime state (creature positions) needs sync protocol. |
| **Accessibility** | Color-blind palette variants not defined. Sanity glitch may trigger photosensitivity. |
| **Level streaming** | Large zones need chunked load/unload; not specified. |
| **Ecology simulation** | `PopulationManager` has territory/capacity; predator-prey dynamics across zones not simulated. |

---

## 11. Verification Checklist (Definition of Done)

- [ ] `WorldGenerator(seed=42).generate_zone("zone_01_warmth_entry", 100)` returns valid `LevelTerrain`
- [ ] All 7 zones generate without error at all 4 sanity stages
- [ ] Heightmap platforms are fully connected (A* path start→end exists)
- [ ] Fragment placement: exactly 1 CORE per zone at landmark
- [ ] Parallax layers load for all biome×stage combos (24 sets)
- [ ] Palette transforms produce expected HSV ranges
- [ ] Sanity shader params change smoothly across 0–100
- [ ] `PopulationManager` spawns creatures matching biome weights
- [ ] Determinism test: two runs with seed=42 produce byte-identical terrain arrays
- [ ] Performance: zone generation < 100ms on target hardware

---

## 12. File Structure (Target)

```
src/procedural-generation/prc-world/
├── __init__.py                 # Public API (this blueprint §6.1)
├── world_generator.py          # WorldGenerator class (§6.2)
├── zone_definition.py          # WorldZone, BiomeType, Landmark dataclasses
├── terrain_generator.py        # TerrainGenerator, heightmap, platforms (§6.3)
├── palette.py                  # BiomePalette, SanityPalette, transforms
├── data_loader.py              # load_biomes, load_zones, load_fragments
├── sanity_morph.py             # Stage resolution, morph logic
├── tests/
│   ├── test_world_generator.py
│   ├── test_terrain_generator.py
│   └── test_determinism.py
└── data/
    ├── biomes.json             # §5.1
    ├── zones.json              # §5.2
    └── fragments.json          # §5.3
```

---

## 13. Next Steps (Implementation Order)

1. **Data files first** — `biomes.json`, `zones.json`, `fragments.json` (source of truth)
2. **Dataclasses + loaders** — `zone_definition.py`, `data_loader.py`
3. **Terrain generator** — heightmap, platforms, connectivity test
4. **World generator** — zone sequencing, biome resolution, fragment/decor placement
5. **Palette + sanity morph** — HSV transforms, shader param generation
6. **Parallax asset generation** — extend `art/cairo_renderer.py` for 24 layer sets
7. **Integration tests** — determinism, connectivity, creature spawn verification
8. **Shader hooks** — vertex morph + fragment palette/glitch in `nur_game/shaders/`

---

*Blueprint version 1.0 — matches prc-creature BLUEPRINT.md depth and style. Deterministic seed 42 enforced throughout. Ready for implementation.*