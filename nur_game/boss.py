"""Final confrontation: a memory that keeps calling the player by the wrong name.

No new controls are introduced. Phase one is a slow, telegraphed dodge while
three true echoes are recovered. Phase two borrows Undertale's mercy logic: the
way forward is to stop answering, not to attack.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from . import config
from .levels import Echo
from .story import BOSS_LINES
from .illustration import boss_sprite, prop_sprite


@dataclass
class Shard:
    x: float
    y: float
    vx: float
    vy: float
    telegraph: float = 1.0
    life: float = 9.0


class AlzheimerBoss:
    def __init__(self, echoes: tuple[Echo, ...], seed: int) -> None:
        self.x = 1080.0
        self.y = 322.0
        self.echoes = [{"x": e.x, "y": e.y, "label": e.label, "taken": False} for e in echoes]
        self.rng = random.Random(seed ^ 0x5151)
        self.phase = 0
        self.spawn_timer = 2.8
        self.shards: list[Shard] = []
        self.name_presses = 0
        self.press_cooldown = 0.0
        self.timer = 0.0
        self.done = False
        self.invulnerable = 0.0
        self.pulse = 0.0
        self.line_index = 0

    @property
    def line(self) -> str:
        return BOSS_LINES[self.line_index % len(BOSS_LINES)]

    def _spawn_shard(self, player: tuple[float, float]) -> None:
        if len(self.shards) >= 6:
            return
        dx, dy = player[0] - self.x, player[1] - self.y
        length = max(1.0, math.hypot(dx, dy))
        speed = 92.0 + self.rng.random() * 26.0
        jitter = self.rng.uniform(-0.16, 0.16)
        self.shards.append(
            Shard(
                self.x - 58.0,
                self.y + self.rng.uniform(-28, 34),
                (dx / length - jitter) * speed,
                (dy / length + jitter * 0.4) * speed,
            )
        )

    def update(
        self,
        dt: float,
        player: tuple[float, float],
        action_pressed: bool,
        lantern_charge: float,
        lantern_carried: bool = True,
    ) -> str | None:
        """Return one event: ``echo``, ``hit``, ``press``, ``phase`` or ``win``."""
        self.pulse += dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.press_cooldown = max(0.0, self.press_cooldown - dt)
        event: str | None = None

        if self.phase == 0:
            if lantern_carried:
                self.shards.clear()
            self.spawn_timer -= dt
            if self.spawn_timer <= 0 and not lantern_carried:
                self._spawn_shard(player)
                self.spawn_timer = max(1.3, 2.9 - (1.0 - lantern_charge) * 1.3)
            for shard in self.shards:
                if shard.telegraph > 0:
                    shard.telegraph -= dt
                    continue
                shard.x += shard.vx * dt
                shard.y += shard.vy * dt
                shard.life -= dt
                if (
                    not lantern_carried and self.invulnerable <= 0
                    and math.hypot(player[0] - shard.x, player[1] - shard.y) < 20.0
                ):
                    self.invulnerable = 1.1
                    event = "hit"
            self.shards = [shard for shard in self.shards if shard.life > 0 and -80 < shard.x < 1680]
            for echo in self.echoes:
                if not echo["taken"] and math.hypot(player[0] - echo["x"], player[1] - echo["y"]) < 36.0:
                    echo["taken"] = True
                    self.line_index += 1
                    event = "echo"
            if all(echo["taken"] for echo in self.echoes):
                self.phase = 1
                self.timer = 0.0
                self.shards.clear()
                event = "phase"

        elif self.phase == 1:
            self.timer += dt
            if self.timer > 3.2:
                self.line_index += 1
                self.timer = 0.0
            if action_pressed and self.press_cooldown <= 0 and math.hypot(player[0] - self.x, player[1] - self.y) < 155.0:
                self.name_presses += 1
                self.press_cooldown = 1.1
                self.line_index += 1
                event = "press"
                if self.name_presses >= 3:
                    self.phase = 2
                    self.timer = 0.0
                    event = "phase"

        elif self.phase == 2 and not self.done:
            self.timer += dt
            if self.timer >= 2.4:
                self.done = True
                event = "win"

        return event

    def draw(self, screen: pygame.Surface, camera: float, illumination: float) -> None:
        x = round(self.x - camera)
        y = round(self.y)
        colour = (180, 170, 160) if illumination > 0.2 else (140, 130, 120)
        # Outer aura.
        aura = pygame.Surface((300, 340), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (*colour, 120), (10, 10, 280, 320))
        screen.blit(aura, (x - 150, y - 170))
        screen.blit(boss_sprite(int(self.pulse * 3) % 8), (x - 160, y - 166))
        # Veins.
        for i in range(9):
            angle = i * 0.82 + self.pulse * 0.12
            ox = x + math.cos(angle) * 86
            oy = y + math.sin(angle) * 70
            pygame.draw.line(screen, config.BLOOD, (x, y - 12), (ox, oy), 2)
            pygame.draw.circle(screen, (96, 28, 34), (round(ox), round(oy)), 3)
        pygame.draw.arc(screen, (132, 96, 84), (x - 46, y + 24, 92, 52), 0.12, math.pi - 0.12, 3)
        # Eyes.
        eye_pulse = 0.6 + 0.4 * abs(math.sin(self.pulse * 1.3))
        pygame.draw.ellipse(screen, (150, 96, 82), (x - 24, y - 34, 16, 10))
        pygame.draw.ellipse(screen, (150, 96, 82), (x + 8, y - 34, 16, 10))
        pygame.draw.circle(screen, (22, 12, 14), (x - 16, y - 29), round(4 * eye_pulse))
        pygame.draw.circle(screen, (22, 12, 14), (x + 16, y - 29), round(4 * eye_pulse))

        for echo in self.echoes:
            if echo["taken"]:
                continue
            ex = round(echo["x"] - camera)
            ey = round(echo["y"] + math.sin(self.pulse * 2 + ex) * 3)
            image = prop_sprite(echo["label"])
            screen.blit(image, image.get_rect(center=(ex, ey)))
            pygame.draw.line(screen, config.EMBER, (ex, ey - 14), (ex, ey - 26), 2)
            pygame.draw.circle(screen, config.WAX, (ex, ey - 28), 3)

        for shard in self.shards:
            sx = round(shard.x - camera)
            sy = round(shard.y)
            if shard.telegraph > 0:
                radius = round(28 * (1 - shard.telegraph) + 8)
                pygame.draw.circle(screen, (100, 76, 68), (sx, sy), radius, 1)
                pygame.draw.circle(screen, (100, 76, 68), (sx, sy), 3)
                continue
            pygame.draw.polygon(
                screen,
                (128, 116, 108),
                [(sx - 8, sy - 12), (sx + 7, sy - 4), (sx + 3, sy + 13), (sx - 10, sy + 2)],
            )
            pygame.draw.circle(screen, config.BLOOD, (sx, sy), 3)

        if self.phase >= 1:
            alpha = 120 + int(80 * abs(math.sin(self.pulse * 2)))
            ring = pygame.Surface((280, 280), pygame.SRCALPHA)
            pygame.draw.circle(ring, (190, 150, 120, alpha), (140, 140), 128, 2)
            pygame.draw.circle(ring, (190, 150, 120, alpha // 2), (140, 140), 110, 1)
            screen.blit(ring, (x - 140, y - 140))

    def snapshot(self) -> dict:
        return {
            "phase": self.phase,
            "echoes": sum(1 for echo in self.echoes if echo["taken"]),
            "presses": self.name_presses,
            "shards": len(self.shards),
            "done": self.done,
        }
