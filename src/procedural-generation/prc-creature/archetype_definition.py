"""Creature Archetype Definitions — Dataclasses & Enums

Data-driven definitions for procedural creature generation.
All values deterministic with seed=42.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
import json
from pathlib import Path


class BodyPlanType(str, Enum):
    QUADRUPED = "quadruped"
    BIPED = "biped"
    HEXAPOD = "hexapod"
    SERPENTINE = "serpentine"
    FLOATING = "floating"
    MULTI_LIMBED = "multi_limbed"
    WINGED = "winged"
    AMORPHOUS = "amorphous"


class SizeClass(str, Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"


class ArchetypeType(str, Enum):
    PREDATOR = "predator"
    PREY = "prey"
    SCAVENGER = "scavenger"
    TERRITORIAL = "territorial"
    CURIOUS = "curious"
    PARASITIC = "parasitic"
    GUARDIAN = "guardian"
    AMBUSH = "ambush"
    VOID_WALKER = "void_walker"
    GENTLE_LIGHT = "gentle_light"


class SocialStructure(str, Enum):
    SOLITARY = "solitary"
    PAIR = "pair"
    PACK = "pack"
    HERD = "herd"
    SWARM = "swarm"
    COLONY = "colony"
    LOOSE_GROUP = "loose_group"
    SOCIAL = "social"
    SCRIPTED = "scripted"


class ActivityCycle(str, Enum):
    DIURNAL = "diurnal"
    NOCTURNAL = "nocturnal"
    CREPUSCULAR = "crepuscular"
    RANDOM = "random"
    SCRIPTED = "scripted"


class LocomotionType(str, Enum):
    LEGGED = "legged"
    SERPENTINE = "serpentine"
    FLOATING = "floating"
    WINGED = "winged"
    AMORPHOUS = "amorphous"


class GaitType(str, Enum):
    # Legged
    WALK = "walk"
    TROT = "trot"
    GALLOP = "gallop"
    BOUND = "bound"
    RUN = "run"
    CLIMB = "climb"
    CROUCH = "crouch"
    HOP = "hop"
    SCUTTLE = "scuttle"
    GRAPPLE = "grapple"
    TRIPOD = "tripod"
    WAVE = "wave"
    RIPPLE = "ripple"
    # Serpentine
    UNDULATE = "undulate"
    SIDEWIND = "sidewind"
    CONCERTINA = "concertina"
    SWIM = "swim"
    CLIMB_SERPENTINE = "climb_serpentine"
    # Floating
    DRIFT = "drift"
    PULSE = "pulse"
    JET = "jet"
    TETHER = "tether"
    # Winged
    FLIGHT = "flight"
    GLIDE = "glide"
    PERCH = "perch"
    # Amorphous
    FLOW = "flow"
    OOZE = "ooze"
    SPLIT = "split"
    MERGE = "merge"
    EXTEND = "extend"
    CLIMB_AMORPHOUS = "climb_amorphous"


@dataclass(frozen=True)
class SizeClassParams:
    """Scaling parameters per size class."""
    mass_range: tuple[float, float]           # kg
    body_length_range: tuple[float, float]    # pixels
    leg_length_mult: tuple[float, float]      # multiplier
    step_height_range: tuple[float, float]    # pixels
    speed_mult: tuple[float, float]           # multiplier
    audio_pitch_shift: int                    # octaves

    @property
    def avg_scale(self) -> float:
        """Average linear scale factor."""
        return (self.body_length_range[0] + self.body_length_range[1]) / 240.0  # 240 = medium baseline


SIZE_CLASS_PARAMS: dict[SizeClass, SizeClassParams] = {
    SizeClass.TINY: SizeClassParams(
        mass_range=(0.5, 2.0),
        body_length_range=(20.0, 40.0),
        leg_length_mult=(0.3, 0.5),
        step_height_range=(4.0, 8.0),
        speed_mult=(0.5, 0.8),
        audio_pitch_shift=2
    ),
    SizeClass.SMALL: SizeClassParams(
        mass_range=(2.0, 10.0),
        body_length_range=(40.0, 80.0),
        leg_length_mult=(0.5, 0.8),
        step_height_range=(8.0, 16.0),
        speed_mult=(0.8, 1.2),
        audio_pitch_shift=1
    ),
    SizeClass.MEDIUM: SizeClassParams(
        mass_range=(10.0, 40.0),
        body_length_range=(80.0, 160.0),
        leg_length_mult=(0.8, 1.2),
        step_height_range=(16.0, 32.0),
        speed_mult=(1.0, 1.0),
        audio_pitch_shift=0
    ),
    SizeClass.LARGE: SizeClassParams(
        mass_range=(40.0, 150.0),
        body_length_range=(160.0, 300.0),
        leg_length_mult=(1.2, 1.8),
        step_height_range=(32.0, 60.0),
        speed_mult=(0.7, 1.0),
        audio_pitch_shift=-1
    ),
    SizeClass.HUGE: SizeClassParams(
        mass_range=(150.0, 500.0),
        body_length_range=(300.0, 500.0),
        leg_length_mult=(1.5, 2.5),
        step_height_range=(50.0, 100.0),
        speed_mult=(0.4, 0.7),
        audio_pitch_shift=-2
    ),
}


@dataclass(frozen=True)
class LimbSegmentDef:
    """Single segment of a limb."""
    length_ratio: float          # Proportion of total limb length
    thickness_ratio: float = 1.0 # Relative thickness
    joint_limit_deg: tuple[float, float] = (-90.0, 90.0)  # Min/max angle
    compliance: float = 0.1      # Spring-damper compliance (0=rigid, 1=soft)


@dataclass(frozen=True)
class LimbDef:
    """Definition of a single limb."""
    name: str
    limb_type: Literal["leg", "arm", "wing", "tail", "neck", "head", "tendril", "pseudopod"]
    anchor: tuple[float, float]  # Body-relative anchor point (0-1 normalized)
    segments: list[LimbSegmentDef]
    nominal_offset: tuple[float, float] | None = None  # Rest position offset
    gait_phase_offset: float = 0.0  # Phase in gait cycle (0-1)
    is_ground_contact: bool = False


@dataclass(frozen=True)
class BodyPlanDef:
    """Complete body plan definition from JSON."""
    body_plan_type: BodyPlanType
    description: str
    limbs: dict  # Raw limb config from JSON
    gaits: list[GaitType]
    default_gait: GaitType
    size_range: list[SizeClass]
    archetype_affinity: list[ArchetypeType]
    locomotion_type: LocomotionType
    foot_friction: float
    climb_capable: bool
    swim_capable: bool


@dataclass(frozen=True)
class SanityModifiers:
    """Behavior modifications at sanity thresholds."""
    thresholds: dict[int, dict[str, float]]  # sanity -> {param: multiplier}

    def get_modifiers(self, sanity: float) -> dict[str, float]:
        """Get combined modifiers for given sanity level."""
        result = {}
        for threshold in sorted(self.thresholds.keys()):
            if sanity <= threshold:
                result.update(self.thresholds[threshold])
        return result


@dataclass(frozen=True)
class PopulationParams:
    """Population dynamics parameters."""
    carrying_capacity: int
    territory_size: float
    reproduction_rate: float
    mortality_rate: float


@dataclass(frozen=True)
class ArchetypeDef:
    """Complete archetype definition from JSON."""
    archetype_type: ArchetypeType
    base_drives: list[str]
    state_priorities: list[str]
    social: SocialStructure
    sanity_mods: SanityModifiers
    palette: str
    vocal_profile: str
    population: PopulationParams
    activity_cycle: ActivityCycle
    food_preference: list[str]
    is_cutscene: bool


# Vocal profiles mapping to synthesis parameters
VOCAL_PROFILES: dict[str, dict] = {
    "deep_terrestrial": {
        "fundamental_range": (40.0, 120.0),
        "formant_ratios": [1.0, 2.5, 4.0, 5.5],
        "breathiness": 0.3,
        "roughness": 0.4,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (2.0, 5.0), "pitch_range": (-2, 2), "rhythm": "irregular", "harmonicity": 0.7},
            "alert": {"pattern": "pulse", "duration": (0.5, 1.5), "pitch_range": (0, 5), "rhythm": "regular", "harmonicity": 0.8},
            "aggressive": {"pattern": "scream", "duration": (1.0, 3.0), "pitch_range": (5, 12), "rhythm": "burst", "harmonicity": 0.5},
            "pain": {"pattern": "scream", "duration": (0.3, 1.0), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.3},
            "death": {"pattern": "drone", "duration": (2.0, 5.0), "pitch_range": (-12, -5), "rhythm": "continuous", "harmonicity": 0.9}
        }
    },
    "high_terrestrial": {
        "fundamental_range": (300.0, 800.0),
        "formant_ratios": [1.0, 2.0, 3.0, 4.5],
        "breathiness": 0.2,
        "roughness": 0.2,
        "call_types": {
            "idle": {"pattern": "chirp", "duration": (0.2, 0.8), "pitch_range": (-5, 5), "rhythm": "irregular", "harmonicity": 0.8},
            "alert": {"pattern": "trill", "duration": (0.5, 1.5), "pitch_range": (5, 12), "rhythm": "regular", "harmonicity": 0.9},
            "aggressive": {"pattern": "scream", "duration": (0.5, 1.5), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.4},
            "pain": {"pattern": "scream", "duration": (0.2, 0.8), "pitch_range": (24, 36), "rhythm": "burst", "harmonicity": 0.2},
            "death": {"pattern": "drone", "duration": (1.0, 3.0), "pitch_range": (-12, 0), "rhythm": "continuous", "harmonicity": 0.8}
        }
    },
    "raspy_terrestrial": {
        "fundamental_range": (80.0, 200.0),
        "formant_ratios": [1.0, 2.2, 3.5, 5.0],
        "breathiness": 0.6,
        "roughness": 0.7,
        "call_types": {
            "idle": {"pattern": "click", "duration": (0.1, 0.3), "pitch_range": (-12, 0), "rhythm": "irregular", "harmonicity": 0.3},
            "alert": {"pattern": "pulse", "duration": (0.3, 1.0), "pitch_range": (0, 7), "rhythm": "regular", "harmonicity": 0.5},
            "aggressive": {"pattern": "scream", "duration": (0.8, 2.0), "pitch_range": (7, 19), "rhythm": "burst", "harmonicity": 0.3},
            "pain": {"pattern": "scream", "duration": (0.2, 0.6), "pitch_range": (19, 31), "rhythm": "burst", "harmonicity": 0.1},
            "death": {"pattern": "drone", "duration": (1.5, 4.0), "pitch_range": (-19, -7), "rhythm": "continuous", "harmonicity": 0.6}
        }
    },
    "resonant_terrestrial": {
        "fundamental_range": (60.0, 150.0),
        "formant_ratios": [1.0, 2.0, 3.0, 4.0, 5.0],
        "breathiness": 0.2,
        "roughness": 0.3,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (3.0, 8.0), "pitch_range": (-5, 5), "rhythm": "continuous", "harmonicity": 0.9},
            "alert": {"pattern": "pulse", "duration": (1.0, 2.0), "pitch_range": (0, 5), "rhythm": "regular", "harmonicity": 0.8},
            "aggressive": {"pattern": "scream", "duration": (1.5, 4.0), "pitch_range": (5, 12), "rhythm": "burst", "harmonicity": 0.6},
            "pain": {"pattern": "scream", "duration": (0.5, 1.5), "pitch_range": (12, 19), "rhythm": "burst", "harmonicity": 0.4},
            "death": {"pattern": "drone", "duration": (3.0, 6.0), "pitch_range": (-12, -5), "rhythm": "continuous", "harmonicity": 0.8}
        }
    },
    "melodic_terrestrial": {
        "fundamental_range": (200.0, 500.0),
        "formant_ratios": [1.0, 1.5, 2.0, 2.5, 3.0],
        "breathiness": 0.15,
        "roughness": 0.15,
        "call_types": {
            "idle": {"pattern": "trill", "duration": (0.5, 2.0), "pitch_range": (-7, 7), "rhythm": "irregular", "harmonicity": 0.9},
            "alert": {"pattern": "chirp", "duration": (0.2, 0.6), "pitch_range": (7, 14), "rhythm": "regular", "harmonicity": 0.95},
            "aggressive": {"pattern": "pulse", "duration": (0.8, 2.0), "pitch_range": (0, 12), "rhythm": "burst", "harmonicity": 0.7},
            "pain": {"pattern": "scream", "duration": (0.3, 1.0), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.5},
            "death": {"pattern": "drone", "duration": (2.0, 5.0), "pitch_range": (-12, 0), "rhythm": "continuous", "harmonicity": 0.9}
        }
    },
    "wet_subtle": {
        "fundamental_range": (150.0, 400.0),
        "formant_ratios": [1.0, 1.8, 2.8, 4.2],
        "breathiness": 0.5,
        "roughness": 0.4,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (2.0, 5.0), "pitch_range": (-5, 5), "rhythm": "continuous", "harmonicity": 0.6},
            "alert": {"pattern": "click", "duration": (0.05, 0.15), "pitch_range": (0, 12), "rhythm": "burst", "harmonicity": 0.2},
            "aggressive": {"pattern": "scream", "duration": (0.5, 1.5), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.3},
            "pain": {"pattern": "scream", "duration": (0.2, 0.6), "pitch_range": (24, 36), "rhythm": "burst", "harmonicity": 0.1},
            "death": {"pattern": "drone", "duration": (1.0, 3.0), "pitch_range": (-12, -5), "rhythm": "continuous", "harmonicity": 0.7}
        }
    },
    "harmonic_terrestrial": {
        "fundamental_range": (100.0, 300.0),
        "formant_ratios": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "breathiness": 0.1,
        "roughness": 0.1,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (4.0, 10.0), "pitch_range": (-7, 7), "rhythm": "continuous", "harmonicity": 0.95},
            "alert": {"pattern": "pulse", "duration": (1.0, 2.0), "pitch_range": (0, 7), "rhythm": "regular", "harmonicity": 0.9},
            "aggressive": {"pattern": "scream", "duration": (1.0, 3.0), "pitch_range": (7, 19), "rhythm": "burst", "harmonicity": 0.7},
            "pain": {"pattern": "scream", "duration": (0.5, 1.5), "pitch_range": (19, 31), "rhythm": "burst", "harmonicity": 0.5},
            "death": {"pattern": "drone", "duration": (3.0, 8.0), "pitch_range": (-19, -7), "rhythm": "continuous", "harmonicity": 0.9}
        }
    },
    "silent_terrestrial": {
        "fundamental_range": (50.0, 100.0),
        "formant_ratios": [1.0, 2.5, 4.5],
        "breathiness": 0.8,
        "roughness": 0.6,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (5.0, 15.0), "pitch_range": (-12, -5), "rhythm": "continuous", "harmonicity": 0.4},
            "alert": {"pattern": "pulse", "duration": (0.1, 0.3), "pitch_range": (0, 5), "rhythm": "burst", "harmonicity": 0.2},
            "aggressive": {"pattern": "click", "duration": (0.05, 0.1), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.1},
            "pain": {"pattern": "scream", "duration": (0.3, 1.0), "pitch_range": (24, 36), "rhythm": "burst", "harmonicity": 0.15},
            "death": {"pattern": "drone", "duration": (2.0, 6.0), "pitch_range": (-24, -12), "rhythm": "continuous", "harmonicity": 0.5}
        }
    },
    "digital_corrupted": {
        "fundamental_range": (80.0, 200.0),
        "formant_ratios": [1.0, 1.414, 2.0, 2.828, 4.0],
        "breathiness": 0.7,
        "roughness": 0.9,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (1.0, 3.0), "pitch_range": (-12, 12), "rhythm": "irregular", "harmonicity": 0.2},
            "alert": {"pattern": "scream", "duration": (0.3, 1.0), "pitch_range": (12, 24), "rhythm": "burst", "harmonicity": 0.1},
            "aggressive": {"pattern": "scream", "duration": (0.5, 2.0), "pitch_range": (19, 36), "rhythm": "burst", "harmonicity": 0.05},
            "pain": {"pattern": "scream", "duration": (0.2, 0.8), "pitch_range": (36, 48), "rhythm": "burst", "harmonicity": 0.0},
            "death": {"pattern": "drone", "duration": (0.5, 2.0), "pitch_range": (-24, 24), "rhythm": "irregular", "harmonicity": 0.1}
        }
    },
    "ethereal_harmonic": {
        "fundamental_range": (220.0, 440.0),
        "formant_ratios": [1.0, 1.25, 1.5, 1.667, 2.0, 2.5, 3.0],
        "breathiness": 0.05,
        "roughness": 0.0,
        "call_types": {
            "idle": {"pattern": "drone", "duration": (10.0, 30.0), "pitch_range": (-5, 5), "rhythm": "continuous", "harmonicity": 1.0},
            "alert": {"pattern": "trill", "duration": (2.0, 5.0), "pitch_range": (0, 12), "rhythm": "regular", "harmonicity": 0.95},
            "aggressive": {"pattern": "pulse", "duration": (1.0, 3.0), "pitch_range": (5, 12), "rhythm": "regular", "harmonicity": 0.9},
            "pain": {"pattern": "drone", "duration": (3.0, 8.0), "pitch_range": (-12, -5), "rhythm": "continuous", "harmonicity": 0.95},
            "death": {"pattern": "drone", "duration": (5.0, 15.0), "pitch_range": (-24, -12), "rhythm": "continuous", "harmonicity": 1.0}
        }
    }
}


# Palette definitions (HSV ranges)
PALETTES: dict[str, dict] = {
    "predator": {"base_hue": (0.0, 0.15), "base_sat": (0.4, 0.7), "base_val": (0.2, 0.5), "accent_hue": (0.95, 1.0), "accent_sat": (0.7, 1.0), "accent_val": (0.6, 0.9)},
    "prey": {"base_hue": (0.05, 0.12), "base_sat": (0.3, 0.5), "base_val": (0.5, 0.7), "accent_hue": (0.55, 0.65), "accent_sat": (0.4, 0.7), "accent_val": (0.7, 0.9)},
    "scavenger": {"base_hue": (0.08, 0.12), "base_sat": (0.4, 0.6), "base_val": (0.3, 0.5), "accent_hue": (0.12, 0.18), "accent_sat": (0.6, 0.9), "accent_val": (0.7, 0.95)},
    "territorial": {"base_hue": (0.75, 0.85), "base_sat": (0.4, 0.6), "base_val": (0.2, 0.4), "accent_hue": (0.05, 0.1), "accent_sat": (0.7, 1.0), "accent_val": (0.6, 0.9)},
    "curious": {"base_hue": (0.8, 0.9), "base_sat": (0.4, 0.6), "base_val": (0.5, 0.7), "accent_hue": (0.45, 0.55), "accent_sat": (0.5, 0.8), "accent_val": (0.7, 0.9)},
    "parasitic": {"base_hue": (0.85, 0.95), "base_sat": (0.5, 0.7), "base_val": (0.1, 0.3), "accent_hue": (0.3, 0.4), "accent_sat": (0.7, 1.0), "accent_val": (0.6, 0.9)},
    "guardian": {"base_hue": (0.3, 0.4), "base_sat": (0.4, 0.6), "base_val": (0.3, 0.5), "accent_hue": (0.12, 0.18), "accent_sat": (0.7, 1.0), "accent_val": (0.8, 1.0)},
    "ambush": {"base_hue": (0.9, 0.98), "base_sat": (0.3, 0.5), "base_val": (0.05, 0.15), "accent_hue": (0.85, 0.95), "accent_sat": (0.5, 0.8), "accent_val": (0.4, 0.7)},
    "void": {"base_hue": (0.0, 0.0), "base_sat": (0.0, 0.1), "base_val": (0.0, 0.1), "accent_hue": (0.5, 0.6), "accent_sat": (0.3, 0.6), "accent_val": (0.3, 0.6)},
    "gentle_light": {"base_hue": (0.1, 0.15), "base_sat": (0.1, 0.3), "base_val": (0.8, 1.0), "accent_hue": (0.55, 0.6), "accent_sat": (0.2, 0.5), "accent_val": (0.9, 1.0)},
}


# Stage palette shifts (sanity-based visual corruption)
STAGE_PALETTE_SHIFT: dict[int, dict] = {
    1: {"saturation_mult": 1.0, "value_mult": 1.0, "hue_shift": 0.0, "glitch_chance": 0.0},
    2: {"saturation_mult": 0.8, "value_mult": 0.9, "hue_shift": 0.02, "glitch_chance": 0.02},
    3: {"saturation_mult": 0.5, "value_mult": 0.7, "hue_shift": 0.05, "glitch_chance": 0.1},
    4: {"saturation_mult": 0.2, "value_mult": 0.4, "hue_shift": 0.1, "glitch_chance": 0.3},
}


def load_archetypes(path: Path) -> dict[ArchetypeType, ArchetypeDef]:
    """Load archetype definitions from JSON."""
    with open(path) as f:
        data = json.load(f)

    result = {}
    for key, value in data.items():
        atype = ArchetypeType(key)
        result[atype] = ArchetypeDef(
            archetype_type=atype,
            base_drives=value["base_drives"],
            state_priorities=value["state_priorities"],
            social=SocialStructure(value["social"]),
            sanity_mods=SanityModifiers(thresholds={int(k): v for k, v in value["sanity_mods"].items()}),
            palette=value["palette"],
            vocal_profile=value["vocal_profile"],
            population=PopulationParams(**value["population"]),
            activity_cycle=ActivityCycle(value["activity_cycle"]),
            food_preference=value["food_preference"],
            is_cutscene=value["is_cutscene"]
        )
    return result


def load_body_plans(path: Path) -> dict[BodyPlanType, BodyPlanDef]:
    """Load body plan definitions from JSON."""
    with open(path) as f:
        data = json.load(f)

    result = {}
    for key, value in data.items():
        btype = BodyPlanType(key)
        result[btype] = BodyPlanDef(
            body_plan_type=btype,
            description=value["description"],
            limbs=value["limbs"],
            gaits=[GaitType(g) for g in value["gaits"]],
            default_gait=GaitType(value["default_gait"]),
            size_range=[SizeClass(s) for s in value["size_range"]],
            archetype_affinity=[ArchetypeType(a) for a in value["archetype_affinity"]],
            locomotion_type=LocomotionType(value["locomotion_type"]),
            foot_friction=value["foot_friction"],
            climb_capable=value["climb_capable"],
            swim_capable=value["swim_capable"]
        )
    return result