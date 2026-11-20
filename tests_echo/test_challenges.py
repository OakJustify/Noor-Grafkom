"""Procedural challenge generation, fairness and runtime integration tests."""

from dataclasses import replace
import random
import time

import pygame
import pytest

from echo_game.challenges import (
    CATALOG,
    Challenge,
    ChallengeConfig,
    ChallengeContext,
    ChallengeDefinition,
    EnemySpec,
    LightCache,
    PuzzleCatalog,
    PuzzleComposer,
    PuzzleGenerator,
    PuzzleRules,
    PuzzleValidator,
    ShadowZone,
)
from echo_game.game import Game, SIZE
from echo_game.physics import Input
from echo_game.procedural import (
    EndlessPilot,
    EndlessWorld,
    EnemyState,
    GenerationProfile,
    Platform,
    ProceduralGenerator,
)


def platform(index=1, x=0.0, y=460.0, width=340.0, difficulty=4.0):
    return Platform(index, x, y, width, 28.0, index, difficulty)


def challenge_signature(generator, count=120, difficulty=7.0):
    rows = []
    for index in range(count):
        row = generator.generate(
            platform(index + 1, index * 400.0, 440.0, 340.0, difficulty),
            GenerationProfile.create(difficulty),
            ChallengeContext(difficulty))
        if row is None:
            rows.append(None)
            continue
        rows.append((
            row.kind, row.platform_id, row.damage,
            tuple((barrier.x, barrier.y, barrier.height) for barrier in row.barriers),
            tuple((switch.x, switch.y, switch.barrier_id) for switch in row.switches),
            tuple((zone.x, zone.y, zone.width) for zone in row.shadows),
            tuple((enemy.x, enemy.patrol_left, enemy.patrol_right) for enemy in row.enemies),
            tuple((cache.x, cache.y) for cache in row.caches),
        ))
    return rows


def make_challenge(kind="runtime", **kwargs):
    values = dict(
        id=9000, kind=kind, label="TEST CHALLENGE",
        tags=("light", "hazard"), platform_id=0, generation_index=0,
        difficulty=2.0, damage=1)
    values.update(kwargs)
    return Challenge(**values)


def test_catalog_has_unique_hybrid_definitions():
    catalog = PuzzleCatalog(CATALOG)
    assert len(catalog.definitions) == len(CATALOG)
    assert {"light_gate", "shadow_run", "sentry", "dark_gate",
            "lit_gauntlet", "beacon_charge"} == set(catalog.by_kind)
    tags = {tag for definition in CATALOG for tag in definition.tags}
    assert {"light", "hazard", "enemy", "interactive", "gate", "environment"} <= tags


def test_rules_exclude_damage_and_light_when_resources_are_low():
    rules = PuzzleRules()
    catalog = PuzzleCatalog()
    healthy = rules.eligible(catalog, ChallengeContext(10.0, 1.0, 1.0), 400.0)
    hurt = rules.eligible(catalog, ChallengeContext(10.0, 0.1, 1.0), 400.0)
    dark = rules.eligible(catalog, ChallengeContext(10.0, 1.0, 0.1), 400.0)
    assert any(definition.damage for definition in healthy)
    assert all(definition.damage == 0 for definition in hurt)
    assert all(not definition.requires_light for definition in dark)
    assert all(not (definition.damage and "environment" in definition.tags)
               for definition in dark)


def test_composer_places_switch_before_a_seal_that_cannot_be_jumped():
    definition = PuzzleCatalog().get("light_gate")
    composer = PuzzleComposer()
    target = platform(width=340)
    challenge, _ = composer.compose(
        definition, target, 2.0, random.Random(5), start_id=1)
    assert challenge is not None
    switch = challenge.switches[0]
    barrier = challenge.barriers[0]
    assert switch.barrier_id == barrier.id
    assert switch.x < barrier.x
    assert barrier.bottom == pytest.approx(target.y)
    # The real controller reaches about 94.3 px, so 118+ px of field is sealed.
    assert barrier.height > 118
    assert PuzzleValidator().validate(
        challenge, target, ChallengeContext(2.0, 1.0, 1.0)) == []


