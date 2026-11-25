"""Sanity, hallucination pressure and phantom presentation (Python F3)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..encounters import creature_sprite


@dataclass
class Phantom:
    kind: int
    x: float
    y: float
    life: float = 2.0
    age: float = 0.0

    @property
    def alpha(self) -> int:
        return max(0, round(160 * (1.0 - self.age / self.life)))


class PhantomDirector:
    """Render-only monsters: never added to Pymunk, never damage the player."""

    def __init__(self, seed: int = 0x4E00):
        self.rng = random.Random(seed)
        self.phantoms: list[Phantom] = []
        self.timer = 0.0

    def clear(self) -> None:
        self.phantoms.clear()
        self.timer = 0.0

    def update(self, dt: float, current: float, maximum: float, player) -> None:
        for phantom in self.phantoms:
            phantom.age += dt
        self.phantoms = [p for p in self.phantoms if p.age < p.life]
        self.timer = max(0.0, self.timer - dt)
        if current > maximum * 0.25 or self.timer > 0 or len(self.phantoms) >= 4:
            return
        self.timer = 1.1
        kind = self.rng.randrange(8)
        x = float(player[0]) + self.rng.uniform(-220, 220)
        y = 330.0 if kind in (2, 4) else 425.0
        self.phantoms.append(Phantom(kind, x, y))

    def draw(self, screen: pygame.Surface, camera: float) -> None:
        for phantom in self.phantoms:
            x = phantom.x - camera
            if not -160 < x < screen.get_width() + 160:
                continue
            image = creature_sprite(phantom.kind, int(phantom.age * 7) % 8).copy()
            scale = (0.7, 0.95, 1.05, 0.76, 0.78, 0.9, 1.1, 0.8)[phantom.kind]
            image = pygame.transform.smoothscale(
                image, (round(240 * scale), round(270 * scale)))
            image.set_alpha(phantom.alpha)
            screen.blit(image, (round(x - 120 * scale), round(phantom.y + 35 - 235 * scale)))

    def snapshot(self) -> dict:
        return {"count": len(self.phantoms),
                "kinds": [p.kind for p in self.phantoms],
                "collision": False}
