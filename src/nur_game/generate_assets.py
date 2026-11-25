"""Generate the four static ending illustrations for NÜR (deterministic)."""

from __future__ import annotations

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from . import config
from .story import CUTSCENES

SIZE = config.SIZE


def _surface(seed: int, wash: tuple[int, int, int]) -> pygame.Surface:
    rng = random.Random(config.SEED + seed)
    surface = pygame.Surface(SIZE)
    surface.fill(wash)
    for _ in range(220):
        x, y = rng.randrange(SIZE[0]), rng.randrange(SIZE[1])
        colour = (max(0, wash[0] + rng.randrange(-5, 8)),) * 3
        pygame.draw.line(surface, colour, (x, y), (x + rng.randrange(-30, 30), y), 1)
    return surface


def frame_warmth() -> pygame.Surface:
    s = _surface(1, (16, 16, 19))
    pygame.draw.rect(s, (34, 31, 29), (260, 80, 440, 400))
    pygame.draw.rect(s, (12, 11, 13), (284, 104, 392, 376))
    pygame.draw.rect(s, (52, 43, 34), (400, 360, 160, 12))
    pygame.draw.rect(s, (40, 34, 28), (415, 372, 10, 78))
    pygame.draw.rect(s, (40, 34, 28), (535, 372, 10, 78))
    pygame.draw.ellipse(s, (196, 132, 62), (470, 315, 20, 34))
    glow = pygame.Surface((360, 360), pygame.SRCALPHA)
    for r in range(180, 0, -4):
        pygame.draw.circle(glow, (202, 146, 74, max(1, int(14 * (1 - r / 180)))), (180, 180), r)
    s.blit(glow, (310, 180))
    return s


def frame_fractured() -> pygame.Surface:
    s = _surface(2, (13, 13, 16))
    for offset in (-26, 0, 34):
        pygame.draw.rect(s, (30 - abs(offset) // 4, 28, 31), (330 + offset, 70, 300, 410), 2)
    pygame.draw.circle(s, (54, 46, 44), (690, 160), 58, 3)
    pygame.draw.line(s, (160, 145, 126), (690, 160), (690, 114), 3)
    pygame.draw.line(s, (160, 145, 126), (690, 160), (726, 160), 2)
    pygame.draw.line(s, (160, 145, 126), (690, 160), (660, 190), 2)
    for x in (170, 250, 810):
        pygame.draw.ellipse(s, (24, 23, 26), (x, 250, 60, 190))
    return s


def frame_labyrinth() -> pygame.Surface:
    s = _surface(3, (10, 11, 14))
    rng = random.Random(config.SEED + 33)
    for _ in range(9):
        x = rng.randrange(40, 860)
        pygame.draw.rect(s, (23, 23, 27), (x, 0, rng.randrange(40, 110), SIZE[1]))
    for _ in range(7):
        y = rng.randrange(40, 500)
        pygame.draw.rect(s, (19, 19, 23), (0, y, SIZE[0], rng.randrange(18, 44)))
    for x, y in ((320, 180), (610, 300), (790, 140)):
        pygame.draw.rect(s, (150, 141, 124), (x - 10, y - 14, 20, 28))
        pygame.draw.circle(s, config.EMBER, (x, y), 4)
    return s


def frame_end() -> pygame.Surface:
    s = _surface(4, (7, 8, 10))
    pygame.draw.rect(s, (24, 23, 26), (300, 90, 360, 380))
    pygame.draw.rect(s, (4, 5, 7), (322, 112, 316, 336))
    pygame.draw.rect(s, (198, 158, 92), (322, 452, 316, 4))
    glow = pygame.Surface((650, 180), pygame.SRCALPHA)
    for r in range(160, 0, -4):
        pygame.draw.ellipse(glow, (206, 160, 96, max(1, int(11 * (1 - r / 160)))),
                            (325 - r, 90 - r // 2, r * 2, r))
    s.blit(glow, (0, 380))
    pygame.draw.ellipse(s, (16, 15, 18), (455, 300, 50, 110))
    return s


FRAMES = (frame_warmth, frame_fractured, frame_labyrinth, frame_end)


def generate() -> list[str]:
    config.CUTSCENE_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for cutscene, maker in zip(CUTSCENES, FRAMES):
        path = config.CUTSCENE_DIR / f"{cutscene.key}.png"
        pygame.image.save(maker(), str(path))
        written.append(str(path.relative_to(config.ROOT)))
    return written


if __name__ == "__main__":
    from .audio import ensure_generated

    ensure_generated()
    for item in generate():
        print(item)
