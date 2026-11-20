"""Original, deterministic Cairo artwork for ECHO: The Hollow Signal.

The renderer never calls Cairo during a frame. PNGs are generated once, loaded
as pygame surfaces, and animation/rotation/scaling variants are bounded caches.
Positions supplied to sprite methods are screen-space physics-body centres.
"""
from __future__ import annotations

import math
import random
from collections import OrderedDict
from pathlib import Path

import cairo
import numpy as np
import pygame

from .levels import LEVELS

SEED = 0xEC4017
ART_VERSION = 2
ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "echo"
ART_ROOT = ASSET_ROOT / "art"
LANDSCAPE_SIZE = (1920, 540)
PLAYER_CELL = (96, 112)
PLAYER_FRAMES = 12
CHAPTERS = len(LEVELS)
BEACON_X = 842


def _surface(width: int, height: int):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    return surface, ctx


def _color(ctx, color, alpha=1.0):
    if isinstance(color, (float, int)):
        value = color / 255.0
        ctx.set_source_rgba(value, value, value, alpha)
    else:
        ctx.set_source_rgba(*(v / 255.0 for v in color), alpha)


def _poly(ctx, points, color, alpha=1.0):
    ctx.new_path()
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    ctx.close_path()
    _color(ctx, color, alpha)
    ctx.fill()


def _line(ctx, points, color, width=1.0, alpha=1.0):
    ctx.new_path()
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    _color(ctx, color, alpha)
    ctx.set_line_width(width)
    ctx.stroke()


def _circle(ctx, x, y, radius, color, alpha=1.0):
    ctx.new_path()
    ctx.arc(x, y, radius, 0, math.tau)
    _color(ctx, color, alpha)
    ctx.fill()


def _rect(ctx, x, y, w, h, color, alpha=1.0):
    ctx.new_path()
    ctx.rectangle(x, y, w, h)
    _color(ctx, color, alpha)
    ctx.fill()


def _branch(ctx, rng, x, y, length, angle, width, depth, color):
    """A constrained recursive skeleton: every fork is narrower and wind-bent."""
    dx, dy = math.cos(angle) * length, math.sin(angle) * length
    end_x, end_y = x + dx, y + dy
    ctx.new_path()
    ctx.move_to(x, y)
    ctx.curve_to(x + dx * .30 + width, y + dy * .36,
                 end_x - dx * .17, end_y - dy * .17, end_x, end_y)
    _color(ctx, color)
    ctx.set_line_width(max(.65, width))
    ctx.stroke()
    if depth <= 0 or length < 7:
        return
    _branch(ctx, rng, end_x, end_y, length * rng.uniform(.60, .79),
            angle + rng.uniform(-.15, .19), width * .67, depth - 1, color)
    for direction in (-1, 1):
        if rng.random() < .91:
            fork = rng.uniform(.40, .88)
            _branch(ctx, rng, x + dx * fork, y + dy * fork,
                    length * rng.uniform(.34, .61),
                    angle + direction * rng.uniform(.37, .88),
                    width * .46, depth - 1, color)


def _tree(ctx, rng, x, baseline, height, width, color, conifer=False):
    if conifer:
        _line(ctx, [(x, baseline), (x - height * .03, baseline - height)], color, width)
        for n in range(4, 26):
            t = n / 28
            yy = baseline - height + height * t
            reach = height * t * rng.uniform(.16, .27)
            _poly(ctx, [(x - height * .03, yy - 7), (x - reach, yy + height * .06),
                        (x + rng.uniform(.5, .9) * reach, yy + height * .085)], color)
    else:
        _branch(ctx, rng, x, baseline, height * .49,
                -math.pi / 2 + rng.uniform(-.13, .13), width, 5, color)
        _poly(ctx, [(x - width * .7, baseline + 3), (x - width * .28, baseline - height * .24),
                    (x + width * .28, baseline - height * .29),
                    (x + width, baseline + 3)], color)


def _sky(path: Path):
    surface, ctx = _surface(*LANDSCAPE_SIZE)
    gradient = cairo.LinearGradient(0, 0, 0, 540)
    for stop, rgb in ((0, (17, 23, 27)), (.40, (55, 65, 70)),
                      (.72, (110, 119, 121)), (1, (38, 46, 49))):
        gradient.add_color_stop_rgb(stop, *(v / 255 for v in rgb))
    ctx.set_source(gradient)
    ctx.paint()
    haze = cairo.RadialGradient(1330, 186, 0, 1330, 186, 470)
    haze.add_color_stop_rgba(0, .76, .79, .77, .14)
    haze.add_color_stop_rgba(1, .76, .79, .77, 0)
    ctx.set_source(haze)
    ctx.paint()
    # A barely visible, broken lunar halo; no stock photographs or textures.
    _circle(ctx, 1330, 174, 32, (161, 171, 173), .08)
    rng = random.Random(SEED)
    for _ in range(70):
        y = rng.uniform(38, 395)
        _line(ctx, [(rng.uniform(-400, 1920), y), (rng.uniform(900, 2350), y + 1)],
              (173, 182, 183), rng.uniform(.5, 3), .013)
    surface.write_to_png(str(path))


