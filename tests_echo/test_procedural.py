"""Procedural endless-mode tests: physics, fairness, determinism, streaming."""

import pygame
import pytest

from echo_game.game import Game, SIZE
from echo_game.physics import GRAVITY, JUMP_SPEED, MOVE_SPEED, PLAYER_SIZE
from echo_game.rooms import RoomPilot
from echo_game.procedural import (
    EndlessPilot,
    EndlessWorld,
    GenerationConfig,
    GenerationProfile,
    Platform,
    PlayerCapabilities,
    ProceduralGenerator,
    ProceduralRoomGenerator,
    ProceduralRoomWorld,
)


def signature(generator, count=40):
    base = Platform(0, -80.0, 460.0, 920.0, 180.0, -1, 1.0)
    generator.previous = base
    generator.next_platform_id = 1
    rows = []
    for index in range(count):
        segment = generator.generate_next(index * 350.0)
        rows.append((
            segment.platform.x, segment.platform.y, segment.platform.width,
            tuple((h.x, h.y, h.radius, h.travel, h.rate) for h in segment.hazards),
        ))
    return rows


def traversal(seed, frames=6000):
    world = EndlessWorld(seed)
    pilot = EndlessPilot()
    for _ in range(frames):
        world.step(pilot.control(world))
        if world.dead:
            break
    return world


def test_capabilities_are_read_from_the_real_controller():
    caps = PlayerCapabilities.from_controller()
    assert caps.horizontal_speed == MOVE_SPEED
    assert caps.jump_speed == JUMP_SPEED
    assert caps.jump_speed == pytest.approx(445.0)
    assert caps.gravity == GRAVITY
    assert (caps.width, caps.height) == PLAYER_SIZE
    # This is the regression that mattered: a jump derived from GRAVITY
    # produced a takeoff speed of 467,250 px/s and accepted every gap.
    assert caps.max_jump_height == pytest.approx(94.3, abs=0.2)
    assert caps.horizontal_reach(0) == pytest.approx(161.0, abs=0.5)


def test_difficulty_is_bounded_and_grows_logarithmically():
    world = EndlessWorld(1)
    manager = world.generator.difficulty_manager
    values = [manager.calculate(d) for d in (0, 100, 1_000, 10_000, 10 ** 9)]
    assert values[0] == 1.0
    assert all(a <= b for a, b in zip(values, values[1:]))
    assert all(1.0 <= value <= manager.maximum for value in values)
    low = GenerationProfile.create(1.0)
    high = GenerationProfile.create(10.0)
    assert high.gap_range[1] >= low.gap_range[1]
    assert high.hazard_probability >= low.hazard_probability
    assert high.max_hazards >= low.max_hazards


def test_generation_is_seed_reproducible():
    first = signature(ProceduralGenerator(2026))
    replay = signature(ProceduralGenerator(2026))
    other = signature(ProceduralGenerator(2027))
    assert first == replay
    assert first != other


def test_impossible_platforms_are_rejected():
    generator = ProceduralGenerator(3)
    previous = Platform(1, 0.0, 460.0, 300.0, 28.0, 1, 1.0)
    far = Platform(2, 560.0, 460.0, 300.0, 28.0, 2, 1.0)
    valid, reasons = generator.validate_platform(previous, far)
    assert not valid
    assert any("cannot reach" in reason for reason in reasons)
    assert any("above maximum" in reason for reason in reasons)

    too_high = Platform(2, 340.0, 300.0, 300.0, 28.0, 2, 1.0)
    valid, reasons = generator.validate_platform(previous, too_high)
    assert not valid
    assert any("higher than maximum jump" in reason for reason in reasons)

    narrow = Platform(2, 350.0, 460.0, 40.0, 28.0, 2, 1.0)
    valid, reasons = generator.validate_platform(previous, narrow)
    assert not valid
    assert any("landing too narrow" in reason for reason in reasons)


def test_fallback_is_flat_close_and_reachable():
    class Impossible(ProceduralGenerator):
        def _candidate(self, previous, profile, recovery):
            return Platform(self.next_platform_id, previous.right + 900.0,
                            previous.y - 300.0, 20.0, 28.0,
                            self.index + 1, profile.difficulty)

    previous = Platform(1, 0.0, 460.0, 300.0, 28.0, 1, 1.0)
    generator = Impossible(4, config=GenerationConfig(max_attempts=3),
                           previous=previous)
    segment = generator.generate_next(0)
    assert segment.validation.fallback_used
    assert generator.fallback_count == 1
    assert segment.platform.x - previous.right == pytest.approx(48.0)
    assert segment.platform.y == previous.y
    assert segment.platform.width >= generator.config.minimum_landing_width
    valid, reasons = generator.validate_platform(previous, segment.platform)
    assert valid, reasons
    assert segment.hazards == ()


