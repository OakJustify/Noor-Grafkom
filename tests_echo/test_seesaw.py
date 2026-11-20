"""Natural-spawn, ordinary-input witnesses for the oscillatory room variant.

No stage/teleport fixture: comparison worlds differ only in physical setup.
The production room/constraints are used directly. Comparison worlds change
only a declared rotary lock or damping, never runtime state.
"""

import pymunk
import pytest

import echo_game.physics as ph
from echo_game.seesaw import (
    ANGLE_LIMIT, BEAM_MASS, DEPART_ANGLE, DEPART_MAX_SPEED,
    SPRING_DAMPING, SPRING_STIFFNESS, SeesawPilot, add_seesaw_constraints,
)


def oscillating_world(monkeypatch, *, locked=False, damping=SPRING_DAMPING):
    world = ph.World(3)
    joints = [joint for joint in world.space.constraints
              if world.beam.body in (joint.a, joint.b)]
    assert len(joints) == 3
    for joint in joints:
        if isinstance(joint, pymunk.RotaryLimitJoint) and locked:
            joint.min = joint.max = 0
        if isinstance(joint, pymunk.DampedRotarySpring):
            joint.damping = damping
    return world


def simulate(world, controller, steps=3600, input_stride=1):
    inputs, angles, departures = [], [], []
    for _ in range(steps // input_stride):
        previous_phase = getattr(controller, "phase", None)
        control = controller.control(world)
        if getattr(controller, "phase", None) == "exit" and previous_phase != "exit":
            departures.append((world.time, world.player.position.x,
                               world.beam.body.angle, world.beam.body.angular_velocity))
            assert control.move == 1 and control.jump
        for substep in range(input_stride):
            # Game.update samples controls at 60 Hz and applies jump only to
            # the first of its two fixed 120 Hz physics substeps.
            applied = control if substep == 0 else ph.Input(
                move=control.move, grab=control.grab,
                action=control.action, climb=control.climb,
            )
            inputs.append(applied)
            world.step(applied)
            angles.append(world.beam.body.angle)
            if world.dead or world.complete:
                break
        if world.dead or world.complete:
            break
    return inputs, angles, departures


class DirectWalker:
    """A generous direct attempt: run right and request a jump near the end."""

    def control(self, world):
        return ph.Input(move=1, jump=world.grounded and world.player.position.x >= 1015)


class StandingWalker:
    """Walk onto the right end, then stand there without reversing or jumping."""

    def control(self, world):
        return ph.Input(move=1 if world.player.position.x < 1015 else 0)


def test_oscillatory_constraints_are_passive_and_restoring(monkeypatch):
    world = oscillating_world(monkeypatch)
    body = world.beam.body
    assert body.mass == BEAM_MASS
    assert body.moment == pytest.approx(pymunk.moment_for_box(BEAM_MASS, (440, 18)))
    spring = next(c for c in world.space.constraints if isinstance(c, pymunk.DampedRotarySpring))
    limit = next(c for c in world.space.constraints if isinstance(c, pymunk.RotaryLimitJoint))
    assert spring.rest_angle == 0 and spring.stiffness == SPRING_STIFFNESS
    assert spring.damping == SPRING_DAMPING
    assert (limit.min, limit.max) == (-ANGLE_LIMIT, ANGLE_LIMIT)
    assert not world.crates
    for _ in range(240):
        world.step()
    assert body.angle == 0 and body.angular_velocity == 0


@pytest.mark.parametrize("damping", [15_000, 20_000, 25_000, 30_000])
@pytest.mark.parametrize("input_stride", [1, 2], ids=["120Hz-input", "60Hz-input"])
def test_alternating_inputs_build_motion_and_depart_at_high_crest(monkeypatch, damping, input_stride):
    world = oscillating_world(monkeypatch, damping=damping)
    pilot = SeesawPilot()
    inputs, angles, departures = simulate(world, pilot, input_stride=input_stride)
    assert world.complete and not world.dead
    assert len(inputs) < 2200
    assert pilot.reversals >= 4
    assert any(control.move < 0 for control in inputs)
    assert sum(control.jump for control in inputs) >= 5
    assert max(angles) > 0.30 and min(angles) < -0.30
    assert max(angles) - min(angles) > 0.65
    assert len(departures) == 1
    _, x, angle, omega = departures[0]
    assert x >= 1015 and angle < DEPART_ANGLE and abs(omega) < DEPART_MAX_SPEED
    # Actually land on the destination, not just enter the checkpoint's broad
    # trigger while airborne or fall beside it.
    assert world.grounded and world.support.body_type == pymunk.Body.STATIC
    assert world.player.position.y == pytest.approx(275.15, abs=0.1)


def test_standing_builds_less_motion_than_alternating_runs_and_jumps(monkeypatch):
    active = oscillating_world(monkeypatch)
    _, active_angles, _ = simulate(active, SeesawPilot())
    standing = oscillating_world(monkeypatch)
    _, standing_angles, _ = simulate(standing, StandingWalker())
    assert not standing.complete and not standing.dead
    assert max(active_angles) - min(active_angles) > max(standing_angles) - min(standing_angles) + 0.10
    # Endpoint standing settles near the down/right stop. It does not
    # continue producing the negative/right-high crests used by the witness.
    assert max(standing_angles[-600:]) - min(standing_angles[-600:]) < 0.01
    assert standing.beam.body.angle > 0.32


def test_direct_walk_and_jump_cannot_reach_raised_bank(monkeypatch):
    world = oscillating_world(monkeypatch)
    inputs, _, _ = simulate(world, DirectWalker())
    assert any(control.jump for control in inputs)
    assert world.dead and not world.complete


def test_successful_input_trace_replays_but_static_support_fails(monkeypatch):
    original = oscillating_world(monkeypatch)
    inputs, _, _ = simulate(original, SeesawPilot())
    assert original.complete
    replay = oscillating_world(monkeypatch)
    for control in inputs:
        replay.step(control)
    assert replay.complete and not replay.dead
    assert replay.snapshot() == original.snapshot()
    static = oscillating_world(monkeypatch, locked=True)
    for control in inputs:
        static.step(control)
        if static.dead or static.complete:
            break
    assert static.dead and not static.complete
    assert abs(static.beam.body.angle) < 1e-8
