"""Generate ECHO's modular greyscale tower-crane obstacles with Cairo.

Usage: .venv-echo/bin/python -m echo_game.generate_cranes [--force]
           [--variants 24] [--seed 20261116]

A tower crane is assembled from independent parts the way a real crane is
bolted together: a concrete footing, a stack of lattice mast sections, a
slewing unit, an operator cab, a tower head (apex), a jib, a counter-jib, a
counterweight and a hoist block. Every shape variant has a different
silhouette and every part is built from several primitives (posts, chords,
braces, plates, rings, bolts), so a randomizer can mix shapes and tones
freely. Pixels are greyscale only, so the game can tint any part at runtime
with a seeded colour (pygame.BLEND_MULT), exactly like the rocket and block
libraries. No display, mixer or network access.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import cairo

CRANE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "obstacle" / "cranes"
PART_ROOT = CRANE_ROOT / "parts"
VARIANT_ROOT = CRANE_ROOT / "variants"
CANVAS = (660, 640)
GROUND = 26
PAD = 10
OUTLINE = 44.0
TONES = {"dark": 0.83, "mid": 1.0, "light": 1.17}


# ---------------------------------------------------------------------------
# Small drawing helpers shared by every part.
def _gray(value, alpha=1.0):
    v = max(0, min(255, value)) / 255.0
    return (v, v, v, alpha)


def _set(ctx, value, alpha=1.0):
    ctx.set_source_rgba(*_gray(value, alpha))


def _palette(tone):
    mid = 152.0 * TONES[tone]
    return (min(246.0, mid + 58), mid, max(58.0, mid - 54))


def _vgrad(ctx, height, pal):
    light, mid, dark = pal
    gradient = cairo.LinearGradient(0, 0, 0, height)
    for stop, value in ((0.0, light), (0.55, mid), (1.0, dark)):
        v = value / 255.0
        gradient.add_color_stop_rgb(stop, v, v, v)
    ctx.set_source(gradient)


def _hgrad(ctx, width, pal):
    light, mid, dark = pal
    gradient = cairo.LinearGradient(0, 0, width, 0)
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


def _line(ctx, x0, y0, x1, y1):
    ctx.move_to(x0, y0)
    ctx.line_to(x1, y1)


def _dots(ctx, positions, radius=2.0, value=58, alpha=.75):
    _set(ctx, value, alpha)
    for x, y in positions:
        ctx.new_path()
        ctx.arc(x, y, radius, 0, math.tau)
        ctx.fill()


def _panel(ctx, w, h, value=238, alpha=.24):
    """Light backing plate behind a lattice, so braces read as steel."""
    _set(ctx, value, alpha)
    _rect(ctx, 0, 0, w, h)
    ctx.fill()


# ---------------------------------------------------------------------------
# Footing: concrete slab, separate pads, steel grillage, stepped plinth.
def _draw_base(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "slab":
        _poly(ctx, [(7, 0), (w - 7, 0), (w, h), (0, h)])
        _vgrad(ctx, h, pal)
        ctx.fill_preserve()
        ctx.save()
        _poly(ctx, [(7, 0), (w - 7, 0), (w, h), (0, h)])
        ctx.clip()
        _rect(ctx, 0, 0, w, 7)
        _set(ctx, light, .28)
        ctx.fill()
        _rect(ctx, 0, h - 8, w, h)
        _set(ctx, dark, .30)
        ctx.fill()
        _set(ctx, dark, .35)
        ctx.set_line_width(2.0)
        _line(ctx, w * .30, 8, w * .20, h)
        _line(ctx, w * .66, 8, w * .74, h)
        ctx.stroke()
        _dots(ctx, [(8 + i * 16, 9) for i in range(int(w - 16) // 16)], 1.9)
        ctx.restore()
        _poly(ctx, [(7, 0), (w - 7, 0), (w, h), (0, h)])
        _outline(ctx)
    elif shape == "pads":
        gap = 10
        pad_w = (w - gap * 3) / 4
        for i in range(4):
            x0 = i * (pad_w + gap)
            _poly(ctx, [(x0 + 3, 0), (x0 + pad_w - 3, 0), (x0 + pad_w, h),
                        (x0, h)])
            _vgrad(ctx, h, pal)
            ctx.fill_preserve()
            _set(ctx, dark, .30)
            _rect(ctx, x0, h - 7, x0 + pad_w, h)
            ctx.fill()
            _poly(ctx, [(x0 + 3, 0), (x0 + pad_w - 3, 0), (x0 + pad_w, h), (x0, h)])
            _outline(ctx, 3.0)
        _rect(ctx, 0, 3, w, 11)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, 0, 3, w, 11)
        _outline(ctx, 3.2)
    elif shape == "grillage":
        _rect(ctx, 0, 0, w, 9)
        _hgrad(ctx, w, pal)
        ctx.fill()
        _rect(ctx, 0, 0, w, 9)
        _outline(ctx, 3.2)
        for x in (w * .10, w * .34, w * .58, w * .82):
            _rect(ctx, x, 9, x + 12, h)
            _vgrad(ctx, h, pal)
            ctx.fill()
            _rect(ctx, x, 9, x + 12, h)
            _outline(ctx, 3.0)
        _rect(ctx, 0, h - 8, w, h)
        _set(ctx, dark, .55)
        ctx.fill()
    else:  # plinth, stepped concrete block
        levels = ((0, w, h * .46), (w * .10, w * .90, h * .30),
                  (w * .22, w * .78, h * .24))
        y = 0
        for x0, x1, height in levels:
            _rect(ctx, x0, y, x1, y + height)
            _vgrad(ctx, h, pal)
            ctx.fill()
            _rect(ctx, x0, y, x1, y + height)
            _outline(ctx, 3.4)
            y += height
        _dots(ctx, [(w * .5 - 12, h * .70), (w * .5 + 12, h * .70)],
              2.2, value=40)


# ---------------------------------------------------------------------------
# Mast sections: square lattice, X-braced, diamond, ladder, tubular.
def _draw_mast(ctx, shape, w, h, pal):
    light, mid, dark = pal
    frame = 8.0
    if shape == "tubular":
        _round_rect(ctx, 0, 0, w, h, 9)
        _hgrad(ctx, w, pal)
        ctx.fill_preserve()
        ctx.save()
        _round_rect(ctx, 0, 0, w, h, 9)
        ctx.clip()
        # One flange top and bottom like a bolted tube column, then a weld
        # seam and a ladder strip so it is not just a plain pipe.
        for y in (0, h - 7):
            _rect(ctx, -1, y, w + 1, y + 7)
            _set(ctx, light, .38)
            ctx.fill()
            _set(ctx, dark, .6)
            ctx.set_line_width(1.8)
            _line(ctx, 0, y + 7, w, y + 7)
            ctx.stroke()
        _set(ctx, dark, .30)
        ctx.set_line_width(2.2)
        _line(ctx, w * .5, 10, w * .5, h - 10)
        ctx.stroke()
        _rect(ctx, 0, 0, w * .26, h)
        _set(ctx, light, .26)
        ctx.fill()
        _dots(ctx, [(w * .5, y) for y in range(16, int(h) - 6, 20)], 1.9)
        _dots(ctx, [(w * .14, y) for y in range(16, int(h) - 6, 20)], 1.7,
              alpha=.45)
        ctx.restore()
        _round_rect(ctx, 0, 0, w, h, 9)
        _outline(ctx)
        return

    _panel(ctx, w, h)
    for x0 in (0, w - frame):
        _rect(ctx, x0, 0, x0 + frame, h)
        _hgrad(ctx, w, pal)
        ctx.fill()
        _rect(ctx, x0, 0, x0 + frame, h)
        _outline(ctx, 2.6)
    cells = 4
    step = h / cells
    _set(ctx, dark, .88)
    ctx.set_line_width(3.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(cells):
        y0, y1 = i * step, (i + 1) * step
        if shape in ("square", "ladder"):
            _line(ctx, frame, y1, w - frame, y1)
        if shape in ("square", "xbrace"):
            _line(ctx, frame, y0, w - frame, y1)
            _line(ctx, w - frame, y0, frame, y1)
        elif shape == "diamond":
            _line(ctx, frame, y0, w - frame, y1)
    ctx.stroke()
    # Bolt plates at the section ends: two joined primitives, not one box.
    for y0 in (h - 3, 0):
        _rect(ctx, frame - 2, y0, w - frame + 2, y0 + 6)
        _set(ctx, 74, .5)
        ctx.fill()
    _rect(ctx, 0, 0, w, h)
    _outline(ctx, 3.8)


# ---------------------------------------------------------------------------
# Slewing unit: ring, machined box, toothed gear ring.
def _draw_slew(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "toothed":
        _poly(ctx, [(0, 0), (w, 0), (w, h - 6), (w - 5, h), (5, h), (0, h - 6)])
        _hgrad(ctx, w, pal)
        ctx.fill_preserve()
        ctx.save()
        _poly(ctx, [(0, 0), (w, 0), (w, h - 6), (w - 5, h), (5, h), (0, h - 6)])
        ctx.clip()
        _set(ctx, dark, .45)
        for x in range(6, int(w) - 4, 10):
            _poly(ctx, [(x, h - 6), (x + 5, h - 1), (x + 5, h), (x, h)])
            ctx.fill()
        ctx.restore()
        _poly(ctx, [(0, 0), (w, 0), (w, h - 6), (w - 5, h), (5, h), (0, h - 6)])
        _outline(ctx, 3.4)
    else:
        _round_rect(ctx, 0, 0, w, h, 6 if shape == "ring" else 2)
        _hgrad(ctx, w, pal)
        ctx.fill_preserve()
        ctx.save()
        _round_rect(ctx, 0, 0, w, h, 6 if shape == "ring" else 2)
        ctx.clip()
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, light, .35)
        ctx.fill()
        _rect(ctx, 0, h - 6, w, h)
        _set(ctx, dark, .40)
        ctx.fill()
        if shape == "ring":
            _dots(ctx, [(x, h * .5) for x in range(9, int(w) - 4, 11)], 1.9)
        else:
            _set(ctx, dark, .38)
            ctx.set_line_width(2.0)
            for x in (w * .25, w * .5, w * .75):
                _line(ctx, x, 4, x, h - 4)
            ctx.stroke()
        ctx.restore()
        _round_rect(ctx, 0, 0, w, h, 6 if shape == "ring" else 2)
        _outline(ctx, 3.4)


# ---------------------------------------------------------------------------
# Operator cab: box, rounded, slanted glass, small hut with overhang.
def _draw_cab(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "slanted":
        body = [(0, h), (0, h * .34), (w * .30, 0), (w, 0), (w, h)]
    elif shape == "rounded":
        _round_rect(ctx, 0, 0, w, h, 9)
        body = None
    else:
        body = [(0, 0), (w, 0), (w, h), (0, h)]

    if body:
        _poly(ctx, body)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    if body:
        _poly(ctx, body)
    else:
        _round_rect(ctx, 0, 0, w, h, 9)
    ctx.clip()
    # Glass: a band across the front, plus a mullion.
    _rect(ctx, w * .14, h * .18, w * .86, h * .58)
    _set(ctx, 232, .82)
    ctx.fill()
    _set(ctx, 96, .9)
    ctx.set_line_width(1.8)
    _line(ctx, w * .46, h * .18, w * .46, h * .58)
    ctx.stroke()
    _rect(ctx, 0, h * .66, w, h)
    _set(ctx, 118, .95)
    ctx.fill()
    _set(ctx, 72, .5)
    ctx.set_line_width(2.0)
    _line(ctx, w * .56, h * .70, w * .56, h)
    ctx.stroke()
    _rect(ctx, 0, 0, w, 5)
    _set(ctx, light, .40)
    ctx.fill()
    ctx.restore()

    if body:
        _poly(ctx, body)
    else:
        _round_rect(ctx, 0, 0, w, h, 9)
    _outline(ctx, 3.6)
    # Roof plate: the cab is a body plus a bolted lid.
    _rect(ctx, -3, -4, w + 3, 4)
    _set(ctx, mid, .95)
    ctx.fill()
    _rect(ctx, -3, -4, w + 3, 4)
    _outline(ctx, 3.0)
    if shape == "hut":
        _rect(ctx, -6, -9, w + 2, -4)
        _set(ctx, light, .9)
        ctx.fill()
        _rect(ctx, -6, -9, w + 2, -4)
        _outline(ctx, 2.8)


# ---------------------------------------------------------------------------
# Tower head: pyramid truss, cage, spike with sheave, tripod.
def _draw_apex(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "pyramid":
        _poly(ctx, [(0, h), (w * .5, 0), (w, h)])
    elif shape == "cage":
        _poly(ctx, [(0, h), (w * .26, 0), (w * .74, 0), (w, h)])
    elif shape == "spike":
        _poly(ctx, [(0, h), (w * .34, 6), (w * .5, 0), (w * .66, 6), (w, h)])
    else:  # tripod
        _poly(ctx, [(0, h), (w * .22, 0), (w * .78, 0), (w, h)])
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    if shape == "pyramid":
        _poly(ctx, [(0, h), (w * .5, 0), (w, h)])
    elif shape == "cage":
        _poly(ctx, [(0, h), (w * .26, 0), (w * .74, 0), (w, h)])
    elif shape == "spike":
        _poly(ctx, [(0, h), (w * .34, 6), (w * .5, 0), (w * .66, 6), (w, h)])
    else:
        _poly(ctx, [(0, h), (w * .22, 0), (w * .78, 0), (w, h)])
    ctx.clip()
    _set(ctx, dark, .80)
    ctx.set_line_width(3.0)
    rows = 4
    for i in range(1, rows):
        y = h - i * h / rows
        span = (h - y) / h
        _line(ctx, w * .5 - span * w * .5 + 3, y,
              w * .5 + span * w * .5 - 3, y)
    if shape == "cage":
        for x in (w * .5,):
            _line(ctx, x, 10, x, h - 2)
    for sign in (-1, 1):
        _line(ctx, w * .5, h * .12, w * .5 + sign * w * .40, h * .92)
    ctx.stroke()
    ctx.restore()
    if shape == "pyramid":
        _poly(ctx, [(0, h), (w * .5, 0), (w, h)])
    elif shape == "cage":
        _poly(ctx, [(0, h), (w * .26, 0), (w * .74, 0), (w, h)])
    elif shape == "spike":
        _poly(ctx, [(0, h), (w * .34, 6), (w * .5, 0), (w * .66, 6), (w, h)])
    else:
        _poly(ctx, [(0, h), (w * .22, 0), (w * .78, 0), (w, h)])
    _outline(ctx, 3.6)
    # Head sheave: two circles with a pin, sitting on the crown.
    top = 10 if shape != "pyramid" else h * .16
    cx = w * .5
    ctx.new_path()
    ctx.arc(cx, top, 8.5, 0, math.tau)
    _set(ctx, mid, 1.0)
    ctx.fill_preserve()
    _outline(ctx, 2.6)
    _dots(ctx, [(cx, top)], 2.4, value=52)
    _rect(ctx, cx - 2, h - 9, cx + 2, h)
    _set(ctx, dark, .5)
    ctx.fill()


# ---------------------------------------------------------------------------
# Jib: triangular truss, tapered truss, parallel-chord truss, plate girder.
def _draw_jib(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "plate":
        body = [(0, 0), (w - 14, 0), (w, h * .5), (w - 14, h), (0, h)]
    elif shape == "tapered":
        body = [(0, 0), (w * .34, h * .34), (w, h * .66), (w, h), (0, h)]
    else:
        body = [(0, 0), (w, 0), (w, h), (0, h)]
    _poly(ctx, body)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    _poly(ctx, body)
    ctx.clip()
    if shape == "plate":
        _panel(ctx, w, h, value=228, alpha=.20)
        _set(ctx, dark, .40)
        ctx.set_line_width(2.2)
        for x in range(26, int(w) - 10, 34):
            _line(ctx, x, 3, x, h - 3)
        ctx.stroke()
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, light, .32)
        ctx.fill()
        _rect(ctx, 0, h - 5, w, h)
        _set(ctx, dark, .34)
        ctx.fill()
    else:
        _panel(ctx, w, h)
        # Chords: bottom and top flange, filled as separate strips.
        for y0 in (0, h - 7):
            _rect(ctx, 0, y0, w, y0 + 7)
            _hgrad(ctx, w, pal)
            ctx.fill()
        _set(ctx, dark, .82)
        ctx.set_line_width(2.8)
        step = 26
        for x in range(0, int(w) - step, step):
            _line(ctx, x, h - 6, x + step, 6)
            _line(ctx, x, 6, x, h - 6)
        ctx.stroke()
        if shape != "tapered":
            _rect(ctx, 0, h * .5 - 2, w, h * .5 + 2)
            _set(ctx, dark, .35)
            ctx.fill()
    ctx.restore()
    _poly(ctx, body)
    _outline(ctx, 3.6)
    # Tip plate at the free end, always drawn as an extra primitive.
    _rect(ctx, w - 10, 2, w, h - 2)
    _set(ctx, dark, .45)
    ctx.fill()
    _rect(ctx, w - 10, 2, w, h - 2)
    _outline(ctx, 2.4)


# ---------------------------------------------------------------------------
# Counter-jib: lattice arm, railed walkway, boxed arm.
def _draw_counterjib(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "boxed":
        body = [(0, 0), (w, 0), (w, h), (0, h)]
    else:
        body = [(0, 0), (w, 0), (w, h), (0, h)]
    _poly(ctx, body)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    _poly(ctx, body)
    ctx.clip()
    if shape == "walkway":
        _panel(ctx, w, h, alpha=.26)
        _rect(ctx, 0, h - 9, w, h)
        _set(ctx, 132, 1.0)
        ctx.fill()
        _set(ctx, dark, .85)
        ctx.set_line_width(2.4)
        for x in range(8, int(w) - 4, 18):
            _line(ctx, x, 2, x, h - 9)
        _line(ctx, 0, 3, w, 3)
        ctx.stroke()
    elif shape == "boxed":
        _set(ctx, dark, .42)
        ctx.set_line_width(2.2)
        for x in range(20, int(w) - 8, 30):
            _line(ctx, x, 3, x, h - 3)
        ctx.stroke()
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, light, .30)
        ctx.fill()
    else:
        _panel(ctx, w, h)
        for y0 in (0, h - 7):
            _rect(ctx, 0, y0, w, y0 + 7)
            _hgrad(ctx, w, pal)
            ctx.fill()
        _set(ctx, dark, .82)
        ctx.set_line_width(2.6)
        step = 24
        for x in range(0, int(w) - step, step):
            _line(ctx, x, h - 6, x + step, 6)
            _line(ctx, x, 6, x, h - 6)
        ctx.stroke()
    ctx.restore()
    _poly(ctx, body)
    _outline(ctx, 3.6)


# ---------------------------------------------------------------------------
# Counterweight: single slab, stack, ribbed block, hollow frame.
def _draw_cw(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "stack":
        blocks = 3
        for i in range(blocks):
            y0 = i * h / blocks
            y1 = y0 + h / blocks - 3
            _rect(ctx, 0, y0, w, y1)
            _vgrad(ctx, h, pal)
            ctx.fill()
            _rect(ctx, 0, y0, w, y1)
            _outline(ctx, 2.8)
            _dots(ctx, [(w * .5 - 12, y0 + 6), (w * .5 + 12, y0 + 6)], 1.8,
                  alpha=.6)
        _rect(ctx, 3, 0, 7, h - 3)
        _set(ctx, dark, .45)
        ctx.fill()
        return
    if shape == "frame":
        _panel(ctx, w, h, alpha=.30)
        _rect(ctx, 0, 0, w, 8)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, 0, h - 9, w, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, 0, 0, 8, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w - 8, 0, w, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _set(ctx, dark, .55)
        ctx.set_line_width(2.4)
        _line(ctx, 6, 6, w - 6, h - 6)
        _line(ctx, w - 6, 6, 6, h - 6)
        ctx.stroke()
        _rect(ctx, 0, 0, w, h)
        _outline(ctx, 3.4)
        return

    _poly(ctx, [(0, 0), (w, 0), (w, h), (0, h)])
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    _rect(ctx, 0, 0, w, h)
    ctx.clip()
    if shape == "ribbed":
        _set(ctx, light, .26)
        for x in range(7, int(w) - 6, 13):
            _rect(ctx, x, 4, x + 6, h - 4)
            ctx.fill()
        _set(ctx, dark, .40)
        ctx.set_line_width(1.6)
        for x in range(13, int(w) - 6, 13):
            _line(ctx, x, 4, x, h - 4)
        ctx.stroke()
    _rect(ctx, 0, h - 7, w, h)
    _set(ctx, dark, .32)
    ctx.fill()
    _dots(ctx, [(w * .5 - 14, h * .22), (w * .5 + 14, h * .22)], 2.0)
    # Lifting eye: an arc that makes the weight read as a cast block.
    ctx.new_path()
    ctx.arc(w * .5, h * .10, 7.5, math.pi, math.tau)
    _set(ctx, 92, .9)
    ctx.set_line_width(3.0)
    ctx.stroke()
    ctx.restore()
    _rect(ctx, 0, 0, w, h)
    _outline(ctx, 3.4)


# ---------------------------------------------------------------------------
# Hoist: single sheave block, double sheave, open hook, spreader beam.
def _draw_hoist(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "clamp":
        _rect(ctx, 0, 0, w, 10)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, 0, 0, w, 10)
        _outline(ctx, 3.0)
        for x in (w * .22, w * .78):
            _rect(ctx, x - 3, 8, x + 3, h * .62)
            _set(ctx, 138, 1.0)
            ctx.fill()
            _rect(ctx, x - 3, 8, x + 3, h * .62)
            _outline(ctx, 2.2)
            ctx.new_path()
            ctx.arc(x, h * .74, 7, math.pi * .1, math.pi * .9)
            _set(ctx, 96, .95)
            ctx.set_line_width(3.4)
            ctx.stroke()
        _rect(ctx, w * .5 - 2, 0, w * .5 + 2, -6)
        _set(ctx, dark, .7)
        ctx.fill()
        return

    if shape == "hook":
        _rect(ctx, w * .5 - 4, 0, w * .5 + 4, 12)
        _set(ctx, 122, 1.0)
        ctx.fill()
        _rect(ctx, w * .5 - 4, 0, w * .5 + 4, 12)
        _outline(ctx, 2.4)
        ctx.new_path()
        ctx.arc(w * .5, h * .58, w * .34, -math.pi * .15, math.pi * 1.25)
        _set(ctx, 108, 1.0)
        ctx.set_line_width(9.0)
        ctx.stroke_preserve()
        _outline(ctx, 11.0, alpha=.55, value=30)
        _set(ctx, 158, 1.0)
        ctx.set_line_width(6.0)
        ctx.stroke()
        _dots(ctx, [(w * .5, 12)], 3.0)
        return

    sheaves = 2 if shape == "double" else 1
    body_h = h * .62
    _round_rect(ctx, 0, 0, w, body_h, 5)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    _round_rect(ctx, 0, 0, w, body_h, 5)
    _outline(ctx, 3.2)
    for i in range(sheaves):
        cx = w * .5 + (i - (sheaves - 1) / 2) * (w * .40)
        cy = body_h * .48
        radius = min(w * .22, body_h * .34)
        ctx.new_path()
        ctx.arc(cx, cy, radius, 0, math.tau)
        _set(ctx, 196, 1.0)
        ctx.fill_preserve()
        _outline(ctx, 2.4)
        _dots(ctx, [(cx, cy)], 2.4, value=48)
    # Cheek plate plus a shackle, so the block is clearly several primitives.
    _rect(ctx, 0, body_h - 6, w, body_h)
    _set(ctx, dark, .34)
    ctx.fill()
    _rect(ctx, w * .5 - 6, -8, w * .5 + 6, 1)
    _set(ctx, mid, .95)
    ctx.fill()
    _rect(ctx, w * .5 - 6, -8, w * .5 + 6, 1)
    _outline(ctx, 2.2)
    if shape == "block":
        ctx.new_path()
        ctx.arc(w * .5, body_h + 10, 9, math.pi * .15, math.pi * 1.05)
        _set(ctx, 112, 1.0)
        ctx.set_line_width(5.0)
        ctx.stroke()
        _outline(ctx, 6.0, alpha=.5, value=30)
    else:
        _rect(ctx, w * .5 - 4, body_h, w * .5 + 4, h - 2)
        _set(ctx, 140, 1.0)
        ctx.fill()
        _rect(ctx, w * .5 - 4, body_h, w * .5 + 4, h - 2)
        _outline(ctx, 2.2)


DRAWERS = {
    "base": _draw_base,
    "mast": _draw_mast,
    "slew": _draw_slew,
    "cab": _draw_cab,
    "apex": _draw_apex,
    "jib": _draw_jib,
    "counterjib": _draw_counterjib,
    "counterweight": _draw_cw,
    "hoist": _draw_hoist,
}

# Where the composer attaches each part, as a fraction/offset of the part box.
# base: top centre, mast/slew/apex: bottom centre, cab/jib: bottom left,
# counterjib: bottom right, counterweight/hoist: top centre.
ORIGINS = {
    "base": lambda w, h: (w / 2, 0.0),
    "mast": lambda w, h: (w / 2, h),
    "slew": lambda w, h: (w / 2, h),
    "cab": lambda w, h: (0.0, 0.0),
    "apex": lambda w, h: (w / 2, h),
    "jib": lambda w, h: (0.0, h),
    "counterjib": lambda w, h: (w, h),
    "counterweight": lambda w, h: (w / 2, 0.0),
    "hoist": lambda w, h: (w / 2, 0.0),
}


# ---------------------------------------------------------------------------
# Library definition. Shapes differ in silhouette, tone only changes value.
def _spec(kind, shape, w, h, tone):
    ox, oy = ORIGINS[kind](w, h)
    return dict(kind=kind, shape=shape, w=float(w), h=float(h), tone=tone,
                origin=(ox, oy), name=f"{shape}_{tone}",
                file=PART_ROOT / kind / f"{shape}_{tone}.png")


def _part_specs():
    specs = []
    bases = (("slab", 150, 34), ("pads", 156, 30),
             ("grillage", 140, 32), ("plinth", 116, 42))
    for shape, w, h in bases:
        for tone in ("mid", "light"):
            specs.append(_spec("base", shape, w, h, tone))

    for shape in ("square", "xbrace", "diamond", "ladder", "tubular"):
        for tone in ("mid", "dark"):
            specs.append(_spec("mast", shape, 58, 100, tone))

    for shape in ("ring", "box", "toothed"):
        for tone in ("mid", "dark"):
            specs.append(_spec("slew", shape, 68, 22, tone))

    cabs = (("box", 54, 42), ("rounded", 52, 40),
            ("slanted", 58, 44), ("hut", 56, 46))
    for shape, w, h in cabs:
        for tone in ("mid", "light"):
            specs.append(_spec("cab", shape, w, h, tone))

    apexes = (("pyramid", 48, 66), ("cage", 42, 60),
              ("spike", 30, 74), ("tripod", 46, 56))
    for shape, w, h in apexes:
        for tone in ("mid", "dark"):
            specs.append(_spec("apex", shape, w, h, tone))

    jibs = (("lattice", 340, 30), ("tapered", 300, 34),
            ("parallel", 320, 28), ("plate", 286, 26))
    for shape, w, h in jibs:
        for tone in ("mid", "dark"):
            specs.append(_spec("jib", shape, w, h, tone))

    cjs = (("lattice", 152, 26), ("walkway", 140, 30), ("boxed", 132, 26))
    for shape, w, h in cjs:
        for tone in ("mid", "light"):
            specs.append(_spec("counterjib", shape, w, h, tone))

    cws = (("slab", 58, 46), ("stack", 54, 64),
           ("ribbed", 56, 52), ("frame", 54, 50))
    for shape, w, h in cws:
        for tone in ("dark", "mid"):
            specs.append(_spec("counterweight", shape, w, h, tone))

    hoists = (("block", 30, 36), ("double", 36, 42),
              ("hook", 26, 46), ("clamp", 50, 32))
    for shape, w, h in hoists:
        for tone in ("dark", "mid"):
            specs.append(_spec("hoist", shape, w, h, tone))
    return specs


PARTS = _part_specs()
LIBRARY = {}
for _spec_entry in PARTS:
    LIBRARY.setdefault(_spec_entry["kind"], []).append(_spec_entry)


def _render_part(spec):
    width = int(round(spec["w"])) + PAD * 2
    height = int(round(spec["h"])) + PAD * 2
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.translate(PAD, PAD)
    DRAWERS[spec["kind"]](ctx, spec["shape"], spec["w"], spec["h"],
                          _palette(spec["tone"]))
    return surface


# ---------------------------------------------------------------------------
# Composition: real crane topology, random part choice.
def random_choice(rng):
    """Pick one part from each family; reusable by the game at runtime."""
    return {
        "base": rng.choice(LIBRARY["base"]),
        "mast": rng.choice(LIBRARY["mast"]),
        "mast_sections": rng.randint(3, 4),
        "slew": rng.choice(LIBRARY["slew"]),
        "cab": rng.choice(LIBRARY["cab"]) if rng.random() < 0.85 else None,
        "apex": rng.choice(LIBRARY["apex"]),
        "jib": rng.choice(LIBRARY["jib"]),
        "counterjib": rng.choice(LIBRARY["counterjib"]),
        "counterweight": rng.choice(LIBRARY["counterweight"]),
        "hoist": rng.choice(LIBRARY["hoist"]),
        "hoist_at": rng.uniform(0.28, 0.72),
        "hoist_drop": rng.uniform(52, 150),
        "pendant": rng.choice(("single", "double", "truss")),
        "section_h": rng.uniform(92, 108),
    }


def _layout(choice):
    """Return (kind, spec, x, y) placements plus the anchors the cables need."""
    base, mast = choice["base"], choice["mast"]
    slew, apex = choice["slew"], choice["apex"]
    jib, cj = choice["jib"], choice["counterjib"]
    cw, hoist, cab = choice["counterweight"], choice["hoist"], choice["cab"]

    width, height = CANVAS
    ground = height - GROUND
    mast_h = choice["section_h"] * choice["mast_sections"]
    base_top = ground - base["h"]
    mast_bottom = base_top
    slew_bottom = mast_bottom - mast_h
    slew_top = slew_bottom - slew["h"]
    jib_bottom = slew_top

    left = cj["w"] - 16
    right = jib["w"] - 16
    cx = max(28.0, (width - (left + right)) / 2) + left

    pieces = [
        ("base", base, cx, base_top),
        ("mast", mast, cx, mast_bottom),
        ("mast", mast, cx, mast_bottom - choice["section_h"]),
        ("mast", mast, cx, mast_bottom - choice["section_h"] * 2),
        ("mast", mast, cx, mast_bottom - choice["section_h"] * 3),
    ]
    if choice["mast_sections"] > 4:
        pieces.append(("mast", mast, cx, mast_bottom - choice["section_h"] * 4))
    pieces += [
        ("slew", slew, cx, slew_bottom),
        ("counterjib", cj, cx + 16, slew_top),
        ("jib", jib, cx - 16, slew_top),
        ("apex", apex, cx, slew_top),
    ]
    if cab:
        pieces.append(("cab", cab, cx + mast["w"] / 2 - 10, slew_top + 1))

    cj_left = cx + 16 - cj["w"]
    pieces.append(("counterweight", cw, cj_left + cw["w"] / 2 + 8,
                   slew_top + 2))

    hoist_x = (cx - 16) + jib["w"] * choice["hoist_at"]
    hoist_y = jib_bottom + choice["hoist_drop"]
    pieces.append(("hoist", hoist, hoist_x, hoist_y))

    order = ["base", "mast", "slew", "counterjib", "counterweight", "cab",
             "jib", "apex", "hoist"]
    pieces.sort(key=lambda piece: order.index(piece[0]))
    anchors = {
        "cx": cx,
        "apex_top": slew_top - apex["h"] + (10 if apex["shape"] != "pyramid"
                                            else apex["h"] * .16),
        "jib_x0": cx - 16,
        "jib_top": jib_bottom - jib["h"],
        "jib_len": jib["w"],
        "cj_left": cj_left,
        "cj_top": jib_bottom - cj["h"],
        "cj_len": cj["w"],
        "hoist_x": hoist_x,
        "hoist_y": hoist_y,
        "jib_bottom": jib_bottom,
    }
    return pieces, anchors


def _draw_pendants(ctx, anchors, style):
    """Pendant tie bars: 1, 2 or 3 lines drawn between the same two points."""
    x_top, y_top = anchors["cx"], anchors["apex_top"]
    targets = (
        (anchors["jib_x0"] + anchors["jib_len"] * .72,
         anchors["jib_top"] + 7),
        (anchors["cj_left"] + anchors["cj_len"] * .20,
         anchors["cj_top"] + 7),
    )
    offsets = {"single": (0.0,), "double": (-2.2, 2.2),
               "truss": (-3.4, 0.0, 3.4)}[style]
    _set(ctx, 68, .92)
    ctx.set_line_width(2.6 if style == "single" else 2.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for tx, ty in targets:
        for offset in offsets:
            _line(ctx, x_top, y_top + offset, tx, ty + offset)
    ctx.stroke()
    if style == "truss":
        _set(ctx, 62, .85)
        ctx.set_line_width(1.8)
        for tx, ty in targets:
            length = math.hypot(tx - x_top, ty - y_top)
            steps = max(4, int(length // 16))
            for i in range(steps):
                t0, t1 = i / steps, (i + 1) / steps
                xa = x_top + (tx - x_top) * t0
                ya = y_top + (ty - y_top) * t0
                xb = x_top + (tx - x_top) * t1
                yb = y_top + (ty - y_top) * t1
                _line(ctx, xa, ya - 3.4, xb, yb + 3.4)
            ctx.stroke()


def _compose(choice):
    width, height = CANVAS
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    pieces, anchors = _layout(choice)
    _draw_pendants(ctx, anchors, choice["pendant"])

    for _, spec, x, y in pieces:
        image = cairo.ImageSurface.create_from_png(str(spec["file"]))
        ox, oy = spec["origin"]
        ctx.set_source_surface(image, x - ox - PAD, y - oy - PAD)
        ctx.paint()

    # Hoist rope and trolley: geometry that depends on the variant, so it is
    # drawn by the composer instead of being baked into a fixed PNG.
    rope_x = anchors["hoist_x"]
    _set(ctx, 58, .92)
    ctx.set_line_width(2.4)
    _line(ctx, rope_x, anchors["jib_bottom"], rope_x, anchors["hoist_y"])
    ctx.stroke()
    _round_rect(ctx, rope_x - 11, anchors["jib_bottom"] - 7,
                rope_x + 11, anchors["jib_bottom"] + 3, 3)
    _set(ctx, 96, 1.0)
    ctx.fill_preserve()
    _outline(ctx, 2.4, alpha=.85, value=40)
    return surface


def _choice_record(choice):
    record = {}
    for key, value in choice.items():
        if isinstance(value, dict):
            record[key] = value["name"]
        elif isinstance(value, float):
            record[key] = round(value, 2)
        else:
            record[key] = value
    return record


def _preview(records, destination, columns=4):
    cell_w, cell_h, gap, label = 300, 292, 14, 20
    rows = math.ceil(len(records) / columns)
    width = gap + columns * (cell_w + gap)
    height = gap + rows * (cell_h + label + gap) + 18
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    for index, record in enumerate(records):
        column, row = index % columns, index // columns
        x = gap + column * (cell_w + gap)
        y = gap + row * (cell_h + label + gap)
        image = cairo.ImageSurface.create_from_png(str(CRANE_ROOT / record["file"]))
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
    ctx.show_text("Greyscale modular tower cranes - every part is a separate PNG in parts/")
    surface.write_to_png(str(destination))


def _write_manifest(specs, records):
    part_index = {}
    for spec in specs:
        part_index.setdefault(spec["kind"], []).append({
            "name": spec["name"],
            "shape": spec["shape"],
            "tone": spec["tone"],
            "file": str(spec["file"].relative_to(CRANE_ROOT)),
            "width": spec["w"],
            "height": spec["h"],
            "origin": [spec["origin"][0], spec["origin"][1]],
        })
    (CRANE_ROOT / "parts.json").write_text(json.dumps({
        "canvas": list(CANVAS),
        "ground_y": CANVAS[1] - GROUND,
        "greyscale": True,
        "parts": part_index,
    }, indent=2) + "\n", encoding="utf-8")
    (CRANE_ROOT / "variants.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8")


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
        destination = VARIANT_ROOT / f"crane-{index + 1:02d}.png"
        _compose(choice).write_to_png(str(destination))
        written.append(destination)
        records.append({"file": str(destination.relative_to(CRANE_ROOT)),
                        "parts": _choice_record(choice)})

    _write_manifest(PARTS, records)
    preview = CRANE_ROOT / "preview.png"
    _preview(records, preview)
    written.append(preview)
    return written, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-render the whole part library as well as variants")
    parser.add_argument("--variants", type=int, default=24,
                        help="number of composed crane samples (default 24)")
    parser.add_argument("--seed", default="20261116",
                        help="seed for the sample composition (default 20261116)")
    parser.add_argument("--quiet", action="store_true",
                        help="only print the final summary")
    args = parser.parse_args(argv)
    if args.variants < 1:
        parser.error("--variants must be at least 1")
    _, records = generate(force=args.force, variants=args.variants,
                          seed=args.seed, quiet=args.quiet)
    print(f"Crane assets ready: {len(PARTS)} parts in {len(LIBRARY)} categories, "
          f"{len(records)} variants; {CRANE_ROOT / 'preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
