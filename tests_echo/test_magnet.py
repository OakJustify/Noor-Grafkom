"""Source-linked magnetic capture contracts using actual contacts and inputs.

The campaign witnesses start at the real spawn. The one momentum fixture is
explicitly staged in free space to isolate the instantaneous field change.
"""

import pymunk
import pytest

from echo_game.magnet import MagnetPilot
from echo_game.physics import DT, GRAVITY, Input, World


def drive(world, pilot, frames=2400, stride=1):
    inputs, captured, supports = [], [], set()
    for _ in range(frames):
        control = pilot.control(world)
        for substep in range(stride):
            applied = control if substep == 0 else Input(control.move, action=control.action)
            world.step(applied)
            inputs.append(applied)
            captured.append(tuple(sorted(world.magnet.captured)))
            if world.support in [block.body for block in world.crates]:
                supports.add(next(i for i, block in enumerate(world.crates) if world.support == block.body))
            assert world.gravity == 1 and tuple(world.space.gravity) == (0, GRAVITY)
            if world.dead or world.complete:
                return inputs, captured, supports
    return inputs, captured, supports


def prepare_split():
    world, pilot = World(5), MagnetPilot()
    for _ in range(400):
        world.step(pilot.control(world))
        if pilot.phase == "cross":
            return world
    pytest.fail("Natural-input pilot did not create a split")


@pytest.mark.parametrize("stride", [1, 2], ids=["120Hz-input", "60Hz-input"])
def test_magnetic_split_height_route_from_spawn(stride):
    world = World(5)
    inputs, captures, supports = drive(world, MagnetPilot(), stride=stride)
    assert world.complete and not world.dead
    assert world.time < 8
    assert supports == {1}  # The returned second block actually supports the player.
    assert set(captures) == {(), (0,)}
    assert world.magnet.snapshot() == {"enabled": True, "box_gravity": 1, "captured": [0]}
    assert world.crates[0].body.position.y < 310
    assert world.crates[1].body.position.y == pytest.approx(418.15, abs=0.2)
    assert world.grounded and world.support.body_type == pymunk.Body.STATIC
    assert world.player.position.y == pytest.approx(295.15, abs=0.2)
    assert sum(i.action and (n == 0 or not inputs[n - 1].action) for n, i in enumerate(inputs)) == 3


class MistimedPilot(MagnetPilot):
    def __init__(self, timing):
        super().__init__()
        self.timing = timing
        self.started = None
        self.captured_when_reversed = None

    def control(self, world):
        if self.phase == "catch":
            if self.started is None:
                self.started = world.time
            elapsed = world.time - self.started
            reverse = (self.timing == "early" and elapsed >= .10
                       or self.timing == "late" and len(world.magnet.captured) == 2
                       or self.timing == "momentum" and elapsed >= .53)
            if reverse:
                self.captured_when_reversed = sorted(world.magnet.captured)
                self.phase = "cross"
                return Input(action=True)
            return Input()
        return super().control(world)


@pytest.mark.parametrize("timing, expected", [("early", []), ("late", [0, 1]), ("momentum", [0, 1])])
def test_early_and_late_switches_fail_the_split_route(timing, expected):
    world, pilot = World(5), MistimedPilot(timing)
    _, _, supports = drive(world, pilot, frames=1500)
    assert not world.complete
    assert world.player.position.x < 1050
    assert sorted(world.magnet.captured) == expected
    assert world.magnet.box_gravity == 1
    assert 1 not in supports
    if timing == "momentum":
        # Reversing just before second contact is already too late: acceleration
        # changes sign but existing upward momentum still carries it to the plate.
        assert pilot.captured_when_reversed == [0]


def test_magnet_requires_power_and_actual_ceiling_contact():
    world, pilot = World(5), MagnetPilot()
    while pilot.phase != "lift":
        world.step(pilot.control(world))
    assert world.magnet.enabled and world.magnet.box_gravity == 1
    for _ in range(120):
        world.step()
    assert not world.magnet.captured
    assert world.crates[0].body.position.y == pytest.approx(383, abs=.2)
    while world.magnet.box_gravity == 1:
        world.step(pilot.control(world))
    for _ in range(25):
        world.step()
    assert not world.magnet.captured  # Already rising, still clear of the plate.
    assert world.crates[0].body.position.y < 365
    for _ in range(80):
        world.step()
    assert sorted(world.magnet.captured) == [0, 1]
    for record in world.magnet.capture_history:
        index = record["block"]
        block = world.crates[index]
        top_at_contact = record["position"][1] - block.size[1] / 2 - 2
        assert abs(top_at_contact - world.level.magnet.ceilings[index]) < 6
    history = list(world.magnet.capture_history)
    for _ in range(120):
        world.step()
    assert world.magnet.capture_history == history  # No duplicate capture per frame.


def test_unpowered_ceiling_does_not_retain_contacted_blocks():
    world = World(5)
    # Walk directly to the field control, passing the separate magnet control.
    while world.player.position.x < 462:
        world.step(Input(move=1))
    world.step(Input(action=True))
    for _ in range(160):
        world.step()
    assert world.magnet.contacts == {0, 1}
    assert not world.magnet.enabled and not world.magnet.captured
    world.step(Input(action=True))
    for _ in range(160):
        world.step()
    assert [p.body.position.y for p in world.crates] == pytest.approx([383.15, 418.15], abs=.2)


def test_box_field_preserves_velocity_and_leaves_player_gravity_alone():
    world = World(5)
    # Staged free-space fixture, not a campaign solution.
    for body, position, velocity in (
        (world.player, (465, 400), (23, -70)),
        (world.crates[0].body, (720, 330), (0, -120)),
        (world.crates[1].body, (940, 300), (0, 30)),
    ):
        body.position, body.velocity = position, velocity
        world.space.reindex_shapes_for_body(body)
    bodies = [world.player] + [prop.body for prop in world.crates]
    before = [tuple(b.velocity) for b in bodies]
    world.interact()
    assert [tuple(b.velocity) for b in bodies] == before
    assert world.magnet.box_gravity == -1 and world.gravity == 1
    assert tuple(world.space.gravity) == (0, GRAVITY)
    world.step()
    assert world.player.velocity.y == pytest.approx(-70 + GRAVITY * DT)
    assert world.crates[0].body.velocity.y == pytest.approx(-120 - GRAVITY * DT)
    assert world.crates[1].body.velocity.y == pytest.approx(30 - GRAVITY * DT)


def test_magnet_release_drops_retained_block_without_switching_gravity():
    world = prepare_split()
    world.drain_events()
    while world.player.position.x > 347:
        world.step(Input(move=-1))
    before = world.crates[0].body.position.y
    assert sorted(world.magnet.captured) == [0]
    joint = world.magnet.captured[0]
    world.step(Input(action=True))
    assert joint not in world.space.constraints
    assert not world.magnet.enabled and not world.magnet.captured
    assert world.magnet.box_gravity == 1 and world.gravity == 1
    assert "magnet_release" in world.drain_events()
    for _ in range(120):
        world.step()
    assert world.crates[0].body.position.y > before + 70


def test_magnetic_input_trace_replays_deterministically():
    original = World(5)
    inputs, _, _ = drive(original, MagnetPilot())
    replay = World(5)
    for control in inputs:
        replay.step(control)
    assert replay.snapshot() == original.snapshot()
    assert replay.magnet.capture_history == original.magnet.capture_history
