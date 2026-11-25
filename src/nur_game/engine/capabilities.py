"""Jump-reach analysis used to validate authored jumps."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..geometry import Rect
from .constants import GRAVITY, JUMP_SPEED, MOVE_SPEED, PLAYER_SIZE

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
    def from_controller(cls) -> PlayerCapabilities:
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
            if (passed_apex and player_right >= platform_left and player_left <= platform_right
                    and player_bottom >= platform_top):
                landed = True
                break

            # Early exit: if we're past the platform horizontally and descending
            if passed_apex and player_left > platform_right:
                break

        return landed


