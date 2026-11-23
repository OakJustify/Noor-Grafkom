"""Dark vector-style rendering: parallax silhouettes, candle light, static frames."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from . import config
from .story import CUTSCENES


class NurArt:
    def __init__(self, size: tuple[int, int] = config.SIZE) -> None:
        self.size = size
        self._backgrounds: dict[int, tuple[pygame.Surface, ...]] = {}
        self._radials: dict[int, pygame.Surface] = {}
        self._cutscenes: dict[str, pygame.Surface] = {}
        self.vignette = self._build_vignette()
        self.grain = self._build_grain()
        self.bg_offsets = (0.0, 0.0, 0.0)

    def _new(self, alpha: bool = True) -> pygame.Surface:
        return pygame.Surface(self.size, pygame.SRCALPHA if alpha else 0)

    def _build_vignette(self) -> pygame.Surface:
        surface = self._new()
        cx, cy = self.size[0] // 2, self.size[1] // 2
        maximum = math.hypot(cx, cy)
        for radius in range(int(maximum), 0, -6):
            progress = radius / maximum
            alpha = int(165 * progress ** 2.4)
            pygame.draw.circle(surface, (0, 0, 0, alpha), (cx, cy), radius)
        return surface

    def _build_grain(self) -> pygame.Surface:
        rng = random.Random(0x6A1E)
        tile = pygame.Surface((96, 96), pygame.SRCALPHA)
        for y in range(96):
            for x in range(96):
                value = rng.randint(70, 150)
                tile.set_at((x, y), (value, value, value, rng.randint(4, 18)))
        return tile

    def _radial(self, radius: float) -> pygame.Surface:
        radius = max(24, min(520, round(radius / 6) * 6))
        cached = self._radials.get(radius)
        if cached is not None:
            return cached
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for ring in range(radius, 0, -3):
            alpha = int(255 * (1.0 - ring / radius) ** 1.35)
            pygame.draw.circle(surface, (0, 0, 0, alpha), (radius, radius), ring)
        self._radials[radius] = surface
        return surface

    def background(self, room: int) -> tuple[pygame.Surface, ...]:
        cached = self._backgrounds.get(room)
        if cached is not None:
            return cached
        rng = random.Random(config.SEED + room * 977)
        width, height = self.size
        far = self._new(False)
        for y in range(height):
            t = y / height
            colour = (
                int(9 + 12 * t),
                int(10 + 12 * t),
                int(13 + 14 * t),
            )
            pygame.draw.line(far, colour, (0, y), (width, y))
        pygame.draw.ellipse(far, (24, 25, 29), (width * 0.58, 40, 260, 150))

        mid = self._new()
        near = self._new()
        decorators = (
            self._draw_room_interior,  # house
            self._draw_corridor,
            self._draw_kitchen,
            self._draw_attic,
            self._draw_ward,
        )
        decorators[min(room, len(decorators) - 1)](mid, near, rng, width, height)
        layers = (far, mid, near)
        self._backgrounds[room] = layers
        return layers

    def _draw_room_interior(self, mid, near, rng, w, h) -> None:
        pygame.draw.rect(mid, (17, 18, 22), (70, 90, 230, 370))
        pygame.draw.rect(mid, (28, 28, 33), (92, 112, 186, 348))
        pygame.draw.rect(mid, (12, 12, 15), (654, 60, 210, 400))
        pygame.draw.rect(mid, (41, 39, 39), (672, 82, 174, 378))
        pygame.draw.rect(near, (11, 12, 15), (0, 392, w, 148))
        pygame.draw.rect(near, (31, 30, 32), (390, 392, 180, 12))
        for x in (404, 548):
            pygame.draw.rect(near, (25, 24, 27), (x, 404, 12, 54))

    def _draw_corridor(self, mid, near, rng, w, h) -> None:
        for x in range(-40, w + 200, 260):
            pygame.draw.rect(mid, (20, 21, 25), (x, 70, 150, 390))
            pygame.draw.rect(mid, (9, 10, 13), (x + 18, 96, 114, 364))
            pygame.draw.line(mid, (35, 34, 36), (x + 75, 96), (x + 75, 460), 2)
        pygame.draw.rect(near, (12, 13, 16), (0, 404, w, 136))
        for _ in range(9):
            x = rng.uniform(0, w)
            pygame.draw.line(near, (24, 24, 27), (x, 404), (x + 26, 540), 2)

    def _draw_kitchen(self, mid, near, rng, w, h) -> None:
        for x in (90, 380, 670, 960):
            pygame.draw.rect(mid, (22, 23, 27), (x, 140, 210, 250))
            pygame.draw.rect(mid, (10, 11, 14), (x + 12, 156, 186, 218))
            pygame.draw.line(mid, (37, 35, 34), (x + 105, 156), (x + 105, 374), 2)
        pygame.draw.rect(near, (13, 14, 17), (0, 404, w, 136))
        pygame.draw.rect(near, (29, 28, 30), (250, 370, 300, 14))

    def _draw_attic(self, mid, near, rng, w, h) -> None:
        for x in range(40, w + 100, 150):
            pygame.draw.polygon(mid, (22, 22, 26), [(x, 40), (x + 26, 40), (x + 96, 460), (x + 70, 460)])
        for x in range(60, w, 180):
            pygame.draw.rect(mid, (16, 17, 20), (x, 250, 130, 18))
            pygame.draw.line(mid, (30, 29, 31), (x, 250), (x + 130, 250), 2)
        pygame.draw.rect(near, (12, 13, 16), (0, 404, w, 136))
        for _ in range(14):
            x, y = rng.uniform(0, w), rng.uniform(270, 420)
            pygame.draw.rect(near, (34, 32, 31), (x, y, 22, 15))

    def _draw_ward(self, mid, near, rng, w, h) -> None:
        pygame.draw.ellipse(mid, (18, 17, 21), (330, 80, 420, 370))
        for i in range(12):
            x = 150 + i * 62
            pygame.draw.line(mid, (24, 23, 27), (x, 0), (x + rng.uniform(-40, 40), 460), 3)
        pygame.draw.rect(near, (11, 12, 15), (0, 404, w, 136))
        for x in (120, 780):
            pygame.draw.rect(near, (27, 25, 28), (x, 300, 90, 160))

    def draw_background(self, screen: pygame.Surface, camera: float, room: int, time: float) -> None:
        layers = self.background(room)
        for image, speed in zip(layers, (0.0, 0.10, 0.24)):
            width = image.get_width()
            offset = -round(camera * speed) % width - width
            for x in range(offset, screen.get_width(), width):
                screen.blit(image, (x, 0))
        fog = self.grain
        offset_x = int((time * 5 + camera * 0.05) % 96)
        for x in range(-96, screen.get_width() + 96, 96):
            screen.blit(fog, (x + offset_x, 0))

    def draw_terrain(self, screen: pygame.Surface, world, camera: float, illumination: float) -> None:
        base = (int(16 + 8 * illumination), int(17 + 8 * illumination), int(20 + 8 * illumination))
        edge = (int(38 + 14 * illumination), int(36 + 12 * illumination), int(34 + 10 * illumination))
        for rect in world.terrain_rects():
            x = round(rect.x - camera)
            pygame.draw.rect(screen, base, (x, rect.y, rect.w, rect.h))
            pygame.draw.line(screen, edge, (x, rect.y), (x + rect.w, rect.y), 2)
        if world.gate_body:
            gate = world.level.gate
            fraction = 1.0 - world.gate_fraction
            y = gate.y - fraction * (gate.h + 20)
            pygame.draw.rect(screen, (24, 24, 28), (round(gate.x - camera), round(y), gate.w, gate.h))
        if world.level.plate:
            plate = world.level.plate
            colour = config.WAX if world.gate_open else (45, 43, 42)
            pygame.draw.rect(screen, colour, (round(plate.x - camera), plate.y, plate.w, plate.h))
        for crate in world.crates:
            x, y = crate.body.position
            size = crate.size[0]
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (round(x - camera), round(y))
            pygame.draw.rect(screen, (34, 32, 31), rect)
            pygame.draw.rect(screen, (54, 49, 44), rect, 2)
        for x, y, radius in world.saw_positions():
            sx, sy = round(x - camera), round(y)
            pygame.draw.circle(screen, (38, 36, 38), (sx, sy), radius)
            pygame.draw.circle(screen, (88, 80, 76), (sx, sy), max(3, radius - 7), 2)

    def draw_fragment(self, screen, fragment, camera, time, collected) -> None:
        if collected:
            return
        x = round(fragment.x - camera)
        y = round(fragment.y + math.sin(time * 1.7 + fragment.x) * 4)
        pygame.draw.rect(screen, (146, 139, 124), (x - 11, y - 14, 22, 28))
        pygame.draw.rect(screen, (192, 181, 157), (x - 11, y - 14, 22, 28), 1)
        pygame.draw.circle(screen, config.EMBER, (x - 4, y - 4), 2)
        pygame.draw.circle(screen, config.WAX, (x + 4, y + 2), 2)

    def draw_memory_candle(self, screen, position, camera, time, available) -> None:
        if not available:
            return
        x = round(position[0] - camera)
        y = round(position[1] + math.sin(time * 2.3) * 3)
        pygame.draw.rect(screen, (158, 145, 116), (x - 5, y - 2, 10, 20))
        pygame.draw.ellipse(screen, config.EMBER, (x - 3, y - 12, 6, 12))
        pygame.draw.circle(screen, config.WAX, (x, y - 15), 12, 1)

    def draw_player(self, screen, player, camera, illumination, facing, time) -> None:
        x = round(player[0] - camera)
        y = round(player[1])
        pygame.draw.ellipse(screen, (18, 18, 22), (x - 11, y - 22, 22, 44))
        pygame.draw.polygon(
            screen,
            (25, 24, 27),
            [(x - 7, y + 4), (x - 13, y + 22), (x - 3, y + 18), (x + 3, y + 18), (x + 13, y + 22), (x + 7, y + 4)],
        )
        hx = x + facing * 15
        pygame.draw.rect(screen, (120, 102, 74), (hx - 3, y + 2, 6, 14))
        flame = max(2, round(10 * illumination))
        pygame.draw.ellipse(screen, config.EMBER, (hx - flame // 2, y - flame - 2, flame, flame + 3))
        if illumination > 0.18:
            pygame.draw.ellipse(screen, config.WAX, (hx - 2, y - flame + 2, 4, 5))
        glow = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(glow, (200, 132, 66, int(30 * illumination)), (35, 35), 34)
        screen.blit(glow, (hx - 35, y - 35))

    def draw_lighting(self, screen, player_screen, illumination: float, stage: int, time: float) -> None:
        cx, cy = (round(player_screen[0]), round(player_screen[1]))
        darkness = self._new()
        alpha = int(206 + 42 * (1.0 - illumination))
        darkness.fill((0, 0, 0, alpha))
        mask = self._radial(58 + 285 * illumination)
        darkness.blit(mask, (cx - mask.get_width() // 2, cy - mask.get_height() // 2),
                      special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(darkness, (0, 0))

        veil_colours = ((0, 0, 0), (28, 24, 26), (48, 18, 26), (72, 14, 24))
        veil = pygame.Surface(self.size, pygame.SRCALPHA)
        veil.fill((*veil_colours[min(stage, 3)], int(12 + stage * 11)))
        screen.blit(veil, (0, 0))
        screen.blit(self.vignette, (0, 0))
        ox = int((time * 31) % 96)
        oy = int((time * 17) % 96)
        for x in range(-96, self.size[0] + 96, 96):
            for y in range(-96, self.size[1] + 96, 96):
                screen.blit(self.grain, (x + ox, y + oy))

    def cutscene(self, key: str) -> pygame.Surface:
        cached = self._cutscenes.get(key)
        if cached is not None:
            return cached
        path: Path = config.CUTSCENE_DIR / f"{key}.png"
        if path.exists():
            image = pygame.image.load(str(path)).convert_alpha()
        else:
            image = self._fallback_cutscene(key)
        self._cutscenes[key] = image
        return image

    def _fallback_cutscene(self, key: str) -> pygame.Surface:
        surface = self._new(False)
        surface.fill(config.VOID)
        index = next((i for i, cut in enumerate(CUTSCENES) if cut.key == key), 0)
        rng = random.Random(config.SEED + index)
        for _ in range(70):
            x, y = rng.randrange(self.size[0]), rng.randrange(self.size[1])
            colour = (18 + index * 3, 18, 21)
            pygame.draw.line(surface, colour, (x, y), (x + rng.randrange(-40, 40), y + rng.randrange(-18, 18)), 1)
        pygame.draw.rect(surface, (30, 28, 29), (330, 120, 300, 300), 2)
        pygame.draw.ellipse(surface, (44, 30, 32), (390, 170, 180, 190))
        return surface