def _landscape(path: Path, chapter: int, layer: str):
    surface, ctx = _surface(*LANDSCAPE_SIZE)
    rng = random.Random(SEED + chapter * 701 + {"far": 11, "mid": 31, "works": 71}[layer])
    if layer == "far":
        points = [(-10, 560), (-10, 380)]
        for x in range(0, 1950, 18):
            y = 365 + 21 * math.sin(x / 273) + 12 * math.sin(x / 97) + rng.uniform(-5, 5)
            points.append((x, y))
        points.append((1940, 560))
        _poly(ctx, points, (68, 77, 80))
        for _ in range(52):
            x = rng.uniform(-50, 1970)
            baseline = 372 + 17 * math.sin(x / 273)
            _tree(ctx, rng, x, baseline, rng.uniform(55, 155),
                  rng.uniform(1.4, 3.2), (66, 75, 78), conifer=rng.random() < (.6 if chapter < 3 else .28))
        for _ in range(100):
            y = rng.uniform(409, 535)
            x = rng.uniform(0, 1920)
            _line(ctx, [(x, y), (x + rng.uniform(18, 165), y)], (130, 141, 144), .5, .07)
    elif layer == "mid":
        _poly(ctx, [(0, 506), (180, 486), (400, 492), (620, 465), (780, 478),
                    (1100, 464), (1380, 480), (1630, 494), (1920, 490),
                    (1920, 560), (0, 560)], (34, 43, 47))
        for x, height in ((96, 386), (352, 227), (688, 170), (1682, 283), (1854, 414)):
            _tree(ctx, rng, x, 492, height, height / 39, (34, 43, 47), conifer=chapter == 2)
        for _ in range(85):
            x = rng.uniform(0, 1920)
            y = rng.uniform(482, 520)
            _line(ctx, [(x, y), (x + rng.uniform(-6, 9), y - rng.uniform(8, 30))],
                  (28, 37, 41), .8)
        # Severed telegraph wire: a subtle line leading to the floodworks.
        ctx.move_to(350, 316)
        ctx.curve_to(750, 388, 1200, 386, 1705, 269)
        _color(ctx, (36, 44, 48), .50)
        ctx.set_line_width(1)
        ctx.stroke()
    else:
        # The original pump house is defined by a split chimney and water gates.
        base = 438
        main_x = 908 if chapter == 0 else 798
        width = 286 if chapter == 0 else 448
        _rect(ctx, main_x, base - 165, width, 172, (45, 54, 58))
        _poly(ctx, [(main_x - 9, base - 165), (main_x + 62, base - 195),
                    (main_x + width - 8, base - 176), (main_x + width + 12, base - 158)],
              (40, 49, 53))
        for x in range(main_x + 20, main_x + width - 18, 38):
            for y in range(base - 146, base - 58, 35):
                _rect(ctx, x, y, 19, 24, (82, 91, 94), .36)
                _rect(ctx, x + 9, y, 2, 24, (42, 51, 55))
                _rect(ctx, x, y + 10, 19, 2, (42, 51, 55))
        for xx, hh in ((main_x + 65, 284), (main_x + 89, 251)):
            _rect(ctx, xx, base - hh, 15, hh - 172, (48, 57, 61))
            _rect(ctx, xx - 3, base - hh, 21, 5, (42, 51, 55))
        # Gate arches, rivets, paired drainage pipes, rust streaks.
        for x in range(main_x + 18, main_x + width - 15, 61):
            ctx.new_path()
            ctx.arc(x + 21, base - 28, 21, math.pi, math.tau)
            ctx.line_to(x + 42, base + 12)
            ctx.line_to(x, base + 12)
            ctx.close_path()
            _color(ctx, (27, 37, 41))
            ctx.fill()
            for offset in (6, 15, 24, 33):
                _line(ctx, [(x + offset, base - 35), (x + offset, base + 12)], (49, 58, 61), 2)
        for _ in range(45):
            x = rng.uniform(main_x + 5, main_x + width - 5)
            y = rng.uniform(base - 156, base - 5)
            _line(ctx, [(x, y), (x - 1, y + rng.uniform(3, 18))], (27, 36, 40), .7, .38)
        for yy in (base - 38, base - 24):
            _line(ctx, [(main_x - 190, yy + 30), (main_x - 54, yy + 30),
                        (main_x - 54, yy), (main_x, yy)], (42, 51, 55), 8)
            _line(ctx, [(main_x - 190, yy + 28), (main_x - 56, yy + 28)], (94, 104, 107), 1, .25)
        # Hollow signal tower: a floating beacon over triangular cross-bracing.
        tx = BEACON_X
        _poly(ctx, [(tx - 5, 164), (tx + 5, 164), (tx + 35, 440),
                    (tx + 24, 440), (tx, 205), (tx - 24, 440), (tx - 35, 440)], (49, 59, 62))
        for y in range(228, 433, 37):
            span = (y - 164) * .108
            _line(ctx, [(tx - span, y), (tx + span + 4, y + 37),
                        (tx - span - 4, y + 37), (tx + span, y)], (49, 59, 62), 2)
        _rect(ctx, tx - 19, 146, 38, 21, (33, 44, 48))
        _rect(ctx, tx - 10, 149, 20, 13, (177, 206, 205), .80)
        _poly(ctx, [(tx - 25, 145), (tx, 130), (tx + 25, 145)], (36, 46, 50))
        _line(ctx, [(tx, 130), (tx + 2, 105)], (50, 60, 64), 1)
        if chapter >= 1:
            # A receding aqueduct with clipped spillway openings.
            for n in range(5):
                x = 80 + n * 123
                _rect(ctx, x, 337 - n * 4, 114, 12, (50, 59, 62))
                _rect(ctx, x + 10, 348 - n * 4, 14, 89 + n * 4, (50, 59, 62))
                _line(ctx, [(x + 10, 315 - n * 4), (x + 10, 337 - n * 4),
                            (x + 105, 337 - n * 4), (x + 105, 315 - n * 4)], (50, 59, 62), 2)
                _line(ctx, [(x + 9, 316 - n * 4), (x + 114, 316 - n * 4)], (50, 59, 62), 2)
        if chapter == 2:
            ctx.new_path()
            ctx.arc(711, 311, 61, 0, math.tau)
            _color(ctx, (44, 55, 59))
            ctx.set_line_width(7)
            ctx.stroke()
            for n in range(12):
                a = n * math.tau / 12
                _line(ctx, [(711, 311), (711 + math.cos(a) * 60, 311 + math.sin(a) * 60)],
                      (44, 55, 59), 2)
            _circle(ctx, 711, 311, 11, (44, 55, 59))
        if chapter == 3:
            # Counterweight gantry: unequal hanging iron blocks and a pulley.
            _rect(ctx, 425, 181, 13, 259, (40, 51, 57))
            _rect(ctx, 652, 181, 13, 259, (40, 51, 57))
            _poly(ctx, [(410, 169), (678, 169), (678, 191), (410, 191)], (40, 51, 57))
            for xx in range(441, 650, 29):
                _line(ctx, [(xx, 172), (xx + 21, 188)], (24, 38, 45), 2)
            for xx, block_y in ((491, 332), (602, 259)):
                _line(ctx, [(xx, 189), (xx, block_y)], (36, 48, 54), 2)
                _rect(ctx, xx - 19, block_y, 38, 46, (32, 45, 51))
                _rect(ctx, xx - 16, block_y + 4, 32, 4, (72, 87, 92), .5)
                _line(ctx, [(xx - 14, block_y + 14), (xx + 14, block_y + 14)], (48, 62, 68), 1)
            for xx in (491, 602):
                _circle(ctx, xx, 192, 13, (30, 44, 50))
                _circle(ctx, xx, 192, 7, (76, 94, 100))
                _circle(ctx, xx, 192, 3, (30, 44, 50))
            _line(ctx, [(438, 219), (652, 384)], (40, 51, 57), 4)
            _line(ctx, [(438, 384), (652, 219)], (40, 51, 57), 4)
        if chapter == 4:
            # The final relay yard: tapered antenna masts and collapsed dishes.
            for xx, top in ((293, 179), (536, 129), (718, 198)):
                _poly(ctx, [(xx - 11, 440), (xx - 2, top), (xx + 2, top),
                            (xx + 11, 440)], (45, 58, 64))
                _line(ctx, [(xx - 39, top + 30), (xx + 39, top + 30)], (45, 58, 64), 2)
                for span in (-28, -12, 12, 28):
                    _line(ctx, [(xx + span, top + 11), (xx + span, top + 48)], (45, 58, 64), 1.5)
                _line(ctx, [(xx, top + 50), (xx - 74, 438)], (50, 62, 67), .8)
                _line(ctx, [(xx, top + 50), (xx + 74, 438)], (50, 62, 67), .8)
                _circle(ctx, xx, top, 2, (176, 199, 197), .55)
            ctx.new_path()
            ctx.move_to(286, 368)
            ctx.curve_to(415, 405, 580, 389, 720, 341)
            _color(ctx, (42, 55, 62))
            ctx.set_line_width(1)
            ctx.stroke()
        if chapter == 5:
            # A quiet induction hall: paired coils and ceramic insulator stacks.
            for xx, top in ((260, 208), (486, 148), (687, 186)):
                _rect(ctx, xx - 9, top + 21, 18, 438 - top, (37, 50, 56))
                for yy in range(top, top + 104, 15):
                    _rect(ctx, xx - 32, yy, 64, 7, (64, 79, 83))
                    _line(ctx, [(xx - 30, yy + 1), (xx + 30, yy + 1)], (101, 118, 116), 1, .45)
                _line(ctx, [(xx, top), (xx, top - 27), (xx + 79, top - 27),
                            (xx + 79, 438)], (43, 58, 64), 3)
            _line(ctx, [(230, 414), (742, 414)], (34, 49, 55), 14)
    surface.write_to_png(str(path))


