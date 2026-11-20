"""A player-driven oscillating support, not a permanently weighted staircase.

The run/jump/reverse/phase departure is grounded in REFERENCE_GAMEPLAY.md §5;
all geometry, spring constants and thresholds here are original ECHO tuning.
Recommended room: beam (840, 440, 440), spawn (140, 380), no crates,
left bank Rect(-80, 420, 695, 220), right bank Rect(1090, 300, 690, 340),
width 1700, exit (1580, 270). Positive angles lower the right end (Y down).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pymunk

if TYPE_CHECKING:
    from .physics import Input, Prop, World


BEAM_MASS = 70.0
SPRING_STIFFNESS = 1_000_000.0
SPRING_DAMPING = 20_000.0
ANGLE_LIMIT = 0.36
END_MARGIN = 45.0
DEPART_ANGLE = -0.26
DEPART_MAX_SPEED = 0.08


def add_seesaw_constraints(space: pymunk.Space, beam: Prop) -> tuple[pymunk.Constraint, ...]:
    """Configure a newly created beam and add its three passive constraints.

    Call instead of the old seesaw joint block, not in addition to it. Only
    initial mass/inertia/friction and physical constraints are configured;
    neither this helper nor the pilot drives beam angle, speed or torque.
    """
    body = beam.body
    body.mass = BEAM_MASS
    body.moment = pymunk.moment_for_box(BEAM_MASS, beam.size)
    beam.shape.friction = 0.85
    pivot = pymunk.PivotJoint(space.static_body, body, tuple(body.position))
    limit = pymunk.RotaryLimitJoint(space.static_body, body, -ANGLE_LIMIT, ANGLE_LIMIT)
    spring = pymunk.DampedRotarySpring(
        space.static_body, body, 0, SPRING_STIFFNESS, SPRING_DAMPING
    )
    constraints = (pivot, limit, spring)
    space.add(*constraints)
    return constraints


class SeesawPilot:
    """An input-only witness: approach, alternate ends, leave near a high crest.

    The endpoint jumps unload the support briefly while momentum carries it
    through the reversal. Departure reads both angle and angular velocity;
    it is not granted after a repetition count or at a hard-coded time.
    """

    def __init__(self):
        self.phase = "approach"
        self.direction = 1
        self.reversals = 0

    def control(self, world: World) -> Input:
        # Local import avoids a cycle when physics imports the joint helper.
        from .physics import Input

        if self.phase == "exit":
            return Input(move=1)
        body = world.beam.body
        extent = world.beam.size[0] / 2 - END_MARGIN
        left, right = body.position.x - extent, body.position.x + extent
        x = world.player.position.x
        if self.phase == "approach":
            if x < right:
                return Input(move=1)
            self.phase = "pump"
            self.direction = -1
            self.reversals += 1
            return Input(move=-1, jump=True)
        if self.direction < 0 and x <= left:
            self.direction = 1
            self.reversals += 1
            return Input(move=1, jump=True)
        if self.direction > 0 and x >= right:
            if (body.angle < DEPART_ANGLE
                    and abs(body.angular_velocity) < DEPART_MAX_SPEED
                    and (world.grounded or world.coyote > 0)):
                self.phase = "exit"
                return Input(move=1, jump=True)
            self.direction = -1
            self.reversals += 1
            return Input(move=-1, jump=True)
        return Input(move=self.direction)