def test_validator_rejects_unreachable_jumpable_overlapping_and_unfair_challenges():
    definition = PuzzleCatalog().get("light_gate")
    target = platform(width=340)
    challenge, _ = PuzzleComposer().compose(
        definition, target, 2.0, random.Random(9), start_id=1)
    assert challenge is not None
    context = ChallengeContext(2.0, 1.0, 1.0)
    validator = PuzzleValidator()
    assert validator.validate(challenge, target, context) == []

    switch = challenge.switches[0]
    barrier = challenge.barriers[0]
    unreachable = replace(
        challenge, switches=(replace(switch, x=barrier.x + 8),))
    assert any("unreachable" in reason
               for reason in validator.validate(unreachable, target, context))

    jumpable = replace(
        challenge, barriers=(replace(barrier, height=70.0),))
    assert any("jumped" in reason
               for reason in validator.validate(jumpable, target, context))

    overlapping = replace(challenge, shadows=(ShadowZone(
        77, barrier.x - 20, target.y - 64, 80, 64, 1, challenge.id),))
    assert any("overlaps" in reason
               for reason in validator.validate(overlapping, target, context))

    hurt = ChallengeContext(2.0, 0.1, 1.0)
    damaging = replace(challenge, damage=1)
    assert any("low health" in reason
               for reason in validator.validate(damaging, target, hurt))


def test_validator_uses_measured_jump_height_for_seals():
    definition = PuzzleCatalog().get("light_gate")
    target = platform(width=340)
    challenge, _ = PuzzleComposer().compose(
        definition, target, 2.0, random.Random(17), start_id=1)
    assert challenge is not None

    class TallCourier:
        max_jump_height = 200.0

    context = ChallengeContext(2.0, 1.0, 1.0, capabilities=TallCourier())
    reasons = PuzzleValidator().validate(challenge, target, context)
    assert any("jumped" in reason for reason in reasons)


def test_repeated_composition_failure_uses_a_safe_no_challenge_fallback():
    definition = ChallengeDefinition(
        "light_gate", "IMPOSSIBLE SEAL", ("light", "gate", "interactive"),
        1.0, 1.0, 1.0, 0, True)

    class FailedComposer(PuzzleComposer):
        def compose(self, *args, **kwargs):
            return None, 1

    generator = PuzzleGenerator(
        3, catalog=PuzzleCatalog((definition,)), composer=FailedComposer())
    profile = replace(GenerationProfile.create(10.0),
                      challenge_probability=1.0)
    for index in range(20):
        challenge = generator.generate(
            platform(index + 1, index * 400.0, 440.0, 340.0),
            profile, ChallengeContext(10.0))
        assert challenge is None
    assert generator.stats.generated == 0
    assert generator.stats.fallbacks == 20
    assert generator.stats.rejections == 20 * generator.config.layout_attempts


def test_challenge_generation_is_seed_deterministic():
    first = challenge_signature(PuzzleGenerator(2026))
    replay = challenge_signature(PuzzleGenerator(2026))
    other = challenge_signature(PuzzleGenerator(2027))
    assert first == replay
    assert first != other
    assert any(row is not None for row in first)


@pytest.mark.parametrize("difficulty", [1.0, 4.0, 10.0])
def test_generation_rate_and_validity_across_seeds(difficulty):
    generated = 0
    requests = 0
    rejections = 0
    fallbacks = 0
    for seed in range(1, 9):
        generator = PuzzleGenerator(seed)
        for index in range(70):
            requests += 1
            target = platform(index + 1, index * 400.0, 440.0, 340.0)
            challenge = generator.generate(
                target, GenerationProfile.create(difficulty),
                ChallengeContext(difficulty))
            if challenge is not None:
                generated += 1
                reasons = PuzzleValidator().validate(
                    challenge, target, ChallengeContext(difficulty))
                assert reasons == [], reasons
        rejections += generator.stats.rejections
        fallbacks += generator.stats.fallbacks
    assert generated / requests >= 0.15
    assert fallbacks == 0
    assert rejections < requests * 0.25


