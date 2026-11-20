"""Contact capture and a box-only gravity field for the sixth room.

IGN chapter 22 / PortForward chapter 34 report independent magnet and gravity
controls creating a split-height route. Vertical guides, plate heights, masses
and finite-force capture constraints are original ECHO choices, not a recovered
LIMBO solver. No body positions or velocities are assigned during play here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pymunk

if TYPE_CHECKING:
    from .levels import MagneticPuzzle
    from .physics import Input, Prop, World


BLOCK_COLLISION = 20
CEILING_COLLISION = 21


class MagneticCeiling:
    def __init__(self, space: pymunk.Space, blocks: list[Prop], config: MagneticPuzzle,
                 events: list[str], gravity: float, solid: int):
        self.space, self.blocks, self.config = space, blocks, config
        self.events, self.gravity_strength = events, gravity
        self.enabled = False
        self.box_gravity = 1
        self.captured: dict[int, pymunk.PivotJoint] = {}
        self.capture_history = []
        self.contacts: set[int] = set()
        self.plates = []
        self._indices = {prop.shape: i for i, prop in enumerate(blocks)}
        for prop, ceiling in zip(blocks, config.ceilings, strict=True):
            body = prop.body
            body.moment = float("inf")
            prop.shape.collision_type = BLOCK_COLLISION
            x, _ = body.position
            guide = pymunk.GrooveJoint(
                space.static_body, body,
                (x, ceiling + prop.size[1] / 2 - 8),
                (x, config.floor_y - prop.size[1] / 2 + 8), (0, 0),
            )
            plate_body = pymunk.Body(body_type=pymunk.Body.STATIC)
            plate_body.position = (x, ceiling - 10)
            plate = pymunk.Poly.create_box(plate_body, (prop.size[0] + 16, 20))
            plate.filter = pymunk.ShapeFilter(categories=solid)
            plate.collision_type = CEILING_COLLISION
            space.add(guide, plate_body, plate)
            self.plates.append(plate)
        space.on_collision(BLOCK_COLLISION, CEILING_COLLISION, post_solve=self._contact)

    def _contact(self, arbiter, space, data):
        block, plate = arbiter.shapes
        index = self._indices[block]
        # Normal points from A (block) to B (plate/ceiling).
        # When block hits ceiling from below, normal points up (negative Y in Pygame).
        # If block is already captured, skip - we don't need to re-capture.
        if plate == self.plates[index] and index not in self.captured:
            if arbiter.normal.y < -0.5:
                self.contacts.add(index)

    def toggle_magnet(self):
        self.enabled = not self.enabled
        if not self.enabled and self.captured:
            self.space.remove(*self.captured.values())
            self.captured.clear()
            self.events.append("magnet_release")
        else:
            self.events.append("magnet")

    def toggle_gravity(self):
        self.box_gravity *= -1
        self.events.append("gravity")

    def prepare_step(self):
        self.contacts.clear()
        for prop in self.blocks:
            # Cancel/replace only this block's share of normal space gravity.
            # The courier's acceleration and all existing velocities survive.
            force = prop.body.mass * self.gravity_strength * (self.box_gravity - 1)
            prop.body.apply_force_at_world_point((0, force), prop.body.position)

    def finish_step(self, time: float):
        if not self.enabled:
            return
        for index in sorted(self.contacts - self.captured.keys()):
            body = self.blocks[index].body
            joint = pymunk.PivotJoint(self.space.static_body, body, tuple(body.position))
            joint.max_force = body.mass * self.gravity_strength * 12
            self.space.add(joint)
            self.captured[index] = joint
            self.capture_history.append({"block": index, "time": round(time, 6),
                                         "position": list(body.position)})
            self.events.append("magnet_capture")

    def snapshot(self):
        return {"enabled": self.enabled, "box_gravity": self.box_gravity,
                "captured": sorted(self.captured)}


class MagnetPilot:
    """Natural-spawn witness using only the player's movement/jump/action keys."""

    def __init__(self):
        self.phase = "power"

    def control(self, world: World) -> Input:
        from .physics import Input

        rig, x = world.magnet, world.player.position.x
        if self.phase == "power":
            if x < rig.config.magnet_switch[0] - 4:
                return Input(move=1)
            self.phase = "lift"
            return Input(action=True)
        if self.phase == "lift":
            if x < rig.config.gravity_switch[0] - 4:
                return Input(move=1)
            self.phase = "catch"
            return Input(action=True)
        if self.phase == "catch":
            if 0 not in rig.captured:
                return Input()
            self.phase = "cross"
            return Input(action=True)
        if self.phase == "cross":
            if x >= 823 and world.grounded:
                self.phase = "board"
                return Input(move=1, jump=True)
            return Input(move=1)
        if self.phase == "board":
            if world.support == rig.blocks[1].body:
                self.phase = "bank"
            return Input(move=1 if x < 955 else 0)
        if self.phase == "bank":
            if x >= 960 and world.grounded:
                self.phase = "exit"
                return Input(move=1, jump=True)
            return Input(move=1)
        return Input(move=1)
