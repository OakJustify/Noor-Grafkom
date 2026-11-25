"""Seeded ink-and-fog scenery and coherent materials, generated once then cached.

SciPy supplies wrapped Gaussian fields rather than per-pixel static. Scenery is
low-contrast and never draws a bright fake landing edge in the play plane.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pygame
from scipy.ndimage import gaussian_filter

from .illustration import Ink

# Muted paper, ink, oxidised brass and moss: the wisp/lantern own the highlights.
PALETTES = {
    "garden": ((30, 48, 50), (94, 109, 86)),
    "forest": ((17, 31, 39), (61, 88, 79)),
    "canal": ((28, 43, 52), (91, 114, 113)),
    "station": ((28, 38, 47), (97, 101, 93)),
    "library": ((37, 35, 39), (117, 102, 78)),
    "workshop": ((26, 38, 42), (91, 98, 87)),
    "observatory": ((14, 24, 39), (66, 87, 103)),
    "chapel": ((29, 37, 47), (111, 110, 89)),
    "hospital": ((36, 52, 52), (118, 132, 113)),
    "home": ((58, 57, 51), (152, 139, 111)),
    "corridor": ((40, 42, 40), (120, 113, 94)),
    "kitchen": ((41, 43, 38), (133, 124, 98)),
    "attic": ((28, 34, 37), (98, 94, 76)),
    "ward": ((30, 41, 44), (99, 108, 94)),
}


def coherent_field(size, seed, scales=(2, 7, 18)):
    """Periodic x/y texture suitable for seamless material tiles and fog."""
    rng = np.random.default_rng(seed % (2 ** 64))
    field = np.zeros(size)
    for scale, weight in zip(scales, (0.55, 0.30, 0.15)):
        layer = gaussian_filter(rng.normal(size=size), scale, mode="wrap")
        field += layer / max(1e-6, layer.std()) * weight
    return np.clip(field / 2.5, -1, 1)


def atmosphere(size, seed, top, bottom):
    width, height = size
    field = coherent_field((max(16, width // 4), max(16, height // 4)), seed)
    yy = np.linspace(0, 1, field.shape[1])[None, :, None]
    a, b = np.array(top), np.array(bottom)
    rgb = a + (b - a) * yy + field[:, :, None] * 11
    pixels = np.clip(rgb, 0, 255).astype(np.uint8)
    return pygame.transform.smoothscale(pygame.surfarray.make_surface(pixels), size)


def _tree(art, x, floor, rng, colour, scale=1.0):
    height = rng.uniform(245, 430) * scale
    bend = rng.uniform(-40, 40)
    top = floor - height
    thick = rng.uniform(12, 23) * scale
    art.poly(colour, [(x - thick, floor), (x - thick * 0.5, top + height * 0.35),
                      (x + bend - 3, top), (x + bend + 6, top - 12),
                      (x + thick * 0.7, top + height * 0.5), (x + thick, floor)])
    for index in range(4):
        sy = top + 60 + index * height * 0.12
        side = -1 if index % 2 else 1
        ex, ey = x + side * rng.uniform(40, 85) * scale, sy - rng.uniform(35, 75) * scale
        art.line(colour, (x + bend * 0.4, sy + 28), (ex, ey), max(2, round(5 * scale)))
        for _ in range(3):
            radius = rng.uniform(25, 60) * scale
            art.ellipse((*colour[:3], min(210, colour[3])),
                        (ex - radius + rng.uniform(-25, 25), ey - radius / 2, radius * 2, radius))


def scene_layers(style, size, seed):
    width, height = size[0] * 2, size[1]
    size = (width, height)
    rng = random.Random(seed)
    top, bottom = PALETTES[style]
    far = atmosphere(size, seed, top, bottom)
    distant, mid, near = Ink(size), Ink(size), Ink(size)
    outside = style in ("garden", "forest", "canal", "station", "observatory")
    if outside:
        # Layered, asymmetrical silhouettes rather than triangular wallpaper.
        for layer in range(3):
            horizon = 310 + layer * 40
            points = [(0, height)]
            for x in range(0, width + 25, 24):
                y = horizon + math.sin(x * 0.006 + layer * 2) * 24 + rng.uniform(-8, 8)
                points.append((x, y))
            points.append((width, height))
            distant.poly((22 + layer * 7, 41 + layer * 8, 45 + layer * 8, 90 + layer * 20), points)
        moon_x = rng.randrange(width // 3, width - 150)
        distant.ellipse((197, 203, 169, 44), (moon_x - 60, 58, 120, 120))
        distant.ellipse((*top, 190), (moon_x - 28, 40, 116, 114))
        if style == "observatory":
            for _ in range(105):
                x, y = rng.randrange(width), rng.randrange(35, 290)
                distant.ellipse((202, 216, 196, rng.randint(40, 100)), (x, y, 1.5, 1.5))
        # Small abandoned village shapes are grounded in distant perspective.
        if style != "forest":
            for _ in range(9):
                x, y = rng.randrange(width), rng.randrange(250, 330)
                w, h = rng.randrange(60, 140), rng.randrange(60, 125)
                distant.rect((35, 55, 57, 160), (x, y, w, h))
                distant.poly((25, 43, 49, 170), [(x - 8, y), (x + w * 0.44, y - h * 0.45), (x + w + 8, y)])
                distant.rect((165, 145, 88, 95), (x + w * 0.58, y + 19, 9, 17))
    else:
        # Stains and light wells, not repeated full-width cupboards.
        for x in range(120, width, 420):
            wx, wy = x + rng.randrange(-40, 80), rng.randrange(65, 100)
            ww, wh = rng.randrange(95, 150), rng.randrange(185, 260)
            mid.poly((185, 185, 149, 13), [(wx, wy), (wx + ww, wy),
                                         (wx + ww + 95, height), (wx - 140, height)])
            mid.rect((27, 43, 47, 130), (wx - 7, wy - 8, ww + 14, wh + 16), radius=5)
            mid.rect((124, 151, 141, 60), (wx, wy, ww, wh), radius=4)
            mid.line((135, 137, 108, 95), (wx + ww / 2, wy), (wx + ww / 2, wy + wh), 3)
            mid.line((135, 137, 108, 65), (wx, wy + wh * 0.58), (wx + ww, wy + wh * 0.58), 2)
            # Curtains curve into the shadow rather than looking like platforms.
            for side in (-1, 1):
                cx = wx - 10 if side < 0 else wx + ww + 10
                mid.poly((40, 59, 58, 110), [(cx, wy - 10), (cx + side * 24, wy - 10),
                                                          (cx + side * 36, wy + wh), (cx - side * 8, wy + wh - 12)])
        for _ in range(14):
            x, y = rng.randrange(width), rng.randrange(55, 330)
            mid.rect((78, 82, 68, 65), (x, y, rng.randrange(22, 45), rng.randrange(30, 60)), 2)

    far.blit(distant.finish(), (0, 0))
    if style in ("forest", "garden"):
        for x in range(40, width, 190):
            _tree(mid, x + rng.randrange(-60, 60), 480, rng, (27, 52, 52, 170))
        if style == "garden":
            for x in range(130, width, 480):
                mid.poly((59, 84, 69, 125), [(x, 420), (x, 235), (x + 100, 160),
                                                          (x + 210, 232), (x + 210, 420)], 3)
                for dx in (50, 105, 160):
                    mid.line((73, 99, 80, 90), (x + dx, 212), (x + dx, 421), 2)
                for n in range(13):
                    px, py = x + rng.randrange(20, 190), rng.randrange(320, 420)
                    mid.line((74, 103, 76, 95), (px, 430), (px + 10, py), 2)
                    mid.ellipse((104, 127, 86, 85), (px, py, 17, 9))
    elif style == "canal":
        mid.rect((49, 81, 88, 85), (0, 318, width, 142))
        for _ in range(65):
            x, y = rng.randrange(width), rng.randrange(334, 454)
            mid.line((142, 162, 142, 40), (x, y), (x + rng.randrange(15, 60), y), 1)
        for x in range(80, width, 470):
            mid.ellipse((36, 58, 62, 140), (x, 233, 270, 220), 16)
            mid.rect((28, 52, 56, 130), (x - 4, 337, 35, 123))
            mid.rect((28, 52, 56, 130), (x + 242, 337, 35, 123))
    elif style == "library":
        for x in range(60, width, 350):
            sw = rng.randrange(150, 225)
            mid.rect((38, 43, 39, 150), (x, 135, sw, 302), radius=2)
            for y in range(183, 435, 49):
                mid.line((92, 84, 59, 150), (x + 3, y), (x + sw - 3, y), 3)
                bx = x + 9
                while bx < x + sw - 12:
                    bw, bh = rng.randrange(7, 16), rng.randrange(25, 43)
                    colour = rng.choice(((81, 95, 81, 125), (120, 94, 67, 120), (73, 92, 101, 140)))
                    mid.rect(colour, (bx, y - bh, bw, bh))
                    bx += bw + rng.randrange(2, 6)
    elif style in ("workshop", "attic"):
        for x in range(70, width, 330):
            mid.poly((41, 53, 49, 110), [(x, 0), (x + 14, 0), (x + 62, 442), (x + 40, 442)])
            for n in range(3):
                cx, cy = x + 95 + n * 47, 150 + n * 51
                mid.ellipse((102, 116, 96, 75), (cx - 25, cy - 25, 50, 50), 3)
                for bit in range(6):
                    angle = bit * math.tau / 6
                    mid.line((79, 96, 86, 95), (cx, cy), (cx + math.cos(angle) * 23, cy + math.sin(angle) * 23), 2)
    elif style == "chapel":
        for x in range(100, width, 400):
            mid.poly((117, 132, 111, 75), [(x, 325), (x, 115), (x + 80, 44),
                                         (x + 160, 115), (x + 160, 325)], 4)
            for offset in range(10, 155, 24):
                mid.line((103, 127, 114, 40), (x + offset, 130), (x + offset, 321), 7)
    elif style in ("hospital", "ward"):
        for x in range(130, width, 430):
            mid.ellipse((171, 180, 151, 70), (x + 8, 327, 49, 19))
            mid.poly((92, 117, 106, 95), [(x, 350), (x + 145, 350), (x + 132, 369), (x + 5, 365)])
            mid.line((60, 82, 79, 100), (x + 6, 365), (x + 6, 432), 3)
            mid.line((60, 82, 79, 100), (x + 131, 368), (x + 131, 432), 3)
    elif style == "station":
        for x in range(120, width, 510):
            x += rng.randrange(-35, 55)
            clock_y = rng.randrange(100, 165)
            mid.line((64, 82, 77, 130), (x, 120), (x, 427), 8)
            mid.ellipse((122, 139, 116, 125), (x - 28, clock_y - 28, 56, 56), 3)
            angle = rng.uniform(-math.pi, math.pi)
            mid.line((173, 165, 124, 95), (x, clock_y), (x + math.cos(angle) * 16, clock_y + math.sin(angle) * 16), 2)
    elif style == "observatory":
        for x in range(150, width, 540):
            x += rng.randrange(-40, 65)
            y = rng.randrange(65, 112)
            radius = rng.randrange(75, 101)
            mid.ellipse((73, 102, 115, 125), (x - radius, y, radius * 2, radius * 2), 2)
            mid.ellipse((96, 128, 137, 65), (x - radius * 0.46, y + 18, radius * 1.3, radius * 1.9), 2)
            mid.line((56, 84, 93, 120), (x + 9, y + radius * 2), (x - 49, 431), 4)
            mid.line((56, 84, 93, 120), (x + 9, y + radius * 2), (x + 71, 431), 4)
    elif style in ("home", "kitchen", "corridor"):
        for x in range(120, width, 420):
            mid.rect((48, 55, 47, 70), (x, 349, 145, 12), radius=3)
            for dx in (12, 122):
                mid.line((50, 56, 48, 95), (x + dx, 361), (x + dx, 432), 5)
            mid.ellipse((146, 129, 84, 85), (x + 50, 322, 22, 27))
    # Thin roots/curtain edges frame only the periphery. They do not hide jumps.
    for x in range(15, width, 650):
        if style in ("garden", "forest"):
            _tree(near, x, 550, rng, (14, 32, 35, 95), 1.25)
        else:
            near.poly((18, 33, 37, 55), [(x, 0), (x + 20, 0), (x + 31, 250), (x + 5, 310)])
    middle, foreground = mid.finish(), near.finish()
    # Dissolve scenery at the period boundary rather than abruptly cutting a
    # window/tree when the parallax strip wraps. The fog field itself wraps.
    for image in (middle, foreground):
        alpha = pygame.surfarray.pixels_alpha(image)
        ramp = np.minimum(1, np.minimum(np.arange(width), np.arange(width)[::-1]) / 45)
        alpha[:] = (alpha * ramp[:, None]).astype(np.uint8)
        del alpha
    return far, middle, foreground
