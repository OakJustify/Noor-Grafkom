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
    ) -> str | None:
        """Return one event: ``echo``, ``hit``, ``press``, ``phase`` or ``win``."""
        self.pulse += dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.press_cooldown = max(0.0, self.press_cooldown - dt)
        event: str | None = None

        if self.phase == 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
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
                    self.invulnerable <= 0
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
        pulse = 1.0 + math.sin(self.pulse * 1.9) * 0.035
        colour = (30, 26, 31) if illumination > 0.2 else (18, 17, 21)
        pygame.draw.ellipse(
            screen,
            colour,
            (x - 118 * pulse, y - 122 * pulse, 236 * pulse, 276 * pulse),
        )
        pygame.draw.ellipse(screen, (12, 12, 16), (x - 58, y - 66, 116, 150))
        # Veins and a mouth are suggestive body horror, not explicit gore.
        for i in range(7):
            angle = i * 0.9 + self.pulse * 0.08
            ox = x + math.cos(angle) * 78
            oy = y + math.sin(angle) * 62
            pygame.draw.line(screen, config.BLOOD, (x, y - 10), (ox, oy), 2)
        pygame.draw.arc(screen, (120, 88, 78), (x - 40, y + 26, 80, 46), 0.15, math.pi - 0.15, 3)

        for echo in self.echoes:
            if echo["taken"]:
                continue
            ex = round(echo["x"] - camera)
            ey = round(echo["y"] + math.sin(self.pulse * 2 + ex) * 3)
            pygame.draw.rect(screen, (188, 178, 152), (ex - 9, ey - 13, 18, 26))
            pygame.draw.line(screen, config.EMBER, (ex, ey - 13), (ex, ey - 23), 2)
            pygame.draw.circle(screen, config.WAX, (ex, ey - 25), 3)

        for shard in self.shards:
            sx = round(shard.x - camera)
            sy = round(shard.y)
            if shard.telegraph > 0:
                radius = round(28 * (1 - shard.telegraph) + 8)
                pygame.draw.circle(screen, (96, 72, 66), (sx, sy), radius, 1)
                continue
            pygame.draw.polygon(
                screen,
                (124, 112, 104),
                [(sx - 8, sy - 12), (sx + 7, sy - 4), (sx + 3, sy + 13), (sx - 10, sy + 2)],
            )
            pygame.draw.circle(screen, config.BLOOD, (sx, sy), 3)

        if self.phase >= 1:
            alpha = 120 + int(80 * abs(math.sin(self.pulse * 2)))
            ring = pygame.Surface((260, 260), pygame.SRCALPHA)
            pygame.draw.circle(ring, (190, 150, 120, alpha), (130, 130), 118, 2)
            screen.blit(ring, (x - 130, y - 130))

    def snapshot(self) -> dict:
        return {
            "phase": self.phase,
            "echoes": sum(1 for echo in self.echoes if echo["taken"]),
            "presses": self.name_presses,
            "shards": len(self.shards),
            "done": self.done,
        }
