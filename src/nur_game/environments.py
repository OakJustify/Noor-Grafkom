"""Original layered scenery for the longer journey; existing house art is untouched."""

import math
import random

import pygame

from .illustration import Ink

PALETTES = {
    "garden": ((60, 91, 98), (144, 171, 143)),
    "forest": ((28, 52, 69), (91, 125, 114)),
    "canal": ((62, 95, 117), (151, 172, 171)),
    "station": ((69, 88, 108), (147, 152, 141)),
    "library": ((93, 86, 83), (169, 155, 126)),
    "workshop": ((62, 79, 90), (143, 157, 142)),
    "observatory": ((23, 39, 65), (80, 106, 127)),
    "chapel": ((81, 95, 119), (170, 166, 140)),
    "hospital": ((87, 118, 119), (194, 204, 183)),
    "home": ((95, 110, 111), (210, 197, 166)),
}


def environment_layers(style, size, seed):
    from .procedural import scene_layers

    return scene_layers(style, size, seed)


def legacy_environment_layers(style, size, seed):
    width, height = size
    rng = random.Random(seed)
    far = pygame.Surface(size)
    top, bottom = PALETTES[style]
    for y in range(height):
        t = y / height
        colour = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        pygame.draw.line(far, colour, (0, y), (width, y))
    sky = Ink(size)
    for _ in range(90):
        x, y = rng.randrange(width), rng.randrange(220)
        sky.ellipse((232, 226, 185, rng.randint(70, 160)), (x, y, 1, 1))
    sky.ellipse((212, 225, 204, 90), (width - 250, 66, 90, 90))
    sky.ellipse((*top, 210), (width - 224, 50, 90, 90))
    for i in range(12):
        x = i * 100 + rng.randrange(-20, 20)
        y = rng.randrange(210, 320)
        sky.poly((35, 62, 72, 125), [(x - 80, 400), (x, y), (x + 95, 400)])
    far.blit(sky.finish(), (0, 0))
    mid, near = Ink(size), Ink(size)
    if style in ("garden", "forest"):
        for i in range(9):
            x = i * 125 + rng.randrange(-30, 30)
            mid.poly((39, 72, 73, 205), [(x - 9, 460), (x - 3, 200), (x + 8, 80),
                                       (x + 22, 82), (x + 11, 245), (x + 16, 460)])
            mid.line((115, 150, 135, 130), (x + 8, 430), (x + 9, 190), 2)
            for side in (-1, 1):
                mid.line((36, 72, 71, 210), (x + 8, 170), (x + side * 58, 123), 5)
                mid.ellipse((57, 101, 86, 170), (x - 62 + side * 15, 45, 136, 110))
        if style == "garden":
            for x in range(10, width, 180):
                mid.rect((105, 130, 109), (x, 324, 130, 12))
                mid.line((65, 102, 87), (x + 7, 324), (x + 7, 447), 5)
                mid.line((65, 102, 87), (x + 122, 324), (x + 122, 447), 5)
                for n in range(6):
                    mid.ellipse((121, 158, 107), (x + 15 + n * 18, 302, 12, 21))
                    mid.ellipse((225, 174, 129), (x + 17 + n * 18, 298, 6, 7))
    elif style == "canal":
        mid.rect((90, 130, 137), (0, 265, width, 195))
        for y in range(270, 450, 16):
            for x in range(rng.randrange(50), width, 90):
                mid.line((161, 193, 183, 125), (x, y), (x + 42, y), 2)
        for x in range(-80, width, 240):
            mid.rect((97, 109, 104), (x, 204, 184, 36), radius=4)
            mid.rect((70, 93, 99), (x + 8, 237, 24, 223))
            mid.rect((70, 93, 99), (x + 152, 237, 24, 223))
            mid.ellipse((59, 79, 87), (x + 27, 214, 133, 126))
            mid.ellipse((109, 153, 151), (x + 42, 228, 104, 116))
    elif style == "observatory":
        for x in range(80, width, 260):
            mid.ellipse((79, 108, 125), (x - 60, 82, 180, 180), 3)
            for n in range(8):
                angle = n * math.tau / 8
                mid.line((145, 169, 165), (x + 30, 172),
                         (x + 30 + math.cos(angle) * 88, 172 + math.sin(angle) * 88))
            mid.rect((51, 79, 95), (x + 24, 263, 12, 183))
            mid.line((122, 161, 172), (x + 30, 290), (x - 20, 445), 4)
            mid.line((122, 161, 172), (x + 30, 290), (x + 80, 445), 4)
    else:
        mid.rect((*bottom, 235), (0, 0, width, 460))
        for x in range(0, width, 220):
            mid.rect((71, 95, 99), (x + 40, 60, 144, 229), radius=4)
            mid.rect((139, 172, 176), (x + 48, 68, 128, 212), radius=3)
            mid.line((214, 204, 165), (x + 111, 66), (x + 111, 280), 4)
            mid.line((214, 204, 165), (x + 46, 173), (x + 178, 173), 4)
        mid.rect((81, 106, 104), (0, 326, width, 134))
        for x in range(0, width, 75):
            mid.rect((145, 158, 131), (x + 5, 340, 65, 98), 1)
        if style == "library":
            for x in range(20, width, 240):
                mid.rect((69, 68, 55), (x, 100, 130, 345))
                for row in range(6):
                    y = 145 + row * 49
                    mid.line((187, 152, 95), (x, y), (x + 130, y), 4)
                    for n in range(10):
                        colour = (104 + n % 4 * 15, 100 + n % 3 * 14, 74)
                        mid.rect(colour, (x + 5 + n * 12, y - 31 - n % 3 * 4, 8, 30 + n % 3 * 4))
        elif style == "workshop":
            for x in range(70, width, 260):
                mid.ellipse((71, 94, 100), (x - 30, 120, 130, 130), 8)
                for n in range(10):
                    a = n * math.tau / 10
                    mid.line((99, 125, 124), (x + 35, 185), (x + 35 + math.cos(a) * 60, 185 + math.sin(a) * 60), 5)
                mid.rect((140, 122, 84), (x - 40, 310, 190, 14))
                mid.rect((71, 88, 86), (x - 30, 324, 12, 125))
                mid.rect((71, 88, 86), (x + 127, 324, 12, 125))
        elif style == "chapel":
            for x in range(80, width, 240):
                mid.poly((135, 158, 141), [(x, 80), (x + 70, 20), (x + 140, 80), (x + 140, 294), (x, 294)], 3)
                for n in range(5):
                    mid.rect((104 + n * 12, 149, 144 - n * 6, 150), (x + 8 + n * 25, 92, 23, 189))
        elif style == "station":
            for x in range(90, width, 240):
                mid.rect((49, 74, 85), (x, 295, 140, 76), radius=4)
                mid.line((204, 180, 119), (x + 8, 355), (x + 132, 355), 3)
                mid.ellipse((194, 196, 163), (x + 45, 36, 48, 48))
                mid.line((66, 83, 86), (x + 69, 60), (x + 69, 42), 2)
                mid.line((66, 83, 86), (x + 69, 60), (x + 80, 65), 2)
        elif style == "hospital":
            for x in range(45, width, 230):
                mid.rect((149, 174, 158), (x, 300, 160, 25), radius=4)
                mid.ellipse((228, 227, 198), (x + 8, 280, 49, 20))
                mid.line((101, 128, 126), (x + 4, 326), (x + 4, 445), 3)
                mid.line((101, 128, 126), (x + 156, 326), (x + 156, 445), 3)
        elif style == "home":
            for x in range(70, width, 230):
                mid.rect((136, 107, 68), (x, 340, 160, 12))
                mid.rect((95, 93, 73), (x + 12, 352, 10, 96))
                mid.rect((95, 93, 73), (x + 135, 352, 10, 96))
                mid.ellipse((185, 166, 119), (x + 50, 313, 26, 27))
    # Near layer adds silhouettes at a different parallax rate without hiding
    # traversable floor. Depth is scenery, never a fake collision platform.
    for x in range(-20, width, 340):
        near.poly((25, 51, 59, 70), [(x, 0), (x + 14, 0), (x + 19, 340), (x + 6, 365)])
    # Chapter-specific wear, picture arrangements and hanging brass lights.
    # Identical architectural styles still feel like separate rooms.
    for _ in range(60):
        x, y = rng.randrange(width), rng.randrange(350)
        mid.line((221, 215, 185, 22), (x, y), (x + rng.randrange(4, 28), y + rng.randrange(-3, 4)))
    for x in rng.sample(range(60, width - 80, 30), 4):
        y = rng.randrange(75, 155)
        mid.line((57, 84, 89), (x, 0), (x, y), 2)
        mid.rect((195, 165, 98), (x - 8, y, 16, 26), radius=3)
        mid.rect((248, 222, 149), (x - 4, y + 4, 8, 17), radius=2)
    mid.rect((19, 39, 49), (0, 460, width, height - 460))
    return far, mid.finish(), near.finish()
