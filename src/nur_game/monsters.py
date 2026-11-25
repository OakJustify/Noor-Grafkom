"""Bilateral monster animation, patrol/detect/flee AI.

Python/Pygame adaptation of Task F1.  There are no Unity prefabs or Animator
Controllers here: a sprite has explicit right/left variants (left is a cached
horizontal render of the authored right sprite), and the state machine operates
on world-space x positions over the authored terrain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pygame


class MonsterState(str, Enum):
    PATROL = "patrol"
    DETECT = "detect"
    FLEE = "flee"
    RETURN = "return"


def _walkable(world, x: float, y: float, kind: int, half_width: float = 12.0) -> bool:
    """Cheap terrain guard for ground monsters.

    The authored world has no Unity layers; solid terrain rectangles are the
    equivalent of Platform|Obstacle.  Ground walkers stay on a continuous
    surface and never step into a wall or over a gap.
    """
    if world is None:
        return True
    try:
        rects = world.terrain_rects()
    except AttributeError:
        return True
    # Aerial silhouettes (LONCENG KOSONG, SAYAP RETAK) ignore floor gaps.
    if kind in (2, 4):
        return not any(rect.contains(x, y) and rect.h >= 30 for rect in rects)
    for rect in rects:
        if rect.h >= 30 and rect.x - half_width < x < rect.x + rect.w + half_width and rect.contains(x, y):
            return False
    # The walker's feet sit at y + 22 on the authored promenade (y ≈ 425).
    foot = y + 35
    return any(rect.x - half_width <= x <= rect.x + rect.w + half_width
               and rect.y - 8 <= foot <= rect.y + rect.h for rect in rects if rect.h < 30) or \
        any(rect.x - half_width <= x <= rect.x + rect.w + half_width
            and rect.y - 8 <= foot <= rect.y + 12 for rect in rects if rect.h >= 30)


def line_of_sight(world, start: tuple[float, float], end: tuple[float, float], steps: int = 18) -> bool:
    """Return False when authored terrain blocks the segment.

    Platform rails and raised floors count as occluders; the broad ground plane
    below the actors does not.
    """
    if world is None:
        return True
    try:
        rects = world.terrain_rects()
    except AttributeError:
        return True
    sx, sy = start
    ex, ey = end
    for step in range(1, steps):
        t = step / steps
        px, py = sx + (ex - sx) * t, sy + (ey - sy) * t
        for rect in rects:
            if rect.h < 8 or rect.y >= 455:
                continue
            if rect.contains(px, py):
                return False
    return True


@dataclass
class MonsterAnimator:
    """Directional animation selection without negative sprite scaling."""

    facing_right: bool = True
    speed: float = 0.0
    fleeing: bool = False
    clock: float = 0.0
    _left_cache: dict[tuple[int, int], pygame.Surface] = field(default_factory=dict, repr=False)

    def set_movement(self, horizontal_speed: float, is_fleeing: bool) -> None:
        self.speed = max(0.0, abs(float(horizontal_speed)))
        self.fleeing = bool(is_fleeing)

    def set_facing_direction(self, direction) -> None:
        if abs(float(direction[0])) > 0.01:
            self.facing_right = float(direction[0]) > 0

    def play_flee_start(self) -> None:
        self.fleeing = True

    def play_flee_end(self) -> None:
        self.fleeing = False

    def update(self, dt: float) -> None:
        self.clock += max(0.0, float(dt))

    @property
    def pose(self) -> str:
        if self.fleeing and self.speed > 1:
            return "run"
        if self.speed > 1:
            return "walk"
        return "idle"

    def frame(self) -> int:
        fps = 14 if self.pose == "run" else 10 if self.pose == "walk" else 6
        return int(self.clock * fps) % 8

    def sprite(self, kind: int, frame: int | None = None) -> pygame.Surface:
        # Imported lazily: encounters imports this module for its dataclasses.
        from .encounters import creature_sprite

        image = creature_sprite(kind, self.frame() if frame is None else frame)
        if self.facing_right:
            return image
        key = (kind, self.frame() if frame is None else frame)
        if key not in self._left_cache:
            self._left_cache[key] = pygame.transform.flip(image, True, False)
        return self._left_cache[key]


@dataclass
class MonsterFleeBehavior:
    """Turn visibly away from the threat, then run forward.

    An opposite-facing turn consumes the same half-second a 360 deg/s Unity
    turn would need for 180 degrees.  The monster never runs backwards.
    """

    flee_speed: float = 205.0
    turn_speed: float = 360.0
    turn_timer: float = 0.0
    facing_right: bool = True
    last_velocity: float = 0.0

    def _turn_duration(self) -> float:
        return 180.0 / max(1.0, self.turn_speed)

    def flee_from(self, origin, threat, dt: float, world=None, kind: int = 0) -> float:
        dx = float(origin[0]) - float(threat[0])
        desired_right = dx >= 0
        if desired_right != self.facing_right:
            self.turn_timer = max(self.turn_timer, self._turn_duration())
            self.facing_right = desired_right
        self.turn_timer = max(0.0, self.turn_timer - dt)
        if self.turn_timer > 0:
            self.last_velocity = 0.0
            return 0.0
        direction = 1.0 if self.facing_right else -1.0
        next_x = float(origin[0]) + direction * self.flee_speed * dt
        if not _walkable(world, next_x, float(origin[1]), kind):
            self.last_velocity = 0.0
            return 0.0
        self.last_velocity = direction * self.flee_speed
        return self.last_velocity


@dataclass
class MonsterAI:
    """Patrol → Detect → Flee → Return, with a world-space patrol leg."""

    detection_radius: float = 320.0
    safe_distance: float = 480.0
    patrol_range: float = 140.0
    patrol_speed: float = 25.0
    return_speed: float = 70.0
    state: MonsterState = MonsterState.PATROL
    anchor: float = 0.0
    target: float = 0.0
    direction: int = 1

    def reset(self, home: float) -> None:
        self.anchor = float(home)
        self.target = self.anchor + self.patrol_range
        self.direction = 1
        self.state = MonsterState.PATROL

    def _patrol_velocity(self, x: float, dt: float, world, kind: int) -> float:
        if abs(x - self.target) <= 12:
            if self.direction > 0:
                self.target = self.anchor - self.patrol_range
            else:
                self.target = self.anchor + self.patrol_range
            self.direction *= -1
        direction = 1.0 if self.target > x else -1.0
        next_x = x + direction * self.patrol_speed * dt
        if not _walkable(world, next_x, 425.0, kind):
            # Reverse at a ledge instead of walking off it.
            self.direction *= -1
            self.target = self.anchor + (self.patrol_range if self.direction > 0 else -self.patrol_range)
            return 0.0
        return direction * self.patrol_speed

    def update(self, dt: float, x: float, player, brightness: float, los: bool,
               world=None, kind: int = 0) -> tuple[float, bool]:
        distance = abs(float(x) - float(player[0]))
        if self.state == MonsterState.PATROL:
            if brightness > 0.3 and distance < self.detection_radius:
                self.state = MonsterState.DETECT
            else:
                return self._patrol_velocity(x, dt, world, kind), False
        if self.state == MonsterState.DETECT:
            if brightness > 0.5 and los:
                self.state = MonsterState.FLEE
                return 0.0, True
            if brightness <= 0.3 or distance > self.detection_radius * 1.25:
                self.state = MonsterState.RETURN
            return 0.0, False
        if self.state == MonsterState.FLEE:
            if distance > self.safe_distance and not los:
                self.state = MonsterState.RETURN
            # Protection can end while the lantern is still in hand; once the
            # threat is dim or occluded, resume detection instead of freezing.
            elif brightness <= 0.5 or not los:
                self.state = MonsterState.DETECT
            return 0.0, self.state == MonsterState.FLEE
        # RETURN
        if abs(x - self.anchor) <= 18:
            self.state = MonsterState.PATROL
            self.target = self.anchor + self.patrol_range
            self.direction = 1
            return 0.0, False
        direction = 1.0 if self.anchor > x else -1.0
        next_x = x + direction * self.return_speed * dt
        if not _walkable(world, next_x, 425.0, kind):
            self.state = MonsterState.PATROL
            self.anchor = float(x)
            self.target = float(x)
            return 0.0, False
        return direction * self.return_speed, False
