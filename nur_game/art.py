"""Rich vector-style rendering for NÜR: layered parallax, candle light and atmosphere."""

from __future__ import annotations

import math
import random
from pathlib import Path

import pygame
import numpy as np

from . import config
from .story import CUTSCENES
from .illustration import enrich_room, prop_sprite
from .wisp import ANIMATIONS, PIVOT, facing_sprite, jump_frame, movement_pose
from .levels import NUR_LEVELS
from .environments import environment_layers


class NurArt:
    def __init__(self, size: tuple[int, int] = config.SIZE) -> None:
        self.size = size
        self._backgrounds: dict[int, tuple[pygame.Surface, ...]] = {}
        self._radials: dict[int, pygame.Surface] = {}
        self._cutscenes: dict[str, pygame.Surface] = {}
        self.vignette = self._build_vignette()
        self.grain = self._build_grain()
        self.bg_offsets = (0.0, 0.0, 0.0)
        self._dust_seed = 0x707E
        self._overlay = self._new()
        self._warmth = self._new()

    def _new(self, alpha: bool = True) -> pygame.Surface:
        return pygame.Surface(self.size, pygame.SRCALPHA if alpha else 0)

    def _build_vignette(self) -> pygame.Surface:
        surface = self._new()
        width, height = self.size
        x = np.linspace(-1, 1, width)[:, None]
        y = np.linspace(-1, 1, height)[None, :]
        alpha = np.clip((x * x + y * y) ** 1.7 * 48, 0, 115).astype(np.uint8)
        pygame.surfarray.pixels_alpha(surface)[:] = alpha
        return surface

    def _build_grain(self) -> pygame.Surface:
        rng = random.Random(0x6A1E)
        tile = pygame.Surface((96, 96), pygame.SRCALPHA)
        for y in range(96):
            for x in range(96):
                value = rng.randint(60, 170)
                tile.set_at((x, y), (value, value, value, rng.randint(2, 7)))
        return tile

    def _radial(self, radius: float) -> pygame.Surface:
        radius = max(24, min(520, round(radius / 8) * 8))
        cached = self._radials.get(radius)
        if cached is not None:
            return cached
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        axis = np.arange(radius * 2) - radius
        distance = np.hypot(axis[:, None], axis[None, :]) / radius
        # Remove alpha, not RGB. A smooth falloff avoids the old white disk.
        alpha = (140 * np.clip(1 - distance, 0, 1) ** 1.4).astype(np.uint8)
        pygame.surfarray.pixels_alpha(surface)[:] = alpha
        if len(self._radials) >= 16:
            self._radials.pop(next(iter(self._radials)))
        self._radials[radius] = surface
        return surface

    def _vertical_gradient(self, surface: pygame.Surface, top: tuple[int, int, int],
                           bottom: tuple[int, int, int]) -> None:
        width, height = surface.get_size()
        for y in range(height):
            t = y / max(1, height - 1)
            colour = (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            )
            pygame.draw.line(surface, colour, (0, y), (width, y))

    def background(self, room: int) -> tuple[pygame.Surface, ...]:
        cached = self._backgrounds.get(room)
        if cached is not None:
            return cached
        if len(self._backgrounds) >= 6:
            self._backgrounds.pop(next(iter(self._backgrounds)))
        style = NUR_LEVELS[room].environment
        if style:
            layers = environment_layers(style, self.size, config.SEED + room * 977)
            self._backgrounds[room] = layers
            return layers
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

    def draw_background(self, screen: pygame.Surface, camera: float, room: int, time: float) -> None:
        layers = self.background(room)
        for image, speed in zip(layers, (0.0, 0.12, 0.28)):
            width = image.get_width()
            offset = -round(camera * speed) % width - width
            for x in range(offset, screen.get_width() + width, width):
                screen.blit(image, (x, 0))
        # Parallax dust that moves independently.
        rng = random.Random(self._dust_seed)
        for n in range(28):
            base_x = rng.uniform(0, self.size[0] + 120)
            base_y = rng.uniform(40, self.size[1] - 80)
            speed = 0.04 + (n % 5) * 0.03
            x = (base_x - camera * speed + time * (1.2 + n % 4)) % (self.size[0] + 120) - 60
            y = base_y + math.sin(time * 0.7 + n * 1.3) * 8
            alpha = 18 + (n % 7) * 6
            pygame.draw.circle(screen, (185, 178, 164, alpha), (round(x), round(y)), 1)

    def draw_terrain(self, screen: pygame.Surface, world, camera: float, illumination: float) -> None:
        base, edge, shadow = (91, 76, 58), (186, 160, 114), (36, 39, 39)
        for rect in world.terrain_rects():
            x = round(rect.x - camera)
            if x > screen.get_width() or x + rect.w < 0:
                continue
            area = pygame.Rect(x, rect.y, rect.w, rect.h)
            pygame.draw.rect(screen, shadow, area.move(0, 5))
            pygame.draw.rect(screen, base, area)
            for row in range(int(rect.y) + 8, min(screen.get_height(), int(rect.y + rect.h)), 18):
                pygame.draw.line(screen, (65, 59, 48), (x, row), (x + rect.w, row))
                for tx in range(x + (row // 18 % 2) * 52, x + int(rect.w), 104):
                    if -104 < tx < screen.get_width() + 104:
                        pygame.draw.line(screen, (48, 49, 43), (tx, row - 16), (tx, row))
                        pygame.draw.line(screen, (132, 107, 71), (tx + 8, row - 7), (min(tx + 85, x + rect.w), row - 7))
            pygame.draw.rect(screen, (114, 93, 61), (x, rect.y, rect.w, 6))
            pygame.draw.line(screen, edge, (x, rect.y), (x + rect.w, rect.y), 2)
            if rect.h < 30:
                for bx in (x + 14, x + int(rect.w) - 24):
                    pygame.draw.polygon(screen, (51, 60, 59), [(bx, rect.y + rect.h),
                                        (bx + 18, rect.y + rect.h), (bx, rect.y + rect.h + 22)])
        if world.gate_body:
            gate = world.level.gate
            y = gate.y - world.gate_fraction * (gate.h + 20)
            gx = round(gate.x - camera)
            pygame.draw.rect(screen, (41, 51, 53), (gx - 4, 22, gate.w + 8, gate.y + gate.h - 22))
            pygame.draw.rect(screen, (91, 111, 110), (gx, y, gate.w, gate.h), border_radius=2)
            for gy in range(round(y + 8), round(y + gate.h), 21):
                pygame.draw.line(screen, (54, 72, 74), (gx + 2, gy), (gx + gate.w - 2, gy), 2)
            pygame.draw.line(screen, (194, 175, 131), (gx + 2, y), (gx + 2, y + gate.h), 2)
        if world.level.plate:
            plate = world.level.plate
            colour = config.WAX if world.gate_open else (180, 170, 155)
            px = round(plate.x - camera)
            pygame.draw.rect(screen, (180, 170, 155), (px + 2, plate.y + 3, plate.w, plate.h), border_radius=2)
            pygame.draw.rect(screen, colour, (px, plate.y, plate.w, plate.h), border_radius=2)
            pygame.draw.line(screen, (255, 230, 180), (px + 4, plate.y + 2), (px + plate.w - 4, plate.y + 2), 1)
            # Physical cable makes the weight/door relationship readable.
            if world.level.gate:
                gx = round(world.level.gate.x - camera)
                colour = config.WAX if world.gate_open else (106, 126, 122)
                pygame.draw.lines(screen, colour, False,
                                  [(px + plate.w // 2, plate.y + 12), (gx + 13, plate.y + 12),
                                   (gx + 13, world.level.gate.y - 8)], 2)
        for crate in world.crates:
            x, y = crate.body.position
            size = crate.size[0]
            cx = round(x - camera)
            cy = round(y)
            image = prop_sprite("crate", int(size))
            image = pygame.transform.rotate(image, -math.degrees(crate.body.angle))
            screen.blit(image, image.get_rect(center=(cx, cy)))
        for body in world.ropes:
            length = world.level.rope[3]
            a, b = body.local_to_world((0, -length / 2)), body.local_to_world((0, length / 2))
            start, end = (round(a.x - camera), round(a.y)), (round(b.x - camera), round(b.y))
            pygame.draw.line(screen, (38, 42, 38), start, end, 5)
            pygame.draw.line(screen, (189, 166, 118), start, end, 3)
            pygame.draw.circle(screen, (111, 94, 66), end, 3)
        for x, y, radius in world.saw_positions():
            sx, sy = round(x - camera), round(y)
            # Glow.
            glow = pygame.Surface((radius * 4 + 8, radius * 4 + 8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (220, 140, 100, 35), (radius * 2 + 4, radius * 2 + 4), radius * 2)
            screen.blit(glow, (sx - radius * 2 - 4, sy - radius * 2 - 4))
            pygame.draw.circle(screen, (83, 97, 101), (sx, sy), radius)
            pygame.draw.circle(screen, (178, 185, 172), (sx, sy), max(3, radius - 6), 2)
            # Teeth.
            for i in range(8):
                angle = i * math.tau / 8 + world.time * 3
                tx = sx + round(math.cos(angle) * (radius - 2))
                ty = sy + round(math.sin(angle) * (radius - 2))
                pygame.draw.circle(screen, (120, 105, 90), (tx, ty), 3)
            pygame.draw.circle(screen, (39, 50, 55), (sx, sy), 7)
            pygame.draw.circle(screen, config.EMBER, (sx, sy), 3)

    def draw_exit(self, screen, position, camera, time, boss_arena=False, ready=True) -> None:
        if boss_arena:
            return
        x, y = round(position[0] - camera), round(position[1] + 30)
        if not -80 < x < screen.get_width() + 80:
            return
        pygame.draw.rect(screen, (51, 65, 66), (x - 40, y - 154, 80, 154), border_radius=3)
        pygame.draw.rect(screen, (163, 152, 116), (x - 36, y - 150, 72, 150), 2, border_radius=2)
        pygame.draw.rect(screen, (38, 50, 54), (x - 30, y - 144, 60, 144))
        pygame.draw.polygon(screen, (131, 121, 89), [(x + 25, y - 142), (x + 33, y - 147),
                            (x + 33, y - 1), (x + 25, y - 5)])
        pygame.draw.line(screen, config.WAX if ready else (83, 116, 121), (x + 30, y - 146), (x + 30, y - 2), 2)
        if not ready:
            pygame.draw.rect(screen, (94, 117, 120), (x - 29, y - 83, 59, 10), border_radius=2)
        for i in range(5 if ready else 0):
            sy = y - 20 - (time * 18 + i * 24) % 120
            sx = x + math.sin(time + i) * 15
            pygame.draw.circle(screen, (179, 175, 137), (round(sx), round(sy)), 1)

    def draw_fragment(self, screen, fragment, camera, time, collected) -> None:
        if collected:
            return
        x = round(fragment.x - camera)
        y = round(fragment.y + math.sin(time * 1.7 + fragment.x) * 4)
        glow = pygame.Surface((52, 52), pygame.SRCALPHA)
        pygame.draw.circle(glow, (214, 118, 58, 28), (26, 26), 24)
        screen.blit(glow, (x - 26, y - 26))
        image = prop_sprite(fragment.key)
        screen.blit(image, image.get_rect(center=(x, y)))

    def draw_memory_candle(self, screen, position, camera, time, available) -> None:
        if not available:
            return
        x = round(position[0] - camera)
        y = round(position[1] + math.sin(time * 2.3) * 3)
        flicker = 0.75 + 0.25 * math.sin(time * 9.3)
        glow = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(glow, (214, 118, 58, int(45 * flicker)), (35, 35), 32)
        screen.blit(glow, (x - 35, y - 42))
        image = prop_sprite("candle")
        screen.blit(image, image.get_rect(center=(x, y)))

    def draw_player(self, screen, player, camera, illumination, facing, time,
                    velocity=(0, 0), grounded=True, animation=None) -> None:
        x = round(player[0] - camera)
        y = round(player[1])
        # Shadow.
        shadow = pygame.Surface((44, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), (0, 0, 44, 16))
        screen.blit(shadow, (x - 22, y + 18))
        if animation is not None:
            pose, frame = animation.pose, animation.frame
        else:
            pose = movement_pose(velocity, grounded)
            spec = ANIMATIONS[pose]
            frame = jump_frame(velocity[1]) if pose == "jump" else int(time * spec.fps) % spec.frames
        image = facing_sprite(pose, frame, -1 if facing < 0 else 1)
        # Mirror around the same world-space pivot: changing direction never hops.
        pivot_x = PIVOT[0] if facing >= 0 else image.get_width() - 1 - PIVOT[0]
        screen.blit(image, (x - pivot_x, y - PIVOT[1]))

    def draw_lighting(self, screen: pygame.Surface, player_screen, illumination: float, stage: int, time: float) -> None:
        cx, cy = (round(player_screen[0]), round(player_screen[1]))
        darkness = self._overlay
        alpha = int(75 + 65 * (1.0 - illumination))
        darkness.fill((5, 12, 18, alpha))
        mask = self._radial(58 + 285 * illumination)
        darkness.blit(mask, (cx - mask.get_width() // 2, cy - mask.get_height() // 2),
                      special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(darkness, (0, 0))

        screen.blit(self.vignette, (0, 0))
        # Alpha compositing, not additive RGB (which ignored alpha and bleached art).
        flicker = 0.92 + 0.08 * math.sin(time * 7.3)
        warmth = self._warmth
        warmth.fill((0, 0, 0, 0))
        for radius in range(68, 0, -4):
            amount = int((1 - radius / 68) ** 2 * (12 + 20 * illumination) * flicker)
            pygame.draw.circle(warmth, (247, 191, 98, amount), (cx, cy), radius)
        screen.blit(warmth, (0, 0))
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
        for _ in range(90):
            x, y = rng.randrange(self.size[0]), rng.randrange(self.size[1])
            colour = (18 + index * 3, 18, 21)
            pygame.draw.line(surface, colour, (x, y), (x + rng.randrange(-40, 40), y + rng.randrange(-18, 18)), 1)
        pygame.draw.rect(surface, (30, 28, 29), (300, 90, 360, 360), 2)
        pygame.draw.ellipse(surface, (44, 30, 32), (360, 140, 240, 250))
        return surface