def test_low_health_and_low_lantern_force_a_recovery_cache():
    generator = PuzzleGenerator(11)
    produced = []
    for index in range(80):
        challenge = generator.generate(
            platform(index + 1, index * 400.0, 440.0, 340.0),
            GenerationProfile.create(4.0),
            ChallengeContext(4.0, health_fraction=0.1, lantern_fraction=0.1))
        if challenge is not None:
            produced.append(challenge)
    assert produced
    assert all(challenge.kind == "beacon_charge" for challenge in produced)
    assert generator.stats.fallbacks == 0


def test_health_damage_has_invulnerability_cooldown_and_fatal_end():
    world = EndlessWorld(1)
    start = world.health
    assert world.take_damage(1, source_x=0)
    assert world.health == start - 1
    assert world.invulnerability > 0
    assert not world.take_damage(1, source_x=0)
    assert world.health == start - 1
    for _ in range(world.max_health):
        world.invulnerability = 0
        world.take_damage(1, source_x=0)
    assert world.dead
    assert world.health == 0
    assert world.death_reason


def test_lantern_toggles_drains_and_recharges():
    world = EndlessWorld(1)
    assert world.lantern_on
    for _ in range(120):
        world.step(Input())
    assert world.lantern_energy < 1.0
    world.step(Input(lantern=True))
    assert not world.lantern_on
    before = world.lantern_energy
    for _ in range(120):
        world.step(Input())
    assert world.lantern_energy > before
    world.lantern_energy = 0.0
    world.step(Input(lantern=True))
    assert not world.lantern_on


def test_shadow_zone_damages_only_while_lantern_is_dark():
    world = EndlessWorld(1)
    x, y = world.player.position
    zone = ShadowZone(8001, x - 30, y - 22, 70, 64, 1, 9001)
    world.challenges = [make_challenge(shadows=(zone,))]
    world.lantern_on = True
    world.invulnerability = 0
    health = world.health
    world._update_challenges(1 / 120)
    assert world.health == health
    world.lantern_on = False
    world._update_challenges(1 / 120)
    assert world.health == health - 1


def test_light_seal_requires_lit_lantern_and_removes_its_body():
    world = EndlessWorld(1)
    target = world.base_platform
    definition = PuzzleCatalog().get("light_gate")
    challenge, _ = PuzzleComposer().compose(
        definition, target, 2.0, random.Random(13), start_id=7000)
    assert challenge is not None
    world._spawn_challenge(challenge)
    barrier = challenge.barriers[0]
    switch = challenge.switches[0]
    assert barrier.id in world.barrier_geometry
    world.player.position = (switch.x, switch.y)
    world.lantern_on = False
    world.interact()
    assert switch.id not in world.active_switches
    assert barrier.id in world.barrier_geometry
    world.lantern_on = True
    world.interact()
    assert switch.id in world.active_switches
    assert barrier.id not in world.barrier_geometry


def test_sentry_recoils_from_light_and_cache_restores_resources():
    world = EndlessWorld(1)
    x, y = world.player.position
    enemy = EnemySpec(8100, x + 60, y - 18, 24, 36, x + 30, x + 150,
                      50.0, 1, 9002)
    cache = LightCache(8101, x, y - 24, 24, 9003)
    world.challenges = [make_challenge(
        kind="lit_gauntlet", enemies=(enemy,))]
    world.enemy_states = {enemy.id: EnemyState(enemy.x)}
    state = world.enemy_states[enemy.id]
    before = state.x
    world.lantern_on = True
    world._update_challenges(1 / 120)
    assert state.stun > 0
    assert state.x != before

    world.challenges = [make_challenge(
        kind="beacon_charge", caches=(cache,), damage=0)]
    world.health = 2
    world.lantern_energy = 0.2
    world._update_challenges(1 / 120)
    assert world.health == 3
    assert world.lantern_energy == 1.0
    assert cache.id in world.used_caches
    world.health = 3
    world._update_challenges(1 / 120)
    assert world.health == 3


