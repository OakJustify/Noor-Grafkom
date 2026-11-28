"""Factory & controller for procedural creatures.

Main public entry point for prc-creature.  It combines morphology, behavior,
in-memory vocal synthesis, population limits and the runtime vector renderer.
No animation-controller shim is needed: the renderer consumes the generated
``CreatureDefinition`` directly.
"""

from __future__ import annotations

import numpy as np

from .archetype_definition import (
    ActivityCycle,
    ArchetypeType,
    BodyPlanType,
    SanityModifiers,
    SizeClass,
    SocialStructure,
)
from .audio_synthesizer import CreatureAudioGenerator
from .behavior_engine import BehaviorStateMachine, EnvironmentalContext
from .morphology_generator import CreatureDefinition, MorphologyGenerator
from .population_manager import PopulationManager
from .vector_renderer import CreatureVector


class ProceduralCreatureInstance:
    """Active in-game instance of a procedurally generated creature."""

    def __init__(
        self,
        instance_id: str,
        definition: CreatureDefinition,
        spawn_pos: tuple[float, float],
        audio_gen: CreatureAudioGenerator,
    ):
        self.instance_id = instance_id
        self.def_ = definition
        self.pos = spawn_pos
        self.rotation: float = 0.0
        self.velocity: tuple[float, float] = (0.0, 0.0)

        self.behavior = BehaviorStateMachine(
            creature_id=instance_id,
            archetype=definition.archetype,
            base_drives=definition.base_drives,
            state_priorities=definition.state_priorities,
            sanity_mods=SanityModifiers(thresholds=definition.sanity_modifiers),
            social=SocialStructure(definition.social_structure),
            activity_cycle=ActivityCycle(definition.activity_cycle),
            seed=definition.seed,
        )

        self.audio_gen = audio_gen
        self.vocal_audio: dict[str, np.ndarray] = {}
        self._preload_audio()

        self.renderer = CreatureVector(definition)
        self.state = self.behavior.current_state.value

    def _preload_audio(self):
        """Synthesize all vocal calls in memory; nothing is written to disk."""
        self.vocal_audio = self.audio_gen.synthesize_vocalizations(
            self.def_.vocal, seed=self.def_.seed
        )

    def update(self, dt: float, ctx: EnvironmentalContext):
        """Update behavior and the vector pose for the current frame."""
        self.state = self.behavior.update(ctx).value
        self.renderer.update(
            dt,
            self.pos[0],
            self.pos[1],
            vx=self.velocity[0],
            vy=self.velocity[1],
            state=self.state,
            on_ground=True,
        )

    def play_vocal(self, call_type: str) -> np.ndarray | None:
        """Return a pre-synthesized vocal buffer, or None for an unknown call."""
        return self.vocal_audio.get(call_type)


class CreatureFactory:
    """Factory for managing procedural creature creation and population."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.morph_gen = MorphologyGenerator(seed)
        self.audio_gen = CreatureAudioGenerator(seed)
        self.pop_mgr = PopulationManager(seed)
        self.active_instances: dict[str, ProceduralCreatureInstance] = {}

    def spawn_creature(
        self,
        archetype: ArchetypeType,
        spawn_pos: tuple[float, float],
        stage: int = 1,
        body_plan: BodyPlanType | None = None,
        size_class: SizeClass | None = None,
    ) -> ProceduralCreatureInstance | None:
        """Spawn a creature with cached audio and territory allocation."""
        arch_def = self.morph_gen.archetypes[archetype]
        if not self.pop_mgr.can_spawn_creature(
            archetype, stage, len(self.active_instances), arch_def.population
        ):
            return None

        instance_id = f"creature_{archetype.value}_{len(self.active_instances) + 1}"
        definition = self.morph_gen.generate(
            archetype=archetype,
            body_plan=body_plan,
            size_class=size_class,
            stage=stage,
            override_seed=self.seed + len(self.active_instances),
        )

        instance = ProceduralCreatureInstance(
            instance_id=instance_id,
            definition=definition,
            spawn_pos=spawn_pos,
            audio_gen=self.audio_gen,
        )
        self.pop_mgr.allocate_territory(
            instance_id, archetype, spawn_pos, arch_def.population
        )
        self.active_instances[instance_id] = instance
        return instance

    def despawn_creature(self, instance_id: str):
        """Despawn and remove a creature."""
        if instance_id in self.active_instances:
            del self.active_instances[instance_id]
            self.pop_mgr.remove_creature(instance_id)