def _courier_frame(ctx, frame):
    """A lantern courier with a rain hood, wrap coat and forked signal scarf."""
    walk = 2 <= frame <= 9
    phase = (frame - 2) / 8 * math.tau if walk else 0
    stride = math.sin(phase) * 5.1 if walk else 0
    lift = abs(math.cos(phase)) * .65 if walk else math.sin(frame * 2) * .35
    jump = frame >= 10
    ctx.translate(48, 56 + lift * 2)
    ctx.scale(2, 2)
    # rear boot / bent shin, then coat, then front shin: physically legible motion.
    for back in (True, False):
        leg = -stride if back else stride
        if jump:
            knee = (4 if back else -3, 11)
            ankle = (8 if back else -6, 18 if frame == 10 else 21)
        else:
            knee = (leg * .55 + (-2 if back else 2), 14)
            ankle = (leg + (-2 if back else 2), 22 - max(0, -leg) * .38)
        tone = (15, 22, 25) if back else (23, 31, 35)
        _line(ctx, [(-2 if back else 2, 7), knee, ankle], tone, 4.4)
        _line(ctx, [ankle, (ankle[0] + 4, ankle[1])], tone, 4.2)
        if not back:
            _line(ctx, [(ankle[0] - .5, ankle[1] + 1.8),
                        (ankle[0] + 4, ankle[1] + 1.8)], (111, 124, 125), .6, .55)
    _poly(ctx, [(-7, -7), (4, -8), (8, 4), (9, 12), (3, 14),
                (-1, 12), (-6, 14), (-9, 9)], (29, 38, 42))
    _line(ctx, [(-7, -5), (-9, 8), (-6, 13)], (99, 115, 116), .7, .6)
    _line(ctx, [(3, -4), (4, 11), (7, 12)], (73, 88, 93), .65)
    _line(ctx, [(-4, 9), (2, 10), (6, 9)], (12, 21, 25), .8)
    # A swinging arm with a narrow cuff.
    hand_x = 7 + math.sin(phase + math.pi) * 1.5 if walk else 7
    if jump:
        hand_x = 10
    _line(ctx, [(5, -5), (8, 1), (hand_x, 7 if not jump else -2)], (22, 31, 35), 4)
    _line(ctx, [(hand_x - 1.1, 6 if not jump else -3),
                (hand_x + 1.2, 6 if not jump else -3)], (100, 115, 116), .7)
    # Hood is deliberately asymmetric, with a deep void and a rounded brow.
    ctx.new_path()
    ctx.move_to(-8, -7)
    ctx.curve_to(-13, -16, -6, -24, 1, -24)
    ctx.curve_to(8, -24, 11, -19, 11, -13)
    ctx.line_to(7, -7)
    ctx.curve_to(0, -5, -3, -7, -8, -7)
    ctx.close_path()
    _color(ctx, (41, 51, 55))
    ctx.fill()
    ctx.new_path()
    ctx.move_to(2, -21)
    ctx.curve_to(10, -21, 10, -16, 9, -11)
    ctx.curve_to(6, -8, 2, -8, 0, -12)
    ctx.curve_to(-1, -16, 0, -18, 2, -21)
    _color(ctx, (8, 15, 18))
    ctx.fill()
    _line(ctx, [(-8, -12), (-8, -18), (-4, -22), (1, -24), (6, -22)],
          (151, 164, 164), .75, .68)
    _circle(ctx, 7, -15, .72, (211, 219, 209), .9)
    # Scarf is a separate silhouette, not a recoloured target-game character.
    flutter = math.sin(phase + .6) * 2 if walk else (-2 if jump else frame * .5)
    _poly(ctx, [(-4, -9), (-10, -10), (-18, -6 + flutter),
                (-22, -8 + flutter), (-20, -3 + flutter),
                (-14, -4 + flutter), (-6, -6)], (83, 108, 113))
    _line(ctx, [(-4, -8), (-11, -8), (-18, -5 + flutter)], (158, 178, 175), .55, .7)
    _line(ctx, [(-5, -6), (4, -5)], (139, 153, 151), 1.6)
    # Chest lantern: suspended round cage, pale core, two retaining struts.
    _line(ctx, [(2, -5), (0, 1)], (136, 143, 137), .6)
    _circle(ctx, 0, 1, 4.1, (13, 24, 28))
    _circle(ctx, 0, 1, 3.0, (179, 213, 209))
    _circle(ctx, -.6, .4, 1.6, (238, 239, 218))
    _line(ctx, [(-2, -.8), (-2, 3)], (66, 91, 94), .55)
    _line(ctx, [(2, -.8), (2, 3)], (66, 91, 94), .55)


