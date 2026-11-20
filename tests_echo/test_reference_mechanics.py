"""Qualitative source-grounded contracts, separate from campaign solvability.

Fixture staging is explicit; no staged positions are used in the campaign
witness. Sources and coverage limits live in reference-contracts.json.
"""

import json
import ast
from pathlib import Path

import pytest

from echo_game.physics import DT, Input, World
from echo_game.pilot import Pilot


def stage(body, world, position):
    body.position = position
    body.velocity = (0, 0)
    world.space.reindex_shapes_for_body(body)


def floating_fixture():
    world = World(2)
    crate = world.crates[0].body
    stage(crate, world, (630, 490))
    stage(world.player, world, (630, 420))
    for _ in range(600):
        world.step()
    assert not world.dead and world.support == crate
    return world, crate


def test_rope_climbing_moves_hand_along_segments():
    world = World(1)
    tip = world.ropes[-1]
    stage(world.player, world, tuple(tip.position))
    for _ in range(40):
        world.step(Input(grab=True))
    assert world.grab_kind == "rope"
    distance = world.rope_distance
    start_y = world.player.position.y
    for _ in range(180):
        world.step(Input(grab=True, climb=1))
    assert world.grab_kind == "rope" and not world.dead
    assert world.rope_distance < distance - 100
    assert world.player.position.y < start_y - 60
    assert world.ropes.index(world.grabbed) < len(world.ropes) - 3
    climbed = world.rope_distance
    for _ in range(60):
        world.step(Input(grab=True, climb=-1))
    assert world.rope_distance > climbed + 40


def test_rope_release_does_not_teleport_or_erase_momentum():
    world = World(1)
    stage(world.player, world, tuple(world.ropes[-1].position))
    world.step(Input(grab=True))
    assert world.grab_kind == "rope"
    world.player.velocity = (180, -65)
    pos = tuple(world.player.position)
    world._release()
    assert tuple(world.player.position) == pos
    assert tuple(world.player.velocity) == (180, -65)
    assert world.grab_joint is None


def test_rope_high_ledge_witness_uses_climbing():
    # Paired input-only witnesses for this geometry, not proof that every
    # imaginable no-climb strategy is impossible in ECHO or in LIMBO.
    outcomes = []
    for climb in (True, False):
        world, pilot = World(1), Pilot(1)
        for _ in range(1800):
            control = pilot.control(world)
            if not climb:
                control = Input(control.move, control.jump, control.grab, control.action)
            world.step(control)
            if world.dead or world.complete:
                break
        outcomes.append((world.complete, world.dead))
    assert outcomes == [(True, False), (False, True)]


def test_water_valve_starts_stops_and_bounds_fill():
    world = World(2)
    stage(world.player, world, world.level.valve)
    for _ in range(120):
        world.step()
    assert world.water_surface == 500
    for _ in range(120):
        world.step(Input(action=True))
    assert world.water_surface == pytest.approx(480)
    assert world.water_transferred_area == pytest.approx(20 * 280)
    world.step()  # Release action: holding it is not repeated valve operation.
    world.step(Input(action=True))
    stopped = world.water_surface
    for _ in range(120):
        world.step(Input(action=True))
    assert not world.water_active and world.water_surface == stopped
    world.step()
    world.step(Input(action=True))
    for _ in range(1800):
        world.step()
    assert world.water_surface == 330 and not world.water_active
    assert world.water_transferred_area == pytest.approx(170 * 280)


def test_loaded_box_rises_with_water():
    world, crate = floating_fixture()
    initial = (crate.position.y, world.player.position.y)
    # The fixture starts filling while the already staged character is aboard.
    world.water_active = True
    for _ in range(360):
        world.step()
    assert world.water_surface == pytest.approx(440)
    assert crate.position.y < initial[0] - 45
    assert world.player.position.y < initial[1] - 45
    assert world.support == crate and not world.dead
    assert world.player.position.y < world.water_surface


def test_cover_blocks_box_until_opening_is_exposed():
    world = World(2)
    crate = world.crates[0].body
    world.water_surface = 330
    stage(crate, world, (630, 430))
    for _ in range(600):
        world.step()
    blocked_y = crate.position.y
    assert blocked_y > world.level.cover.y + 35
    assert not world.cover_open
    stage(world.player, world, world.level.cover_switch)
    world.step(Input(action=True))
    for _ in range(600):
        world.step()
    assert world.cover_fraction == 1
    assert crate.position.y < blocked_y - 60


def test_no_fill_does_not_reach_water_exit():
    world, pilot = World(2), Pilot(2)
    for _ in range(1800):
        control = pilot.control(world)
        # Allow the cover operation, but withhold water-valve activation.
        if world.cover_open:
            control = Input(control.move, control.jump, control.grab, False, control.climb)
        world.step(control)
        if world.dead or world.complete:
            break
    assert not world.complete
    assert world.water_surface == world.level.water.y


