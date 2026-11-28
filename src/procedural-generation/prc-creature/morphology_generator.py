"""Morphology Generator — Body Plan → CreatureDefinition

Generates deterministic creature morphologies compatible with prc-animation.
Uses seed=42 for all randomness.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import random
import math
from pathlib import Path

from .archetype_definition import (
    BodyPlanType, SizeClass, ArchetypeType, GaitType,
    BodyPlanDef, ArchetypeDef, SIZE_CLASS_PARAMS,
    LimbDef, LimbSegmentDef, LocomotionType,
    load_archetypes, load_body_plans,
    VOCAL_PROFILES, PALETTES, STAGE_PALETTE_SHIFT
)


# ──────────────────────────────────────────────────────────────
# Output: CreatureDefinition (compatible with prc-animation)
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CreatureSegmentDef:
    """Single segment for prc-animation."""
    length: float
    thickness: float
    joint_limit_deg: tuple[float, float]
    compliance: float


@dataclass(frozen=True)
class CreatureLimbDef:
    """Limb definition for prc-animation."""
    name: str
    limb_type: Literal["leg", "arm", "wing", "tail", "neck", "head", "tendril", "pseudopod"]
    anchor: tuple[float, float]
    segments: list[CreatureSegmentDef]
    nominal_offset: tuple[float, float] | None
    gait_phase_offset: float
    is_ground_contact: bool


@dataclass(frozen=True)
class GaitDef:
    """Gait parameters for prc-animation gait generator."""
    gait_type: GaitType
    duty_cycle: float          # Fraction of cycle foot is on ground (0.5-0.75)
    phase_offsets: list[float] # Per-limb phase offset (0-1)
    frequency_range: tuple[float, float]  # Hz at speed 1.0
    speed_range: tuple[float, float]      # Body lengths per second
    max_step_length: float
    step_height: float
    compliance: float = 0.1


@dataclass(frozen=True)
class VocalParams:
    """Vocal synthesis parameters."""
    fundamental_freq: float
    formant_ratios: list[float]
    breathiness: float
    roughness: float
    call_types: dict[str, dict]  # call_type -> {pattern, duration, pitch_range, rhythm, harmonicity}


@dataclass(frozen=True)
class VisualParams:
    """Visual generation parameters."""
    palette_name: str
    base_hue_range: tuple[float, float]
    base_sat_range: tuple[float, float]
    base_val_range: tuple[float, float]
    accent_hue_range: tuple[float, float]
    accent_sat_range: tuple[float, float]
    accent_val_range: tuple[float, float]
    pattern_type: str
    pattern_seed: int
    glitch_stage: int


@dataclass(frozen=True)
class CreatureDefinition:
    """Complete creature definition — output of MorphologyGenerator.
    
    Compatible with prc-animation.ProceduralAnimationController.
    """
    # Identity
    seed: int
    archetype: ArchetypeType
    body_plan: BodyPlanType
    size_class: SizeClass
    stage_spawned: int

    # Morphology
    body: dict  # mass, width, height, segment_count
    limbs: list[CreatureLimbDef]
    gaits: dict[GaitType, GaitDef]

    # Behavior (references)
    behavior_archetype: ArchetypeType
    state_priorities: list[str]
    base_drives: list[str]
    social_structure: str
    activity_cycle: str
    food_preference: list[str]
    is_cutscene: bool

    # Audio
    vocal: VocalParams
    footprint_sound_profile: str  # "light", "medium", "heavy", "wet", "silent"

    # Visual
    visual: VisualParams

    # Population
    population_params: dict

    # Sanity
    sanity_modifiers: dict[int, dict[str, float]]


# ──────────────────────────────────────────────────────────────
# Morphology Generator
# ──────────────────────────────────────────────────────────────

class MorphologyGenerator:
    """Generate CreatureDefinition from archetype + body plan + size."""

    DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "creatures"

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.archetypes = load_archetypes(self.DATA_DIR / "archetypes.json")
        self.body_plans = load_body_plans(self.DATA_DIR / "body_plans.json")

    def generate(
        self,
        archetype: ArchetypeType,
        body_plan: BodyPlanType | None = None,
        size_class: SizeClass | None = None,
        stage: int = 1,
        override_seed: int | None = None
    ) -> CreatureDefinition:
        """Generate a complete creature definition."""
        if override_seed is not None:
            rng = random.Random(override_seed)
        else:
            rng = self.rng

        arch = self.archetypes[archetype]

        # Select body plan if not specified
        if body_plan is None:
            body_plan = rng.choice(arch.body_plan_affinity if hasattr(arch, 'body_plan_affinity') else list(BodyPlanType))
        bp = self.body_plans[body_plan]

        # Select size class if not specified
        if size_class is None:
            size_class = rng.choice(bp.size_range)
        size_params = SIZE_CLASS_PARAMS[size_class]

        # Generate all components
        body = self._generate_body(size_params, bp, rng)
        limbs = self._generate_limbs(body, bp, size_params, rng)
        gaits = self._generate_gaits(limbs, bp, size_params, rng)
        vocal = self._generate_vocal(arch, body, size_params, rng)
        visual = self._generate_visual(arch, stage, rng)
        footprint = self._determine_footprint(body, bp)

        return CreatureDefinition(
            seed=override_seed or self.seed,
            archetype=archetype,
            body_plan=body_plan,
            size_class=size_class,
            stage_spawned=stage,
            body=body,
            limbs=limbs,
            gaits=gaits,
            behavior_archetype=archetype,
            state_priorities=arch.state_priorities,
            base_drives=arch.base_drives,
            social_structure=arch.social.value,
            activity_cycle=arch.activity_cycle.value,
            food_preference=arch.food_preference,
            is_cutscene=arch.is_cutscene,
            vocal=vocal,
            footprint_sound_profile=footprint,
            visual=visual,
            population_params={
                "carrying_capacity": arch.population.carrying_capacity,
                "territory_size": arch.population.territory_size,
                "reproduction_rate": arch.population.reproduction_rate,
                "mortality_rate": arch.population.mortality_rate
            },
            sanity_modifiers=arch.sanity_mods.thresholds
        )

    def _generate_body(self, size_params: SizeClassParams, bp: BodyPlanDef, rng: random.Random) -> dict:
        """Generate body parameters."""
        # Mass: cubic scaling with length
        length = rng.uniform(*size_params.body_length_range)
        mass = rng.uniform(*size_params.mass_range)

        # Width/height proportions based on locomotion
        if bp.locomotion_type == LocomotionType.SERPENTINE:
            width = length * rng.uniform(0.08, 0.15)
            height = width
            # Use body_segments range from JSON if available
            seg_config = bp.limbs.get("body_segments", [8, 20])
            if isinstance(seg_config, list) and len(seg_config) == 2:
                segment_count = rng.randint(seg_config[0], seg_config[1])
            else:
                segment_count = seg_config if isinstance(seg_config, int) else rng.randint(8, 20)
        elif bp.locomotion_type == LocomotionType.FLOATING:
            width = length * rng.uniform(0.6, 1.0)
            height = width * rng.uniform(0.5, 0.8)
            segment_count = 1
        elif bp.locomotion_type == LocomotionType.AMORPHOUS:
            width = length * rng.uniform(0.4, 0.8)
            height = width * rng.uniform(0.3, 0.6)
            segment_count = 1
        else:
            width = length * rng.uniform(0.3, 0.5)
            height = width * rng.uniform(0.6, 1.0)
            segment_count = 1

        return {
            "mass": mass,
            "length": length,
            "width": width,
            "height": height,
            "segment_count": segment_count
        }

    def _generate_limbs(
        self,
        body: dict,
        bp: BodyPlanDef,
        size_params: SizeClassParams,
        rng: random.Random
    ) -> list[CreatureLimbDef]:
        """Generate limb definitions from body plan."""
        limbs = []
        limb_config = bp.limbs

        # Helper to create segments
        def make_segments(ratios: list[float], total_length: float, base_thickness: float) -> list[CreatureSegmentDef]:
            segs = []
            for i, ratio in enumerate(ratios):
                seg_length = total_length * ratio
                # Taper thickness towards tip
                thickness = base_thickness * (1.0 - 0.3 * (i / max(1, len(ratios) - 1)))
                segs.append(CreatureSegmentDef(
                    length=seg_length,
                    thickness=thickness,
                    joint_limit_deg=(-90.0, 90.0),
                    compliance=0.1 + 0.05 * i  # More compliant towards tip
                ))
            return segs

        body_len = body["length"]
        leg_len_mult = rng.uniform(*size_params.leg_length_mult)

        # Legs
        if "legs" in limb_config:
            leg_count = limb_config["legs"]
            if isinstance(leg_count, list):
                leg_count = rng.randint(leg_count[0], leg_count[1])

            leg_segs = limb_config.get("leg_segments", 3)
            leg_ratios = limb_config.get("leg_segment_ratios", [0.4, 0.35, 0.25][:leg_segs])
            leg_total_len = body_len * 0.4 * leg_len_mult
            base_thick = body["width"] * 0.15

            spacing_config = limb_config.get("leg_pair_spacing", [0.25] * (leg_count // 2))
            if len(spacing_config) < leg_count // 2:
                spacing = [0.2 + 0.6 * i / max(1, leg_count // 2 - 1) for i in range(leg_count // 2)]
            else:
                spacing = spacing_config

            for i in range(leg_count):
                pair_idx = i // 2
                side = 1 if i % 2 == 0 else -1
                y_offset = spacing[pair_idx] if pair_idx < len(spacing) else 0.5

                anchor_x = 0.3 + 0.4 * y_offset
                anchor_y = 0.5 + side * 0.4

                # Phase offset for gait
                if bp.default_gait == GaitType.TROT:
                    phase = 0.5 if i % 2 == 0 else 0.0
                elif bp.default_gait == GaitType.WAVE:
                    phase = i / leg_count
                else:
                    phase = rng.uniform(0, 1)

                limbs.append(CreatureLimbDef(
                    name=f"leg_{i}",
                    limb_type="leg",
                    anchor=(anchor_x, anchor_y),
                    segments=make_segments(leg_ratios, leg_total_len, base_thick),
                    nominal_offset=(0.0, -leg_total_len * 0.8 * side),
                    gait_phase_offset=phase,
                    is_ground_contact=True
                ))

        # Arms
        if "arms" in limb_config:
            arm_count = limb_config["arms"]
            if isinstance(arm_count, list):
                arm_count = rng.randint(arm_count[0], arm_count[1])

            arm_segs = limb_config.get("arm_segments", 3)
            arm_ratios = limb_config.get("arm_segment_ratios", [0.4, 0.35, 0.25][:arm_segs])
            arm_total_len = body_len * 0.35 * leg_len_mult
            base_thick = body["width"] * 0.12

            for i in range(arm_count):
                side = 1 if i % 2 == 0 else -1
                anchor_x = 0.2 + 0.1 * i
                anchor_y = 0.3 + side * 0.35

                limbs.append(CreatureLimbDef(
                    name=f"arm_{i}",
                    limb_type="arm",
                    anchor=(anchor_x, anchor_y),
                    segments=make_segments(arm_ratios, arm_total_len, base_thick),
                    nominal_offset=(arm_total_len * 0.5, -arm_total_len * 0.3),
                    gait_phase_offset=rng.uniform(0, 1),
                    is_ground_contact=False
                ))

        # Wings
        if "wings" in limb_config:
            wing_segs = limb_config.get("wing_segments", 3)
            wing_ratios = limb_config.get("wing_segment_ratios", [0.3, 0.4, 0.3][:wing_segs])
            wing_total_len = body_len * 0.8
            base_thick = body["width"] * 0.05

            for i in range(limb_config["wings"]):
                side = 1 if i % 2 == 0 else -1
                limbs.append(CreatureLimbDef(
                    name=f"wing_{i}",
                    limb_type="wing",
                    anchor=(0.3, 0.35 + side * 0.3),
                    segments=make_segments(wing_ratios, wing_total_len, base_thick),
                    nominal_offset=(wing_total_len * 0.6 * side, -wing_total_len * 0.2),
                    gait_phase_offset=0.5 if i == 0 else 0.0,
                    is_ground_contact=False
                ))

        # Tail
        if limb_config.get("tail"):
            tail_segs = limb_config.get("tail_segments", 4)
            tail_ratios = limb_config.get("tail_segment_ratios", [0.3, 0.25, 0.25, 0.2][:tail_segs])
            tail_total_len = body_len * 0.6
            base_thick = body["width"] * 0.15

            limbs.append(CreatureLimbDef(
                name="tail",
                limb_type="tail",
                anchor=(0.95, 0.5),
                segments=make_segments(tail_ratios, tail_total_len, base_thick),
                nominal_offset=(tail_total_len * 0.5, 0.0),
                gait_phase_offset=0.0,
                is_ground_contact=False
            ))

        # Neck
        if limb_config.get("neck"):
            neck_segs = limb_config.get("neck_segments", 2)
            neck_ratios = limb_config.get("neck_segment_ratios", [0.6, 0.4][:neck_segs])
            neck_total_len = body_len * 0.25
            base_thick = body["width"] * 0.18

            limbs.append(CreatureLimbDef(
                name="neck",
                limb_type="neck",
                anchor=(0.15, 0.5),
                segments=make_segments(neck_ratios, neck_total_len, base_thick),
                nominal_offset=(neck_total_len, 0.0),
                gait_phase_offset=0.0,
                is_ground_contact=False
            ))

        # Head
        if limb_config.get("head"):
            head_size = body_len * limb_config.get("head_size_ratio", 0.15)
            limbs.append(CreatureLimbDef(
                name="head",
                limb_type="head",
                anchor=(0.05, 0.5),
                segments=[CreatureSegmentDef(
                    length=head_size,
                    thickness=head_size * 0.8,
                    joint_limit_deg=(-45.0, 45.0),
                    compliance=0.05
                )],
                nominal_offset=None,
                gait_phase_offset=0.0,
                is_ground_contact=False
            ))

        # Tendrils (floating)
        if "tendrils" in limb_config:
            tendril_count = rng.randint(*limb_config["tendrils"])
            tendril_segs = limb_config["tendril_segments"]
            if isinstance(tendril_segs, list):
                tendril_segs = rng.randint(tendril_segs[0], tendril_segs[1])

            for i in range(tendril_count):
                seg_ratios = [1.0 / tendril_segs] * tendril_segs
                tendril_len = body_len * rng.uniform(0.3, 0.8)
                angle = rng.uniform(0, 2 * math.pi)

                limbs.append(CreatureLimbDef(
                    name=f"tendril_{i}",
                    limb_type="tendril",
                    anchor=(0.5 + 0.3 * math.cos(angle), 0.5 + 0.3 * math.sin(angle)),
                    segments=make_segments(seg_ratios, tendril_len, body["width"] * 0.05),
                    nominal_offset=(tendril_len * math.cos(angle), tendril_len * math.sin(angle)),
                    gait_phase_offset=rng.uniform(0, 1),
                    is_ground_contact=False
                ))

        # Pseudopods (amorphous)
        if "pseudopods" in limb_config:
            pod_count = rng.randint(*limb_config["pseudopods"])
            for i in range(pod_count):
                pod_segs = rng.randint(*limb_config["pod_segments"])
                pod_len = body_len * rng.uniform(0.2, 0.6)
                angle = rng.uniform(0, 2 * math.pi)

                limbs.append(CreatureLimbDef(
                    name=f"pseudopod_{i}",
                    limb_type="pseudopod",
                    anchor=(0.5 + 0.2 * math.cos(angle), 0.5 + 0.2 * math.sin(angle)),
                    segments=make_segments([1.0/pod_segs]*pod_segs, pod_len, body["width"] * 0.1),
                    nominal_offset=(pod_len * math.cos(angle), pod_len * math.sin(angle)),
                    gait_phase_offset=rng.uniform(0, 1),
                    is_ground_contact=rng.random() < 0.3
                ))

        return limbs

    def _generate_gaits(
        self,
        limbs: list[CreatureLimbDef],
        bp: BodyPlanDef,
        size_params: SizeClassParams,
        rng: random.Random
    ) -> dict[GaitType, GaitDef]:
        """Generate gait parameters for all available gaits."""
        gaits = {}
        leg_limbs = [l for l in limbs if l.limb_type == "leg" and l.is_ground_contact]
        leg_count = len(leg_limbs)

        # Base step length from leg length
        avg_leg_len = sum(sum(s.length for s in l.segments) for l in leg_limbs) / max(1, leg_count)
        base_step = avg_leg_len * 1.2

        for gait_type in bp.gaits:
            if gait_type == GaitType.WALK:
                duty = 0.75
                phase_offs = [i / leg_count * 0.5 for i in range(leg_count)] if leg_count > 0 else [0]
                freq = (1.5, 3.0)
                speed = (0.5, 1.0)
            elif gait_type == GaitType.TROT:
                duty = 0.5
                phase_offs = [0.5 if i % 2 == 0 else 0.0 for i in range(leg_count)]
                freq = (2.5, 4.5)
                speed = (1.5, 2.5)
            elif gait_type == GaitType.GALLOP:
                duty = 0.4
                phase_offs = [0.0, 0.1, 0.6, 0.7][:leg_count]
                freq = (3.0, 5.0)
                speed = (2.5, 4.0)
            elif gait_type == GaitType.BOUND:
                duty = 0.35
                phase_offs = [0.0, 0.0, 0.5, 0.5][:leg_count]
                freq = (2.5, 4.0)
                speed = (2.0, 3.5)
            elif gait_type == GaitType.RUN:
                duty = 0.45
                phase_offs = [0.0, 0.5][:leg_count]
                freq = (3.0, 5.0)
                speed = (2.0, 3.5)
            elif gait_type == GaitType.TRIPOD:
                duty = 0.5
                phase_offs = [0.0, 0.5, 0.0, 0.5, 0.0, 0.5][:leg_count]
                freq = (4.0, 7.0)
                speed = (1.5, 3.0)
            elif gait_type == GaitType.WAVE:
                duty = 0.6
                phase_offs = [i / leg_count for i in range(leg_count)]
                freq = (1.5, 3.0)
                speed = (0.8, 1.5)
            elif gait_type == GaitType.UNDULATE:
                duty = 0.8
                phase_offs = [0.0]
                freq = (0.8, 1.5)
                speed = (0.5, 1.2)
            elif gait_type == GaitType.DRIFT:
                duty = 1.0
                phase_offs = [0.0]
                freq = (0.1, 0.3)
                speed = (0.1, 0.3)
            else:
                duty = 0.6
                phase_offs = [i / max(1, leg_count) for i in range(max(1, leg_count))]
                freq = (1.0, 2.0)
                speed = (0.5, 1.0)

            speed_mult = rng.uniform(*size_params.speed_mult)
            gaits[gait_type] = GaitDef(
                gait_type=gait_type,
                duty_cycle=duty,
                phase_offsets=phase_offs,
                frequency_range=(freq[0] * speed_mult, freq[1] * speed_mult),
                speed_range=(speed[0] * speed_mult, speed[1] * speed_mult),
                max_step_length=base_step * rng.uniform(0.8, 1.2),
                step_height=rng.uniform(*size_params.step_height_range),
                compliance=0.1
            )

        return gaits

    def _generate_vocal(
        self,
        arch: ArchetypeDef,
        body: dict,
        size_params: SizeClassParams,
        rng: random.Random
    ) -> VocalParams:
        """Generate vocal parameters from archetype and morphology."""
        profile = VOCAL_PROFILES[arch.vocal_profile]

        # Fundamental frequency scaled by mass (larger = lower)
        mass = body["mass"]
        base_f0 = rng.uniform(*profile["fundamental_range"])
        f0 = base_f0 * (10.0 / mass) ** 0.33  # Cube root scaling

        # Formants scaled by body length (longer neck = lower formants)
        length = body["length"]
        formant_scale = (160.0 / length) ** 0.5  # 160 = medium baseline
        formants = [r * formant_scale for r in profile["formant_ratios"]]

        return VocalParams(
            fundamental_freq=f0,
            formant_ratios=formants,
            breathiness=profile["breathiness"] * rng.uniform(0.9, 1.1),
            roughness=profile["roughness"] * rng.uniform(0.9, 1.1),
            call_types=profile["call_types"]
        )

    def _generate_visual(
        self,
        arch: ArchetypeDef,
        stage: int,
        rng: random.Random
    ) -> VisualParams:
        """Generate visual parameters."""
        palette = PALETTES[arch.palette]
        stage_shift = STAGE_PALETTE_SHIFT.get(stage, STAGE_PALETTE_SHIFT[1])

        # Pattern type based on archetype + body plan
        patterns = ["scales", "fur", "skin", "chitin", "slime", "feathers", "shadow", "membrane"]
        pattern_weights = {
            "predator": [0.3, 0.2, 0.2, 0.1, 0.05, 0.05, 0.05, 0.05],
            "prey": [0.1, 0.3, 0.3, 0.05, 0.05, 0.1, 0.05, 0.05],
            "scavenger": [0.15, 0.15, 0.2, 0.2, 0.1, 0.05, 0.1, 0.05],
            "parasitic": [0.05, 0.05, 0.1, 0.15, 0.3, 0.05, 0.15, 0.15],
            "void_walker": [0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.5, 0.4],
            "gentle_light": [0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.1, 0.8],
        }
        weights = pattern_weights.get(arch.archetype_type.value, [1/8]*8)
        pattern = rng.choices(patterns, weights=weights)[0]

        return VisualParams(
            palette_name=arch.palette,
            base_hue_range=palette["base_hue"],
            base_sat_range=(palette["base_sat"][0] * stage_shift["saturation_mult"],
                            palette["base_sat"][1] * stage_shift["saturation_mult"]),
            base_val_range=(palette["base_val"][0] * stage_shift["value_mult"],
                            palette["base_val"][1] * stage_shift["value_mult"]),
            accent_hue_range=(
                (palette["accent_hue"][0] + stage_shift["hue_shift"]) % 1.0,
                (palette["accent_hue"][1] + stage_shift["hue_shift"]) % 1.0
            ),
            accent_sat_range=palette["accent_sat"],
            accent_val_range=palette["accent_val"],
            pattern_type=pattern,
            pattern_seed=rng.randint(0, 2**31 - 1),
            glitch_stage=stage
        )

    def _determine_footprint(self, body: dict, bp: BodyPlanDef) -> str:
        """Determine footstep sound profile."""
        mass = body["mass"]
        if bp.locomotion_type == LocomotionType.FLOATING:
            return "silent"
        elif bp.locomotion_type == LocomotionType.AMORPHOUS:
            return "wet"
        elif mass < 5:
            return "light"
        elif mass < 50:
            return "medium"
        else:
            return "heavy"


# ──────────────────────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────────────────────

def generate_creature(
    archetype: ArchetypeType,
    body_plan: BodyPlanType | None = None,
    size_class: SizeClass | None = None,
    stage: int = 1,
    seed: int = 42
) -> CreatureDefinition:
    """One-shot creature generation."""
    gen = MorphologyGenerator(seed)
    return gen.generate(archetype, body_plan, size_class, stage)