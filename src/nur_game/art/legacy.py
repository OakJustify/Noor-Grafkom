"""Rich vector-style rendering for NÜR: layered parallax, candle light and atmosphere."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame
import numpy as np

from .. import config
from ..story import CUTSCENES
from ..illustration import enrich_room, prop_sprite
from ..wisp import ANIMATIONS, PIVOT, facing_sprite, jump_frame, movement_pose
from ..levels import NUR_LEVELS
from ..environments import environment_layers
from ..materials import MATERIALS, material_tile, platform_sprite, room_material, saw_sprite


class LegacyArtMixin:
    def legacy_background(self, room):
        """Retain the prior house artwork for comparison; not the active scenery."""
        rng = random.Random(config.SEED + room * 977)
        width, height = self.size
        far = self._new(False)
        self._vertical_gradient(far, (240, 232, 218), (215, 205, 190))
        # Distant moon / window glow.
        glow_x = width * rng.uniform(0.55, 0.82)
        glow_y = height * rng.uniform(0.12, 0.26)
        glow = pygame.Surface((260, 260), pygame.SRCALPHA)
        for ring in range(130, 0, -6):
            alpha = int(18 * (1.0 - ring / 130))
            pygame.draw.circle(glow, (180, 170, 150, alpha), (130, 130), ring)
        far.blit(glow, (glow_x - 130, glow_y - 130))
        # Distant rooftops / trees as silhouettes.
        silhouette = pygame.Surface((width, height), pygame.SRCALPHA)
        for _ in range(14):
            x = rng.uniform(-40, width + 40)
            peak = rng.uniform(0.42, 0.74) * height
            base = height * 0.78
            points = [
                (x - rng.uniform(20, 70), base),
                (x - rng.uniform(5, 35), peak),
                (x + rng.uniform(5, 35), peak - rng.uniform(0, 40)),
                (x + rng.uniform(20, 70), base),
            ]
            pygame.draw.polygon(silhouette, (12, 13, 16), points)
        far.blit(silhouette, (0, 0))

        mid = self._new()
        near = self._new()
        decorators = (
            self._draw_room_interior,
            self._draw_corridor,
            self._draw_kitchen,
            self._draw_attic,
            self._draw_ward,
        )
        art_room = 4 if room == config.BOSS_ARENA_ROOM else min(room, 4)
        decorators[art_room](mid, near, rng, width, height)
        enrich_room(mid, near, art_room, config.SEED + room * 977)
        # Subtle dust motes baked into the mid layer for depth.
        dust = pygame.Surface((width, height), pygame.SRCALPHA)
        dust_rng = random.Random(config.SEED + room * 131)
        for _ in range(40):
            x = dust_rng.randrange(width)
            y = dust_rng.randrange(height)
            radius = dust_rng.choice((1, 1, 2))
            alpha = dust_rng.randint(6, 22)
            pygame.draw.circle(dust, (190, 182, 168, alpha), (x, y), radius)
        mid.blit(dust, (0, 0))
        layers = (far, mid, near)
        self._backgrounds[room] = layers
        return layers

    def _draw_room_interior(self, mid, near, rng, w, h) -> None:
        # Bright warm living room at the start.
        pygame.draw.rect(mid, (245, 238, 224), (0, 0, w, h))
        for x in range(0, w, 120):
            pygame.draw.rect(mid, (220, 212, 194), (x, 0, 2, h))
            pygame.draw.rect(mid, (200, 190, 172), (x + 62, 0, 58, h))
        # Window with soft daylight.
        pygame.draw.rect(mid, (230, 224, 210), (w - 260, 70, 180, 250), border_radius=4)
        pygame.draw.rect(mid, (250, 246, 236), (w - 250, 82, 160, 226), border_radius=3)
        window_glow = pygame.Surface((200, 260), pygame.SRCALPHA)
        for ring in range(100, 0, -8):
            alpha = int(14 * (1.0 - ring / 100))
            pygame.draw.circle(window_glow, (255, 248, 230, alpha), (100, 130), ring)
        mid.blit(window_glow, (w - 270, 60))
        # Door frame.
        pygame.draw.rect(mid, (210, 200, 182), (58, 70, 150, 395), border_radius=3)
        pygame.draw.rect(mid, (190, 178, 160), (74, 88, 118, 377), border_radius=2)
        # Table and chair silhouettes.
        pygame.draw.rect(mid, (180, 166, 146), (300, 350, 250, 14))
        pygame.draw.rect(mid, (150, 138, 122), (320, 364, 12, 92))
        pygame.draw.rect(mid, (150, 138, 122), (518, 364, 12, 92))
        pygame.draw.rect(mid, (200, 186, 166), (760, 290, 120, 170), border_radius=4)
        # Floor.
        pygame.draw.rect(near, (220, 210, 192), (0, 402, w, 138))
        for x in range(0, w, 46):
            pygame.draw.line(near, (190, 178, 160), (x, 402), (x, 540), 1)
        pygame.draw.rect(near, (160, 148, 132), (380, 398, 200, 8))
        for x in (404, 548):
            pygame.draw.rect(near, (140, 130, 116), (x, 410, 12, 60))

    def _draw_corridor(self, mid, near, rng, w, h) -> None:
        pygame.draw.rect(mid, (235, 228, 214), (0, 0, w, h))
        for x in range(-60, w + 120, 230):
            pygame.draw.rect(mid, (210, 202, 186), (x, 50, 170, 410), border_radius=3)
            pygame.draw.rect(mid, (190, 180, 164), (x + 18, 72, 134, 388), border_radius=2)
            pygame.draw.line(mid, (170, 160, 144), (x + 85, 72), (x + 85, 460), 2)
            pygame.draw.rect(mid, (175, 164, 148), (x + 12, 40, 146, 16), border_radius=2)
        # Hanging lamps.
        for x in range(110, w, 230):
            pygame.draw.line(mid, (160, 148, 132), (x, 40), (x, 86), 1)
            pygame.draw.ellipse(mid, (180, 164, 144), (x - 10, 86, 20, 14))
            lamp = pygame.Surface((80, 80), pygame.SRCALPHA)
            for ring in range(40, 0, -4):
                alpha = int(20 * (1.0 - ring / 40))
                pygame.draw.circle(lamp, (255, 220, 180, alpha), (40, 40), ring)
            mid.blit(lamp, (x - 40, 46))
        pygame.draw.rect(near, (210, 200, 184), (0, 404, w, 136))
        for _ in range(12):
            x = rng.uniform(0, w)
            pygame.draw.line(near, (180, 168, 152), (x, 404), (x + 28, 540), 2)
        for x in (260, 520, 780, 1040):
            pygame.draw.rect(near, (170, 158, 142), (x, 392, 150, 12))

    def _draw_kitchen(self, mid, near, rng, w, h) -> None:
        pygame.draw.rect(mid, (240, 232, 218), (0, 0, w, h))
        for x in (70, 360, 650, 940):
            pygame.draw.rect(mid, (215, 204, 188), (x, 120, 230, 280), border_radius=4)
            pygame.draw.rect(mid, (195, 182, 166), (x + 14, 138, 202, 244), border_radius=3)
            pygame.draw.line(mid, (170, 158, 142), (x + 115, 138), (x + 115, 382), 2)
            # Shelves.
            for y in (180, 250, 320):
                pygame.draw.rect(mid, (175, 162, 146), (x + 22, y, 186, 6))
            # Jars.
            for j in range(3):
                pygame.draw.ellipse(mid, (160, 148, 132), (x + 34 + j * 58, 164, 24, 18))
        # Counter.
        pygame.draw.rect(mid, (190, 176, 160), (0, 372, w, 38))
        pygame.draw.rect(mid, (170, 156, 140), (0, 410, w, 130))
        # Sink.
        pygame.draw.rect(mid, (180, 168, 152), (470, 360, 150, 22), border_radius=3)
        pygame.draw.rect(mid, (150, 140, 126), (485, 364, 120, 14), border_radius=2)
        pygame.draw.rect(near, (200, 188, 172), (0, 404, w, 136))
        pygame.draw.rect(near, (160, 148, 132), (230, 368, 340, 14))

    def _draw_attic(self, mid, near, rng, w, h) -> None:
        pygame.draw.rect(mid, (230, 222, 208), (0, 0, w, h))
        for x in range(30, w + 80, 140):
            pygame.draw.polygon(mid, (200, 190, 174), [(x, 20), (x + 22, 20), (x + 92, 460), (x + 70, 460)])
            pygame.draw.line(mid, (170, 158, 142), (x + 11, 20), (x + 81, 460), 1)
        for x in range(50, w, 170):
            pygame.draw.rect(mid, (190, 178, 162), (x, 240, 140, 16))
            pygame.draw.rect(mid, (170, 158, 142), (x, 240, 140, 2))
            # Boxes.
            pygame.draw.rect(mid, (170, 156, 140), (x + 10, 256, 42, 30), border_radius=2)
            pygame.draw.rect(mid, (170, 156, 140), (x + 62, 256, 54, 30), border_radius=2)
        # Dust motes / cobwebs.
        for _ in range(16):
            x = rng.uniform(0, w)
            y = rng.uniform(260, 420)
            pygame.draw.rect(near, (160, 148, 134), (x, y, rng.uniform(18, 40), 2))
        pygame.draw.rect(near, (200, 188, 172), (0, 404, w, 136))
        for _ in range(14):
            x, y = rng.uniform(0, w), rng.uniform(270, 420)
            pygame.draw.rect(near, (170, 158, 144), (x, y, 24, 16), border_radius=2)

    def _draw_ward(self, mid, near, rng, w, h) -> None:
        pygame.draw.rect(mid, (235, 227, 213), (0, 0, w, h))
        # Large shadowed form behind the boss arena.
        pygame.draw.ellipse(mid, (205, 192, 176), (250, 40, 560, 420))
        for i in range(14):
            x = 120 + i * 58
            pygame.draw.line(mid, (175, 162, 146), (x, 0), (x + rng.uniform(-30, 30), 460), 3)
        # Curtains / partitions.
        for x in (90, 760):
            pygame.draw.rect(mid, (200, 184, 168), (x, 60, 110, 400), border_radius=4)
            pygame.draw.rect(mid, (180, 166, 150), (x + 12, 76, 86, 368), border_radius=3)
        # Floor.
        pygame.draw.rect(near, (210, 198, 182), (0, 404, w, 136))
        for x in range(0, w, 34):
            pygame.draw.line(near, (180, 168, 152), (x, 404), (x, 540), 1)
        for x in (120, 780):
            pygame.draw.rect(near, (170, 156, 142), (x, 292, 96, 168), border_radius=3)

