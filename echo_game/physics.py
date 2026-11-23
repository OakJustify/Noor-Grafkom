"""Deterministic Pymunk simulation, independent of rendering and sound.

The controller is deliberately not a teleporting platformer controller: crates,
ropes and the seesaw interact through mass, friction and solver constraints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pymunk

from .levels import LEVELS, Rect
from .magnet import MagneticCeiling
from .seesaw import add_seesaw_constraints

DT = 1 / 120
GRAVITY = 1050.0
MOVE_SPEED = 190.0
JUMP_SPEED = 445.0
PLAYER_SIZE = (22, 44)
PLAYER = 1
SOLID = 2
ROPE = 4
# Acceleration constants (px/s²) - exposed for tuning
GROUND_ACCEL = 4500.0
AIR_ACCEL = 620.0
CRATE_GROUND_ACCEL = 4500.0  # Same as ground when holding crate
CRATE_AIR_ACCEL = 620.0


@dataclass(frozen=True)
class PlayerCapabilities:
    """Values copied from the controller actually used by the game."""

    horizontal_speed: float
    jump_speed: float
    gravity: float
    width: float
    height: float
    air_control: float = 1.0

    @classmethod
    def from_controller(cls) -> "PlayerCapabilities":
        return cls(MOVE_SPEED, JUMP_SPEED, GRAVITY, *PLAYER_SIZE)

    @property
    def max_jump_height(self) -> float:
        return self.jump_speed ** 2 / (2 * self.gravity)

    def time_to_height(self, delta_y: float) -> float | None:
        """Time to reach a surface ``delta_y`` below takeoff on the descent.

        Y grows downward in Pygame/Pymunk, so a higher target has a negative
        delta.  The descending root is used: landing on a roof happens after
        the apex, not while the courier is still rising through it.
        """
        v, g = self.jump_speed, self.gravity
        discriminant = v * v + 2 * g * delta_y
        if discriminant < 0:
            return None
        return (v + math.sqrt(discriminant)) / g

    def horizontal_reach(self, delta_y: float) -> float | None:
        time = self.time_to_height(delta_y)
        return None if time is None else self.horizontal_speed * time

    def can_land_on(self, previous, candidate) -> bool:
        """Simulate a jump from previous platform's right edge and check if player lands on candidate's top surface.

        The simulation uses the same physics constants as the game controller:
        - Takeoff from previous.right with max horizontal velocity (MOVE_SPEED)
        - Jump velocity JUMP_SPEED upward
        - Gravity GRAVITY downward
        - Player collision box: PLAYER_SIZE (22x44) with corner radius 3

        Returns True if the trajectory intersects the candidate platform's top surface
        during the descent phase (after apex).
        """
        caps = self
        dt = DT
        g = caps.gravity
        vx = caps.horizontal_speed
        vy = -caps.jump_speed  # negative because Y grows downward

        # Takeoff position: player's center when right edge is at previous.right
        # Player width = 22, so center_x = previous.right - 11
        x = previous.right - caps.width / 2
        # Player stands on previous platform: bottom at previous.y, center_y = previous.y - height/2
        y = previous.y - caps.height / 2

        # Platform top surface bounds
        platform_left = candidate.x
        platform_right = candidate.right
        platform_top = candidate.y

        # Simulation limits
        max_steps = 300  # ~2.5 seconds at 120Hz
        landed = False
        passed_apex = False

        for _ in range(max_steps):
            # Update position
            x += vx * dt
            vy += g * dt
            y += vy * dt

            # Track if we've passed the apex (started descending)
            if vy > 0:
                passed_apex = True

            # Player AABB
            player_left = x - caps.width / 2
            player_right = x + caps.width / 2
            player_bottom = y + caps.height / 2

            # Check if we've fallen past the platform (missed it)
            if player_bottom > platform_top + caps.height:
                # We're well below the platform top without landing
                break

            # Check landing collision during descent
            if passed_apex:
                # Horizontal overlap with platform
                if player_right >= platform_left and player_left <= platform_right:
                    # Vertical: player bottom has reached or crossed platform top
                    if player_bottom >= platform_top:
                        landed = True
                        break

            # Early exit: if we're past the platform horizontally and descending
            if passed_apex and player_left > platform_right:
                break

        return landed


@dataclass(frozen=True)
class Input:
    move: float = 0
    jump: bool = False
    grab: bool = False
    action: bool = False
    climb: float = 0
    lantern: bool = False


@dataclass
class Prop:
    body: pymunk.Body
    shape: pymunk.Shape
    size: tuple[float, float]
    heavy: bool = False


class World:
    def __init__(self, chapter: int = 0, level=None, bounds: bool = True, iterations: int = 30):
        if level is None:
            if not 0 <= chapter < len(LEVELS):
                raise ValueError("Invalid chapter")
            level = LEVELS[chapter]
        self.chapter = chapter
        self.level = level
        self.endless = False
        self.space = pymunk.Space()
        self.space.gravity = (0, GRAVITY)
        self.space.iterations = iterations
        self.space.collision_slop = 0.15
        self.time = 0.0
        self.gravity = 1
        self.events: list[str] = []
        self.dead = False
        self.complete = False
        self.death_reason = ""
        self.grounded = False
        self.support: pymunk.Body | None = None
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.water_time = 0.0
        self.facing = 1
        self.gate_open = False
        self.gate_fraction = 0.0
        self.gravity_remaining = 0.0
        self.gravity_beep_remaining = 0.0
        self.action_held = False
        self.water_surface = self.level.water.y if self.level.water else None
        self.water_active = False
        self.water_transferred_area = 0.0
        self.cover_open = False
        self.cover_fraction = 0.0
        self.cover_body = None
        self.rope_distance = 0.0
        self.grab_joint: pymunk.Constraint | None = None
        self.grabbed: pymunk.Body | None = None
        self.grab_kind = ""
        self.regrab_delay = 0.0
        self.crates: list[Prop] = []
        self.ropes: list[pymunk.Body] = []
        self.rope_shapes: list[pymunk.Shape] = []
        self.beam: Prop | None = None
        self.gate_body: pymunk.Body | None = None
        self.magnet: MagneticCeiling | None = None
        self.lantern_on = False
        for rect in self.level.terrain:
            self._static_rect(rect)
        # Room bounds are solid; the bottom is deliberately a fall hazard.
        self._static_rect(Rect(-100, -200, 20, 1000))
        if bounds:
            self._static_rect(Rect(self.level.width + 80, -200, 20, 1000))
        self.player = pymunk.Body(2.0, float("inf"))
        self.player.position = self.level.spawn
        self.player_shape = pymunk.Poly.create_box(self.player, PLAYER_SIZE, radius=3)
        self.player_shape.friction = 0.75
        self.player_shape.filter = pymunk.ShapeFilter(categories=PLAYER, mask=SOLID)
        self.space.add(self.player, self.player_shape)
        for x, y, size, mass in self.level.crates:
            self.crates.append(self._prop((x, y), (size, size), mass))
        if self.level.magnet:
            magnetic_blocks = [self.crates[i] for i in self.level.magnet.crate_indices]
            self.magnet = MagneticCeiling(self.space, magnetic_blocks, self.level.magnet,
                                          self.events, GRAVITY, SOLID)
        if self.level.gate:
            r = self.level.gate
            self.gate_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            self.gate_body.position = (r.x + r.w / 2, r.y + r.h / 2)
            shape = pymunk.Poly.create_box(self.gate_body, (r.w, r.h))
            shape.friction = 0.7
            shape.filter = pymunk.ShapeFilter(categories=SOLID)
            self.space.add(self.gate_body, shape)
        if self.level.rope:
            self._rope(*self.level.rope)
        if self.level.cover:
            r = self.level.cover
            self.cover_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            self.cover_body.position = (r.x + r.w / 2, r.y + r.h / 2)
            shape = pymunk.Poly.create_box(self.cover_body, (r.w, r.h))
            shape.friction = 0.7
            shape.filter = pymunk.ShapeFilter(categories=SOLID)
            self.space.add(self.cover_body, shape)
        if self.level.seesaw:
            x, y, length = self.level.seesaw
            self.beam = self._prop((x, y), (length, 18), 70)
            add_seesaw_constraints(self.space, self.beam)

    def _static_rect(self, r: Rect):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = (r.x + r.w / 2, r.y + r.h / 2)
        shape = pymunk.Poly.create_box(body, (r.w, r.h))
        shape.friction = 0.35
        shape.filter = pymunk.ShapeFilter(categories=SOLID)
        self.space.add(body, shape)
        return body, shape

    @property
    def width(self):
        return self.level.width

    def terrain_rects(self):
        return self.level.terrain

    def _prop(self, pos, size, mass) -> Prop:
        body = pymunk.Body(mass, pymunk.moment_for_box(mass, size))
        body.position = pos
        shape = pymunk.Poly.create_box(body, size, radius=2)
        shape.friction = 0.7 if mass >= 20 else 0.42
        shape.elasticity = 0.0
        shape.filter = pymunk.ShapeFilter(categories=SOLID)
        self.space.add(body, shape)
        return Prop(body, shape, size, mass >= 20)

    def _rope(self, x: float, y: float, count: int, length: float):
        self.rope_anchor = (x, y)
        direction = pymunk.Vec2d(-math.sin(0.43), math.cos(0.43))
        previous = self.space.static_body
        for i in range(count):
            body = pymunk.Body(0.25, pymunk.moment_for_segment(0.25, (0, -length / 2), (0, length / 2), 2))
            body.position = pymunk.Vec2d(x, y) + direction * (length * (i + 0.5))
            body.angle = 0.43
            shape = pymunk.Segment(body, (0, -length / 2), (0, length / 2), 2)
            shape.filter = pymunk.ShapeFilter(group=2, categories=ROPE, mask=SOLID)
            shape.friction = 0.5
            self.space.add(body, shape)
            anchor = pymunk.Vec2d(x, y) + direction * (length * i)
            pivot = pymunk.PivotJoint(previous, body, anchor)
            pivot.collide_bodies = False
            self.space.add(pivot)
            if i:
                limit = pymunk.RotaryLimitJoint(previous, body, -0.4, 0.4)
                self.space.add(limit)
            self.ropes.append(body)
            self.rope_shapes.append(shape)
            previous = body

    def _ground(self):
        p = self.player.position
        foot = p.y + self.gravity * 22
        self.grounded = False
        self.support = None
        if self.player.velocity.y * self.gravity < -70:
            return
        for dx in (-7, 0, 7):
            hits = self.space.segment_query((p.x + dx, foot - self.gravity * 3),
                                            (p.x + dx, foot + self.gravity * 7), 1,
                                            pymunk.ShapeFilter(mask=SOLID))
            for hit in hits:
                if not hit.shape.sensor and hit.normal.y * self.gravity < -0.45:
                    self.grounded = True
                    self.support = hit.shape.body
                    return

    def _release(self):
        if self.grab_joint:
            self.space.remove(self.grab_joint)
        self.grab_joint = None
        self.grabbed = None
        self.grab_kind = ""

    def _grab(self):
        if self.grab_joint or self.regrab_delay > 0:
            return
        p = self.player.position
        # Prefer rope; query actual segments rather than just a guessed endpoint.
        candidates = []
        for body, shape in zip(self.ropes, self.rope_shapes):
            query = shape.point_query(p)
            if query.distance < 46:
                candidates.append((max(0, query.distance), body, query.point, "rope"))
        for prop in self.crates:
            query = prop.shape.point_query(p)
            if query.distance < 30 and abs(prop.body.position.y - p.y) < prop.size[1] * 0.6:
                candidates.append((max(0, query.distance) + 10, prop.body, query.point, "crate"))
        if not candidates:
            return
        _, body, point, kind = min(candidates, key=lambda c: c[0])
        if kind == "rope":
            joint = pymunk.PivotJoint(self.player, body, point)
            joint.max_force = 12000
            index = self.ropes.index(body)
            length = self.level.rope[3]
            self.rope_distance = index * length + max(0, min(length, body.world_to_local(point).y + length / 2))
        else:
            side = 1 if body.position.x > p.x else -1
            joint = pymunk.DampedSpring(self.player, body, (side * 14, 0),
                                        body.world_to_local(point), 8, 600, 65)
            joint.max_force = 6000
        joint.collide_bodies = False
        self.space.add(joint)
        self.grab_joint, self.grabbed, self.grab_kind = joint, body, kind
        self.events.append("grab")

    def _climb_rope(self, direction: float, dt: float):
        """Move the hand constraint along the chain, not the character position.

        Climbing and swing/release are walkthrough-observed behaviors; this
        sliding hand constraint and its speed are ECHO's chosen approximation.
        """
        if not direction or self.grab_kind != "rope":
            return
        length = self.level.rope[3]
        distance = max(40, min(len(self.ropes) * length - 2,
                              self.rope_distance - max(-1, min(1, direction)) * 85 * dt))
        index = min(len(self.ropes) - 1, int(distance / length))
        body = self.ropes[index]
        hand = self.grab_joint.anchor_a
        if body != self.grabbed:
            self.space.remove(self.grab_joint)
            self.grab_joint = pymunk.PivotJoint(self.player, body, hand, (0, distance - index * length - length / 2))
            self.grab_joint.max_force = 12000
            self.grab_joint.collide_bodies = False
            self.space.add(self.grab_joint)
            self.grabbed = body
        else:
            self.grab_joint.anchor_b = (0, distance - index * length - length / 2)
        self.rope_distance = distance

    def _water_flow(self, dt: float):
        if not self.level.water or not self.water_active:
            return
        target = self.level.water.y - self.level.water_raise
        rise = min(self.level.water_rate * dt, max(0, self.water_surface - target))
        self.water_surface -= rise
        self.water_transferred_area += rise * self.level.water.w
        if self.water_surface <= target + 1e-8:
            self.water_surface = target
            self.water_active = False

    def _cover(self, dt: float):
        if not self.cover_body:
            return
        target = 1.0 if self.cover_open else 0.0
        delta = max(-dt, min(dt, target - self.cover_fraction))
        self.cover_fraction += delta
        self.cover_body.velocity = (-delta * (self.level.cover.w + 20) / dt, 0)

    def _buoyancy(self):
        water = self.level.water
        if not water:
            return
        for prop in self.crates:
            b = prop.body
            if water.x - prop.size[0] / 2 < b.position.x < water.x + water.w + prop.size[0] / 2:
                prop.shape.cache_bb()
                bb = prop.shape.bb
                depth = min(bb.top - bb.bottom, max(0, bb.top - self.water_surface))
                ratio = min(1, depth / prop.size[1])
                if ratio:
                    b.apply_force_at_world_point((0, -GRAVITY * b.mass * 2.3 * ratio), b.position)
                    b.force += (-b.velocity.x * b.mass * 4 * ratio, -b.velocity.y * b.mass * 6 * ratio)
                    b.torque -= b.angular_velocity * b.moment * 3 * ratio
                    # A box's broad waterline provides a restoring torque.
                    b.torque -= math.sin(b.angle) * b.moment * 30 * ratio

    def saw_positions(self):
        return [(x + math.sin(self.time * rate) * travel, y, radius)
                for x, y, radius, travel, rate in self.level.saws]

    def interact(self):
        p = self.player.position
        if self.magnet:
            if p.get_distance(self.level.magnet.magnet_switch) < 45:
                self.magnet.toggle_magnet()
                return
            if p.get_distance(self.level.magnet.gravity_switch) < 45:
                self.magnet.toggle_gravity()
                return
        if self.level.cover_switch and p.get_distance(self.level.cover_switch) < 45:
            self.cover_open = not self.cover_open
            self.events.append("gate")
            return
        if self.level.valve and p.get_distance(self.level.valve) < 66:
            self.water_active = not self.water_active
            self.events.append("gate")
            return
        for switch in self.level.switches:
            if p.get_distance(switch) < 66:
                self.gravity_remaining = self.level.gravity_duration
                self.gravity_beep_remaining = 1.0
                self.flip_gravity(-1)
                self.events.append("tick")
                return

    def flip_gravity(self, direction: int):
        self._release()
        self.gravity = direction
        self.space.gravity = (0, GRAVITY * direction)
        # A field changes acceleration, not existing momentum. Resetting vy
        # removed the mid-air timing described in the reference walkthrough.
        # Preserve coyote and jump_buffer across gravity flip (C5).
        self.grounded = False
        self.events.append("gravity")

    def _gate(self, dt):
        if not self.gate_body:
            return
        was_open = self.gate_open
        self.gate_open = False
        if self.level.plate:
            r = self.level.plate
            for shape in [self.player_shape] + [c.shape for c in self.crates]:
                shape.cache_bb()
                bb = shape.bb
                if (bb.right > r.x and bb.left < r.x + r.w
                        and r.y - 2 <= bb.top <= r.y + r.h + 8):
                    self.gate_open = True
        if self.gate_open and not was_open:
            self.events.append("gate")
        target = 1.0 if self.gate_open else 0.0
        delta = max(-dt * 1.4, min(dt * 1.4, target - self.gate_fraction))
        if delta < 0:
            # A descending door cannot pass through a box in its opening.
            # Kinematic Chipmunk bodies have infinite effective mass, so bound
            # their sweep before integration rather than crush a jammed crate.
            gate = self.level.gate
            bottom = self.gate_body.position.y + gate.h / 2
            next_bottom = bottom - delta * (gate.h + 20)
            for prop in self.crates:
                prop.shape.cache_bb()
                bb = prop.shape.bb
                if (bb.right > gate.x and bb.left < gate.x + gate.w
                        and bb.top > bottom - gate.h and bb.bottom < next_bottom):
                    clearance = max(0, bb.bottom - bottom)
                    delta = max(delta, -clearance / (gate.h + 20))
        self.gate_fraction += delta
        self.gate_body.velocity = (0, -delta * (self.level.gate.h + 20) / dt)

    def kill(self, reason: str):
        if not self.dead:
            self.dead = True
            self.death_reason = reason
            self._release()
            self.events.append("death")

    def _saw_contact(self, x: float):
        """Campaign saws remain immediately fatal."""
        self.kill("The machinery is still hungry.")

    def _fall_death(self):
        self.kill("The dark has no floor.")

    def step(self, control: Input = Input(), dt: float = DT):
        if self.dead or self.complete:
            return
        if not 0 < dt <= 1 / 30:
            raise ValueError("Use small fixed steps (normally 1/120 second)")
        self.time += dt
        self.regrab_delay = max(0, self.regrab_delay - dt)
        if self.gravity_remaining:
            self.gravity_remaining = max(0, self.gravity_remaining - dt)
            if self.gravity_remaining < 1e-8:
                self.gravity_remaining = 0
                self.gravity_beep_remaining = 0
                self.flip_gravity(1)
            else:
                self.gravity_beep_remaining -= dt
                if self.gravity_beep_remaining <= 0:
                    self.events.append("tick")
                    self.gravity_beep_remaining += max(0.12, self.gravity_remaining * 0.2)
        old_ground = self.grounded
        self._ground()
        if self.grounded and not old_ground:
            self.events.append("land")
        self.coyote = 0.10 if self.grounded else max(0, self.coyote - dt)
        self.jump_buffer = max(0, self.jump_buffer - dt)
        if control.action and not self.action_held:
            self.interact()
        self.action_held = control.action
        if control.jump:
            self.jump_buffer = 0.12
        if not control.grab:
            self._release()
        elif self.grab_joint is None:
            self._grab()
        move = max(-1.0, min(1.0, control.move))
        if move:
            self.facing = 1 if move > 0 else -1
        if self.grab_kind == "rope":
            self._climb_rope(control.climb, dt)
            self.player.apply_force_at_world_point((move * 750, 0), self.player.position)
            if control.jump:
                vx, vy = self.player.velocity
                self._release()
                self.player.velocity = (vx + move * 75, vy - self.gravity * 130)
                self.regrab_delay = 0.15  # Reduced from 0.3s for better responsiveness
                self.jump_buffer = 0
                self.events.append("jump")
        else:
            target = move * (135 if self.grab_kind == "crate" else MOVE_SPEED)
            if self.grab_kind == "crate":
                accel = CRATE_GROUND_ACCEL if self.grounded else CRATE_AIR_ACCEL
            else:
                accel = GROUND_ACCEL if self.grounded else AIR_ACCEL
            vx, vy = self.player.velocity
            dv = max(-accel * dt, min(accel * dt, target - vx))
            # Walking force transfers momentum into bodies through contacts.
            self.player.velocity = (vx + dv, vy)
            if self.jump_buffer and self.coyote:
                self.player.velocity = (self.player.velocity.x, -self.gravity * JUMP_SPEED)
                # JUMP_SPEED is the controller's actual takeoff speed; the
                # procedural validator imports the same constant.
                self.jump_buffer = self.coyote = 0
                self.grounded = False
                self.events.append("jump")
        self._water_flow(dt)
        self._cover(dt)
        self._buoyancy()
        self._gate(dt)
        if self.magnet:
            self.magnet.prepare_step()
        self.space.step(dt)
        if self.magnet:
            self.magnet.finish_step(self.time)
        self.player.angle = 0
        p = self.player.position
        # Player half-height is 22 (PLAYER_SIZE[1] / 2). Use full height for collision.
        half_height = 22
        for x, y, radius in self.saw_positions():
            # Capsule-like closest point test, not a full bounding circle.
            cy = max(p.y - half_height, min(p.y + half_height, y))
            if math.hypot(p.x - x, cy - y) < radius + 10:
                self._saw_contact(x)
                if self.dead:
                    break
        if (self.gravity == 1 and ((p.y > 590 and self.chapter != 2) or p.y > 640)
                or self.gravity == -1 and ((p.y < -590 and self.chapter != 2) or p.y < -640)):
            self._fall_death()
        water = self.level.water
        if water and water.x < p.x < water.x + water.w and p.y > self.water_surface + 16:
            self.water_time += dt
            if self.water_time > 0.45:
                self.kill("The flood is too deep. The crate floats; you do not.")
        else:
            self.water_time = max(0, self.water_time - dt * 2)
        if self.gate_body and not self.gate_open:
            if self.gate_body.position.get_distance(p) < 30 and abs(self.player.velocity.y) < 20:
                self.kill("Keep a weight on the plate.")
        if not self.dead and p.x > self.level.exit[0] - 28 and abs(p.y - self.level.exit[1]) < 100:
            self.complete = True
            self._release()
            self.events.append("checkpoint")

    def toggle_lantern(self):
        self.lantern_on = not self.lantern_on

    def drain_events(self) -> list[str]:
        events = list(self.events)
        self.events.clear()
        return events

    def snapshot(self):
        return {"chapter": self.chapter + 1, "time": round(self.time, 3),
                "player": [round(n, 2) for n in self.player.position],
                "velocity": [round(n, 2) for n in self.player.velocity],
                "grounded": self.grounded, "gravity": self.gravity,
                "gravity_remaining": round(self.gravity_remaining, 3),
                "water_surface": round(self.water_surface, 3) if self.water_surface is not None else None,
                "water_active": self.water_active,
                "water_transferred_area": round(self.water_transferred_area, 3),
                "cover_open": self.cover_open,
                "cover_fraction": round(self.cover_fraction, 3),
                "rope_distance": round(self.rope_distance, 3) if self.grab_kind == "rope" else None,
                "gate_open": self.gate_open, "gate_fraction": round(self.gate_fraction, 3),
                "grab_kind": self.grab_kind, "dead": self.dead, "complete": self.complete,
                "crates": [{"position": [round(n, 2) for n in c.body.position],
                            "angle": round(c.body.angle, 4)} for c in self.crates],
                "beam_angle": round(self.beam.body.angle, 4) if self.beam else None,
                "magnet": self.magnet.snapshot() if self.magnet else None}