def _player_sheet(path: Path):
    surface, ctx = _surface(PLAYER_CELL[0] * PLAYER_FRAMES, PLAYER_CELL[1])
    for frame in range(PLAYER_FRAMES):
        ctx.save()
        ctx.rectangle(frame * 96, 0, 96, 112)
        ctx.clip()
        ctx.translate(frame * 96, 0)
        _courier_frame(ctx, frame)
        ctx.restore()
    surface.write_to_png(str(path))


def _crate(path: Path, heavy=False):
    surface, ctx = _surface(256, 256)
    rng = random.Random(SEED + int(heavy))
    _rect(ctx, 16, 16, 224, 224, (22, 30, 34))
    if heavy:
        for x in range(28, 234, 24):
            _rect(ctx, x, 24, 15, 208, (33, 43, 48))
            _line(ctx, [(x, 24), (x, 232)], (82, 94, 98), 1.2, .65)
        _rect(ctx, 21, 24, 214, 12, (82, 95, 96))
        _rect(ctx, 21, 219, 214, 12, (62, 75, 79))
        _line(ctx, [(29, 34), (223, 221)], (16, 25, 30), 18)
        _line(ctx, [(29, 34), (223, 221)], (70, 84, 88), 3)
        _circle(ctx, 128, 128, 28, (15, 25, 30))
        _circle(ctx, 128, 128, 18, (69, 83, 87))
        _rect(ctx, 123, 119, 10, 19, (25, 36, 42))
    else:
        for n in range(6):
            x = 20 + n * 36
            _rect(ctx, x, 23, 33, 210, (43 + n % 3 * 4, 50 + n % 3 * 4, 53 + n % 3 * 4))
            _line(ctx, [(x, 23), (x, 232)], (12, 21, 26), 2)
            for _ in range(6):
                y = rng.uniform(28, 214)
                xx = x + rng.uniform(4, 29)
                _line(ctx, [(xx, y), (xx + rng.uniform(-2, 2), y + rng.uniform(7, 35))],
                      (118, 125, 118), .8, .15)
        for points in ([(29, 30), (225, 225)], [(29, 225), (225, 30)]):
            _line(ctx, points, (21, 30, 35), 18)
            _line(ctx, points, (94, 107, 107), 1.6, .6)
        for yy in (24, 218):
            _rect(ctx, 23, yy, 210, 13, (31, 41, 45))
            _line(ctx, [(24, yy), (232, yy)], (128, 139, 133), 1.5, .7)
        # Three small tally scratches, a recognisable courier freight mark.
        for xx in (108, 120, 132):
            _line(ctx, [(xx + 3, 105), (xx - 2, 127)], (151, 162, 153), 2.2, .7)
    _line(ctx, [(17, 238), (17, 17), (238, 17)], (154, 166, 161), 2, .72)
    _line(ctx, [(238, 17), (238, 238), (17, 238)], (5, 14, 19), 3)
    for x in (30, 225):
        for y in (30, 225):
            _circle(ctx, x, y, 3.0, (152, 163, 157), .85)
            _circle(ctx, x + .6, y + .6, 1.0, (20, 31, 37))
    surface.write_to_png(str(path))