def test_without_box_player_cannot_swim_to_exit():
    world = World(2)
    crate = world.crates.pop()
    world.space.remove(crate.shape, crate.body)  # Explicit missing-support fixture.
    world.cover_open = True
    world.water_active = True
    for _ in range(1200):
        world.step(Input(move=1))
        if world.dead or world.complete:
            break
    assert world.dead and not world.complete
    assert "flood" in world.death_reason.lower()


def test_walking_on_box_is_not_automatic_rowing():
    world, crate = floating_fixture()
    for _ in range(60):
        world.step(Input(move=1))
    assert world.player.position.x - crate.position.x > 40
    assert world.support != crate


def test_gravity_switch_expires_without_second_relay():
    world = World(4)
    stage(world.player, world, world.level.switches[0])
    world.step(Input(action=True))
    assert world.gravity == -1 and world.gravity_remaining == 5
    for _ in range(600):
        world.step(Input(action=True))  # Holding cannot refresh the countdown.
    assert not world.dead
    assert world.gravity == 1 and world.gravity_remaining == 0
    assert world.space.gravity.y > 0
    assert len(world.level.switches) == 1 and world.gate_body is None


def test_gravity_changes_acceleration_not_existing_velocity():
    world = World(4)
    stage(world.player, world, (350, 300))
    world.player.velocity = (70, -150)
    crate = world.crates[0].body
    stage(crate, world, (460, 300))
    crate.velocity = (15, 40)
    world.flip_gravity(-1)
    assert tuple(world.player.velocity) == (70, -150)
    assert tuple(crate.velocity) == (15, 40)
    world.step()
    assert world.player.velocity.y == pytest.approx(-150 - 1050 * DT)
    assert crate.velocity.y == pytest.approx(40 - 1050 * DT)


def test_airborne_reactivation_restarts_timer():
    world = World(4)
    stage(world.player, world, (350, 380))
    world.gravity_remaining = 0.2
    world.gravity = -1
    world.space.gravity = (0, -1050)
    world.player.velocity = (0, -85)
    world.step(Input(action=True))
    assert not world.grounded and world.gravity_remaining == 5
    assert world.player.velocity.y < -85  # No mid-air velocity reset.


def test_gravity_countdown_beeps_accelerate_then_stop():
    world = World(4)
    stage(world.player, world, world.level.switches[0])
    times = []
    for i in range(720):
        world.step(Input(action=i == 0))
        if "tick" in world.drain_events():
            times.append(world.time)
    intervals = [b - a for a, b in zip(times, times[1:])]
    assert len(intervals) > 8
    assert intervals[-1] < intervals[0] / 3
    assert max(times) < 5.01
    assert world.gravity_remaining == 0


def test_plate_requires_surface_contact_not_a_hovering_centre():
    world = World(0)
    crate = world.crates[0].body
    stage(crate, world, (1000, 390))
    world._gate(DT)
    assert not world.gate_open  # Old centre-band sensor incorrectly opened here.
    stage(crate, world, (1000, 430))
    world._gate(DT)
    assert world.gate_open
    stage(crate, world, (700, 430))
    world._gate(DT)
    assert not world.gate_open


def test_box_jams_closing_gate_until_removed():
    world = World(0)
    crate = world.crates[0]
    gate = world.level.gate
    stage(world.gate_body, world, (gate.x + gate.w / 2, gate.y + gate.h / 2 - gate.h - 20))
    world.gate_fraction = 1
    stage(crate.body, world, (gate.x + gate.w / 2, 430))
    for _ in range(180):
        world.step()
    crate.shape.cache_bb()
    gate_bottom = world.gate_body.position.y + gate.h / 2
    assert not world.gate_open and 0 < world.gate_fraction < 1
    assert gate_bottom <= crate.shape.bb.bottom + 0.5
    assert abs(crate.body.position.y - 431) < 3
    stage(crate.body, world, (600, 430))
    for _ in range(180):
        world.step()
    assert world.gate_fraction == 0


def test_weight_changes_beam_torque():
    angles = []
    for x in (700, 980):
        world = World(3)
        # Body load fixture demonstrates torque; campaign uses only the
        # courier's alternating weight, not a permanently parked iron crate.
        load = world._prop((x, 405), (42, 42), 25)
        for _ in range(360):
            world.step()
        angles.append(world.beam.body.angle)
    assert angles[0] < -0.2 and angles[1] > 0.2


def test_reference_contracts_name_real_tests_and_preserve_limits():
    path = Path(__file__).parents[1] / "docs/echo/reference-contracts.json"
    report = json.loads(path.read_text())
    test_names = {node.name for source in Path(__file__).parent.glob("test_*.py")
                  for node in ast.walk(ast.parse(source.read_text()))
                  if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
    assert len(report["contracts"]) == 6 and report["limitations"]
    for contract in report["contracts"]:
        assert all(source in report["sources"] for source in contract["sources"])
        assert all(test in test_names for test in contract["tests"])
