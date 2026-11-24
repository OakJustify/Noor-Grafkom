"""Cloaked wisp artwork and time-based animation, independent of gameplay physics.

Four eight-frame sets share a fixed pivot: hovering idle, soft walking glide,
forward-leaning running glide and a non-looping, velocity-synchronised jump.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pygame

from echo_game.physics import JUMP_SPEED
from .illustration import Ink

FRAME_SIZE = (104, 104)
PIVOT = (52, 68)
FRAME_COUNT = 8
RUN_THRESHOLD = 150.0


@dataclass(frozen=True)
class AnimationSpec:
    fps: int
    loop: bool = True
    frames: int = FRAME_COUNT


ANIMATIONS = {
    "idle": AnimationSpec(7),
    "walk": AnimationSpec(10),
    "run": AnimationSpec(16),
    "jump": AnimationSpec(12, loop=False),
}


def movement_pose(velocity, grounded: bool) -> str:
    if not grounded:
        return "jump"
    speed = abs(velocity[0])
    if speed < 12:
        return "idle"
    return "run" if speed >= RUN_THRESHOLD else "walk"


def jump_frame(vertical_speed: float) -> int:
    # One progression from takeoff to landing, never an idle-like midair loop.
    progress = max(0.0, min(1.0, (vertical_speed + JUMP_SPEED) / (2 * JUMP_SPEED)))
    return min(FRAME_COUNT - 1, int(progress * FRAME_COUNT))


@dataclass
class WispAnimation:
    pose: str = "idle"
    frame: int = 0
    elapsed: float = 0.0

    def update(self, dt: float, velocity, grounded: bool) -> None:
        pose = movement_pose(velocity, grounded)
        if pose != self.pose:
            self.pose, self.elapsed = pose, 0.0
        else:
            self.elapsed += max(0.0, dt)
        if pose == "jump":
            self.frame = jump_frame(velocity[1])
        else:
            spec = ANIMATIONS[pose]
            self.frame = int(self.elapsed * spec.fps + 1e-9) % spec.frames

    def snapshot(self) -> dict:
        return {"pose": self.pose, "frame": self.frame}


@lru_cache(maxsize=FRAME_COUNT * len(ANIMATIONS))
def wisp_sprite(pose: str, frame: int) -> pygame.Surface:
    """An original RGBA sprite facing right; returned cached surfaces are read-only."""
    if pose not in ANIMATIONS or not 0 <= frame < FRAME_COUNT:
        raise ValueError(f"Unknown wisp frame: {pose}/{frame}")
    art = Ink(FRAME_SIZE)
    x, y = PIVOT
    phase = frame * math.tau / FRAME_COUNT
    wave, curl = math.sin(phase), math.cos(phase)
    if pose == "idle":
        bob, lean, trail = wave * 2.2, curl * 0.7, 5 + wave * 2
        spread, lift, swing = 16 + curl * 2, 0, wave * 2
    elif pose == "walk":
        bob, lean, trail = math.sin(phase * 2) * 1.5, 2 + wave, 12 + curl * 3
        spread, lift, swing = 16 + wave * 3, wave * 2, math.sin(phase + 0.7) * 4
    elif pose == "run":
        bob, lean, trail = math.sin(phase * 2) * 2, 7 + wave * 1.7, 25 + curl * 5
        spread, lift, swing = 19 + wave * 3, -6 + wave * 3, math.sin(phase + 1.1) * 5
    else:
        bob = (3, 1, -1, -3, -4, -2, 0, 2)[frame]
        lean = (-3, -1, 2, 4, 3, 1, -1, -2)[frame]
        trail = (5, 8, 12, 18, 20, 16, 10, 6)[frame]
        spread = (19, 14, 10, 11, 16, 22, 25, 21)[frame]
        lift = (3, -2, -9, -12, -10, -4, 2, 4)[frame]
        swing = (2, 5, 7, 3, -3, -5, -2, 0)[frame]
    y += bob
    hx, hy = x + lean, y - 26
    # A cyan spirit, not a person in costume: no skin, legs or boots.
    for radius in range(20, 2, -2):
        alpha = int((1 - radius / 22) ** 2 * (44 + 7 * wave))
        art.ellipse((137, 225, 212, alpha), (hx - radius, hy - radius + 2, radius * 2, radius * 2))
    # Floating essence spills below the cloth in animated, tapered ribbons.
    tail_y = y + 22 + wave * 2
    art.poly((105, 194, 178, 65), [(x - 10, y + 4), (x + 10, y + 5),
                                 (x + 4, y + 16), (x - 5 - wave * 3, tail_y),
                                 (x - 1, y + 13), (x - 13, y + 16)])
    art.poly((183, 246, 222, 175), [(x - 3, y + 8), (x + 4, y + 9),
                                   (x + curl * 3, y + 17), (x - 3 - wave * 2, tail_y - 1)])
    # Back cape streams farther and flutters faster in the running set.
    cape = [(x - 8 + lean, y - 18), (x - 17 - trail, y - 4 + lift),
            (x - 12 - trail, y + 11 + lift + curl * 3), (x - 18, y + 6),
            (x - 9, y + 15), (x + 4, y - 3)]
    art.poly((27, 48, 56), cape)
    art.poly((91, 124, 126), cape, 1)
    art.poly((45, 78, 84), [(x - 8 + lean, y - 15),
                          (x - 14 - trail, y - 2 + lift), (x - 15, y + 4), (x - 6, y + 7)])
    # Five separate hem points move independently instead of translating a pose.
    hem_y = y + 10 + lift * 0.4
    cloak = [(x - 9 + lean, y - 20), (x + 9 + lean, y - 20),
             (x + 13, y - 1), (x + spread, hem_y + curl * 2),
             (x + 7, hem_y - 1), (x + 3, hem_y + 5 + wave),
             (x - 4, hem_y + 1), (x - 10, hem_y + 6 - curl),
             (x - spread, hem_y + wave * 3), (x - 13, y - 2)]
    art.poly((37, 67, 77), cloak)
    art.poly((137, 166, 161), cloak, 1)
    art.poly((64, 101, 106), [(x - 2 + lean, y - 18), (x + 5 + lean, y - 19),
                             (x + 5, hem_y + 3), (x - 6, hem_y)])
    for offset in (-9, -2, 7):
        art.line((25, 52, 62), (x + offset + lean, y - 12),
                 (x + offset + wave * 2, hem_y - 2))
    art.line((133, 168, 161), (x + 8 + lean, y - 15), (x + spread - 3, hem_y - 2))
    # Pointed oversized hood with a hollow face, spectral glow and bright eyes.
    hood = [(hx - 15, hy - 3), (hx - 12, hy - 13), (hx - 5 - curl * 2, hy - 23),
            (hx + 5, hy - 17), (hx + 13, hy - 7), (hx + 15, hy + 5),
            (hx + 9, hy + 13), (hx - 10, hy + 12), (hx - 16, hy + 4)]
    art.poly((42, 67, 77), hood)
    art.poly((153, 176, 162), hood, 1)
    art.poly((74, 103, 105), [(hx - 11, hy - 11), (hx - 5, hy - 20),
                             (hx + 3, hy - 15), (hx - 3, hy - 6), (hx - 13, hy + 5)])
    art.ellipse((14, 33, 42), (hx - 8, hy - 7, 21, 21))
    for radius in range(10, 1, -1):
        alpha = int((1 - radius / 11) ** 1.3 * (170 + 20 * wave))
        art.ellipse((129, 226, 205, alpha), (hx + 3 - radius, hy + 3 - radius, radius * 2, radius * 2))
    # Two lights read as a friendly wisp; a slight pulse keeps idle alive.
    eye_y = hy + 1 + wave * 0.6
    for offset in (-1, 7):
        art.ellipse((231, 255, 226), (hx + offset, eye_y, 3, 4 + curl * 0.5))
    art.line((100, 152, 147), (hx - 7, hy + 10), (hx + 10, hy + 10))
    # A warm clasp and trailing scarf tie the new hero to the existing palette.
    art.poly((153, 103, 66), [(x - 11 + lean, y - 16), (x + 10 + lean, y - 18),
                             (x + 10 + lean, y - 13), (x - 9 + lean, y - 11)])
    art.ellipse((234, 194, 111), (x + 2 + lean, y - 16, 4, 4))
    art.poly((151, 94, 62), [(x - 9 + lean, y - 14), (x - 15 - trail, y - 7 + lift),
                            (x - 18 - trail, y - 11 + lift), (x - 11 + lean, y - 18)])
    # A floating sleeve suspends the original brass lantern: protection unchanged.
    lx, ly = x + 21 + lean * 0.35 + swing, y + 2 + curl * 1.5
    art.line((63, 96, 100), (x + 9 + lean, y - 9), (lx - 2, ly - 3), 5)
    art.ellipse((161, 225, 202), (lx - 5, ly - 5, 6, 5))
    art.ellipse((189, 158, 95), (lx - 5, ly - 4, 10, 9), 1)
    art.rect((49, 45, 37), (lx - 7, ly + 2, 14, 17), radius=2)
    art.rect((186, 137, 65), (lx - 5, ly + 5, 10, 11), radius=1)
    art.rect((244, 211, 132), (lx - 3, ly + 6, 6, 9), radius=1)
    art.poly((255, 250, 209), [(lx + wave, ly + 5), (lx - 2, ly + 12), (lx + 2, ly + 13)])
    for offset in (-5, 5):
        art.line((104, 81, 46), (lx + offset, ly + 4), (lx + offset, ly + 17))
    art.line((223, 187, 113), (lx - 7, ly + 3), (lx + 7, ly + 3), 2)
    art.line((185, 145, 80), (lx - 7, ly + 18), (lx + 7, ly + 18), 2)
    # Orbiting motes and a longer running wake also make all eight frames unique.
    for index in range(3 if pose == "idle" else 4):
        angle = phase + index * 1.8
        mx = x - (trail * 0.8 if pose in ("run", "walk") else 0) + math.cos(angle) * (18 + index * 3)
        my = y - 4 + math.sin(angle) * 19 + index * 3
        art.ellipse((177, 241, 216, 95 + index * 25), (mx, my, 2, 2))
    return art.finish()


@lru_cache(maxsize=FRAME_COUNT * len(ANIMATIONS) * 2)
def facing_sprite(pose: str, frame: int, facing: int) -> pygame.Surface:
    image = wisp_sprite(pose, frame)
    return pygame.transform.flip(image, True, False) if facing < 0 else image
