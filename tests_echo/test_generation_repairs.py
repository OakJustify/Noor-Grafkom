"""Real-width integration and type-specific placement regression gates."""

from collections import Counter
import argparse
from dataclasses import replace
import random

import pygame
import pytest

from echo_game.challenges import ChallengeContext, PuzzleCatalog, PuzzleComposer, PuzzleValidator
from echo_game.environment import EnvironmentConfig, EnvironmentGenerator, RULES, reserved_rects
from echo_game.game import Game, density_value, SIZE
from echo_game.levels import Rect
from echo_game.procedural import (
    DifficultyManager, EndlessPilot, EndlessWorld, GenerationConfig,
    GenerationProfile, Platform, ProceduralGenerator, SawHazard,
)
from scripts.audit_generation import registration_checks


def generator(seed=7, **settings):
    return ProceduralGenerator(seed, config=GenerationConfig(**settings),
                               previous=Platform(0, -80, 460, 920, 180, -1, 1))


@pytest.mark.parametrize("difficulty", [1, 4, 7, 8.2, 10])
def test_real_width_segments_are_valid_and_diverse(difficulty):
    kinds, environments, counts = set(), Counter(), Counter()
    at_bound = 0
    for seed in (1, 2, 7, 13, 21):
        gen = generator(seed)
        gen.difficulty_manager = DifficultyManager(base=difficulty)
        for _ in range(100):
            previous = gen.previous
            segment = gen.generate_next(0)
            assert gen.validate_platform(previous, segment.platform)[0]
            valid, reasons = gen.validate_segment(segment)
            assert valid, reasons
            assert segment.platform.x > previous.right
            assert not segment.validation.fallback_used
            environments.update(e.kind for e in segment.environment)
            at_bound += segment.platform.y == 470
            counts[len(segment.hazards)] += 1
            if segment.challenge:
                kinds.add(segment.challenge.kind)
    assert set(environments) == {r.kind for r in RULES}
    assert "light_gate" in kinds
    assert at_bound < 10  # no Y-clamp accumulation
    if difficulty >= 4:
        assert {"dark_gate", "lit_gauntlet"} <= kinds
    if difficulty == 10:
        assert counts[2] > 0


@pytest.mark.parametrize("setting", ["environment_density", "obstacle_density", "puzzle_density"])
def test_density_changes_never_consume_structural_randomness(setting):
    plain, disabled = generator(), generator(**{setting: 0})
    for i in range(100):
        first, second = plain.generate_next(i * 900), disabled.generate_next(i * 900)
        assert first.platform == second.platform
        assert plain.rng.getstate() == disabled.rng.getstate()
        if setting == "environment_density":
            assert first.hazards == second.hazards and first.challenge == second.challenge
            assert plain.hazard_rng.getstate() == disabled.hazard_rng.getstate()
            assert not second.environment
        elif setting == "obstacle_density":
            assert not second.hazards
            assert second.challenge is None or second.challenge.damage_cost == 0
        elif setting == "puzzle_density":
            assert second.challenge is None or not second.challenge.switches


def test_enemy_filter_and_configured_minimum_width_apply_to_real_pipeline():
    gen = generator(enemy_types=(), challenge_min_width=500)
    for i in range(200):
        segment = gen.generate_next(i * 1000)
        if segment.challenge:
            assert segment.platform.width >= 500
            assert not segment.challenge.enemies


def test_density_multipliers_increase_measured_category_frequency():
    density_fields = {
        "environment": "environment_density",
        "puzzles": "puzzle_density",
        "obstacles": "obstacle_density",
    }
    for category, field in density_fields.items():
        totals = {}
        for multiplier in (0, 1, 2):
            counts = Counter()
            for seed in (1, 7, 13):
                settings = {name: 1 for name in density_fields.values()}
                settings[field] = multiplier
                gen = generator(seed, **settings)
                gen.difficulty_manager = DifficultyManager(base=7)
                for _ in range(50):
                    segment = gen.generate_next(0)
                    counts["environment"] += len(segment.environment)
                    counts["obstacles"] += len(segment.hazards)
                    if segment.challenge:
                        counts["puzzles"] += bool(segment.challenge.switches)
                        counts["obstacles"] += len(segment.challenge.shadows) + len(segment.challenge.enemies)
            totals[multiplier] = counts[category]
        assert totals[0] == 0
        assert totals[2] > totals[1] > 0, (category, totals)


def test_complete_segment_budget_and_environment_ownership_are_validated():
    gen = generator()
    for _ in range(60):
        segment = gen.generate_next(100000)
        if segment.hazards and segment.environment:
            break
    assert segment.hazards and segment.environment
    depleted = replace(gen.challenge_context, health_fraction=.1)
    assert any("low resources" in r for r in gen.validate_segment(segment, depleted)[1])
    no_damage = replace(gen.challenge_context, damage_cap=0)
    assert "segment exceeds damage budget" in gen.validate_segment(segment, no_damage)[1]
    item = replace(segment.environment[0], platform_id=-1)
    invalid = replace(segment, environment=(item,))
    assert "environment owner mismatch" in gen.validate_segment(invalid)[1]


