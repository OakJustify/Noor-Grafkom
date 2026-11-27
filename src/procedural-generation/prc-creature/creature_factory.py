"""Factory & Controller for Procedural Creatures

Main public entry point for prc-creature.
Integrates MorphologyGenerator, BehaviorStateMachine, AudioSynthesizer, PopulationManager,
and bridges directly to prc-animation's ProceduralAnimationController.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import math

from .archetype_definition import ArchetypeType, BodyPlanType, SizeClass, SanityModifiers, SocialStructure, ActivityCycle
from .morphology_generator import MorphologyGenerator, CreatureDefinition, generate_creature
from .behavior_engine import BehaviorStateMachine, EnvironmentalContext, CreatureState
from .audio_synthesizer import CreatureAudioGenerator
from .population_manager import PopulationManager

# Dynamic import of prc-animation controller to bridge modular systems
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "prc-animation"))
    from ik_rig import IKRig
    from procedural_animation import ProceduralAnimationController
except ImportError:
    IKRig = None
    ProceduralAnimationController = None


class ProceduralCreatureInstance:
    """Active in-game instance of a procedurally generated creature."""

    def __init__(
        self,
        instance_id: str,
        definition: CreatureDefinition,
        spawn_pos: tuple[float, float],
        audio_gen: CreatureAudioGenerator
    ):
        self.instance_id = instance_id
        self.def_ = definition
        self.pos = spawn_pos
        self.rotation: float = 0.0
        self.velocity: tuple[float, float] = (0.0, 0.0)

        # 1. Behavior State Machine
        self.behavior = BehaviorStateMachine(
            creature_id=instance_id,
            archetype=definition.archetype,
            base_drives=definition.base_drives,
            state_priorities=definition.state_priorities,
            sanity_mods=SanityModifiers(thresholds=definition.sanity_modifiers),
            social=SocialStructure(definition.social_structure),
            activity_cycle=ActivityCycle(definition.activity_cycle),
            seed=definition.seed
        )

        # 2. Audio Generator & Pre-cached Audio
        self.audio_gen = audio_gen
        self.vocal_audio_paths: dict[str, Path] = {}
        self._preload_audio()

        # 3. Procedural Animation Controller Bridge (if prc-animation available)
        self.anim_controller = None
        if ProceduralAnimationController is not None:
            # Map CreatureDefinition to prc-animation format
            self.anim_controller = ProceduralAnimationController(
                body_mass=definition.body["mass"],
                body_size=(definition.body["length"], definition.body["width"]),
                seed=definition.seed
            )

    def _preload_audio(self):
        """Pre-generate and cache all vocal calls for this creature upon spawn."""
        for call_type in self.def_.vocal.call_types.keys():
            wav_path = self.audio_gen.get_or_generate_audio(
                creature_id=self.instance_id,
                call_type=call_type,
                vocal=self.def_.vocal,
                seed=self.def_.seed
            )
            self.vocal_audio_paths[call_type] = wav_path

    def update(self, dt: float, ctx: EnvironmentalContext):
        """Update creature state, animation, and behavior for current frame."""
        # Update Behavior
        current_state = self.behavior.update(ctx)

        # Update Procedural Animation
        if self.anim_controller is not None:
            # Drive gait based on velocity and state
            speed = math.hypot(self.velocity[0], self.velocity[1])
            self.anim_controller.update(dt, self.pos, self.rotation, speed)

    def play_vocal(self, call_type: str) -> Path | None:
        """Get path to pre-generated vocal sound file."""
        return self.vocal_audio_paths.get(call_type)


class CreatureFactory:
    """Factory for managing procedural creature creation and population."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.morph_gen = MorphologyGenerator(seed)
        self.audio_gen = CreatureAudioGenerator()
        self.pop_mgr = PopulationManager(seed)
        self.active_instances: dict[str, ProceduralCreatureInstance] = {}

    def spawn_creature(
        self,
        archetype: ArchetypeType,
        spawn_pos: tuple[float, float],
        stage: int = 1,
        body_plan: BodyPlanType | None = None,
        size_class: SizeClass | None = None
    ) -> ProceduralCreatureInstance | None:
        """Spawn a new procedural creature with auto cached audio and territory allocation."""
        # 1. Check Population Limit
        arch_def = self.morph_gen.archetypes[archetype]
        if not self.pop_mgr.can_spawn_creature(archetype, stage, len(self.active_instances), arch_def.population):
            return None

        # 2. Generate Creature Definition
        instance_id = f"creature_{archetype.value}_{len(self.active_instances)+1}"
        definition = self.morph_gen.generate(
            archetype=archetype,
            body_plan=body_plan,
            size_class=size_class,
            stage=stage,
            override_seed=self.seed + len(self.active_instances)
        )

        # 3. Create Instance & Pre-cache Audio
        instance = ProceduralCreatureInstance(
            instance_id=instance_id,
            definition=definition,
            spawn_pos=spawn_pos,
            audio_gen=self.audio_gen
        )

        # 4. Allocate Territory
        self.pop_mgr.allocate_territory(instance_id, archetype, spawn_pos, arch_def.population)
        self.active_instances[instance_id] = instance
        return instance

    def despawn_creature(self, instance_id: str):
        """Despawn and remove a creature."""
        if instance_id in self.active_instances:
            del self.active_instances[instance_id]
            self.pop_mgr.remove_creature(instance_id)