def _magnet(path: Path):
    """Original ceiling-clamp face: paired wound coils over a riveted plate."""
    surface, ctx = _surface(256, 64)
    _rect(ctx, 0, 32, 256, 32, (25, 38, 43))
    _rect(ctx, 3, 53, 250, 10, (71, 94, 94))
    _line(ctx, [(2, 63), (254, 63)], (163, 194, 181), 2)
    for x in (21, 153):
        _rect(ctx, x, 4, 82, 34, (17, 29, 35))
        for xx in range(x + 7, x + 79, 9):
            _line(ctx, [(xx, 6), (xx - 3, 29), (xx + 2, 36)], (100, 125, 117), 4)
            _line(ctx, [(xx, 6), (xx - 3, 29)], (159, 180, 153), 1, .6)
        _rect(ctx, x - 3, 1, 88, 5, (57, 76, 77))
    for x in (10, 116, 140, 246):
        _circle(ctx, x, 44, 3, (163, 184, 173))
        _line(ctx, [(x - 1, 43), (x + 1, 45)], (18, 34, 39), 1)
    _line(ctx, [(110, 22), (128, 13), (146, 22)], (110, 140, 136), 2)
    surface.write_to_png(str(path))


def _saw(path: Path):
    surface, ctx = _surface(256, 256)
    teeth = []
    for n in range(24):
        angle = n / 24 * math.tau
        for offset, radius in ((0, 101), (.19, 119), (.55, 115), (.69, 98)):
            a = angle + offset * math.tau / 24
            teeth.append((128 + math.cos(a) * radius, 128 + math.sin(a) * radius))
    _poly(ctx, teeth, (160, 176, 176))
    _circle(ctx, 128, 128, 95, (25, 36, 42))
    for radius, color, width in ((87, (87, 105, 110), 2), (76, (11, 24, 32), 4)):
        ctx.new_path()
        ctx.arc(128, 128, radius, 0, math.tau)
        _color(ctx, color)
        ctx.set_line_width(width)
        ctx.stroke()
    for n in range(8):
        a = n / 8 * math.tau
        _line(ctx, [(128 + math.cos(a) * 29, 128 + math.sin(a) * 29),
                    (128 + math.cos(a + .08) * 74, 128 + math.sin(a + .08) * 74)],
              (65, 83, 90), 8)
        _circle(ctx, 128 + math.cos(a) * 58, 128 + math.sin(a) * 58, 4, (127, 144, 143))
    _circle(ctx, 128, 128, 27, (103, 123, 127))
    _circle(ctx, 128, 128, 18, (13, 27, 34))
    _circle(ctx, 128, 128, 7, (170, 187, 180))
    surface.write_to_png(str(path))


