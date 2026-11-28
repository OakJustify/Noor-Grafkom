# prc-audio — Procedural Audio System Blueprint

**Module**: `src/procedural-generation/prc-audio/`
**Goal**: Create a hybrid procedural/sample-based audio engine for Noor, focusing on sanity-reactive soundscapes, dynamic creature vocalizations, and adaptive biome soundscapes.

---

## 1. Architecture Overview (Hybrid Design)

The system treats sound as a combination of **static texture** (samples) and **dynamic behavior** (synthesis/DSP parameters).

```
[Game State: Sanity, Biome, Action, CreatureState]
       │
       ▼
[Audio Controller / Middleware Mapper]
       │
       ├─► [Dynamic Mixing System (Layered Ambiences)]
       │
       ├─► [Procedural Foley Engine (Footsteps, Impacts)]
       │
       └─► [Procedural Creature Vocalizer (Synthesis + Mod)]
       │
       ▼
[DSP Processing Layer (Reverb, Distortion, LPF)]
       │
       ▼
[Audio Output Device]
```

---

## 2. Dynamic Mixing System (Ambience & Music)

Focuses on **Vertical Layering** (adding/removing tracks) based on context.

### 2.1 Ambience Layers
Each biome has 3-5 ambient loops that are dynamically mixed:
- **Core Layer**: Constant sound (e.g., wind, cave hum).
- **Life Layer**: Random events (e.g., birds, distant creature cries).
- **Sanity Layer**: Distorted, weird sounds that increase in volume as `world_sanity` decreases.

### 2.2 Music Layers
- **Melodic Layer**: Biome-specific theme.
- **Tension Layer**: Added when `aggression` > threshold.
- **Void Layer**: Inverted/reversed melodic patterns introduced at `world_sanity` < 50.

---

## 3. Procedural Foley Engine (Footsteps & Impacts)

Avoids repetition by using **Randomized Concatenation** and **Parameter Mapping**.

### 3.1 Footstep Logic
1. **Material Detection**: Raycast to determine surface type (Stone, Soil, Water, Void).
2. **Material Map**: Each material maps to a folder of 5–10 short variants.
3. **Randomization**:
   - Select variant (random).
   - Pitch Shift: `±10%` (for variance).
   - Volume: mapped to speed + mass.
   - Low Pass Filter (LPF): mapped to `depth_layer` (Cave vs. Open).

---

## 4. Procedural Creature Vocalizer (Synthesis)

Uses the **Farnell Physical Modeling** concept (source-filter model) for creature calls.

### 4.1 Vocalization Parameters (mapped from `BehaviorEngine`)
- **Pitch**: ∝ Creature Size (huge = low, tiny = high).
- **Formant**: ∝ Morphology (serpentine vs. biped changes resonance).
- **Noise/Harmonic Balance**: ∝ Aggression/Sanity.
- **Distortion**: ∝ `world_sanity` stage.

### 4.2 Implementation (Engine Hooks)
Creatures do NOT store WAVs of their cries. They store an **AudioProfile**:
```python
@dataclass
class AudioProfile:
    base_freq: float
    harmonic_ratio: float
    filter_cutoff: float
    attack_ms: float
    decay_ms: float
```
When `call()` is triggered, the `AudioSynthesizer` generates the buffer in real-time.

---

## 5. DSP & Sanity Effects (The "Noor" Factor)

DSP chains are applied globally based on `world_sanity` and environment.

| Effect | Parameter | Source |
| :--- | :--- | :--- |
| **Low Pass Filter (LPF)** | Cutoff (20kHz → 500Hz) | `depth_layer` (Caves), `world_sanity` |
| **Reverb** | Wet/Dry, Size | `biome_type` (Open vs. Cave) |
| **Pitch Modulation** | Sample Rate Shift | `world_sanity` (Stage 3/4) |
| **Bit-Crush / Distortion**| Crunch Level | `world_sanity` (Stage 2/3/4) |

---

## 6. API Design (`prc-audio`)

```python
# src/procedural-generation/prc-audio/engine.py

class AudioEngine:
    def trigger_event(self, event_name: str, params: Dict[str, Any]):
        """General event handler (e.g., 'FOOTSTEP', 'CREATURE_CALL')."""
        pass

    def update_environment(self, sanity: float, biome: BiomeType):
        """Update global DSP chain based on environment."""
        pass

    def synthesize_vocalization(self, profile: AudioProfile, behavior_state: CreatureState):
        """Generates raw audio buffer for creature behavior."""
        pass
```

---

## 7. Implementation Checklist

- [ ] **Sample Library**: Categorized by material (footsteps) and biome (ambience).
- [ ] **Synthesizer Core**: Simple oscillator-based (Sine/Noise) synth implemented for creature cries.
- [ ] **DSP Chain**: Reverb, LPF, and Distortion wrapper.
- [ ] **Integration Hook**: `BehaviorEngine` triggers `vocalization` based on state change.
- [ ] **Determinism**: Audio synthesis parameters must be derived from `seed=42`.

---

## 8. Data Structures (JSON)

### 8.1 `data/audio/materials.json`
```json
{
  "stone": {"samples": ["s1.wav", "s2.wav"], "pitch_range": [0.9, 1.1]},
  "soil": {"samples": ["d1.wav", "d2.wav"], "pitch_range": [0.8, 1.2]}
}
```

### 8.2 `data/audio/creature_profiles.json`
```json
{
  "predator": {
    "base_freq": 120.0,
    "filter_cutoff": 2000.0,
    "distortion_base": 0.2
  }
}
```

---

*Blueprint version 1.0 — Ready for integration with `prc-creature` and `prc-world`.*