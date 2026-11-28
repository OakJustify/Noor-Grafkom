"""
prc-creature — Procedural Creature Generation Module

Public API:
    generate_creature()          -> CreatureDefinition (morphology + behavior + audio + visual params)
    CreatureFactory              -> Spawn/despawn management with population limits
    ProceduralCreatureInstance   -> Active in-game creature with behavior + animation + cached audio
    MorphologyGenerator          -> Low-level morphology generation
    BehaviorStateMachine         -> Drive-based utility AI
    CreatureAudioGenerator       -> In-memory vocal synthesis (WAV cache optional)
    VisualRenderer               -> pycairo texture generation (offline)
    CreatureVector               -> Runtime pygame vector renderer

Data Files:
    data/creatures/archetypes.json    -> 10 archetypes with drives, sanity mods, vocal profiles
    data/creatures/body_plans.json    -> 8 body plans with limbs, gaits, size affinity

Deterministic seed = 42 across all systems.
"""

from .archetype_definition import (
    ArchetypeType,
    BodyPlanType,
    SizeClass,
    GaitType,
    SocialStructure,
    ActivityCycle,
    LocomotionType,
    load_archetypes,
    load_body_plans,
    SIZE_CLASS_PARAMS,
    VOCAL_PROFILES,
    PALETTES,
    STAGE_PALETTE_SHIFT,
)

from .morphology_generator import (
    MorphologyGenerator,
    generate_creature,
    CreatureDefinition,
)

from .behavior_engine import (
    BehaviorStateMachine,
    EnvironmentalContext,
    CreatureState,
)

from .audio_synthesizer import (
    CreatureAudioGenerator,
)

from .population_manager import (
    PopulationManager,
)

from .creature_factory import (
    CreatureFactory,
    ProceduralCreatureInstance,
)

from .visual_renderer import (
    VisualRenderer,
    RenderedCreatureVisuals,
    generate_creature_visuals,
)

from .vector_renderer import CreatureVector

__all__ = [
    # Types & Enums
    "ArchetypeType",
    "BodyPlanType",
    "SizeClass",
    "GaitType",
    "SocialStructure",
    "ActivityCycle",
    "LocomotionType",
    "CreatureDefinition",
    # Data Loading
    "load_archetypes",
    "load_body_plans",
    # Constants
    "SIZE_CLASS_PARAMS",
    "VOCAL_PROFILES",
    "PALETTES",
    "STAGE_PALETTE_SHIFT",
    # Core Generators
    "MorphologyGenerator",
    "generate_creature",
    # Behavior
    "BehaviorStateMachine",
    "EnvironmentalContext",
    "CreatureState",
    # Audio
    "CreatureAudioGenerator",
    # Population
    "PopulationManager",
    # Factory
    "CreatureFactory",
    "ProceduralCreatureInstance",
    # Visual
    "VisualRenderer",
    "RenderedCreatureVisuals",
    "generate_creature_visuals",
    "CreatureVector",
]