def _moth(path: Path):
    surface, ctx = _surface(256, 64)
    for frame in range(4):
        ctx.save()
        ctx.translate(frame * 64 + 32, 32)
        spread = (1, .65, .25, .65)[frame]
        ctx.save()
        ctx.scale(spread, 1)
        for direction in (-1, 1):
            ctx.save()
            ctx.scale(direction, 1)
            ctx.new_path()
            ctx.move_to(0, -3)
            ctx.curve_to(7, -17, 27, -17, 19, 1)
            ctx.curve_to(30, 12, 11, 18, 1, 5)
            ctx.close_path()
            _color(ctx, (208, 225, 215), .85)
            ctx.fill()
            _line(ctx, [(2, 0), (13, -10)], (98, 141, 145), .8)
            _circle(ctx, 12, -5, 3, (102, 145, 149), .7)
            ctx.restore()
        ctx.restore()
        _line(ctx, [(0, -6), (0, 7)], (243, 242, 224), 2.3)
        _line(ctx, [(0, -6), (-4, -11)], (213, 224, 213), .7)
        _line(ctx, [(0, -6), (4, -11)], (213, 224, 213), .7)
        ctx.restore()
    surface.write_to_png(str(path))


def _glow(path: Path):
    surface, ctx = _surface(192, 192)
    glow = cairo.RadialGradient(96, 96, 0, 96, 96, 95)
    for stop, alpha in ((0, .34), (.10, .21), (.32, .06), (.72, .014), (1, 0)):
        glow.add_color_stop_rgba(stop, .68, .87, .85, alpha)
    ctx.set_source(glow)
    ctx.paint()
    surface.write_to_png(str(path))


def _fog(path: Path):
    surface, ctx = _surface(*LANDSCAPE_SIZE)
    rng = random.Random(SEED + 998)
    # Horizontal gaussian-like bands compose seamlessly as a repeating tile.
    for n in range(10):
        y = rng.uniform(264, 523)
        height = rng.uniform(16, 66)
        gradient = cairo.LinearGradient(0, y - height, 0, y + height)
        gradient.add_color_stop_rgba(0, .67, .72, .73, 0)
        gradient.add_color_stop_rgba(.5, .67, .72, .73, rng.uniform(.026, .068))
        gradient.add_color_stop_rgba(1, .67, .72, .73, 0)
        ctx.set_source(gradient)
        ctx.rectangle(0, y - height, 1920, height * 2)
        ctx.fill()
    # Wrapped elliptical pockets break horizontal uniformity, making the slow
    # runtime translation visible while keeping the tile's edges continuous.
    for _ in range(5):
        x = rng.uniform(0, 1920)
        y = rng.uniform(300, 496)
        reach = rng.uniform(180, 450)
        height = rng.uniform(22, 48)
        for wrapped_x in (x - 1920, x, x + 1920):
            ctx.save()
            ctx.translate(wrapped_x, y)
            ctx.scale(reach, height)
            cloud = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
            cloud.add_color_stop_rgba(0, .68, .74, .75, .09)
            cloud.add_color_stop_rgba(.5, .68, .74, .75, .038)
            cloud.add_color_stop_rgba(1, .68, .74, .75, 0)
            ctx.set_source(cloud)
            ctx.rectangle(-1, -1, 2, 2)
            ctx.fill()
            ctx.restore()
    surface.write_to_png(str(path))


def _foliage(path: Path):
    surface, ctx = _surface(*LANDSCAPE_SIZE)
    rng = random.Random(SEED + 772)
    for x, y, length, angle, width in ((-8, 562, 167, -1.44, 13),
                                       (1890, 558, 195, -1.85, 17),
                                       (-35, -20, 218, .42, 19),
                                       (1939, -7, 190, 2.5, 18)):
        _branch(ctx, rng, x, y, length, angle, width, 5, (6, 13, 17))
    for _ in range(130):
        x = rng.uniform(0, 1920)
        height = rng.uniform(5, 30) * (.8 + .5 * math.sin(x / 83))
        _line(ctx, [(x, 548), (x + rng.uniform(-6, 6), 540 - height)], (5, 12, 16),
              rng.uniform(.8, 2.3))
    surface.write_to_png(str(path))


def _vignette(path: Path):
    surface, ctx = _surface(960, 540)
    ctx.translate(480, 270)
    ctx.scale(480, 270)
    gradient = cairo.RadialGradient(0, 0, .24, 0, 0, 1.35)
    gradient.add_color_stop_rgba(0, .01, .025, .04, 0)
    gradient.add_color_stop_rgba(.55, .01, .025, .04, .09)
    gradient.add_color_stop_rgba(.87, .01, .025, .04, .36)
    gradient.add_color_stop_rgba(1, .01, .025, .04, .68)
    ctx.set_source(gradient)
    ctx.paint()
    surface.write_to_png(str(path))


