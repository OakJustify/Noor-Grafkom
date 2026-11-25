"""Tuning constants for the deterministic Pymunk controller."""

from __future__ import annotations

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
