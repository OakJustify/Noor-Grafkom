"""Generated geometry, composed puzzles, replay and live Endless progression."""

from dataclasses import asdict, replace
import pygame
import pytest

from echo_game.game import Game, SIZE
from echo_game.levels import LEVELS
from echo_game.procedural import EndlessRoomGenerator, EndlessRoomWorld
from echo_game.rooms import ARCHETYPES, RoomPilot, RoomVerifier


@pytest.fixture(scope="module")
def generated_rooms():
    generator = EndlessRoomGenerator(23)
    return [generator.next_room() for _ in range(12)]


def test_rng_draws_every_mechanic_once_per_cycle_and_replays_room_contents():
    first = EndlessRoomGenerator(701)
    replay = EndlessRoomGenerator(701)
    other_seed = EndlessRoomGenerator(702)

    first_cycle = [first.next_room() for _ in LEVELS]
    replay_cycle = [replay.next_room() for _ in LEVELS]
    next_room = first.next_room()

    assert [room.template_index for room in first_cycle] == [
        room.template_index for room in replay_cycle]
    assert [asdict(room) for room in first_cycle] == [asdict(room) for room in replay_cycle]
    assert {room.template_index for room in first_cycle} == set(range(len(LEVELS)))
    assert next_room.template_index != first_cycle[-1].template_index
    assert first_cycle[0].template_index != other_seed.next_room().template_index
    assert [room.number for room in first_cycle] == list(range(1, 7))
    assert first_cycle[0].level.title.startswith("ROOM 01 /")


def test_selected_rooms_keep_all_six_campaign_mechanics(generated_rooms):
    rooms = generated_rooms[:6]
    worlds = [EndlessRoomWorld(23, room) for room in rooms]
    by_template = {world.room_template: world for world in worlds}

    assert len(by_template[0].puzzle_runtimes) >= 2
    assert by_template[1].level.rope
    assert by_template[2].level.water and by_template[2].level.cover
    assert by_template[3].level.seesaw
    assert by_template[4].level.switches and by_template[4].level.saws
    assert by_template[5].level.magnet
    assert all(world.endless and world.room_run for world in worlds)


def test_room_layout_puzzle_and_background_signatures_do_not_repeat(generated_rooms):
    for field in ("layout_signature", "puzzle_signature", "background_signature"):
        signatures = [getattr(room, field) for room in generated_rooms]
        assert len(set(signatures)) == len(signatures)
    for room in generated_rooms:
        # Uniqueness is not a room-number/title trick: geometry and object data
        # change even when the SAME mechanic returns on the next cycle.
        assert room.level.terrain != LEVELS[room.template_index].terrain
        assert 2 <= len(room.stages) <= 4
        assert room.verified_solvable and room.solution_trace[-1]["complete"]
    for a, b in zip(generated_rooms[:6], generated_rooms[6:]):
        assert a.level.terrain != b.level.terrain
    assert len({tuple(s.variant for s in r.stages) for r in generated_rooms}) >= 6


@pytest.mark.parametrize("template", range(6))
def test_all_generated_mechanics_complete_in_live_fixed_step_physics(generated_rooms, template):
    room = next(r for r in generated_rooms if r.template_index == template)
    world, trace = RoomVerifier().simulate(room)
    assert world.complete and not world.dead, trace[-3:]
    assert all(r.solved and r.crate_was_grabbed for r in world.puzzle_runtimes.values())
    if template != 0:
        bypass, _ = RoomVerifier().simulate(room, blocked_archetype=ARCHETYPES[template])
        assert not bypass.complete


def test_failed_generation_never_emits_an_empty_or_unverified_room(monkeypatch):
    generator = EndlessRoomGenerator(7)
    monkeypatch.setattr(generator.verifier, "verify", lambda room: (False, ()))
    with pytest.raises(RuntimeError, match="No solvable"):
        generator.next_room()
    assert generator.rooms_generated == 0
    assert not generator.history


def test_duplicate_geometry_is_rejected_not_renamed(monkeypatch):
    generator = EndlessRoomGenerator(7)
    room = generator.next_room()
    monkeypatch.setattr(generator, "_candidate", lambda *args: replace(room, number=2))
    with pytest.raises(RuntimeError, match="No solvable"):
        generator.next_room()
    assert generator.rooms_generated == 1


def test_remote_relay_crates_do_not_fly_away_during_gravity_field(generated_rooms):
    room = next(r for r in generated_rooms if r.template_index == 4)
    world = EndlessRoomWorld(room.seed, room)
    positions = [tuple(c.body.position) for c in world.crates]
    world.flip_gravity(-1)
    for _ in range(120):
        world.step()
    assert all(abs(c.body.position.y - start[1]) < 10 for c, start in zip(world.crates, positions))


def test_seeded_background_pixels_are_unique_and_cache_is_bounded(generated_rooms):
    game = Game(persist=False, muted=True)
    try:
        samples = []
        for room in generated_rooms[:6]:
            game.art.draw_background(game.canvas, 0, 0, room.theme.palette_index, theme=room.theme)
            samples.append(pygame.image.tobytes(game.canvas, "RGB"))
        assert len(set(samples)) == 6
        cache = game.art._room_backgrounds
        assert len(cache.cache) == 2
        room = generated_rooms[0]
        game.art.draw_background(game.canvas, 0, 0, room.theme.palette_index, theme=room.theme)
        assert pygame.image.tobytes(game.canvas, "RGB") == samples[0]
        builds = cache.builds
        game.art.draw_background(game.canvas, 0, 0, room.theme.palette_index, theme=room.theme)
        assert cache.builds == builds
    finally:
        game.close()


def test_app_retry_preserves_geometry_scenery_and_rng_sequence():
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(7)
        room, state = game.endless_room, game.endless_room_generator.rng.getstate()
        before = pygame.image.tobytes(game.draw(), "RGB")
        game.restart_endless_room()
        assert game.endless_room is room
        assert game.endless_room_generator.rng.getstate() == state
        assert pygame.image.tobytes(game.draw(), "RGB") == before
        game.world.kill("test retry")
        game.update(2)
        assert game.endless_room is room and not game.world.dead
    finally:
        game.close()


def test_solution_witness_matches_actual_game_input_cadence(generated_rooms):
    game = Game(persist=False, muted=True)
    try:
        for room in generated_rooms[:6]:
            game.endless, game.endless_seed = True, room.seed
            game._load_endless_room(room)
            pilot = RoomPilot()
            expected, _ = RoomVerifier().simulate(room)
            for _ in range(RoomVerifier.MAX_STEPS // 2):
                game.update(1 / 60, pilot.control(game.world))
                if game.world.complete or game.world.dead:
                    break
            assert game.world.complete and not game.world.dead
            assert tuple(game.world.player.position) == tuple(expected.player.position)
            assert game.world.time == expected.time
    finally:
        game.close()


def test_completing_room_advances_rng_and_retry_replays_same_room():
    pygame.display.set_mode(SIZE)
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(19)
        first_room = game.endless_room
        first_world = game.world
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        assert game.world is not first_world
        assert game.endless_room == first_room

        game.world.complete = True
        game.update(2.0)
        assert game.endless_room.number == 2
        assert game.endless_room.template_index != first_room.template_index
        assert game.world.level.title.startswith("ROOM 02 /")
    finally:
        game.close()
