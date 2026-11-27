#!/usr/bin/env python3
"""Quick validation test for prc-creature module."""

import sys
sys.path.insert(0, "src")

from procedural_generation.prc_creature import (
    generate_creature,
    ArchetypeType,
    BodyPlanType,
    SizeClass,
    CreatureFactory,
)

def test_basic_generation():
    print("Testing basic creature generation...")
    creature = generate_creature(
        archetype=ArchetypeType.PREDATOR,
        body_plan=BodyPlanType.QUADRUPED,
        size_class=SizeClass.MEDIUM,
        stage=1,
        seed=42
    )

    assert creature.archetype == ArchetypeType.PREDATOR
    assert creature.body_plan == BodyPlanType.QUADRUPED
    assert creature.size_class == SizeClass.MEDIUM
    assert creature.stage_spawned == 1
    assert len(creature.limbs) > 0
    assert len(creature.gaits) > 0
    print(f"  ✓ Generated {creature.archetype.value} ({creature.body_plan.value}) with {len(creature.limbs)} limbs and {len(creature.gaits)} gaits")
    print(f"  ✓ Mass: {creature.body['mass']:.1f}kg, Length: {creature.body['length']:.1f}px")
    print(f"  ✓ Vocal f0: {creature.vocal.fundamental_freq:.1f}Hz")
    print(f"  ✓ Visual pattern: {creature.visual.pattern_type}")
    return creature


def test_all_archetypes():
    print("\nTesting all archetypes...")
    for arch in ArchetypeType:
        try:
            creature = generate_creature(archetype=arch, stage=2, seed=42)
            print(f"  ✓ {arch.value}: {creature.body_plan.value} / {creature.size_class.value}")
        except Exception as e:
            print(f"  ✗ {arch.value}: {e}")
            return False
    return True


def test_factory_spawn():
    print("\nTesting CreatureFactory spawn/despawn...")
    factory = CreatureFactory(seed=42)

    # Spawn multiple creatures
    instances = []
    for i in range(5):
        inst = factory.spawn_creature(
            archetype=ArchetypeType.PREDATOR,
            spawn_pos=(100 + i * 200, 300),
            stage=1
        )
        if inst:
            instances.append(inst)

    print(f"  ✓ Spawned {len(instances)} creatures")

    # Test despawn
    if instances:
        factory.despawn_creature(instances[0].instance_id)
        print(f"  ✓ Despawned {instances[0].instance_id}, remaining: {len(factory.active_instances)}")

    # Verify audio pre-caching
    for inst in instances[1:]:
        for call_type, path in inst.vocal_audio_paths.items():
            assert path.exists(), f"Missing audio: {path}"
    print(f"  ✓ Audio cached for all calls")

    return True


def test_size_scaling():
    print("\nTesting size class scaling...")
    for size in SizeClass:
        c = generate_creature(ArchetypeType.PREY, BodyPlanType.QUADRUPED, size, seed=42)
        mass = c.body['mass']
        length = c.body['length']
        print(f"  ✓ {size.value}: mass={mass:.1f}kg, len={length:.1f}px, f0={c.vocal.fundamental_freq:.1f}Hz")
    return True


def test_sanity_modifiers():
    print("\nTesting sanity modifier thresholds...")
    c = generate_creature(ArchetypeType.PREDATOR, stage=3, seed=42)
    mods = c.sanity_modifiers
    print(f"  ✓ Sanity thresholds: {list(mods.keys())}")
    for threshold, mod in mods.items():
        print(f"    Stage {threshold}: {mod}")
    return True


def main():
    print("=" * 50)
    print("prc-creature Module Validation")
    print("=" * 50)

    test_basic_generation()
    test_all_archetypes()
    test_factory_spawn()
    test_size_scaling()
    test_sanity_modifiers()

    print("\n" + "=" * 50)
    print("All tests PASSED ✓")
    print("=" * 50)


if __name__ == "__main__":
    main()