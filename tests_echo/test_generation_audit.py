"""Preserve diagnostic transparency and guard the repaired audit findings."""

from dataclasses import asdict, replace
import random

import pygame
import pytest

from echo_game.challenges import ChallengeContext, PuzzleCatalog, PuzzleComposer, PuzzleGenerator
from echo_game.game import Game
from echo_game.physics import Input
from echo_game.rooms import RoomPilot
from echo_game.procedural import EndlessWorld, GenerationConfig, GenerationProfile, Platform, ProceduralGenerator
from scripts.audit_generation import GenerationTrace, registration_checks, summarize


def generator(seed=7, config=None):
    return ProceduralGenerator(seed, config=config,
                               previous=Platform(0, -80, 460, 920, 180, -1, 1))


def test_trace_preserves_segments_and_both_rng_states():
    plain, observed = generator(), generator()
    expected = [asdict(plain.generate_next(index * 400)) for index in range(80)]
    with GenerationTrace("determinism-test") as trace:
        actual = [asdict(observed.generate_next(index * 400)) for index in range(80)]
    assert actual == expected
    assert observed.rng.getstate() == plain.rng.getstate()
    assert observed.challenge_generator.rng.getstate() == plain.challenge_generator.rng.getstate()
    assert observed.hazard_rng.getstate() == plain.hazard_rng.getstate()
    assert observed.environment_generator.rng.getstate() == plain.environment_generator.rng.getstate()
    assert observed.challenge_generator.stats == plain.challenge_generator.stats
    summary = summarize(trace.events)
    assert summary["generations"] == 80
    assert summary["unique_platform_world_x"] == 80
    assert summary["accepted_challenges"] > 0
    assert any(event["obstacle_requests"] for event in trace.events)
    assert all(event["environment"]["implemented"] for event in trace.events)
    assert summary["environment_objects"] > 0


def test_trace_restores_hooks_after_exception():
    original = ProceduralGenerator.generate_next
    with pytest.raises(RuntimeError, match="test exit"):
        with GenerationTrace("error-test"):
            raise RuntimeError("test exit")
    assert ProceduralGenerator.generate_next is original


def test_endless_room_sequence_is_replayable_through_the_application():
    game = Game(persist=False, muted=True)
    try:
        def run():
            game.start_endless(7)
            pilot = RoomPilot()
            pilot_world = game.world
            for _ in range(2400):
                if game.world is not pilot_world:
                    pilot = RoomPilot()
                    pilot_world = game.world
                game.update(1 / 60, pilot.control(game.world))
            return (game.world.snapshot(),
                    tuple(room.template_index for room in game.endless_room_generator.history),
                    game.endless_room_generator.rng.getstate())

        expected = run()
        actual = run()
        assert actual == expected
        assert game.world.room_run
        assert game.endless_room_generator.rooms_generated >= 1
    finally:
        game.close()


def test_idle_endless_seed7_does_not_request_more_world():
    with GenerationTrace("idle-test") as trace:
        world = EndlessWorld(7)
        initial_generation = world.generation_count
        initial_challenges = world.challenge_generator.stats.generated
        for _ in range(600):
            world.step(Input())
    assert world.distance == 0
    assert world.generation_count == initial_generation
    assert world.challenge_generator.stats.generated == initial_challenges
    assert summarize(trace.events)["challenge_requests"] > 0


def test_difficulty10_keeps_gauntlets_and_two_saws_available():
    gen = generator()
    gauntlet = PuzzleCatalog().get("lit_gauntlet")
    assert GenerationProfile.create(10).arena_width_range[0] > gauntlet.min_width
    kinds, counts = set(), set()
    for _ in range(300):
        segment = gen.generate_next(1_000_000)
        counts.add(len(segment.hazards))
        if segment.challenge:
            kinds.add(segment.challenge.kind)
    assert "lit_gauntlet" in kinds
    assert 2 in counts


def test_profile_combo_and_damage_fields_control_challenge_output():
    first, second = PuzzleGenerator(7), PuzzleGenerator(7)
    profile = GenerationProfile.create(7)
    changed = replace(profile, combo_probability=1.0, challenge_damage_cap=0)
    expected, actual = [], []
    for index in range(100):
        platform = Platform(index + 1, index * 400, 440, 340, 28, index, 7)
        context = ChallengeContext(7)
        expected.append(first.generate(platform, profile, context))
        actual.append(second.generate(platform, changed, context))
    assert expected != actual
    assert all(c is None or c.damage_cost == 0 for c in actual)


def test_enemy_types_configuration_filters_challenge_sentries():
    gen = generator(config=GenerationConfig(enemy_types=()))
    found = False
    for index in range(120):
        segment = gen.generate_next(index * 400)
        assert segment.enemies == ()
        found |= segment.challenge is not None and bool(segment.challenge.enemies)
    assert not found


def test_shadow_definition_minimum_width_can_compose():
    definition = PuzzleCatalog().get("shadow_run")
    target = Platform(1, 1000, 460, definition.min_width, 28, 1, 4)
    challenge, _ = PuzzleComposer().compose(definition, target, 4, random.Random(7), 1)
    assert challenge is not None


def test_enemy_validator_rect_matches_runtime_and_render_anchor():
    definition = PuzzleCatalog().get("sentry")
    target = Platform(1, 1000, 460, 300, 28, 1, 4)
    challenge, _ = PuzzleComposer().compose(definition, target, 4, random.Random(7), 1)
    enemy = challenge.enemies[0]
    runtime_top = enemy.y - enemy.height / 2
    render_top = (enemy.y + enemy.height / 2) - enemy.height
    assert render_top == runtime_top
    assert enemy.rect.y == runtime_top


def test_low_resources_suppress_saws_without_perturbing_structure():
    healthy, depleted = generator(), generator()
    found = False
    for index in range(100):
        distance = index * 400
        difficulty = healthy.profile(distance).difficulty
        first = healthy.generate_next(distance, ChallengeContext(difficulty, 1, 1))
        second = depleted.generate_next(distance, ChallengeContext(difficulty, 0.1, 0.1))
        assert first.platform == second.platform
        assert not second.hazards
        found |= bool(first.hazards)
    assert found


def test_current_distance_is_not_a_furthest_progress_record():
    world = EndlessWorld(7)
    world.player.position = (400, 430)
    world.step(Input())
    first = world.distance
    first_difficulty = world.difficulty
    world.player.position = (300, 430)
    world.player.velocity = (0, 0)
    world.step(Input())
    assert world.distance < first
    assert world.furthest_distance == first
    assert world.difficulty == first_difficulty


def test_mid_tree_layer_repeats_every_6000_camera_pixels():
    game = Game(persist=False, muted=True)
    try:
        first, second = pygame.Surface((960, 540)), pygame.Surface((960, 540))
        first.fill((0, 0, 0))
        second.fill((0, 0, 0))
        game.art._tile(first, "chapter_0_mid", 0)
        game.art._tile(second, "chapter_0_mid", 6000 * 0.32)
        assert pygame.image.tobytes(first, "RGB") == pygame.image.tobytes(second, "RGB")
    finally:
        game.close()
