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


from .legacy import LegacyArtMixin

class NurArt(LegacyArtMixin):
    def __init__(self, size: tuple[int, int] = config.SIZE, seed: int = config.SEED) -> None:
        self.size = size
        self.seed = int(seed)
        self._backgrounds: dict[int, tuple[pygame.Surface, ...]] = {}
        self._radials: dict[int, pygame.Surface] = {}
        self._cutscenes: dict[str, pygame.Surface] = {}
        self.vignette = self._build_vignette()
        self.grain = self._build_grain()
        self.bg_offsets = (0.0, 0.0, 0.0)
        self._dust_seed = 0x707E
        self._overlay = self._new()
        self._warmth = self._new()

    def set_seed(self, seed):
        if self.seed != seed:
            self.seed = int(seed)
            self._backgrounds.clear()

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
        if not style:
            style = "ward" if room == config.BOSS_ARENA_ROOM else ("home", "corridor", "kitchen", "attic")[room]
        layers = environment_layers(style, self.size, self.seed + room * 977)
        self._backgrounds[room] = layers
        return layers


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
        material = room_material(NUR_LEVELS[world.chapter])
        base, face, edge = MATERIALS[material]
        tile = material_tile(material, self.seed + world.chapter * 31)
        for rect in world.terrain_rects():
            x = round(rect.x - camera)
            if x > screen.get_width() or x + rect.w < 0:
                continue
            if rect.h < 30:
                sprite = platform_sprite(round(rect.w), round(rect.h), material,
                                         self.seed + round(rect.x) + world.chapter * 31)
                screen.blit(sprite, (x - 6, round(rect.y) - 4))
            else:
                area = pygame.Rect(x, rect.y, rect.w, rect.h)
                previous_clip = screen.get_clip()
                screen.set_clip(previous_clip.clip(area))
                start = x + max(0, int(-x // 128)) * 128
                for tx in range(start, min(screen.get_width(), x + round(rect.w)) + 128, 128):
                    for ty in range(round(rect.y), min(screen.get_height(), round(rect.y + rect.h)), 96):
                        screen.blit(tile, (tx, ty))
                screen.set_clip(previous_clip)
                pygame.draw.rect(screen, base, (x, rect.y, rect.w, 5))
                pygame.draw.line(screen, edge, (x, rect.y), (x + rect.w - 1, rect.y), 2)
                pygame.draw.line(screen, face, (x, rect.y + 4), (x + rect.w - 1, rect.y + 4))
                # Cut ends expose the actual edge of a gap, not a painted floor.
                for end in (x, x + round(rect.w) - 1):
                    pygame.draw.line(screen, base, (end, rect.y + 3), (end, rect.y + rect.h), 3)
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
        for origin_x, origin_y, _, travel, _ in world.level.saws:
            pygame.draw.line(screen, (82, 74, 53), (round(origin_x - travel - camera), round(origin_y)),
                             (round(origin_x + travel - camera), round(origin_y)), 2)
        for x, y, radius in world.saw_positions():
            sx, sy = round(x - camera), round(y)
            # Glow.
            glow = pygame.Surface((radius * 4 + 8, radius * 4 + 8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (220, 140, 100, 35), (radius * 2 + 4, radius * 2 + 4), radius * 2)
            screen.blit(glow, (sx - radius * 2 - 4, sy - radius * 2 - 4))
            sprite = saw_sprite(radius, int(world.time * 10) % 16)
            screen.blit(sprite, sprite.get_rect(center=(sx, sy)))

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
        # An empty lantern changes mood, not whether the remaining platforms
        # can be read. Keep silhouette contrast in the darkest attic/forest.
        alpha = int(75 + 50 * (1.0 - illumination))
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
