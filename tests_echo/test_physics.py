"""Regression tests: puzzle solutions use the same inputs as a human player."""

import math

import pytest

from echo_game.physics import DT, Input, World
from echo_game.levels import LEVELS
from echo_game.pilot import Pilot


@pytest.mark.parametrize("chapter", range(len(LEVELS)))
def test_each_room_solvable_with_player_inputs(chapter):
    world, pilot = World(chapter), Pilot(chapter)
    seen = set()
    for _ in range(3600):
        world.step(pilot.control(world))
        seen.update(world.drain_events())
        if world.dead or world.complete:
            break
    assert not world.dead, world.snapshot()
    assert world.complete, world.snapshot()
    assert "checkpoint" in seen
    if chapter == 0:
        assert world.gate_open
        assert "gate" in seen
        assert 940 < world.crates[0].body.position.x < 1130
    if chapter == 1:
        assert "grab" in seen and "jump" in seen
    if chapter == 2:
        assert world.water_surface == world.level.water.y - world.level.water_raise
        assert world.crates[0].body.position.y < 350
    if chapter == 3:
        assert pilot.seesaw.reversals >= 4 and pilot.seesaw.phase == "exit"
    if chapter == 4:
        assert world.gravity_remaining == 0 and world.gravity == 1
        assert "gravity" in seen
    if chapter == 5:
        assert world.magnet.snapshot() == {"enabled": True, "box_gravity": 1, "captured": [0]}
        assert "magnet_capture" in seen


def test_simulation_is_deterministic():
    results = []
    for _ in range(2):
        world, pilot = World(1), Pilot(1)
        for _ in range(750):
            world.step(pilot.control(world))
        results.append(world.snapshot())
    assert results[0] == results[1]


@pytest.mark.parametrize("chapter", range(len(LEVELS)))
def test_spawn_settles_on_solid_ground(chapter):
    world = World(chapter)
    for _ in range(120):
        world.step()
    assert world.grounded
    assert not world.dead
    assert abs(world.player.velocity.y) < 1


def test_cannot_walk_across_rope_gap_without_using_rope():
    world = World(1)
    for _ in range(1200):
        world.step(Input(move=1))
        if world.dead:
            break
    assert world.dead and not world.complete
    assert "floor" in world.death_reason


def test_water_kills_player_not_hollow_crate():
    world = World(2)
    for _ in range(1800):
        world.step(Input(move=1))
        if world.dead:
            break
    assert world.dead
    assert "flood" in world.death_reason.lower()
    assert world.crates[0].body.position.y < world.water_surface + 60


def test_saw_collision_is_lethal():
    # A deliberately staged collision fixture, not a puzzle solution.
    world = World(4)
    world.player.position = (760, 420)
    world.step()
    assert world.dead and "machinery" in world.death_reason


def test_grabbing_and_pulling_crate():
    world = World(0)
    world.player.position = (426, 435)  # Fixture beside a resting crate.
    world.space.reindex_shapes_for_body(world.player)
    for _ in range(120):
        world.step(Input(grab=True))
    assert world.grab_kind == "crate"
    start_x = world.crates[0].body.position.x
    for _ in range(180):
        world.step(Input(move=-1, grab=True))
    assert world.crates[0].body.position.x < start_x - 50
    world.step(Input())
    assert world.grab_joint is None


def test_jump_is_buffered_and_no_air_double_jump():
    world = World(0)
    for _ in range(120):
        world.step()
    world.step(Input(jump=True))
    assert world.player.velocity.y < -400
    for _ in range(20):
        world.step()
    before = world.player.velocity.y
    world.step(Input(jump=True))
    assert world.player.velocity.y > before


def test_plate_opens_and_closes_gate():
    world = World(0)
    crate = world.crates[0].body
    crate.position = (1000, 430)  # Plate sensor fixture.
    world.space.reindex_shapes_for_body(crate)
    for _ in range(120):
        world.step()
    assert world.gate_open and world.gate_fraction == 1
    crate.position = (600, 430)
    world.space.reindex_shapes_for_body(crate)
    for _ in range(120):
        world.step()
    assert not world.gate_open and world.gate_fraction == 0


def test_rope_constraints_do_not_stretch_unbounded():
    world, pilot = World(1), Pilot(1)
    maximum = 0
    for _ in range(750):
        world.step(pilot.control(world))
        length = world.level.rope[3]
        previous = world.rope_anchor
        for body in world.ropes:
            top = body.local_to_world((0, -length / 2))
            maximum = max(maximum, top.get_distance(previous))
            previous = body.local_to_world((0, length / 2))
    assert maximum < 8, maximum


def test_physics_rejects_large_or_invalid_steps():
    with pytest.raises(ValueError):
        World().step(dt=1)
    with pytest.raises(ValueError):
        World(10)
