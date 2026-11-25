"""Cached procedural terrain skins; every bright top edge matches collision."""

import math
from functools import lru_cache

import numpy as np
import pygame

from .illustration import Ink
from .procedural import coherent_field

MATERIALS = {
    "wood": ((66, 57, 44), (108, 87, 55), (191, 167, 112)),
    "moss": ((42, 60, 51), (68, 86, 63), (160, 190, 127)),
    "stone": ((47, 61, 62), (76, 93, 89), (169, 183, 147)),
    "metal": ((37, 56, 64), (68, 93, 96), (171, 196, 174)),
    "tile": ((52, 72, 69), (89, 114, 103), (193, 201, 162)),
}


def room_material(room):
    style = room.environment
    if style in ("forest", "garden"):
        return "moss"
    if style in ("canal", "chapel"):
        return "stone"
    if style in ("observatory", "workshop", "station"):
        return "metal"
    if style == "hospital" or room.act == 6:
        return "tile"
    return "wood"


@lru_cache(maxsize=40)
def material_tile(material, seed):
    base, face, edge = MATERIALS[material]
    field = coherent_field((64, 48), seed, scales=(1, 3, 9))
    pixels = np.clip(np.array(face) + field[:, :, None] * 19, 0, 255).astype(np.uint8)
    tile = pygame.transform.smoothscale(pygame.surfarray.make_surface(pixels), (128, 96)).convert_alpha()
    art = Ink(tile.get_size())
    if material in ("wood", "moss"):
        for y in (0, 24, 48, 72):
            art.line((*base, 210), (0, y), (128, y), 2)
            for index in range(3):
                sy = y + 6 + index * 5
                art.line((*base, 110), (0, sy), (128, sy + math.sin(index + seed) * 2))
            x = 26 if y % 48 else 89
            art.line((*base, 200), (x, y), (x, y + 24))
            art.ellipse((*edge, 100), (x + 4, y + 8, 2, 2))
    else:
        for y in (0, 32, 64):
            art.line((*base, 190), (0, y), (128, y), 2)
            for x in (0, 64, 128):
                tx = x + (32 if y == 32 else 0)
                art.line((*base, 160), (tx, y), (tx, y + 32), 2)
                art.line((*edge, 65), (tx + 6, y + 4), (tx + 54, y + 4))
    tile.blit(art.finish(), (0, 0))
    return tile


@lru_cache(maxsize=160)
def platform_sprite(width, height, material, seed):
    """Pivot (6, 4) is the physical top-left; supports are purely decorative."""
    base, face, edge = MATERIALS[material]
    art = Ink((width + 12, height + 34))
    x, y = 6, 4
    art.rect((9, 21, 24, 115), (x + 2, y + 5, width, height + 3), radius=3)
    art.rect(base, (x, y, width, height), radius=2)
    art.rect(face, (x + 2, y + 3, max(1, width - 4), max(1, height - 6)), radius=2)
    art.line(edge, (x, y), (x + width - 1, y), 2)
    art.line((*edge, 120), (x + 2, y + 3), (x + width - 3, y + 3))
    for dx in range(12, width - 4, 23):
        sy = y + 7 + (dx + seed) % max(1, height - 9)
        art.line((*base, 170), (x + dx, sy), (x + min(width - 5, dx + 17), sy))
    for dx in (9, max(10, width - 13)):
        art.ellipse((25, 43, 43), (x + dx, y + 7, 4, 4))
        art.line((*edge, 160), (x + dx, y + 7), (x + dx + 2, y + 7))
        art.poly((31, 49, 48, 210), [(x + dx - 1, y + height),
                                    (x + dx + 18, y + height), (x + dx + 2, y + height + 19)])
    if material == "moss":
        for dx in range(18, width - 6, 34):
            art.line((104, 147, 96, 180), (x + dx, y + 2), (x + dx - 3, y + 8), 2)
            art.line((43, 78, 66, 170), (x + dx, y + height), (x + dx - 2, y + height + 14), 2)
    return art.finish()


@lru_cache(maxsize=20)
def phantom_sprite(width, height):
    sprite = platform_sprite(width, height, "metal", 404).copy()
    sprite.fill((105, 204, 229, 210), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.line(sprite, (147, 229, 218), (6, 4), (width + 5, 4), 2)
    for x in range(15, width, 21):
        pygame.draw.circle(sprite, (156, 224, 216), (x + 6, 10), 1)
    return sprite


@lru_cache(maxsize=80)
def saw_sprite(radius, frame):
    art = Ink((radius * 2 + 8, radius * 2 + 8))
    centre = radius + 4
    points = []
    for index in range(40):
        angle = index * math.tau / 40 + frame * math.tau / 16
        r = radius if index % 2 else radius - 5
        points.append((centre + math.cos(angle) * r, centre + math.sin(angle) * r))
    art.poly((88, 104, 105), points)
    art.poly((164, 177, 161), points, 1)
    art.ellipse((37, 56, 60), (10, 10, radius * 2 - 12, radius * 2 - 12))
    art.ellipse((145, 154, 136), (12, 12, radius * 2 - 16, radius * 2 - 16), 2)
    art.ellipse((210, 153, 85), (centre - 4, centre - 4, 8, 8))
    for index in range(3):
        angle = index * math.tau / 3 + frame * math.tau / 16
        x, y = centre + math.cos(angle) * radius * 0.46, centre + math.sin(angle) * radius * 0.46
        art.ellipse((93, 116, 112), (x - 2, y - 2, 4, 4))
    return art.finish()