def _grain(path: Path):
    # Cairo owns the PNG encoding. A small periodic tile keeps runtime work tiny.
    rng = np.random.default_rng(SEED)
    data = np.zeros((128, 128, 4), dtype=np.uint8)
    values = rng.integers(0, 2, (128, 128), dtype=np.uint8)
    alpha = rng.integers(0, 10, (128, 128), dtype=np.uint8)
    # FORMAT_ARGB32 is premultiplied native-endian BGRA on this Linux target.
    import sys
    if sys.byteorder == "little":
        data[:, :, :3] = (values * alpha)[:, :, None]
        data[:, :, 3] = alpha
    else:
        data[:, :, 0] = alpha
        data[:, :, 1:] = (values * alpha)[:, :, None]
    surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, 128, 128)
    surface.write_to_png(str(path))


def art_asset_names():
    names = ["sky.png", "courier_sheet.png", "crate.png", "crate_heavy.png",
             "saw.png", "moth_guide.png", "glow.png", "fog.png", "foliage.png",
             "vignette.png", "grain.png", "magnet.png"]
    names += [f"chapter_{chapter}_{layer}.png" for chapter in range(CHAPTERS)
              for layer in ("far", "mid", "works")]
    return names


def ensure_art_assets(force=False, root: Path | None = None):
    """Create only ECHO-owned artwork. Existing assets are kept unless forced."""
    root = Path(root) if root is not None else ART_ROOT
    root.mkdir(parents=True, exist_ok=True)
    generators = {"sky.png": _sky, "courier_sheet.png": _player_sheet,
                  "crate.png": _crate, "crate_heavy.png": lambda p: _crate(p, True),
                  "saw.png": _saw, "moth_guide.png": _moth, "glow.png": _glow,
                  "fog.png": _fog, "foliage.png": _foliage,
                  "vignette.png": _vignette, "grain.png": _grain, "magnet.png": _magnet}
    for chapter in range(CHAPTERS):
        for layer in ("far", "mid", "works"):
            generators[f"chapter_{chapter}_{layer}.png"] = (
                lambda p, c=chapter, l=layer: _landscape(p, c, l))
    for name, generate in generators.items():
        path = root / name
        if force or not path.is_file():
            generate(path)
    return [root / name for name in art_asset_names()]


def _load(path):
    surface = pygame.image.load(str(path))
    # Tests and asset generation do not need a video mode; conversion is optional.
    return surface.convert_alpha() if pygame.display.get_surface() is not None else surface


def _remember(cache, key, value, limit):
    cache[key] = value
    cache.move_to_end(key)
    if len(cache) > limit:
        cache.popitem(last=False)
    return value


