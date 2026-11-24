"""Original, cached, supersampled vector assets. No network or external art required.

Warm brass and ink-blue cloth distinguish things the player can use from the
muted plaster scenery. Animation atlases are built once, not every frame.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame


class Ink:
    """Draw at double resolution then resolve the edges with a smooth downsample."""

    def __init__(self, size):
        self.size = size
        self.surface = pygame.Surface((size[0] * 2, size[1] * 2), pygame.SRCALPHA)

    def rect(self, colour, rect, width=0, radius=0):
        pygame.draw.rect(self.surface, colour, tuple(round(v * 2) for v in rect),
                         width * 2, border_radius=radius * 2)

    def ellipse(self, colour, rect, width=0):
        pygame.draw.ellipse(self.surface, colour, tuple(round(v * 2) for v in rect), width * 2)

    def poly(self, colour, points, width=0):
        pygame.draw.polygon(self.surface, colour, [(round(x * 2), round(y * 2)) for x, y in points], width * 2)

    def line(self, colour, start, end, width=1):
        pygame.draw.line(self.surface, colour, tuple(round(v * 2) for v in start),
                         tuple(round(v * 2) for v in end), width * 2)

    def finish(self):
        return pygame.transform.smoothscale(self.surface, self.size)


def player_sprite(pose: str, frame: int) -> pygame.Surface:
    # Keep the existing public helper; the player now owns a separate atlas.
    from .wisp import wisp_sprite

    return wisp_sprite("jump" if pose == "air" else pose, frame)


@lru_cache(maxsize=24)
def shadow_sprite(variant: int, frame: int) -> pygame.Surface:
    art = Ink((100, 110))
    x, y = 50, 52
    sway = math.sin(frame * math.tau / 8) * 3
    # Each memory has a distinct torn contour rather than the same oval body.
    for i in range(6):
        alpha = 8 + i * 4
        art.ellipse((53, 64, 70, alpha), (9 + i * 4, 4 + i * 3, 82 - i * 8, 94 - i * 5))
    points = [(x - 12, y - 34), (x + 7, y - 41 - variant * 3),
              (x + 18, y - 19), (x + 16, y + 1), (x + 33, y + 26 + sway),
              (x + 16, y + 16), (x + 20, y + 41), (x + 4, y + 28),
              (x - 8, y + 46), (x - 12, y + 23), (x - 30, y + 34 - sway),
              (x - 20, y + 2), (x - 19, y - 16)]
    art.poly((38, 44, 53, 225), points)
    art.poly((107, 116, 116, 150), points, 1)
    art.poly((61, 69, 74, 190), [(x - 10, y - 32), (x - 1, y - 23),
                               (x - 6, y + 22), (x - 17, y + 7)])
    for i in range(5):
        art.line((104, 111, 109, 90), (x - 12 + i * 6, y - 2),
                 (x - 20 + i * 9 + sway, y + 28 + i % 2 * 8))
    art.ellipse((15, 22, 31, 230), (x - 12, y - 27, 26, 30))
    for side in (-1, 1):
        art.ellipse((226, 190, 123, 200), (x + side * 6 - 2, y - 17, 4, 3))
    if variant == 1:
        art.line((125, 123, 109, 160), (x - 20, y - 9), (x - 31, y - 24), 2)
    elif variant == 2:
        art.poly((68, 77, 80, 180), [(x + 10, y - 32), (x + 30, y - 11), (x + 17, y - 5)])
    return art.finish()


@lru_cache(maxsize=16)
def prop_sprite(kind: str, size: int = 58) -> pygame.Surface:
    if kind == "crate":
        art = Ink((size + 8, size + 8))
        art.rect((64, 47, 36), (4, 4, size, size), radius=2)
        for row in range(4):
            top = 6 + row * (size - 4) / 4
            art.rect((129 + row * 4, 95 + row * 3, 61 + row * 2), (6, top, size - 4, (size - 4) / 4 - 1))
            for j in range(3):
                art.line((99, 70, 46), (8 + j * 2, top + 3 + j * 2), (size - 1, top + 4 + j * 2))
        art.line((193, 157, 100), (9, 9), (size - 1, size - 1), 6)
        art.line((111, 77, 46), (11, 10), (size, size - 1))
        art.rect((176, 137, 81), (4, 4, size, size), 3, radius=2)
        for x in (8, size):
            for y in (8, size):
                art.ellipse((49, 43, 38), (x - 1, y - 1, 3, 3))
                art.line((219, 190, 131), (x - 1, y - 1), (x + 1, y - 1))
        return art.finish()
    art = Ink((48, 62))
    if kind == "candle":
        art.ellipse((54, 47, 37), (5, 45, 38, 9))
        art.ellipse((171, 133, 77), (6, 43, 36, 7), 2)
        art.rect((231, 213, 163), (17, 24, 14, 24), radius=3)
        art.rect((177, 154, 111), (26, 27, 4, 21), radius=2)
        art.line((249, 228, 177), (19, 28), (19, 39), 3)
        art.line((51, 40, 29), (24, 24), (24, 19))
        art.poly((241, 161, 70), [(24, 5), (18, 17), (21, 23), (27, 23), (30, 17)])
        art.ellipse((255, 239, 166), (22, 15, 5, 8))
    else:
        # Same readable paper silhouette for true and false fragments.
        art.poly((91, 70, 48), [(9, 15), (35, 13), (38, 48), (12, 50)])
        art.poly((233, 216, 172), [(8, 12), (31, 10), (37, 16), (36, 45), (9, 47)])
        art.poly((174, 151, 112), [(31, 10), (31, 17), (37, 16)])
        if kind == "photo":
            art.rect((59, 71, 72), (12, 17, 20, 20))
            art.ellipse((145, 148, 130), (17, 20, 8, 8))
            art.poly((125, 126, 108), [(21, 26), (15, 34), (28, 34)])
        else:
            for row in range(4):
                art.line((137, 115, 84), (13, 20 + row * 5), (29 - row % 2 * 5, 19 + row * 5))
        art.ellipse((164, 83, 51), (24, 37, 7, 7))
        art.ellipse((222, 157, 81), (26, 39, 3, 3))
    return art.finish()


@lru_cache(maxsize=8)
def boss_sprite(frame: int) -> pygame.Surface:
    art = Ink((320, 370))
    x, y = 160, 166
    sway = math.sin(frame * math.tau / 8) * 5
    outline = [(x - 12, y - 139), (x + 36, y - 125), (x + 69, y - 84),
               (x + 75, y - 20), (x + 101, y + 55), (x + 138, y + 145),
               (x + 77, y + 112), (x + 73 + sway, y + 173), (x + 24, y + 137),
               (x - 14, y + 183), (x - 33, y + 129), (x - 81, y + 170),
               (x - 76, y + 105), (x - 131, y + 145), (x - 93, y + 51),
               (x - 70, y - 21), (x - 61, y - 96)]
    art.poly((141, 145, 132), outline)
    art.poly((205, 198, 165), outline, 1)
    art.poly((94, 111, 111), [(x - 53, y - 100), (x - 28, y - 72),
                            (x - 28, y + 99), (x - 82, y + 139), (x - 65, y + 28)])
    art.poly((176, 174, 150), [(x + 25, y - 120), (x + 60, y - 82),
                              (x + 52, y + 122), (x + 14, y + 147), (x + 30, y - 19)])
    for n in range(11):
        offset = -60 + n * 12
        art.line((102, 119, 116), (x + offset * 0.6, y + 14),
                 (x + offset * 1.5 + sway, y + 113 + n % 3 * 13), 2)
        art.line((196, 190, 155, 110), (x + offset * 0.6 + 3, y + 20),
                 (x + offset * 1.5 + 5 + sway, y + 104 + n % 3 * 13))
    art.ellipse((45, 60, 67), (x - 56, y - 83, 117, 145))
    art.ellipse((202, 190, 152), (x - 54, y - 80, 113, 142), 2)
    art.ellipse((15, 27, 37), (x - 42, y - 66, 88, 116))
    # Clock-like stitches around the empty face reinforce the memory motif.
    for i in range(16):
        angle = i * math.tau / 16
        start = (x + math.cos(angle) * 56, y - 10 + math.sin(angle) * 70)
        end = (x + math.cos(angle) * 63, y - 10 + math.sin(angle) * 77)
        art.line((208, 186, 132), start, end)
    return art.finish()


def enrich_room(mid: pygame.Surface, near: pygame.Surface, room: int, seed: int) -> None:
    """Baked room-specific storytelling, materials and architectural depth."""
    w, h = mid.get_size()
    art = Ink((w, h))
    rng = random.Random(seed)
    # Plaster speckle and delicate wallpaper repeat; deterministic and cached.
    for _ in range(1800):
        x, y = rng.randrange(w), rng.randrange(400)
        art.line((91, 80, 67, rng.randint(8, 24)), (x, y), (x + rng.randint(1, 3), y))
    for x in range(24, w, 42):
        for y in range(40, 330, 54):
            art.poly((124, 118, 96, 25), [(x, y - 6), (x + 4, y), (x, y + 6), (x - 4, y)], 1)
    # Panelled wainscot. Unlike terrain, this remains behind the player.
    art.rect((91, 103, 101), (0, 330, w, 130))
    for x in range(-30, w, 100):
        art.rect((113, 121, 114), (x + 8, 347, 84, 95), 2)
        art.line((65, 78, 78), (x + 11, 350), (x + 11, 439))
        art.line((158, 159, 141), (x + 12, 440), (x + 91, 440))
    art.rect((62, 76, 77), (0, 327, w, 7))
    art.line((188, 180, 153), (0, 327), (w, 327), 2)
    art.rect((48, 61, 65), (0, 450, w, 10))
    # Picture frames and clocks become less reliable from room to room.
    for n, x in enumerate((260, 550) if room == 0 else (220, 470, 720)):
        y = 130 + n % 2 * 22
        art.rect((94, 78, 57), (x - 35, y - 48, 74, 99), radius=2)
        art.rect((201, 177, 124), (x - 32, y - 45, 68, 93), 2)
        art.rect((49, 65, 69), (x - 25, y - 38, 54, 78))
        art.ellipse((124, 135, 127), (x - 9, y - 27, 22, 28))
        art.poly((84, 99, 99), [(x + 1, y - 5), (x - 17, y + 33), (x + 23, y + 33)])
        art.line((227, 204, 158), (x - 30, y + 45), (x + 34, y + 45))
    if room == 0:
        # Moonlit divided glass, curtains, bookcase, kettle and a stopped clock.
        x = w - 260
        art.rect((69, 88, 94), (x + 8, 77, 164, 230))
        for i in range(4):
            art.rect((142 + i * 6, 164 + i * 4, 166), (x + 15 + i % 2 * 77, 85 + i // 2 * 106, 70, 99))
        for i in range(9):
            art.poly((78, 107, 116, 120), [(x + 14 + i * 18, 280), (x + 23 + i * 18, 202 + i % 3 * 20),
                                       (x + 37 + i * 18, 280)])
        art.rect((202, 187, 151), (x + 7, 76, 166, 231), 4)
        art.line((209, 195, 162), (x + 90, 78), (x + 90, 307), 3)
        art.line((209, 195, 162), (x + 9, 189), (x + 172, 189), 3)
        for side in (x - 18, x + 174):
            art.poly((105, 113, 110), [(side, 67), (side + 27, 67), (side + 22, 182),
                                     (side + 35, 313), (side - 6, 313), (side + 5, 183)])
            for i in range(4):
                art.line((163, 161, 140), (side + i * 6, 72), (side + i * 6 + 2, 167))
        art.rect((69, 68, 56), (62, 236, 134, 214))
        for y in (282, 334, 391):
            art.line((155, 125, 82), (65, y), (193, y), 5)
            for n in range(9):
                art.rect((90 + n % 3 * 20, 88 + n % 4 * 9, 72), (72 + n * 13, y - 32 - n % 3 * 5, 9, 31 + n % 3 * 5))
                art.line((200, 177, 130), (74 + n * 13, y - 28), (78 + n * 13, y - 28))
        art.ellipse((86, 80, 63), (353, 307, 33, 30))
        art.ellipse((170, 156, 125), (354, 306, 31, 9), 2)
        art.ellipse((116, 111, 86), (380, 312, 15, 15), 2)
        art.ellipse((69, 72, 67), (414, 45, 55, 55))
        art.ellipse((217, 206, 172), (419, 50, 45, 45))
        art.line((80, 79, 65), (441, 73), (441, 57), 2)
        art.line((80, 79, 65), (441, 73), (453, 80), 2)
    elif room == 1:
        for x in range(35, w, 230):
            art.rect((68, 74, 71), (x, 209, 49, 73), radius=2)
            art.rect((199, 171, 112), (x + 4, 213, 41, 65), 2)
            art.ellipse((52, 57, 56), (x + 15, 222, 21, 27))
            art.line((114, 125, 115), (x + 5, 285), (x + 44, 285))
            art.ellipse((199, 160, 91), (x + 112, 285, 7, 7))
            art.line((105, 95, 74), (x + 115, 292), (x + 115, 307), 2)
    elif room == 2:
        for x in range(0, w, 36):
            for y in range(220, 327, 35):
                art.rect((191, 191, 164, 100), (x + 1, y + 1, 34, 33), 1)
        for x in (90, 375, 665):
            for n in range(4):
                art.rect((91 + n * 12, 111 + n * 8, 96), (x + n * 35, 188, 20, 30), radius=3)
                art.rect((194, 176, 134), (x + n * 35 + 3, 199, 14, 9))
                art.rect((77, 74, 59), (x + n * 35 - 1, 185, 22, 5), radius=1)
        art.line((135, 146, 134), (525, 360), (525, 322), 5)
        art.line((135, 146, 134), (525, 322), (546, 322), 5)
        for x in (670, 705, 742):
            art.line((72, 77, 66), (x, 260), (x, 280))
            art.ellipse((76, 82, 74), (x - 10, 277, 20, 29), 2)
    elif room == 3:
        for x in range(60, w, 160):
            art.poly((68, 79, 77), [(x, 0), (x + 17, 0), (x + 80, 320), (x + 63, 320)])
            art.line((140, 143, 124), (x + 3, 0), (x + 66, 320))
            for i in range(6):
                art.line((101, 110, 100), (x + 11 + i * 8, 24 + i * 40), (x + 14 + i * 8, 47 + i * 40))
        art.ellipse((172, 187, 177), (700, 95, 106, 106))
        art.ellipse((66, 86, 90), (709, 104, 88, 88))
        art.line((188, 183, 153), (753, 102), (753, 194), 4)
        art.line((188, 183, 153), (707, 148), (799, 148), 4)
        for n in range(8):
            x = 45 + n * 110
            art.rect((124, 102, 71), (x, 285, 65, 39), radius=2)
            art.rect((78, 77, 63), (x + 7, 300, 52, 7))
            art.line((196, 175, 127), (x + 32, 287), (x + 32, 322), 3)
    else:
        for x in (88, 754):
            for n in range(9):
                art.line((121, 135, 130), (x + n * 12, 65), (x + n * 12 + 5, 321), 3)
        for x in (320, 580):
            art.line((128, 139, 131), (x, 280), (x + 170, 280), 4)
            art.line((106, 121, 117), (x + 10, 280), (x + 10, 325), 3)
            art.line((106, 121, 117), (x + 158, 280), (x + 158, 325), 3)
            art.ellipse((226, 216, 190), (x + 9, 260, 44, 19))
    mid.blit(art.finish(), (0, 0))
    # Decorative floors must not conceal real holes or look like platforms.
    near.fill((0, 0, 0, 0), (0, 390, w, h - 390))
    abyss = pygame.Surface((w, h - 460))
    for y in range(h - 460):
        value = max(13, 35 - y // 3)
        pygame.draw.line(abyss, (value, value + 7, value + 12), (0, y), (w, y))
    mid.blit(abyss, (0, 460))