def test_cleanup_releases_challenge_geometry_and_runtime_state():
    world = EndlessWorld(7)
    pilot = EndlessPilot()
    for _ in range(2400):
        world.step(pilot.control(world))
        if world.challenges:
            break
    assert world.challenges
    challenge = world.challenges[0]
    target = next(platform for platform in world.generated_platforms
                  if platform.id == challenge.platform_id)
    assert world.barrier_geometry or not challenge.barriers
    world.player.position = (
        target.right + world.config.cleanup_distance + 2000, 430)
    world._cleanup()
    assert challenge not in world.challenges
    for barrier in challenge.barriers:
        assert barrier.id not in world.barrier_geometry
    for enemy in challenge.enemies:
        assert enemy.id not in world.enemy_states


def test_hazard_ids_are_unique_across_generated_segments():
    generator = ProceduralGenerator(5)
    generator.previous = Platform(0, -80.0, 460.0, 920.0, 180.0, -1, 1.0)
    generator.next_platform_id = 1
    ids = []
    for index in range(80):
        segment = generator.generate_next(index * 400.0)
        ids.extend(hazard.id for hazard in segment.hazards)
    assert ids
    assert len(ids) == len(set(ids))


def test_help_panel_does_not_queue_a_jump_or_action():
    game = Game(persist=False)
    pygame.display.set_mode(SIZE)
    try:
        game.start(0)
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        assert game.pending_jump and game.pending_action
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
        assert game.help
        assert not game.pending_jump
        assert not game.pending_action
        # Keys pressed while the panel is open must not leak into play.
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
        assert not game.help
        assert not game.pending_jump
        assert not game.pending_action
    finally:
        game.close()


def test_room_based_endless_uses_campaign_light_renderer():
    game = Game(persist=False)
    pygame.display.set_mode(SIZE)
    try:
        game.start_endless(7)
        world = game.world
        assert world.room_run
        assert game._visual_chapter() == world.room_theme.palette_index
        game.canvas.fill((20, 20, 20))
        before = pygame.image.tobytes(game.canvas, "RGB")
        game._lantern()
        # Campaign rooms have no separate lantern state; their player sprite's
        # glow comes from Art.draw_player rather than the old Endless overlay.
        assert pygame.image.tobytes(game.canvas, "RGB") == before
        game.draw()
        assert pygame.image.tobytes(game.canvas, "RGB") != before
    finally:
        game.close()


def test_endless_room_hud_and_retry_keep_the_selected_rng_puzzle():
    game = Game(persist=False)
    pygame.display.set_mode(SIZE)
    try:
        game.start_endless(7)
        world = game.world
        selected = game.endless_room
        assert game.draw().get_size() == SIZE
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        assert game.world is not world
        assert game.endless_room == selected
        assert game.world.room_number == 1
        assert game.world.room_template == selected.template_index
    finally:
        game.close()


def test_streamed_challenges_stay_valid_while_live():
    for seed in (1, 5, 9, 13):
        world = EndlessWorld(seed)
        pilot = EndlessPilot()
        for _ in range(3000):
            world.step(pilot.control(world))
            if world.dead:
                break
        assert not world.dead
        platforms = {platform.id: platform for platform in world.generated_platforms}
        for challenge in world.challenges:
            target = platforms[challenge.platform_id]
            hazards = [hazard for hazard in world.generated_hazards
                       if hazard.platform_id == challenge.platform_id]
            context = ChallengeContext(
                world.difficulty, 1.0, 1.0,
                capabilities=world.generator.capabilities)
            assert PuzzleValidator().validate(
                challenge, target, context, hazards=hazards) == []
            for barrier in challenge.barriers:
                looks_active = barrier.id in world.barrier_geometry
                assert barrier.switch_id not in world.active_switches or not looks_active


def test_long_sessions_remain_performant_and_survivable():
    started = time.perf_counter()
    for seed in (3, 8, 15):
        world = EndlessWorld(seed)
        pilot = EndlessPilot()
        for _ in range(4500):
            world.step(pilot.control(world))
            if world.dead:
                break
        assert not world.dead, world.snapshot()
        assert world.distance > 6000
        assert world.challenge_generator.stats.generated > 0
        assert world.generator.fallback_count == 0
    assert time.perf_counter() - started < 45.0