class Art:
    """Cached cinematic parallax artwork; caller owns terrain and UI drawing."""

    def __init__(self, size=(960, 540)):
        ensure_art_assets()
        self.size = tuple(map(int, size))
        self._images = {name[:-4]: _load(ART_ROOT / name) for name in art_asset_names()}
        sheet = self._images["courier_sheet"]
        self._players = {}
        for frame in range(PLAYER_FRAMES):
            sprite = pygame.transform.smoothscale(sheet.subsurface((frame * 96, 0, 96, 112)), (48, 56))
            for facing in (-1, 1):
                for gravity in (-1, 1):
                    self._players[(frame, facing, gravity)] = pygame.transform.flip(
                        sprite, facing < 0, gravity < 0)
        self._scaled = OrderedDict()
        self._rotated = OrderedDict()
        self._room_backgrounds = None
        self._glows = {n: pygame.transform.smoothscale(self._images["glow"], (n, n))
                       for n in (56, 64, 72, 80, 96, 144)}
        self._prepare_size(self.size)

    @staticmethod
    def ensure_assets(force=False):
        return ensure_art_assets(force=force)

    def _prepare_size(self, size):
        self.size = tuple(size)
        w, h = self.size
        tile_width = max(1, round(1920 * h / 540))
        self._landscapes = {
            name: pygame.transform.smoothscale(image, (tile_width, h))
            for name, image in self._images.items()
            if name.startswith("chapter_") or name in ("foliage", "fog")}
        self._sky_surface = pygame.transform.smoothscale(self._images["sky"], (w, h))
        if pygame.display.get_surface() is not None:
            self._sky_surface = self._sky_surface.convert()
        self._vignette_surface = pygame.transform.smoothscale(self._images["vignette"], (w, h))
        self._grain_surface = pygame.Surface((w + 128, h + 128), pygame.SRCALPHA)
        grain = self._images["grain"]
        for yy in range(0, h + 128, 128):
            for xx in range(0, w + 128, 128):
                self._grain_surface.blit(grain, (xx, yy))

    def _tile(self, screen, name, offset, y=0):
        image = self._landscapes[name]
        width = image.get_width()
        start = -int(offset % width)
        for x in range(start, screen.get_width(), width):
            screen.blit(image, (x, y), special_flags=pygame.BLEND_ALPHA_SDL2)

    def draw_background(self, screen: pygame.Surface, camera_x: float, time: float, chapter: int, theme=None):
        if screen.get_size() != self.size:
            self._prepare_size(screen.get_size())
        if theme is not None:
            if self._room_backgrounds is None:
                from .room_art import RoomBackgrounds
                self._room_backgrounds = RoomBackgrounds()
            self._room_backgrounds.draw(screen, camera_x, time, theme, self)
            return
        chapter = max(0, min(CHAPTERS - 1, int(chapter)))
        screen.blit(self._sky_surface, (0, 0))
        self._tile(screen, f"chapter_{chapter}_far", camera_x * .075)
        self._tile(screen, f"chapter_{chapter}_works", camera_x * .18)
        # The tower beacon travels with its own layer, not the foreground camera.
        scale = self.size[1] / 540
        width = self._landscapes[f"chapter_{chapter}_works"].get_width()
        x = BEACON_X * scale - camera_x * .18 % width
        glow = self._glows[144]
        glow.set_alpha(round(160 + 30 * math.sin(time * 1.4)))
        for xx in (x - width, x, x + width):
            if -144 < xx < self.size[0] + 144:
                screen.blit(glow, (round(xx - 72), round(155 * scale - 72)),
                            special_flags=pygame.BLEND_ALPHA_SDL2)
        self._tile(screen, f"chapter_{chapter}_mid", camera_x * .32)
        self._tile(screen, "fog", camera_x * .10 + time * 7)
        # Quiet airborne signal dust: deterministic world-space motes.
        for n in range(17):
            xx = (n * 173.39 - camera_x * .23 + time * (2 + n % 3)) % (self.size[0] + 60) - 30
            yy = (95 + n * 47.3 + math.sin(time * .35 + n * 1.7) * 13) % (self.size[1] * .77)
            value = 125 + round(21 * math.sin(time * .6 + n))
            pygame.draw.circle(screen, (value, value + 7, value + 7), (round(xx), round(yy)), 1)

    def draw_player(self, screen: pygame.Surface, pos: tuple[float, float],
                    velocity: tuple[float, float], facing: int, time: float,
                    grounded: bool, gravity: int = 1):
        vx, vy = velocity
        if not grounded:
            frame = 10 if vy * gravity < 0 else 11
        elif abs(vx) > 12:
            frame = 2 + int(time * min(13, 5 + abs(vx) / 24)) % 8
        else:
            frame = int(time * 1.5) % 2
        facing = -1 if facing < 0 else 1
        gravity = -1 if gravity < 0 else 1
        sprite = self._players[(frame, facing, gravity)]
        x, y = pos
        glow_size = 64 if int(time * 5) % 3 else 72
        glow = self._glows[glow_size]
        screen.blit(glow, (round(x - glow_size / 2), round(y + gravity - glow_size / 2)),
                    special_flags=pygame.BLEND_ALPHA_SDL2)
        screen.blit(sprite, (round(x - 24), round(y - 28)))

    def sprite(self, name, size=None):
        """Expose original sprite surfaces, including the four-frame moth sheet.

        Names: crate, crate_heavy, saw, magnet, moth_guide, glow, courier_sheet.
        Callers must not mutate returned cached surfaces.
        """
        image = self._images[name.removesuffix(".png")]
        if size is None:
            return image
        size = tuple(max(1, round(v)) for v in size)
        key = (name, size)
        if key in self._scaled:
            self._scaled.move_to_end(key)
            return self._scaled[key]
        return _remember(self._scaled, key, pygame.transform.smoothscale(image, size), 96)

    def draw_crate(self, screen: pygame.Surface, pos, size: tuple, angle: float, heavy: bool = False):
        # 224px of a 256px canvas is solid: preserve the supplied physics size.
        dims = tuple(max(1, round(float(v) * 256 / 224)) for v in size)
        name = "crate_heavy" if heavy else "crate"
        degree = (round(math.degrees(angle) / 2) * 2) % 360
        key = (name, dims, degree)
        if key in self._rotated:
            self._rotated.move_to_end(key)
            image = self._rotated[key]
        else:
            image = pygame.transform.rotate(self.sprite(name, dims), -degree)
            _remember(self._rotated, key, image, 512)
        screen.blit(image, image.get_rect(center=(round(pos[0]), round(pos[1]))))

    def draw_saw(self, screen: pygame.Surface, pos, radius: float, time: float):
        diameter = max(2, round(radius * 256 / 119))
        degree = (round(time * 260 / 5) * 5) % 360
        key = ("saw", diameter, degree)
        if key in self._rotated:
            self._rotated.move_to_end(key)
            image = self._rotated[key]
        else:
            image = pygame.transform.rotate(self.sprite("saw", (diameter, diameter)), -degree)
            _remember(self._rotated, key, image, 512)
        screen.blit(image, image.get_rect(center=(round(pos[0]), round(pos[1]))))

    def draw_foreground(self, screen: pygame.Surface, camera_x, time):
        if screen.get_size() != self.size:
            self._prepare_size(screen.get_size())
        self._tile(screen, "foliage", camera_x * .61 + math.sin(time * .26) * 1.4)
        screen.blit(self._vignette_surface, (0, 0), special_flags=pygame.BLEND_ALPHA_SDL2)
        step = int(time * 8)
        screen.blit(self._grain_surface, (-step * 17 % 128 - 128, -step * 29 % 128 - 128),
                    special_flags=pygame.BLEND_ALPHA_SDL2)