def test_generated_segments_keep_hazards_clear_of_landing_and_takeoff():
    total_hazards = 0
    recovery_segments = 0
    for seed in range(1, 16):
        generator = ProceduralGenerator(seed)
        generator.previous = Platform(0, -80.0, 460.0, 920.0, 180.0, -1, 1.0)
        generator.next_platform_id = 1
        for index in range(50):
            distance = index * 400.0
            profile = generator.profile(distance)
            recovery = generator.index % profile.recovery_spacing == 0
            segment = generator.generate_next(distance)
            assert segment.enemies == ()
            assert segment.validation.is_valid
            platform = segment.platform
            if recovery:
                recovery_segments += 1
                assert segment.hazards == (), "recovery platforms must stay safe"
            assert generator.config.vertical_min <= platform.y <= generator.config.vertical_max
            assert platform.width >= generator.config.minimum_landing_width
            for hazard in segment.hazards:
                total_hazards += 1
                left = hazard.x - hazard.travel - hazard.radius
                right = hazard.x + hazard.travel + hazard.radius
                assert hazard.y < platform.y
                assert left >= platform.x + generator.config.hazard_left_clearance
                assert right <= platform.right - generator.config.hazard_right_clearance
                assert platform.x <= left < right <= platform.right
            valid, reasons = generator.validate_segment(segment)
            assert valid, reasons
    assert recovery_segments > 50
    assert total_hazards > 50


def test_streaming_cleans_old_geometry_and_bounds_live_objects():
    world = traversal(9, frames=8000)
    assert not world.dead, world.snapshot()
    assert world.distance > 6000
    assert world.puzzles_solved == world.puzzles_spawned
    assert world.generated_until > world.player.position.x + 900
    assert 1 <= len(world.generated_platforms) <= 20
    assert len(world.generated_hazards) <= 12
    assert set(world._platform_geometry) == {p.id for p in world.generated_platforms}
    for platform in world.generated_platforms:
        assert platform.right >= world.player.position.x - world.config.cleanup_distance
    # Every hazard still belongs to a live platform, and no saw survives in
    # the rendering/update lists after its platform is released.
    live_ids = {p.id for p in world.generated_platforms}
    assert all(h.platform_id in live_ids for h in world.generated_hazards)
    rects = world.terrain_rects()
    assert len(rects) == 1 + len(world.generated_platforms)
    assert len(world.saw_positions()) == len(world.generated_hazards)


@pytest.mark.parametrize("seed", [1, 2, 7, 13, 21, 34])
def test_endless_pilot_traverses_several_screens(seed):
    world = traversal(seed, frames=6000)
    assert not world.dead, world.snapshot()
    assert world.distance > 5000
    assert world.generator.fallback_count == 0
    assert world.puzzles_solved == world.puzzles_spawned


def test_same_seed_replays_the_same_live_world():
    def run():
        world = EndlessWorld(77)
        pilot = EndlessPilot()
        for _ in range(2400):
            world.step(pilot.control(world))
        return world.snapshot(), [
            (p.id, p.x, p.y, p.width) for p in world.generated_platforms
        ], [(h.platform_id, h.x, h.radius) for h in world.generated_hazards]

    assert run() == run()


def test_game_menu_key_starts_endless_and_restart_rebuilds_same_seed():
    game = Game(persist=False)
    pygame.display.set_mode(SIZE)
    try:
        assert game.state == "menu"
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        assert game.state == "playing"
        assert game.endless
        assert isinstance(game.world, ProceduralRoomWorld)
        seed = game.endless_seed
        original = game.world
        room = game.endless_room
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        assert game.endless and game.endless_seed == seed
        assert game.world is not original
        assert game.world.seed == seed
        assert game.endless_room == room
    finally:
        game.close()


def test_game_updates_and_draws_endless_campaign_puzzle_rooms():
    game = Game(persist=False)
    pygame.display.set_mode(SIZE)
    try:
        game.start_endless(5)
        pilot = RoomPilot()
        pilot_world = game.world
        for _ in range(3000):
            if game.world is not pilot_world:
                pilot = RoomPilot()
                pilot_world = game.world
            game.update(1 / 60, pilot.control(game.world))
            assert not game.world.dead, game.world.snapshot()
        assert game.endless_room.number >= 2
        assert game.world.room_run
        assert game.draw().get_size() == SIZE
        game.state = "paused"
        assert game.draw().get_size() == SIZE
        game.state = "menu"
        assert game.draw().get_size() == SIZE
    finally:
        game.close()
