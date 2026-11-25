"""NUR movement and interaction rules over its standalone Pymunk engine."""

import math

from .engine import DT, Input, World, JUMP_SPEED, GROUND_ACCEL, AIR_ACCEL
from dataclasses import dataclass
from . import config
from .state import Stamina


@dataclass(frozen=True)
class NurInput(Input):
    shift: bool = False
    sprint: bool = False
    focus: bool = False
    plant: bool = False


class NurWorld(World):
    quest = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stamina = Stamina()
        self.sprinting = False

    def configure_phantoms(self):
        self.phantom_rects = getattr(self.quest.plan, "platforms", ()) if self.quest else ()
        self.phantom_shapes = {}
        self.sync_phantoms()

    def sync_phantoms(self):
        if not hasattr(self, "phantom_shapes"):
            return
        active = self.quest is not None and getattr(self.quest, "phase", 0) == 1
        px, py = self.player.position
        for rect in self.phantom_rects:
            if not active:
                pair = self.phantom_shapes.pop(rect, None)
                if pair:
                    self.space.remove(pair[1], pair[0])
                    if self.support == pair[0]:
                        self.support = None
                        self.grounded = False
                        self.coyote = 0
            elif rect not in self.phantom_shapes:
                # Don't materialise a solid shape inside the player's body.
                # Its outline remains visible; it appears once the space clears.
                overlaps = (rect.x < px + 11 and rect.x + rect.w > px - 11
                            and rect.y < py + 22 and rect.y + rect.h > py - 22)
                if not overlaps:
                    self.phantom_shapes[rect] = self._static_rect(rect)

    def _gate(self, dt):
        if self.quest is None:
            return super()._gate(dt)
        self.gate_open = self.quest.complete
        target = float(self.gate_open)
        delta = max(-dt * 1.4, min(dt * 1.4, target - self.gate_fraction))
        self.gate_fraction += delta
        self.gate_body.velocity = (0, -delta * (self.level.gate.h + 20) / dt)

    def step(self, control: Input = Input(), dt: float = DT):
        if self.dead or self.complete:
            self.sprinting = False
            return
        if not 0 < dt <= 1 / 30:
            raise ValueError("Use small fixed steps (normally 1/120 second)")
        self.sync_phantoms()
        # NUR owns its controller instead of changing the engine's base speed or
        # bypassing collision. Forces, contacts, grabs and jumps remain Pymunk.
        self.time += dt
        self.regrab_delay = max(0, self.regrab_delay - dt)
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
        self.sprinting = self.stamina.step(
            dt, bool(getattr(control, "sprint", False)), abs(self.player.velocity.x) > 30,
            eligible=bool(move) and not self.grab_kind,
        )
        if self.grab_kind == "rope":
            self._climb_rope(control.climb, dt)
            self.player.apply_force_at_world_point((move * 750, 0), self.player.position)
            if control.jump:
                vx, vy = self.player.velocity
                self._release()
                self.player.velocity = (vx + move * 75, vy - self.gravity * 130)
                self.regrab_delay = 0.15
                self.jump_buffer = 0
                self.events.append("jump")
        else:
            speed = 135 if self.grab_kind == "crate" else config.RUN_SPEED if self.sprinting else config.WALK_SPEED
            accel = GROUND_ACCEL if self.grounded else AIR_ACCEL
            vx, vy = self.player.velocity
            dv = max(-accel * dt, min(accel * dt, move * speed - vx))
            self.player.velocity = (vx + dv, vy)
            if self.jump_buffer and self.coyote:
                self.player.velocity = (self.player.velocity.x, -self.gravity * JUMP_SPEED)
                self.jump_buffer = self.coyote = 0
                self.grounded = False
                self.events.append("jump")
        self._water_flow(dt)
        self._cover(dt)
        self._buoyancy()
        self._gate(dt)
        self.space.step(dt)
        self.player.angle = 0
        p = self.player.position
        for x, y, radius in self.saw_positions():
            cy = max(p.y - 22, min(p.y + 22, y))
            if math.hypot(p.x - x, cy - y) < radius + 10:
                self._saw_contact(x)
                if self.dead:
                    break
        if p.y > (640 if self.chapter == 2 else 590):
            self._fall_death()
        water = self.level.water
        if water and water.x < p.x < water.x + water.w and p.y > self.water_surface + 16:
            self.water_time += dt
            if self.water_time > 0.45:
                self.kill("The flood is too deep. The crate floats; you do not.")
        else:
            self.water_time = max(0, self.water_time - dt * 2)
        if not self.dead and p.x > self.level.exit[0] - 28 and abs(p.y - self.level.exit[1]) < 100:
            self.complete = True
            self._release()
            self.events.append("checkpoint")
        if self.quest is not None and not self.quest.complete:
            self.complete = False
            self.events = [event for event in self.events if event != "checkpoint"]
        # The final room ends through mercy, not the campaign's x-coordinate
        # trigger. Reaching the far wall must never freeze an unfinished boss.
        if self.chapter == config.BOSS_ARENA_ROOM and self.complete:
            self.complete = False
            self.events = [event for event in self.events if event != "checkpoint"]

    def snapshot(self):
        return {**super().snapshot(), "sprinting": self.sprinting, "stamina": self.stamina.snapshot()}

    def kill(self, reason: str) -> None:
        # A closed door is a puzzle boundary, not a contact-damage enemy.
        # Its existing solid Pymunk shape still prevents walking through it.
        if reason == "Keep a weight on the plate.":
            return
        super().kill(reason)
