"""Unit tests for prc-creature module."""

import unittest
from pathlib import Path

from src.procedural_generation.prc_creature.archetype_definition import (
    load_archetypes,
    load_body_plans,
    ArchetypeType,
    BodyPlanType,
    SizeClass,
    SanityModifiers
)
from src.procedural_generation.prc_creature.morphology_generator import (
    generate_creature,
    CreatureDefinition
)
from src.procedural_generation.prc_creature.audio_synthesizer import (
    CreatureAudioGenerator
)
from src.procedural_generation.prc_creature.behavior_engine import (
    BehaviorStateMachine,
    EnvironmentalContext,
    CreatureState
)
from src.procedural_generation.prc_creature.population_manager import (
    PopulationManager
)
from src.procedural_generation.prc_creature.creature_factory import (
    CreatureFactory,
    ProceduralCreatureInstance
)


class TestCreatureModule(unittest.TestCase):
    def setUp(self):
        self.archetypes = load_archetypes(Path("data/creatures/archetypes.json"))
        self.body_plans = load_body_plans(Path("data/creatures/body_plans.json"))

    def test_archetypes_and_body_plans_loaded(self):
        self.assertGreaterEqual(len(self.archetypes), 8)
        self.assertGreaterEqual(len(self.body_plans), 8)

    def test_morphology_generation(self):
        creature_def = generate_creature(
            archetype=ArchetypeType.PREDATOR,
            body_plan=BodyPlanType.QUADRUPED,
            size_class=SizeClass.MEDIUM,
            seed=42
        )
        self.assertEqual(creature_def.archetype, ArchetypeType.PREDATOR)
        self.assertEqual(creature_def.body_plan, BodyPlanType.QUADRUPED)
        self.assertGreater(creature_def.body["mass"], 0)
        self.assertGreater(len(creature_def.limbs), 0)

    def test_serpentine_morphology(self):
        creature_def = generate_creature(
            archetype=ArchetypeType.AMBUSH,
            body_plan=BodyPlanType.SERPENTINE,
            seed=42
        )
        self.assertGreaterEqual(creature_def.body["segment_count"], 8)
        self.assertLessEqual(creature_def.body["segment_count"], 20)

    def test_audio_synthesizer_and_cache(self):
        audio_gen = CreatureAudioGenerator(seed=42)
        creature_def = generate_creature(ArchetypeType.PREDATOR, seed=42)
        cache = audio_gen.generate_audio_cache("test_predator", creature_def.vocal, seed=42)
        self.assertTrue(cache.idle.exists())
        self.assertTrue(cache.alert.exists())
        self.assertTrue(cache.aggressive.exists())
        self.assertTrue(cache.pain.exists())
        self.assertTrue(cache.death.exists())

    def test_behavior_engine_state_transitions(self):
        creature_def = generate_creature(ArchetypeType.PREDATOR, seed=42)
        archetype_def = self.archetypes[ArchetypeType.PREDATOR]

        behavior = BehaviorStateMachine(
            creature_id="predator_1",
            archetype=creature_def.archetype,
            base_drives=archetype_def.base_drives,
            state_priorities=archetype_def.state_priorities,
            sanity_mods=archetype_def.sanity_mods,
            social=archetype_def.social,
            activity_cycle=archetype_def.activity_cycle,
            seed=42
        )

        ctx_far = EnvironmentalContext(
            dt=0.1,
            time_of_day=0.5,
            player_pos=(1000.0, 1000.0),
            player_distance=1000.0,
            player_sanity=100.0,
            player_moving=False,
            player_crouching=False,
            nearby_creatures=[],
            nearby_fragments=[],
            territory_center=(0.0, 0.0),
            current_sanity_stage=1,
            world_sanity=100.0
        )
        state_far = behavior.update(ctx_far)
        self.assertIsNotNone(state_far)

        # Move player close to trigger state update
        ctx_near = EnvironmentalContext(
            dt=2.0,  # simulate time past hysteresis timer
            time_of_day=0.5,
            player_pos=(50.0, 50.0),
            player_distance=50.0,
            player_sanity=50.0,
            player_moving=True,
            player_crouching=False,
            nearby_creatures=[],
            nearby_fragments=[],
            territory_center=(0.0, 0.0),
            current_sanity_stage=2,
            world_sanity=50.0
        )
        state_near = behavior.update(ctx_near)
        self.assertEqual(state_near, CreatureState.CHASE)

    def test_population_manager(self):
        pop_mgr = PopulationManager(seed=42)
        creature_def = generate_creature(ArchetypeType.PREDATOR, seed=42)
        archetype_def = self.archetypes[ArchetypeType.PREDATOR]

        can_spawn = pop_mgr.can_spawn_creature(
            archetype=creature_def.archetype,
            stage=1,
            current_active_count=0,
            pop_params=archetype_def.population
        )
        self.assertTrue(can_spawn)

        zone = pop_mgr.allocate_territory(
            creature_id="predator_1",
            archetype=creature_def.archetype,
            spawn_pos=(100.0, 100.0),
            pop_params=archetype_def.population
        )
        self.assertEqual(zone.owner_id, "predator_1")
        self.assertIn("predator_1", zone.current_occupants)

        pop_mgr.remove_creature("predator_1")
        self.assertNotIn("predator_1", zone.current_occupants)

    def test_creature_factory(self):
        factory = CreatureFactory(seed=42)
        instance = factory.spawn_creature(
            archetype=ArchetypeType.PREDATOR,
            spawn_pos=(100.0, 100.0),
            stage=1
        )
        self.assertIsNotNone(instance)
        self.assertEqual(instance.def_.archetype, ArchetypeType.PREDATOR)
        
        # Test update (returns None, but updates state internally)
        ctx = EnvironmentalContext(
            dt=0.1,
            time_of_day=0.5,
            player_pos=(100.0, 100.0),
            player_distance=200.0,
            player_sanity=80.0,
            player_moving=True,
            player_crouching=False,
            nearby_creatures=[],
            nearby_fragments=[],
            territory_center=(0.0, 0.0),
            current_sanity_stage=1,
            world_sanity=80.0
        )
        instance.update(0.1, ctx)  # Should not raise
        initial_state = instance.behavior.current_state

        factory.despawn_creature(instance.instance_id)
        self.assertNotIn(instance.instance_id, factory.active_instances)


if __name__ == "__main__":
    unittest.main()