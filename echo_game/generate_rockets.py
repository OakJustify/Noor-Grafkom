"""Generate ECHO's modular greyscale rocket obstacles with Cairo.

Usage: .venv-echo/bin/python -m echo_game.generate_rockets [--force]
           [--variants 24] [--seed 20261116]

A rocket is assembled from independent parts that share one horizontal axis:
nose, collar, body, strap, fin, nozzle and flame. Every shape variant has a
different silhouette, and each part is itself built from several primitives
(triangles, rectangles, arcs, trapezoids, pentagons), so a randomizer can mix
shapes and tones freely. Pixels are greyscale only, which lets the game tint
any part at runtime with a seeded colour (pygame.BLEND_MULT), exactly like the
block library. No display, mixer or network access.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import cairo

ROCKET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "obstacle" / "rockets"
PART_ROOT = ROCKET_ROOT / "parts"
VARIANT_ROOT = ROCKET_ROOT / "variants"
CANVAS = (512, 176)
AXIS = CANVAS[1] / 2
PAD = 9
BODY_HALF = 24
OUTLINE = 44.0
TONES = {"dark": 0.84, "mid": 1.0, "light": 1.16}


def _gray(value, alpha=1.0):
    v = max(0, min(255, value)) / 255.0
    return (v, v, v, alpha)


def _set(ctx, value, alpha=1.0):
    ctx.set_source_rgba(*_gray(value, alpha))


def _palette(tone):
    mid = 150.0 * TONES[tone]
    return (min(245.0, mid + 62), mid, max(72.0, mid - 52))


def _gradient(ctx, half, pal):
    light, mid, dark = pal
    gradient = cairo.LinearGradient(0, -half, 0, half)
    for stop, value in ((0.0, light), (0.55, mid), (1.0, dark)):
        v = value / 255.0
        gradient.add_color_stop_rgb(stop, v, v, v)
    ctx.set_source(gradient)


def _outline(ctx, width=4.0, alpha=.95, value=OUTLINE):
    _set(ctx, value, alpha)
    ctx.set_line_width(width)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()


def _rect(ctx, x0, y0, x1, y1):
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0)


def _round_rect(ctx, x0, y0, x1, y1, radius):
    r = max(1.0, radius)
    ctx.new_path()
    ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    ctx.arc(x0 + r, y0 + r, r, math.pi, math.pi * 1.5)
    ctx.close_path()


def _poly(ctx, points):
    ctx.new_path()
    ctx.move_to(*points[0])
    for x, y in points[1:]:
        ctx.line_to(x, y)
    ctx.close_path()


def _dots(ctx, positions, radius=1.9, value=58, alpha=.7):
    _set(ctx, value, alpha)
    for x, y in positions:
        ctx.new_path()
        ctx.arc(x, y, radius, 0, math.tau)
        ctx.fill()


# ---------------------------------------------------------------------------
# Noses: cone, blunt cone, dome, stepped cone, pentagon, spearhead.

def _nose_path(ctx, shape, length, half):
    x, h = length, half
    ctx.new_path()
    if shape == "sharp":
        ctx.move_to(0, 0)
        ctx.line_to(x, -h)
        ctx.line_to(x, h)
    elif shape == "blunt":
        ctx.move_to(0, -h * .34)
        ctx.line_to(0, h * .34)
        ctx.line_to(x, h)
        ctx.line_to(x, -h)
    elif shape == "round":
        ctx.move_to(0, 0)
        ctx.curve_to(x * .46, -h * .82, x * .92, -h, x, -h)
        ctx.line_to(x, h)
        ctx.curve_to(x * .92, h, x * .46, h * .82, 0, 0)
    elif shape == "stepped":
        ctx.move_to(0, 0)
        ctx.line_to(x * .30, -h * .56)
        ctx.line_to(x * .30, -h * .86)
        ctx.line_to(x * .46, -h)
        ctx.line_to(x, -h)
        ctx.line_to(x, h)
        ctx.line_to(x * .46, h)
        ctx.line_to(x * .30, h * .86)
        ctx.line_to(x * .30, h * .56)
    elif shape == "pentagon":
        ctx.move_to(0, 0)
        ctx.line_to(x * .54, -h)
        ctx.line_to(x, -h * .78)
        ctx.line_to(x, h * .78)
        ctx.line_to(x * .54, h)
    else:  # spear
        ctx.move_to(0, 0)
        ctx.line_to(x * .70, -h * .88)
        ctx.line_to(x, -h * .60)
        ctx.line_to(x, h * .60)
        ctx.line_to(x * .70, h * .88)
    ctx.close_path()


def _draw_nose(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _nose_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _nose_path(ctx, shape, length, half)
    ctx.clip()
    # Lighter facet along the upper edge: a triangle plus a parallelogram.
    _poly(ctx, [(1, 0), (length, -half), (length * .42, -half * .38)])
    _set(ctx, light, .32)
    ctx.fill()
    _poly(ctx, [(length * .34, half * .18), (length, half * .42),
                (length, half), (length * .30, half * .70)])
    _set(ctx, dark, .26)
    ctx.fill()
    # Base plate with rivets, so a cone reads as two primitives joined.
    _rect(ctx, length - 11, -half, length, half)
    _set(ctx, dark, .30)
    ctx.fill()
    _dots(ctx, [(length - 5.5, -half * .48), (length - 5.5, half * .48)], 1.8)
    ctx.restore()
    _nose_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Collars: flared trapezoid, rounded pill, pentagon, double ring, hexagon,
# notched plate.

def _collar_path(ctx, shape, length, half):
    x, h = length, half
    ctx.new_path()
    if shape == "trapezoid":
        ctx.move_to(0, -h * .78)
        ctx.line_to(x, -h)
        ctx.line_to(x, h)
        ctx.line_to(0, h * .78)
    elif shape == "rounded":
        _round_rect(ctx, 0, -h, x, h, min(x * .42, h * .52))
    elif shape == "pentagon":
        ctx.move_to(0, -h * .78)
        ctx.line_to(x * .46, -h)
        ctx.line_to(x, -h * .62)
        ctx.line_to(x, h * .62)
        ctx.line_to(x * .46, h)
    elif shape == "double":
        _rect(ctx, 0, -h, x * .34, h)
        _rect(ctx, x * .66, -h, x, h)
    elif shape == "hex":
        ctx.move_to(0, -h * .72)
        ctx.line_to(x * .36, -h)
        ctx.line_to(x, -h * .72)
        ctx.line_to(x, h * .72)
        ctx.line_to(x * .36, h)
        ctx.line_to(0, h * .72)
    else:  # notched
        ctx.move_to(0, -h * .82)
        ctx.line_to(x * .22, -h)
        ctx.line_to(x * .80, -h)
        ctx.line_to(x, -h * .50)
        ctx.line_to(x, h * .50)
        ctx.line_to(x * .80, h)
        ctx.line_to(x * .22, h)
        ctx.line_to(0, h * .82)
    ctx.close_path()


def _draw_collar(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _collar_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _collar_path(ctx, shape, length, half)
    ctx.clip()
    # Every collar gets a lip band and a recessed groove built from rectangles.
    _rect(ctx, 0, -half, 4.5, half)
    _set(ctx, light, .35)
    ctx.fill()
    _rect(ctx, length - 4.5, -half, length, half)
    _set(ctx, dark, .34)
    ctx.fill()
    _rect(ctx, 0, -3, length, 3)
    _set(ctx, dark, .30)
    ctx.fill()
    if shape in ("rounded", "double", "notched"):
        _dots(ctx, [(length * .5, -half * .55), (length * .5, half * .55)], 2.2)
    ctx.restore()
    _collar_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Bodies: planked barrels, panelled metal, segmented drum, ribbed shell.
# Each body has its own profile: straight, tapered, bulged, chamfered, stepped.

def _body_path(ctx, shape, length, half):
    x, h = length, half
    ctx.new_path()
    if shape in ("plank-short", "plank-long"):
        _rect(ctx, 0, -h, x, h)
    elif shape == "panel-short":  # chamfered ends, flat sides
        _poly(ctx, [(0, -h + 7), (10, -h), (x - 10, -h), (x, -h + 7),
                    (x, h - 7), (x - 10, h), (10, h), (0, h - 7)])
    elif shape == "panel-long":  # bulged barrel
        ctx.move_to(0, -h)
        ctx.curve_to(x * .3, -h - 3.5, x * .7, -h - 3.5, x, -h)
        ctx.line_to(x, h)
        ctx.curve_to(x * .7, h + 3.5, x * .3, h + 3.5, 0, h)
        ctx.close_path()
    elif shape == "segmented":  # waist: narrower in the middle
        _poly(ctx, [(0, -h), (x * .5, -h + 4), (x, -h),
                    (x, h), (x * .5, h - 4), (0, h)])
    else:  # ribbed: tapered ends
        _poly(ctx, [(0, -h + 5), (9, -h), (x - 9, -h), (x, -h + 5),
                    (x, h - 5), (x - 9, h), (9, h), (0, h - 5)])


def _draw_body(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _body_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _body_path(ctx, shape, length, half)
    ctx.clip()

    if shape.startswith("plank"):
        rows = 4
        step = half * 2 / rows
        _set(ctx, dark, .48)
        ctx.set_line_width(2.4)
        for i in range(1, rows):
            y = -half + i * step
            ctx.move_to(0, y)
            ctx.line_to(length, y)
        ctx.stroke()
        _set(ctx, dark, .32)
        ctx.set_line_width(1.8)
        for i in range(rows):
            offset = 18 if i % 2 else 0
            for x in range(offset + 14, length - 8, 46):
                ctx.move_to(x, -half + i * step + 2)
                ctx.line_to(x, -half + (i + 1) * step - 2)
        ctx.stroke()
        for x in (0, length - 12):
            _rect(ctx, x, -half, x + 12, half)
            _set(ctx, dark, .22)
            ctx.fill()
    elif shape.startswith("panel"):
        _set(ctx, dark, .38)
        ctx.set_line_width(2)
        for x in range(38, length - 8, 38):
            ctx.move_to(x, -half)
            ctx.line_to(x, half)
        ctx.stroke()
        _rect(ctx, 0, -half, length, -half + 7)
        _rect(ctx, 0, half - 7, length, half)
        _set(ctx, dark, .20)
        ctx.fill()
        _dots(ctx, [(x, y) for x in range(16, int(length) - 6, 38)
                    for y in (-half + 11, half - 11)], 1.9)
    elif shape == "segmented":
        for x in (length / 2 - 13, length / 2 + 13):
            _rect(ctx, x - 3, -half, x + 3, half)
            _set(ctx, light, .22)
            ctx.fill()
        _rect(ctx, length / 2 - 10, -half, length / 2 + 10, half)
        _set(ctx, dark, .22)
        ctx.fill()
        _rect(ctx, length / 2 - 10, -half, length / 2 + 10, -half + 4)
        _set(ctx, light, .30)
        ctx.fill()
        _dots(ctx, [(length / 2 + d, y) for d in (-16, 16) for y in (-half * .6, half * .6)], 2.1)
    else:  # ribbed
        for x in range(10, int(length) - 8, 22):
            _rect(ctx, x, -half, x + 9, half)
            _set(ctx, light, .18)
            ctx.fill()
            _set(ctx, dark, .30)
            ctx.set_line_width(1.6)
            ctx.move_to(x + 9, -half)
            ctx.line_to(x + 9, half)
            ctx.stroke()
    ctx.restore()
    _body_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Straps: riveted band, twin bands, slim ring, studded plate, chevron clamp.

def _strap_path(ctx, shape, length, half):
    ctx.new_path()
    if shape == "double":
        _rect(ctx, 0, -half, length * .34, half)
        _rect(ctx, length * .66, -half, length, half)
    else:
        _rect(ctx, 0, -half, length, half)


def _draw_strap(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _strap_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _strap_path(ctx, shape, length, half)
    ctx.clip()

    if shape == "riveted":
        _dots(ctx, [(x, y) for x in range(6, int(length) - 2, 8)
                    for y in (-half + 10, 0, half - 10)], 1.8, alpha=.8)
    elif shape == "double":
        _rect(ctx, length * .34, -7, length * .66, 7)
        _set(ctx, mid, 1.0)
        ctx.fill()
        _rect(ctx, length * .34, -7, length * .66, 7)
        _outline(ctx, 2.4)
        _dots(ctx, [(x, y) for x in range(6, int(length * .3), 9)
                    for y in (-half + 10, 0, half - 10)], 1.7)
        _dots(ctx, [(x, y) for x in range(int(length * .7), int(length) - 3, 9)
                    for y in (-half + 10, 0, half - 10)], 1.7)
    elif shape == "plain":
        _rect(ctx, 0, -half + 5, length, -half + 10)
        _set(ctx, light, .32)
        ctx.fill()
        _rect(ctx, 0, half - 10, length, half - 5)
        _set(ctx, dark, .30)
        ctx.fill()
    elif shape == "studded":
        for x in range(4, int(length) - 4, 11):
            for y in (-half + 10, 0, half - 10):
                _rect(ctx, x, y - 4, x + 6, y + 4)
                _set(ctx, light, .55)
                ctx.fill()
                _rect(ctx, x, y - 4, x + 6, y + 4)
                _outline(ctx, 1.3, alpha=.55)
    else:  # chevron
        _set(ctx, dark, .40)
        for x in range(4, int(length) - 4, 12):
            _poly(ctx, [(x, -half + 8), (x + 6, 0), (x, half - 8),
                        (x + 3, half - 8), (x + 9, 0), (x + 3, -half + 8)])
            ctx.fill()
    ctx.restore()
    _strap_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Fins: swept, straight trapezoid, notched split, rounded, leaf, stepped.

def _fin_path(ctx, shape, length, half):
    root = BODY_HALF
    x, h = length, half
    ctx.new_path()
    for sign in (-1, 1):
        if shape == "swept":
            pts = [(0, root), (x * .74, h), (x, h * .84), (x, root)]
            ctx.move_to(0, sign * pts[0][1])
            for px, py in pts[1:]:
                ctx.line_to(px, sign * py)
        elif shape == "straight":
            pts = [(0, root), (x * .88, h), (x, h * .62), (x, root)]
            ctx.move_to(0, sign * pts[0][1])
            for px, py in pts[1:]:
                ctx.line_to(px, sign * py)
        elif shape == "split":
            pts = [(0, root), (x * .70, h), (x, h * .76),
                   (x * .82, h * .52), (x, root)]
            ctx.move_to(0, sign * pts[0][1])
            for px, py in pts[1:]:
                ctx.line_to(px, sign * py)
        elif shape == "rounded":
            ctx.move_to(0, sign * root)
            ctx.line_to(x * .66, sign * h)
            ctx.curve_to(x * .90, sign * h, x * .97, sign * h * .55, x, sign * root)
        elif shape == "leaf":
            ctx.move_to(0, sign * root)
            ctx.line_to(x * .64, sign * h)
            ctx.line_to(x, sign * root * .9)
        else:  # stepped
            ctx.move_to(0, sign * root)
            ctx.line_to(x * .46, sign * h)
            ctx.line_to(x * .58, sign * h)
            ctx.line_to(x * .58, sign * (root + (h - root) * .55))
            ctx.line_to(x * .76, sign * (root + (h - root) * .55))
            ctx.line_to(x, sign * h * .74)
            ctx.line_to(x, sign * root)
        ctx.close_path()


def _draw_fin(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _fin_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _fin_path(ctx, shape, length, half)
    ctx.clip()
    for sign in (-1, 1):
        # Inner plate: a smaller polygon that turns the fin into a composite.
        _poly(ctx, [(0, sign * BODY_HALF), (length * .60, sign * half * .80),
                    (length * .60, sign * half * .58), (0, sign * (BODY_HALF + 8))])
        _set(ctx, light, .24)
        ctx.fill()
        _rect(ctx, 0, sign * (BODY_HALF - 7), length * .5, sign * 7)
        _set(ctx, dark, .30)
        ctx.fill()
    ctx.restore()
    _fin_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Nozzles: bell, ribbed bell, straight pipe, converging cone, stepped flare.

def _nozzle_path(ctx, shape, length, half):
    ctx.new_path()
    if shape in ("bell", "ribbed"):
        ctx.move_to(0, -BODY_HALF)
        ctx.line_to(length, -half)
        ctx.line_to(length, half)
        ctx.line_to(0, BODY_HALF)
    elif shape == "straight":
        _rect(ctx, 0, -half, length, half)
    elif shape == "cone":
        ctx.move_to(0, -BODY_HALF)
        ctx.line_to(length, -half * .72)
        ctx.line_to(length, half * .72)
        ctx.line_to(0, BODY_HALF)
    else:  # stepped
        ctx.move_to(0, -BODY_HALF)
        ctx.line_to(length * .52, -half * .88)
        ctx.line_to(length * .52, -half)
        ctx.line_to(length, -half * .92)
        ctx.line_to(length, half * .92)
        ctx.line_to(length * .52, half)
        ctx.line_to(length * .52, half * .88)
        ctx.line_to(0, BODY_HALF)
    ctx.close_path()


def _draw_nozzle(ctx, shape, length, half, pal):
    light, mid, dark = pal
    _nozzle_path(ctx, shape, length, half)
    _gradient(ctx, half, pal)
    ctx.fill_preserve()
    ctx.save()
    _nozzle_path(ctx, shape, length, half)
    ctx.clip()
    if shape == "ribbed":
        _set(ctx, dark, .42)
        ctx.set_line_width(3)
        for step in (.30, .48, .66):
            x = length * step
            ctx.move_to(x, -half * .86)
            ctx.line_to(x, half * .86)
        ctx.stroke()
    if shape == "stepped":
        _rect(ctx, length * .52 - 3, -half, length * .52 + 3, half)
        _set(ctx, light, .24)
        ctx.fill()
    # Flared mouth: ellipse plus a rim, two primitives inside the silhouette.
    ctx.save()
    ctx.translate(length - 3, 0)
    ctx.scale(1, .86)
    ctx.arc(0, 0, half * .74, 0, math.tau)
    ctx.restore()
    _set(ctx, 66, .9)
    ctx.fill()
    ctx.save()
    ctx.translate(length - 2, 0)
    ctx.scale(1, .70)
    ctx.arc(0, 0, half * .52, 0, math.tau)
    ctx.restore()
    _set(ctx, mid, .85)
    ctx.fill()
    ctx.restore()
    _nozzle_path(ctx, shape, length, half)
    _outline(ctx)


# ---------------------------------------------------------------------------
# Flames: single tongue, triple, forked, twin jets.

def _tongue(ctx, x, y, width, span):
    ctx.new_path()
    ctx.move_to(x, y - width)
    ctx.curve_to(x + span * .34, y - width * 1.1, x + span * .72, y - width * .5,
                 x + span, y)
    ctx.curve_to(x + span * .72, y + width * .5, x + span * .34, y + width * 1.1,
                 x, y + width)
    ctx.close_path()


def _draw_flame(ctx, shape, length, half, pal):
    light, mid, dark = pal
    gradient = cairo.LinearGradient(0, 0, length, 0)
    for stop, value, alpha in ((0.0, 248, 1.0), (.40, 224, 1.0), (1.0, 182, .62)):
        v = value / 255.0
        gradient.add_color_stop_rgba(stop, v, v, v, alpha)
    ctx.set_source(gradient)
    if shape == "single":
        jets = ((0, half * .62, length),)
    elif shape == "triple":
        jets = ((-half * .5, half * .34, length * .76),
                (0, half * .42, length),
                (half * .5, half * .30, length * .68))
    elif shape == "forked":
        jets = ((-half * .42, half * .38, length), (half * .42, half * .38, length))
    else:  # twin
        jets = ((-half * .48, half * .26, length * .92),
                (half * .48, half * .26, length * .78))
    for y, width, span in jets:
        _tongue(ctx, 0, y, width, span)
        ctx.fill_preserve()
        _outline(ctx, 2.6, alpha=.55, value=92)
    _set(ctx, 252, .9)
    _tongue(ctx, 1, 0, half * .24, length * .46)
    ctx.fill()


DRAWERS = {
    "nose": _draw_nose,
    "collar": _draw_collar,
    "body": _draw_body,
    "strap": _draw_strap,
    "fin": _draw_fin,
    "nozzle": _draw_nozzle,
    "flame": _draw_flame,
}


# ---------------------------------------------------------------------------
# Library definition. Shapes differ in silhouette, tone only changes value.

def _spec(kind, shape, length, half, tone):
    return dict(kind=kind, shape=shape, length=length, half=half, tone=tone,
                name=f"{shape}_{tone}", file=PART_ROOT / kind / f"{shape}_{tone}.png")


def _part_specs():
    specs = []
    noses = (("sharp", 104), ("blunt", 88), ("round", 92),
             ("stepped", 116), ("pentagon", 96), ("spear", 122))
    for shape, length in noses:
        for tone in ("dark", "mid", "light"):
            specs.append(_spec("nose", shape, length, 26, tone))

    collars = (("trapezoid", 28), ("rounded", 24), ("pentagon", 26),
               ("double", 34), ("hex", 26), ("notched", 24))
    for shape, length in collars:
        for tone in ("dark", "mid", "light"):
            specs.append(_spec("collar", shape, length, 32, tone))

    bodies = (("plank-short", 128, "dark"), ("plank-long", 176, "mid"),
              ("panel-short", 136, "light"), ("panel-long", 168, "mid"),
              ("segmented", 150, "light"), ("ribbed", 142, "dark"))
    for shape, length, tone in bodies:
        specs.append(_spec("body", shape, length, BODY_HALF, tone))

    straps = (("riveted", 22), ("double", 32), ("plain", 12),
              ("studded", 26), ("chevron", 20))
    for shape, length in straps:
        for tone in ("mid", "light"):
            specs.append(_spec("strap", shape, length, 30, tone))

    fins = (("swept", 76, 72), ("straight", 68, 66), ("split", 74, 70),
            ("rounded", 78, 76), ("leaf", 64, 64), ("stepped", 72, 74))
    for shape, length, half in fins:
        for tone in ("mid", "light"):
            specs.append(_spec("fin", shape, length, half, tone))

    nozzles = (("bell", 40, 36), ("ribbed", 36, 34), ("straight", 28, 28),
               ("cone", 32, 30), ("stepped", 38, 34))
    for shape, length, half in nozzles:
        for tone in ("mid", "dark"):
            specs.append(_spec("nozzle", shape, length, half, tone))

    flames = (("single", 68, 26), ("triple", 76, 30),
              ("forked", 62, 28), ("twin", 70, 26))
    for shape, length, half in flames:
        specs.append(_spec("flame", shape, length, half, "light"))
    return specs


PARTS = _part_specs()
LIBRARY = {}
for _spec in PARTS:
    LIBRARY.setdefault(_spec["kind"], []).append(_spec)


def _render_part(spec):
    width = spec["length"] + PAD * 2
    height = spec["half"] * 2 + PAD * 2
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.translate(PAD, PAD + spec["half"])
    DRAWERS[spec["kind"]](ctx, spec["shape"], spec["length"], spec["half"],
                          _palette(spec["tone"]))
    return surface


# ---------------------------------------------------------------------------
# Composition: fixed attachment rules, random part choice.

def random_choice(rng):
    """Pick one part from each family; reusable by the game at runtime."""
    return {
        "nose": rng.choice(LIBRARY["nose"]),
        "collar": rng.choice(LIBRARY["collar"]),
        "body": rng.choice(LIBRARY["body"]),
        "strap": rng.choice(LIBRARY["strap"]),
        "strap2": rng.random() < 0.34,
        "fin": rng.choice(LIBRARY["fin"]),
        "nozzle": rng.choice(LIBRARY["nozzle"]),
        "flame": rng.choice(LIBRARY["flame"]) if rng.random() < 0.6 else None,
        "strap_at": rng.uniform(0.34, 0.56),
        "strap2_at": rng.uniform(0.52, 0.64),
    }


def _layout(choice, start):
    """Return (kind, spec, x) placements and the total length."""
    nose, collar, body = choice["nose"], choice["collar"], choice["body"]
    strap, fin, nozzle = choice["strap"], choice["fin"], choice["nozzle"]

    body_x = start + nose["length"] + collar["length"] - 9
    body_end = body_x + body["length"]
    pieces = [
        ("fin", fin, body_end - fin["length"] + 18),
        ("body", body, body_x),
        ("strap", strap, body_x + (body["length"] - strap["length"]) * choice["strap_at"]),
        ("nozzle", nozzle, body_end - 4),
        ("collar", collar, start + nose["length"] - 5),
        ("nose", nose, start),
    ]
    if choice["strap2"]:
        pieces.append(("strap", strap,
                       body_x + (body["length"] - strap["length"]) * choice["strap2_at"]))
    tip = body_end - 4 + nozzle["length"]
    if choice["flame"]:
        pieces.append(("flame", choice["flame"], tip - 6))
        tip = tip - 6 + choice["flame"]["length"]
    draw_order = ["fin", "body", "strap", "nozzle", "collar", "nose", "flame"]
    pieces.sort(key=lambda piece: draw_order.index(piece[0]))
    return pieces, tip - start


def _compose(choice):
    width, height = CANVAS
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    _, total = _layout(choice, 0)
    start = max(6.0, (width - total) / 2)
    pieces, _ = _layout(choice, start)
    for _, spec, x in pieces:
        image = cairo.ImageSurface.create_from_png(str(spec["file"]))
        ctx.set_source_surface(image, x - PAD, AXIS - spec["half"] - PAD)
        ctx.paint()
    return surface


def _choice_record(choice):
    return {key: (value["name"] if isinstance(value, dict) else value)
            for key, value in choice.items()}


def _preview(records, destination, columns=4):
    cell_w, cell_h, gap, label = 320, 110, 14, 20
    rows = math.ceil(len(records) / columns)
    width = gap + columns * (cell_w + gap)
    height = gap + rows * (cell_h + label + gap) + 18
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    for index, record in enumerate(records):
        column, row = index % columns, index // columns
        x = gap + column * (cell_w + gap)
        y = gap + row * (cell_h + label + gap)
        image = cairo.ImageSurface.create_from_png(str(ROCKET_ROOT / record["file"]))
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(cell_w / CANVAS[0], cell_h / CANVAS[1])
        ctx.set_source_surface(image, 0, 0)
        ctx.paint()
        ctx.restore()
        _set(ctx, 60)
        ctx.set_font_size(9)
        ctx.move_to(x, y + cell_h + 12)
        ctx.show_text(Path(record["file"]).stem)
    _set(ctx, 80)
    ctx.set_font_size(10)
    ctx.move_to(gap, height - 8)
    ctx.show_text("Greyscale modular rockets - every part is a separate PNG in parts/")
    surface.write_to_png(str(destination))


def _write_manifest(specs, records):
    part_index = {}
    for spec in specs:
        part_index.setdefault(spec["kind"], []).append({
            "name": spec["name"],
            "shape": spec["shape"],
            "tone": spec["tone"],
            "file": str(spec["file"].relative_to(ROCKET_ROOT)),
            "length": spec["length"],
            "half_height": spec["half"],
        })
    (ROCKET_ROOT / "parts.json").write_text(json.dumps({
        "axis": AXIS,
        "canvas": list(CANVAS),
        "greyscale": True,
        "parts": part_index,
    }, indent=2) + "\n", encoding="utf-8")
    (ROCKET_ROOT / "variants.json").write_text(json.dumps(records, indent=2) + "\n",
                                               encoding="utf-8")


def generate(force=False, variants=24, seed="20261116", quiet=False):
    written = []
    known = {spec["file"] for spec in PARTS}
    for stale in PART_ROOT.rglob("*.png") if PART_ROOT.is_dir() else ():
        if stale not in known:
            stale.unlink()
    for spec in PARTS:
        spec["file"].parent.mkdir(parents=True, exist_ok=True)
        if force or not spec["file"].is_file():
            _render_part(spec).write_to_png(str(spec["file"]))
            if not quiet:
                print(f"{spec['file']}  {spec['file'].stat().st_size:,} bytes")

    VARIANT_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(variants):
        choice = random_choice(random.Random(f"{seed}-{index}"))
        destination = VARIANT_ROOT / f"rocket-{index + 1:02d}.png"
        _compose(choice).write_to_png(str(destination))
        written.append(destination)
        records.append({"file": str(destination.relative_to(ROCKET_ROOT)),
                        "parts": _choice_record(choice)})

    _write_manifest(PARTS, records)
    preview = ROCKET_ROOT / "preview.png"
    _preview(records, preview)
    written.append(preview)
    return written, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-render the whole part library as well as variants")
    parser.add_argument("--variants", type=int, default=24,
                        help="number of composed rocket samples (default 24)")
    parser.add_argument("--seed", default="20261116",
                        help="seed for the sample composition (default 20261116)")
    parser.add_argument("--quiet", action="store_true",
                        help="only print the final summary")
    args = parser.parse_args(argv)
    if args.variants < 1:
        parser.error("--variants must be at least 1")
    _, records = generate(force=args.force, variants=args.variants,
                          seed=args.seed, quiet=args.quiet)
    print(f"Rocket assets ready: {len(PARTS)} parts in {len(LIBRARY)} categories, "
          f"{len(records)} variants; {ROCKET_ROOT / 'preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
