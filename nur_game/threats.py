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
    repelled: float = 0.0

    def __post_init__(self) -> None:
        self.x = self.spawn.x
        self.y = self.spawn.y
        self.phase = self.rng_key * math.tau

    def update(self, dt: float, player: tuple[float, float], player_alive: bool,
              illumination: float = 1.0, lantern_carried: bool = True) -> bool:
        """Return True when the threat touches the player."""
        if not self.active or not player_alive:
            return False
        self.phase += dt
        px, py = player
        distance = math.hypot(px - self.x, py - self.y)
        self.cooldown = max(0.0, self.cooldown - dt)

        # Darkness changes atmosphere, never the lantern's protection contract.
        protected = lantern_carried
        self.repelled += ((1.0 if protected and distance < 150 else 0.0)
                          - self.repelled) * min(1.0, dt * 5)
        if protected:
            # Cancel attacks immediately, including an already committed lunge.
            self.telegraph = self.lunge = 0.0
            self.cooldown = max(self.cooldown, 0.6)
            if distance < 150 and abs(py - self.y) < 90:
                self.direction = 1 if self.x >= px else -1
                self.x += self.direction * min(100 * dt, 150 - distance)
            else:
                self.x += self.direction * 28 * dt
                if abs(self.x - self.spawn.x) > self.spawn.patrol + 150:
                    self.direction = -1 if self.x > self.spawn.x else 1
            self.y += (self.spawn.y - self.y) * min(1.0, dt * 3)
            return False

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
        from .illustration import shadow_sprite

        variant = int(self.rng_key * 3) % 3
        image = shadow_sprite(variant, int(self.phase * 5) % 8).copy()
        image.set_alpha(round(220 - self.repelled * 135))
        screen.blit(image, (x - image.get_width() // 2, y - 52))
        if self.repelled > 0.05:
            for i in range(5):
                sx = x + math.sin(self.phase * 2 + i * 1.7) * (22 + i * 4)
                sy = y - 20 - (self.phase * 24 + i * 13) % 65
                pygame.draw.circle(screen, config.WAX, (round(sx), round(sy)), 1)
        # Warning rings exist only when the lantern is absent.
        sway = math.sin(self.phase * 1.7) * 3
        if self.telegraph > 0:
            progress = 1.0 - self.telegraph / config.THREAT_TELEGRAPH
            radius = round(12 + 34 * progress)
            colour = (int(110 + 90 * progress), int(84 + 40 * progress), 70)
            pygame.draw.circle(screen, colour, (x, y - 16 + sway), radius, 2)
            pygame.draw.circle(screen, colour, (x, y - 16 + sway), 4)
            ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*colour, 35), (radius + 4, radius + 4), radius + 2, 2)
            screen.blit(ring, (x - radius - 4, y - 16 + sway - radius - 4))
        if self.lunge > 0:
            pygame.draw.line(screen, (110, 92, 78), (x, y - 20 + sway),
                             (x + self.direction * 32, y - 12 + sway), 2)


class ThreatDirector:
    """Activates more threats as light dies and as time passes."""

    def __init__(self, spawns: tuple[ThreatSpawn, ...], seed: int) -> None:
        rng = random.Random(seed ^ 0x7EA7)
        self.threats = tuple(Threat(spawn, rng.random()) for spawn in spawns)
        self.time_accumulator = 0.0
        self.extra = 0

    def update(self, dt: float, player: tuple[float, float], stage: int, alive: bool,
              illumination: float = 1.0, lantern_carried: bool = True) -> bool:
        self.time_accumulator += dt
        # One additional memory pressure per 25 seconds, capped so the screen
        # stays readable. Stage 2 activates dormant authored threats early.
        if self.time_accumulator >= 25.0:
            self.time_accumulator -= 25.0
            self.extra = min(3, self.extra + 1)
        touched = False
        for index, threat in enumerate(self.threats):
            threat.active = index == 0 or threat.spawn.minimum_stage <= stage or index <= self.extra
            touched = threat.update(dt, player, alive, illumination, lantern_carried) or touched
        return touched

    def draw(self, screen: pygame.Surface, camera: float, illumination: float) -> None:
        for threat in self.threats:
            if threat.active:
                threat.draw(screen, camera, illumination)

    def snapshot(self) -> dict:
        return {
            "active": sum(1 for threat in self.threats if threat.active),
            "positions": [[round(t.x, 1), round(t.y, 1)] for t in self.threats if t.active],
            "repelled": sum(1 for t in self.threats if t.active and t.repelled > 0.1),
        }