def test_combo_composition_uses_feasible_intervals_for_every_sample():
    composer, catalog = PuzzleComposer(), PuzzleCatalog()
    for kind in ("light_gate", "shadow_run", "sentry", "dark_gate", "lit_gauntlet"):
        definition = catalog.get(kind)
        width = composer.minimum_width(definition)
        platform = Platform(1, 25000, 390, width, 28, 1, 10)
        for seed in range(80):
            challenge, _ = composer.compose(definition, platform, 10, random.Random(seed), 1)
            assert challenge is not None, (kind, seed, width)
            assert PuzzleValidator().validate(challenge, platform, ChallengeContext(10)) == []


def test_validator_rejects_patrol_overlap_even_when_initial_enemy_is_clear():
    platform = Platform(1, 1000, 460, 600, 28, 1, 10)
    challenge, _ = PuzzleComposer().compose(PuzzleCatalog().get("sentry"), platform, 10, random.Random(7), 1)
    enemy = replace(challenge.enemies[0], x=platform.x + 60)
    challenge = replace(challenge, enemies=(enemy,))
    saw = SawHazard(1, platform.right - 100, platform.y - 22, 20, 0, 0, 1, 1)
    assert enemy.rect.x + enemy.rect.w < saw.x - saw.radius
    assert "enemy overlaps a saw" in PuzzleValidator().validate(challenge, platform, ChallengeContext(10), (saw,))


def test_environment_is_supported_spaced_reserved_and_seeded():
    platform = Platform(1, 1000, 420, 600, 28, 1, 7)
    profile = GenerationProfile.create(7)
    reserved = (Rect(1200, 300, 60, 120),)
    first = EnvironmentGenerator(7)
    items = first.generate(platform, profile, reserved)
    assert items == EnvironmentGenerator(7).generate(platform, profile, reserved)
    assert items != EnvironmentGenerator(8).generate(platform, profile, reserved)
    accepted = []
    for item in items:
        assert not item.collidable
        assert first.validate(item, platform, accepted, reserved) == []
        accepted.append(item)
    assert first.last_report["candidates"]
    assert all("reasons" in candidate for candidate in first.last_report["candidates"])
    assert first.generate(replace(platform, id=2, x=2000, generation_index=2), profile) != items


@pytest.mark.parametrize("density", [0, 1, 3])
def test_environment_density_is_bounded_and_effective(density):
    gen = EnvironmentGenerator(7, EnvironmentConfig(density=density))
    total = 0
    for i in range(40):
        platform = Platform(i + 1, i * 500, 400, 400, 28, i + 1, 7)
        items = gen.generate(platform, GenerationProfile.create(7))
        assert len(items) <= gen.config.max_objects
        total += len(items)
    assert total == 0 if density == 0 else total > 100


@pytest.mark.parametrize("seed", [1, 7, 13])
def test_high_difficulty_controller_streaming_and_environment_cleanup(seed):
    # A difficulty floor exercises high-profile geometry from the start without
    # teleporting the player or fabricating 340px platforms.
    world = EndlessWorld(seed, difficulty=DifficultyManager(base=10))
    pilot = EndlessPilot()
    for _ in range(6000):
        world.step(pilot.control(world))
        assert not world.dead, world.snapshot()
    assert world.distance > 6500
    assert world.environment_spawned > len(world.environment_objects)
    assert world.environment_spawned - world.environment_cleaned == len(world.environment_objects)
    assert registration_checks(world) == []
    assert len(world.environment_objects) < 150
    platforms = {p.id: p for p in world.generated_platforms}
    for platform in platforms.values():
        challenge = next((c for c in world.challenges if c.platform_id == platform.id), None)
        hazards = [h for h in world.generated_hazards if h.platform_id == platform.id]
        accepted = []
        for item in world.environment_objects:
            if item.platform_id == platform.id:
                assert world.generator.environment_generator.validate(
                    item, platform, accepted, reserved_rects(challenge, hazards)) == []
                accepted.append(item)


def test_stream_generation_config_and_campaign_render_routes_are_seeded():
    config = GenerationConfig(environment_density=3, obstacle_density=0, puzzle_density=0)
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(7)
        game.world = EndlessWorld(7, config=config)
        first = tuple(game.world.environment_objects)
        platform = game.world.generated_platforms[0]
        game.camera = platform.x
        view_width = SIZE[0]
        for layer in ("rear", "terrain", "front"):
            game.canvas.fill((0, 0, 0))
            game._environment(layer)
            if any(i.layer == layer and platform.x <= i.x < platform.x + view_width
                   for i in first):
                assert pygame.image.tobytes(game.canvas, "RGB") != bytes(960 * 540 * 3)
        replay = EndlessWorld(7, config=config)
        assert replay.config == config
        assert tuple(replay.environment_objects) == first
    finally:
        game.close()


@pytest.mark.parametrize("value", [-1, 4, float("nan"), float("inf")])
def test_density_validation_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        GenerationConfig(environment_density=value)
    with pytest.raises(ValueError):
        EnvironmentConfig(density=value)
    with pytest.raises(argparse.ArgumentTypeError):
        density_value(str(value))
