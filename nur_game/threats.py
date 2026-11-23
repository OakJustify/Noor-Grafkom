"""Memory-threat entities and the director that makes the world denser over time."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from . import config
from .levels import ThreatSpawn


@dataclass
class Threat:
    spawn: ThreatSpawn
    rng_key: float
    active: bool = True
    x: float = 0.0
    y: float = 0.0
    direction: int = 1
    telegraph: float = 0.0
    lunge: float = 0.0
    cooldown: float = 0.0
    phase: float = 0.0

    def __post_init__(self) -> None:
        self.x = self.spawn.x
        self.y = self.spawn.y
        self.phase = self.rng_key * math.tau

    def update(self, dt: float, player: tuple[float, float], player_alive: bool) -> bool:
        """Return True when the threat touches the player."""
        if not self.active or not player_alive:
            return False
        self.phase += dt
        px, py = player
        distance = math.hypot(px - self.x, py - self.y)
        self.cooldown = max(0.0, self.cooldown - dt)

        if self.lunge > 0:
            self.lunge -= dt
            self.x += math.copysign(155.0 * dt, px - self.x)
            self.y += math.copysign(52.0 * dt, py - self.y)
        elif self.telegraph > 0:
            self.telegraph -= dt
            if self.telegraph <= 0:
                self.lunge = 0.36
                self.cooldown = 2.2
        else:
            self.x += self.direction * 42.0 * dt
            if self.x > self.spawn.x + self.spawn.patrol:
                self.x = self.spawn.x + self.spawn.patrol
                self.direction = -1
            elif self.x < self.spawn.x - self.spawn.patrol:
                self.x = self.spawn.x - self.spawn.patrol
                self.direction = 1
            if distance < 160.0 and self.cooldown <= 0:
                self.telegraph = config.THREAT_TELEGRAPH

        return math.hypot(px - self.x, py - self.y) < 25.0 and abs(py - self.y) < 46.0

    def draw(self, screen: pygame.Surface, camera: float, illumination: float) -> None:
        x = round(self.x - camera)
        y = round(self.y)
        if not -80 < x < screen.get_width() + 80:
            return
        sway = math.sin(self.phase * 1.7) * 3
        body = (36, 34, 40) if illumination > 0.35 else (20, 20, 25)
        pygame.draw.ellipse(screen, body, (x - 15, y - 32 + sway, 30, 62))
        pygame.draw.polygon(
            screen,
            body,
            [(x - 11, y - 8), (x - 25, y + 22 + sway), (x - 7, y + 14),
             (x + 7, y + 14), (x + 25, y + 22 + sway), (x + 11, y - 8)],
        )
        if self.telegraph > 0:
            progress = 1.0 - self.telegraph / config.THREAT_TELEGRAPH
            radius = round(10 + 30 * progress)
            colour = (int(90 + 70 * progress), int(72 + 30 * progress), 64)
            pygame.draw.circle(screen, colour, (x, y - 14), radius, 2)
            pygame.draw.circle(screen, colour, (x, y - 14), 3)
        if self.lunge > 0:
            pygame.draw.line(screen, (96, 82, 72), (x, y - 18), (x + self.direction * 28, y - 12), 2)


class ThreatDirector:
    """Activates more threats as light dies and as time passes."""

    def __init__(self, spawns: tuple[ThreatSpawn, ...], seed: int) -> None:
        rng = random.Random(seed ^ 0x7EA7)
        self.threats = tuple(Threat(spawn, rng.random()) for spawn in spawns)
        self.time_accumulator = 0.0
        self.extra = 0

    def update(self, dt: float, player: tuple[float, float], stage: int, alive: bool) -> bool:
        self.time_accumulator += dt
        # One additional memory pressure per 25 seconds, capped so the screen
        # stays readable. Stage 2 activates dormant authored threats early.
        if self.time_accumulator >= 25.0:
            self.time_accumulator -= 25.0
            self.extra = min(3, self.extra + 1)
        touched = False
        for index, threat in enumerate(self.threats):
            threat.active = index == 0 or threat.spawn.minimum_stage <= stage or index <= self.extra
            touched = threat.update(dt, player, alive) or touched
        return touched

    def draw(self, screen: pygame.Surface, camera: float, illumination: float) -> None:
        for threat in self.threats:
            if threat.active:
                threat.draw(screen, camera, illumination)

    def snapshot(self) -> dict:
        return {
            "active": sum(1 for threat in self.threats if threat.active),
            "positions": [[round(t.x, 1), round(t.y, 1)] for t in self.threats if t.active],
        }
