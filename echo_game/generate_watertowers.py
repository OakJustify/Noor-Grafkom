"""Generate ECHO's modular greyscale water-tower obstacles with Cairo.

Usage: .venv-echo/bin/python -m echo_game.generate_watertowers [--force]
           [--variants 24] [--seed 20261116]

An elevated steel water tower is assembled from independent parts the way one
is really built: a concrete footing, stacked leg sections with bracing panels
between them, a platform deck with a railing, the riveted tank, its roof and
roof fittings, plus a riser pipe at the base. Every shape variant has a
different silhouette and every part is built from several primitives (posts,
plates, ties, diagonals, rivets, hoops), so a randomizer can mix shapes and
tones freely. Pixels are greyscale only, so the game can tint any part at
runtime with a seeded colour (pygame.BLEND_MULT), exactly like the block,
rocket and crane libraries. No display, mixer or network access.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import cairo

TOWER_ROOT = Path(__file__).resolve().parent.parent / "assets" / "obstacle" / "watertowers"
PART_ROOT = TOWER_ROOT / "parts"
VARIANT_ROOT = TOWER_ROOT / "variants"
CANVAS = (560, 720)
GROUND = 26
PAD = 10
OUTLINE = 44.0
TONES = {"dark": 0.83, "mid": 1.0, "light": 1.17}
SECTION_H = 80      # one leg / bracing bay
TOP_MARGIN = 34     # headroom kept above the roof fitting
LEG_SPAN = 96       # clear distance between the two front legs
DECK_W = 210        # platform width, also the railing width


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


# ---------------------------------------------------------------------------
# Footing: wide slab, four separate pads, stepped plinth, ring beam.
def _draw_base(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "slab":
        _poly(ctx, [(8, 0), (w - 8, 0), (w, h), (0, h)])
        _vgrad(ctx, h, pal)
        ctx.fill_preserve()
        ctx.save()
        _poly(ctx, [(8, 0), (w - 8, 0), (w, h), (0, h)])
        ctx.clip()
        _rect(ctx, 0, 0, w, 6)
        _set(ctx, light, .30)
        ctx.fill()
        _rect(ctx, 0, h - 8, w, h)
        _set(ctx, dark, .30)
        ctx.fill()
        _set(ctx, dark, .32)
        ctx.set_line_width(2.0)
        _line(ctx, w * .28, 7, w * .18, h)
        _line(ctx, w * .70, 7, w * .78, h)
        ctx.stroke()
        _dots(ctx, [(10 + i * 15, 8) for i in range(int(w - 20) // 15)], 1.9)
        ctx.restore()
        _poly(ctx, [(8, 0), (w - 8, 0), (w, h), (0, h)])
        _outline(ctx)
    elif shape == "pads":
        gap = 14
        pad_w = (w - gap * 3) / 4
        for i in range(4):
            x0 = i * (pad_w + gap)
            _poly(ctx, [(x0 + 3, 0), (x0 + pad_w - 3, 0), (x0 + pad_w, h),
                        (x0, h)])
            _vgrad(ctx, h, pal)
            ctx.fill_preserve()
            _set(ctx, dark, .30)
            _rect(ctx, x0, h - 6, x0 + pad_w, h)
            ctx.fill()
            _poly(ctx, [(x0 + 3, 0), (x0 + pad_w - 3, 0), (x0 + pad_w, h),
                        (x0, h)])
            _outline(ctx, 3.0)
        _rect(ctx, 0, 2, w, 9)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, 0, 2, w, 9)
        _outline(ctx, 3.2)
    elif shape == "plinth":
        levels = ((0, w, h * .44), (w * .11, w * .89, h * .30),
                  (w * .24, w * .76, h * .26))
        y = 0
        for x0, x1, height in levels:
            _rect(ctx, x0, y, x1, y + height)
            _vgrad(ctx, h, pal)
            ctx.fill()
            _rect(ctx, x0, y, x1, y + height)
            _outline(ctx, 3.4)
            y += height
        _dots(ctx, [(w * .5 - 14, h * .72), (w * .5 + 14, h * .72)],
              2.2, value=40)
    else:  # ring beam: a low continuous footing with anchor bolts
        _rect(ctx, 0, 0, w, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        ctx.save()
        _rect(ctx, 0, 0, w, h)
        ctx.clip()
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, light, .32)
        ctx.fill()
        _set(ctx, dark, .34)
        ctx.set_line_width(2.0)
        for x in (w * .2, w * .4, w * .6, w * .8):
            _line(ctx, x, 5, x, h)
        ctx.stroke()
        _dots(ctx, [(12 + i * 18, h * .62) for i in range(int(w - 20) // 18)],
              1.8, alpha=.8)
        ctx.restore()
        _rect(ctx, 0, 0, w, h)
        _outline(ctx)


# ---------------------------------------------------------------------------
# Legs: square post, tapered post, round tube, H-section.
def _draw_leg(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "ibeam":
        web = 7.0
        for x0 in (0, w - web):
            _rect(ctx, x0, 0, x0 + web, h)
            _hgrad(ctx, w, pal)
            ctx.fill()
            _rect(ctx, x0, 0, x0 + web, h)
            _outline(ctx, 2.6)
        _rect(ctx, web, 0, w - web, h)
        _set(ctx, mid, .55)
        ctx.fill()
        _set(ctx, dark, .30)
        ctx.set_line_width(1.6)
        _line(ctx, web, 0, web, h)
        ctx.stroke()
        _dots(ctx, [(w * .5, y) for y in range(14, int(h) - 8, 18)], 1.7)
        _rect(ctx, 0, 0, w, h)
        _outline(ctx, 3.4)
        return

    if shape == "tube":
        _round_rect(ctx, 0, 0, w, h, w * .34)
        _hgrad(ctx, w, pal)
        ctx.fill_preserve()
        ctx.save()
        _round_rect(ctx, 0, 0, w, h, w * .34)
        ctx.clip()
        _rect(ctx, 0, 0, w * .30, h)
        _set(ctx, light, .30)
        ctx.fill()
        for y in (0, h - 7):
            _rect(ctx, -1, y, w + 1, y + 7)
            _set(ctx, light, .34)
            ctx.fill()
            _set(ctx, dark, .55)
            ctx.set_line_width(1.6)
            _line(ctx, 0, y + 7, w, y + 7)
            ctx.stroke()
        ctx.restore()
        _round_rect(ctx, 0, 0, w, h, w * .34)
        _outline(ctx, 3.6)
        return

    if shape == "tapered":
        inset = 5.0
        body = [(0, h), (inset, 0), (w - inset, 0), (w, h)]
    else:
        body = [(0, 0), (w, 0), (w, h), (0, h)]
    _poly(ctx, body)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    _poly(ctx, body)
    ctx.clip()
    _rect(ctx, 0, 0, w * .26, h)
    _set(ctx, light, .26)
    ctx.fill()
    _rect(ctx, w * .78, 0, w, h)
    _set(ctx, dark, .18)
    ctx.fill()
    # End flange plates and a gusset tab, so the leg is not one plain bar.
    for y0 in (0, h - 8):
        _rect(ctx, 0, y0, w, y0 + 8)
        _set(ctx, mid, .55)
        ctx.fill()
        _set(ctx, dark, .45)
        ctx.set_line_width(1.4)
        _line(ctx, 0, y0 + 8, w, y0 + 8)
        ctx.stroke()
    _dots(ctx, [(w * .5 - 4, 4), (w * .5 + 4, 4)], 1.7, value=44)
    _dots(ctx, [(w * .5 - 4, h - 4), (w * .5 + 4, h - 4)], 1.7, value=44)
    ctx.restore()
    _poly(ctx, body)
    _outline(ctx, 3.8)
    # Diagonal gusset halfway, bolted to the web.
    _poly(ctx, [(w * .18, h * .5), (w * .18, h * .62), (w * .82, h * .44),
                (w * .82, h * .36)])
    _set(ctx, mid, .85)
    ctx.fill()
    _poly(ctx, [(w * .18, h * .5), (w * .18, h * .62), (w * .82, h * .44),
                (w * .82, h * .36)])
    _outline(ctx, 2.2)


# ---------------------------------------------------------------------------
# Bracing panels: open steel frame between the two legs of one bay.
def _draw_brace(ctx, shape, w, h, pal):
    light, mid, dark = pal
    ties = (4.0, h - 4.0)
    _set(ctx, dark, .92)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(5.4)
    for y in ties:
        _line(ctx, 0, y, w, y)
    ctx.stroke()

    ctx.set_line_width(4.4)
    _set(ctx, dark, .88)
    if shape == "xbrace":
        _line(ctx, 0, ties[1], w, ties[0])
        _line(ctx, 0, ties[0], w, ties[1])
    elif shape == "diagonal":
        _line(ctx, 0, ties[1], w, ties[0])
        _line(ctx, 0, ties[0], w * .18, ties[0] + 2)
    elif shape == "kbrace":
        _line(ctx, 0, ties[1], w * .5, (ties[0] + ties[1]) * .5)
        _line(ctx, w, ties[1], w * .5, (ties[0] + ties[1]) * .5)
        _line(ctx, w * .5, ties[0], w * .5, ties[1])
    else:  # zigzag
        _line(ctx, 0, ties[1], w * .33, ties[0])
        _line(ctx, w * .33, ties[0], w * .66, ties[1])
        _line(ctx, w * .66, ties[1], w, ties[0])
    ctx.stroke()

    # Gusset plates and bolts where the members meet the legs.
    _dots(ctx, [(x, y) for x in (0, w) for y in ties], 3.0, value=64, alpha=.9)
    _set(ctx, mid, .55)
    ctx.set_line_width(1.4)
    for x in (0, w):
        _line(ctx, x, ties[0], x, ties[1])
    ctx.stroke()


# ---------------------------------------------------------------------------
# Platform: ring truss, solid deck, plate girder frame.
def _draw_platform(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "deck":
        _rect(ctx, 0, 0, w, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        ctx.save()
        _rect(ctx, 0, 0, w, h)
        ctx.clip()
        _rect(ctx, 0, 0, w, 6)
        _set(ctx, light, .34)
        ctx.fill()
        _rect(ctx, 0, h - 7, w, h)
        _set(ctx, dark, .34)
        ctx.fill()
        _set(ctx, dark, .30)
        ctx.set_line_width(1.8)
        for x in range(26, int(w) - 8, 30):
            _line(ctx, x, 6, x, h - 7)
        ctx.stroke()
        _dots(ctx, [(14 + i * 17, h - 3) for i in range(int(w - 16) // 17)],
              1.8)
        ctx.restore()
        _rect(ctx, 0, 0, w, h)
        _outline(ctx, 3.8)
        return

    if shape == "ring":
        _set(ctx, dark, .92)
        ctx.set_line_width(5.4)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for y in (3.5, h - 3.5):
            _line(ctx, 0, y, w, y)
        ctx.stroke()
        _set(ctx, dark, .85)
        ctx.set_line_width(3.6)
        step = 26.0
        x = 0.0
        while x < w - 2:
            _line(ctx, x, h - 3.5, min(w, x + step), 3.5)
            _line(ctx, min(w, x + step), 3.5, min(w, x + step), h - 3.5)
            x += step
        ctx.stroke()
        _dots(ctx, [(x, y) for x in (0, w) for y in (3.5, h - 3.5)],
              3.0, value=64, alpha=.9)
        return

    # plate girder frame: top plate, bottom plate, stiffeners
    for y0 in (0, h - 6):
        _rect(ctx, 0, y0, w, y0 + 6)
        _hgrad(ctx, w, pal)
        ctx.fill()
        _rect(ctx, 0, y0, w, y0 + 6)
        _outline(ctx, 2.4)
    _rect(ctx, 0, 4, w, h - 4)
    _set(ctx, mid, .22)
    ctx.fill()
    _set(ctx, dark, .80)
    ctx.set_line_width(2.6)
    x = 12.0
    while x < w - 8:
        _line(ctx, x, 5, x, h - 5)
        _line(ctx, x, 5, x + 20, h - 5)
        x += 32
    ctx.stroke()
    _rect(ctx, 0, 0, w, h)
    _outline(ctx, 3.2)


# ---------------------------------------------------------------------------
# Railing: two rails with posts, mesh fence, or pickets with a kick plate.
def _draw_railing(ctx, shape, w, h, pal):
    light, mid, dark = pal
    _set(ctx, dark, .90)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(3.4)
    _line(ctx, 0, h - 4, w, h - 4)
    _line(ctx, 0, 7, w, 7)
    ctx.stroke()

    if shape == "mesh":
        _set(ctx, mid, .30)
        _rect(ctx, 0, 7, w, h - 4)
        ctx.fill()
        ctx.save()
        _rect(ctx, 0, 7, w, h - 4)
        ctx.clip()
        _set(ctx, dark, .70)
        ctx.set_line_width(1.8)
        x = -h
        while x < w:
            _line(ctx, x, 7, x + h, h - 4)
            _line(ctx, x + h, 7, x, h - 4)
            x += 11
        ctx.stroke()
        ctx.restore()
        _rect(ctx, 0, 7, w, h - 4)
        _set(ctx, dark, .5)
        ctx.set_line_width(1.6)
        ctx.stroke()
    elif shape == "cage":
        _set(ctx, dark, .82)
        ctx.set_line_width(2.2)
        for x in range(9, int(w) - 4, 12):
            _line(ctx, x, 7, x, h - 4)
        ctx.stroke()
        _rect(ctx, 0, h - 8, w, h - 3)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, 0, h - 8, w, h - 3)
        _outline(ctx, 2.2)

    posts = 5
    for i in range(posts):
        x = i * (w - 5) / (posts - 1)
        _rect(ctx, x, 0, x + 5, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, x, 0, x + 5, h)
        _outline(ctx, 2.4)
    # Post caps.
    _dots(ctx, [(i * (w - 5) / (posts - 1) + 2.5, 2.0) for i in range(posts)],
          2.2, value=64)


# ---------------------------------------------------------------------------
# Tank bodies. All of them keep a flat top at y = 0 so a roof can sit on it.
def _tank_path(ctx, shape, w, h):
    if shape == "cylinder":
        _rect(ctx, 0, 0, w, h)
    elif shape == "barrel":
        ctx.new_path()
        ctx.move_to(8, 0)
        ctx.curve_to(1, h * .18, 0, h * .34, 0, h * .5)
        ctx.curve_to(0, h * .66, 1, h * .82, 8, h)
        ctx.line_to(w - 8, h)
        ctx.curve_to(w - 1, h * .82, w, h * .66, w, h * .5)
        ctx.curve_to(w, h * .34, w - 1, h * .18, w - 8, 0)
        ctx.close_path()
    elif shape == "frustum":
        inx = (w - 132) / 2
        _poly(ctx, [(inx, h), (0, 0), (w, 0), (w - inx, h)])
    else:  # sphere, cut flat where the roof starts and sitting on a skirt
        rx = w / 2
        ry = (h - 18) / 1.661
        cy = ry * 0.661
        ctx.new_path()
        ctx.save()
        ctx.translate(rx, cy)
        ctx.scale(1.0, ry / rx)
        ctx.arc(0, 0, rx, -0.7227, math.pi + 0.7227)
        ctx.restore()
        ctx.close_path()


def _draw_tank(ctx, shape, w, h, pal):
    light, mid, dark = pal
    _tank_path(ctx, shape, w, h)
    _vgrad(ctx, h, pal)
    ctx.fill_preserve()
    ctx.save()
    _tank_path(ctx, shape, w, h)
    ctx.clip()

    if shape == "sphere":
        # Weld bands follow the equator of the spheroid.
        _set(ctx, dark, .34)
        ctx.set_line_width(2.0)
        for f in (0.30, 0.52, 0.72):
            _line(ctx, 0, h * f, w, h * f)
        ctx.stroke()
        _set(ctx, light, .22)
        ctx.new_path()
        ctx.save()
        ctx.translate(w * .40, h * .36)
        ctx.scale(1.0, 0.55)
        ctx.arc(0, 0, w * .16, 0, math.tau)
        ctx.restore()
        ctx.fill()
        _set(ctx, dark, .20)
        _rect(ctx, 0, h * .62, w, h)
        ctx.fill()
    else:
        # Vertical plate seams with two rivet rows.
        _set(ctx, dark, .36)
        ctx.set_line_width(2.0)
        seam = 30 if shape != "barrel" else 34
        for x in range(24, int(w) - 12, seam):
            _line(ctx, x, 8, x, h - 12)
        ctx.stroke()
        # Hoop bands around the shell.
        for f in (0.30, 0.58, 0.84):
            y = h * f
            _rect(ctx, 0, y, w, y + 7)
            _set(ctx, light, .26)
            ctx.fill()
            _set(ctx, dark, .38)
            ctx.set_line_width(1.5)
            _line(ctx, 0, y + 7, w, y + 7)
            ctx.stroke()
        _rect(ctx, 0, 0, w, 7)
        _set(ctx, light, .36)
        ctx.fill()
        _rect(ctx, 0, h - 14, w, h)
        _set(ctx, dark, .22)
        ctx.fill()
        # Rivets along the two upper hoops.
        _dots(ctx, [(x, h * 0.30 + 13) for x in range(14, int(w) - 8, 14)],
              1.7, alpha=.55)
        _dots(ctx, [(x, h * 0.58 + 13) for x in range(14, int(w) - 8, 14)],
              1.7, alpha=.55)

    ctx.restore()
    _tank_path(ctx, shape, w, h)
    _outline(ctx, 4.2)

    if shape == "sphere":
        # Skirt that carries the spheroid down onto the deck.
        _poly(ctx, [(w * .5 - 56, h - 24), (w * .5 + 56, h - 24),
                    (w * .5 + 62, h), (w * .5 - 62, h)])
        _vgrad(ctx, h, pal)
        ctx.fill()
        _poly(ctx, [(w * .5 - 56, h - 24), (w * .5 + 56, h - 24),
                    (w * .5 + 62, h), (w * .5 - 62, h)])
        _outline(ctx, 3.4)
        # Collar ring where the roof lands.
        _rect(ctx, w * .5 - 62, 0, w * .5 + 62, 9)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, w * .5 - 62, 0, w * .5 + 62, 9)
        _outline(ctx, 2.8)
    else:
        # Base ring and top rim: two extra primitives on every shell.
        _rect(ctx, 4, h - 12, w - 4, h)
        _set(ctx, mid, .9)
        ctx.fill()
        _rect(ctx, 4, h - 12, w - 4, h)
        _outline(ctx, 2.6)
        _rect(ctx, 0, 0, w, 6)
        _set(ctx, mid, .9)
        ctx.fill()
        _rect(ctx, 0, 0, w, 6)
        _outline(ctx, 2.4)


# ---------------------------------------------------------------------------
# Roofs: cone, shallow cone, dome, flat deck. Each span renders at its own
# width so a narrow spheroid gets a narrow cap.
def _draw_roof(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "cone":
        body = [(0, h), (w * .5, 0), (w, h)]
    elif shape == "lowcone":
        body = [(0, h), (w * .5, 0), (w, h)]
    elif shape == "dome":
        body = None
    else:  # flat
        body = [(0, 0), (w, 0), (w, h), (0, h)]

    if body:
        _poly(ctx, body)
    else:
        ctx.new_path()
        ctx.save()
        ctx.translate(w * .5, h)
        ctx.scale(1.0, h / (w * .5))
        ctx.arc(0, 0, w * .5, math.pi, math.tau)
        ctx.restore()
        ctx.close_path()
    _vgrad(ctx, max(h, 1), pal)
    ctx.fill_preserve()
    ctx.save()
    if body:
        _poly(ctx, body)
    else:
        ctx.new_path()
        ctx.save()
        ctx.translate(w * .5, h)
        ctx.scale(1.0, h / (w * .5))
        ctx.arc(0, 0, w * .5, math.pi, math.tau)
        ctx.restore()
        ctx.close_path()
    ctx.clip()
    _set(ctx, dark, .34)
    ctx.set_line_width(2.0)
    if shape in ("cone", "lowcone"):
        for i in range(1, 8):
            x = w * i / 8
            _line(ctx, w * .5, 0, x, h)
    elif shape == "dome":
        for i in range(1, 6):
            x = w * i / 6
            _line(ctx, w * .5, 0, x, h)
        _line(ctx, 0, h * .42, w, h * .42)
    else:
        for x in range(20, int(w) - 10, 34):
            _line(ctx, x, 0, x, h)
    ctx.stroke()
    if shape in ("cone", "lowcone", "dome"):
        _rect(ctx, 0, h - 9, w, h)
        _set(ctx, dark, .30)
        ctx.fill()
        _rect(ctx, 0, h - 9, w, 6)
        _set(ctx, light, .26)
        ctx.fill()
    else:
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, light, .34)
        ctx.fill()
        _rect(ctx, 6, 8, w - 6, h - 4)
        _set(ctx, dark, .16)
        ctx.fill()
    ctx.restore()

    if body:
        _poly(ctx, body)
    else:
        ctx.new_path()
        ctx.save()
        ctx.translate(w * .5, h)
        ctx.scale(1.0, h / (w * .5))
        ctx.arc(0, 0, w * .5, math.pi, math.tau)
        ctx.restore()
        ctx.close_path()
    _outline(ctx, 3.8)

    if shape in ("cone", "lowcone", "dome"):
        # Rim band and a finial knob on the crown.
        _rect(ctx, 0, h - 10, w, h)
        _set(ctx, mid, .92)
        ctx.fill()
        _rect(ctx, 0, h - 10, w, h)
        _outline(ctx, 2.6)
        ctx.new_path()
        ctx.arc(w * .5, 4, 5.0, 0, math.tau)
        _set(ctx, mid, 1.0)
        ctx.fill_preserve()
        _outline(ctx, 2.2)
    else:
        # Parapet on the flat deck.
        _rect(ctx, 0, 0, w, 5)
        _set(ctx, mid, .92)
        ctx.fill()
        _rect(ctx, 0, 0, w, 5)
        _outline(ctx, 2.4)


# ---------------------------------------------------------------------------
# Roof fittings: vent pipe, finial ball, antenna, hatch.
def _draw_vent(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "pipe":
        _rect(ctx, w * .32, 10, w * .68, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .32, 10, w * .68, h)
        _outline(ctx, 2.6)
        _rect(ctx, 0, 0, w, 9)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, 0, 0, w, 9)
        _outline(ctx, 2.4)
        _rect(ctx, w * .20, h - 8, w * .80, h)
        _set(ctx, dark, .55)
        ctx.fill()
        _rect(ctx, w * .20, h - 8, w * .80, h)
        _outline(ctx, 2.2)
    elif shape == "ball":
        _rect(ctx, w * .38, 16, w * .62, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .38, 16, w * .62, h)
        _outline(ctx, 2.4)
        ctx.new_path()
        ctx.arc(w * .5, 13, 11, 0, math.tau)
        _vgrad(ctx, 26, pal)
        ctx.fill_preserve()
        _outline(ctx, 2.8)
        _dots(ctx, [(w * .5 - 3, 10)], 1.8, value=190, alpha=.8)
        _rect(ctx, w * .26, h - 7, w * .74, h)
        _set(ctx, dark, .55)
        ctx.fill()
    elif shape == "antenna":
        _rect(ctx, w * .18, h - 9, w * .82, h)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, w * .18, h - 9, w * .82, h)
        _outline(ctx, 2.4)
        _rect(ctx, w * .44, 6, w * .56, h - 9)
        _set(ctx, dark, .80)
        ctx.fill()
        _set(ctx, dark, .85)
        ctx.set_line_width(2.2)
        _line(ctx, w * .5, 6, w * .5, 0)
        for i, y in enumerate((10, 22, 34)):
            half = 8 - i * 2
            _line(ctx, w * .5 - half, y, w * .5 + half, y)
        ctx.stroke()
        _dots(ctx, [(w * .5, 0)], 2.2, value=52)
    else:  # hatch
        _rect(ctx, 2, 4, w - 2, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, 2, 4, w - 2, h)
        _outline(ctx, 2.8)
        _rect(ctx, 0, 0, w, 7)
        _set(ctx, mid, .95)
        ctx.fill()
        _rect(ctx, 0, 0, w, 7)
        _outline(ctx, 2.4)
        ctx.new_path()
        ctx.arc(w * .5, h * .68, 6, math.pi * .05, math.pi * .95)
        _set(ctx, 70, .9)
        ctx.set_line_width(2.4)
        ctx.stroke()
        _dots(ctx, [(w * .24, 11), (w * .76, 11)], 1.8, value=48)


# ---------------------------------------------------------------------------
# Riser pipes standing at the tower base, one per variant.
def _draw_riser(ctx, shape, w, h, pal):
    light, mid, dark = pal
    if shape == "elbow":
        _rect(ctx, w * .30, 12, w * .70, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .30, 12, w * .70, h)
        _outline(ctx, 2.8)
        ctx.new_path()
        ctx.arc(w * .30, 16, w * .30, math.pi, math.pi * 1.5)
        _set(ctx, mid, 1.0)
        ctx.set_line_width(5.0)
        ctx.stroke_preserve()
        _outline(ctx, 8.0, alpha=.6, value=32)
        _set(ctx, mid, 1.0)
        ctx.set_line_width(5.0)
        ctx.stroke()
        _rect(ctx, w * .30, h - 10, w * .70, h)
        _set(ctx, dark, .55)
        ctx.fill()
        _rect(ctx, w * .30, h - 10, w * .70, h)
        _outline(ctx, 2.4)
        _rect(ctx, w * .30, 0, w * .70, 6)
        _set(ctx, dark, .6)
        ctx.fill()
        _rect(ctx, w * .30, 0, w * .70, 6)
        _outline(ctx, 2.2)
    elif shape == "valve":
        _rect(ctx, w * .38, 0, w * .62, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .38, 0, w * .62, h)
        _outline(ctx, 2.6)
        for cy in (h * .30, h * .62):
            _round_rect(ctx, w * .18, cy - 9, w * .82, cy + 9, 3)
            _vgrad(ctx, 18, pal)
            ctx.fill()
            _round_rect(ctx, w * .18, cy - 9, w * .82, cy + 9, 3)
            _outline(ctx, 2.6)
            ctx.new_path()
            ctx.arc(w * .5, cy, 8, 0, math.tau)
            _set(ctx, 196, 1.0)
            ctx.fill_preserve()
            _outline(ctx, 2.2)
            _dots(ctx, [(w * .5, cy)], 2.0, value=52)
        _rect(ctx, w * .30, h - 8, w * .70, h)
        _set(ctx, dark, .55)
        ctx.fill()
    elif shape == "straight":
        _rect(ctx, w * .34, 0, w * .66, h)
        _vgrad(ctx, h, pal)
        ctx.fill_preserve()
        ctx.save()
        _rect(ctx, w * .34, 0, w * .66, h)
        ctx.clip()
        _set(ctx, light, .30)
        _rect(ctx, w * .34, 0, w * .44, h)
        ctx.fill()
        _set(ctx, dark, .42)
        ctx.set_line_width(1.8)
        for y in range(16, int(h) - 8, 24):
            _line(ctx, w * .34, y, w * .66, y)
        ctx.stroke()
        ctx.restore()
        _rect(ctx, w * .34, 0, w * .66, h)
        _outline(ctx, 2.8)
        for y in (14, h - 14):
            _rect(ctx, w * .16, y, w * .84, y + 7)
            _set(ctx, mid, .95)
            ctx.fill()
            _rect(ctx, w * .16, y, w * .84, y + 7)
            _outline(ctx, 2.2)
    else:  # conduit with a junction box
        _rect(ctx, w * .28, 0, w * .72, h * .62)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .28, 0, w * .72, h * .62)
        _outline(ctx, 2.6)
        _rect(ctx, w * .06, h * .52, w * .94, h)
        _vgrad(ctx, h, pal)
        ctx.fill()
        _rect(ctx, w * .06, h * .52, w * .94, h)
        _outline(ctx, 2.8)
        _set(ctx, dark, .40)
        ctx.set_line_width(1.8)
        for x in (w * .30, w * .70):
            _line(ctx, x, h * .56, x, h - 3)
        ctx.stroke()
        _dots(ctx, [(w * .18, h - 8), (w * .82, h - 8)], 1.8, value=44)


DRAWERS = {
    "base": _draw_base,
    "leg": _draw_leg,
    "brace": _draw_brace,
    "platform": _draw_platform,
    "railing": _draw_railing,
    "tank": _draw_tank,
    "roof": _draw_roof,
    "vent": _draw_vent,
    "riser": _draw_riser,
}

# Where the composer attaches each part, in that part's own pixel space.
ORIGINS = {
    "base": lambda w, h: (w / 2, 0.0),
    "leg": lambda w, h: (w / 2, h),
    "brace": lambda w, h: (0.0, h),
    "platform": lambda w, h: (w / 2, 0.0),
    "railing": lambda w, h: (0.0, h),
    "tank": lambda w, h: (w / 2, h),
    "roof": lambda w, h: (w / 2, h),
    "vent": lambda w, h: (w / 2, h),
    "riser": lambda w, h: (w / 2, h),
}


# ---------------------------------------------------------------------------
# Library definition. Shapes differ in silhouette, tone only changes value.
def _spec(kind, shape, w, h, tone, span=None):
    ox, oy = ORIGINS[kind](w, h)
    spec = dict(kind=kind, shape=shape, w=float(w), h=float(h), tone=tone,
                origin=(ox, oy), name=f"{shape}_{tone}",
                file=PART_ROOT / kind / f"{shape}_{tone}.png")
    if span:
        spec["span"] = span
        spec["name"] = f"{shape}_{span}_{tone}"
        spec["file"] = PART_ROOT / kind / f"{shape}_{span}_{tone}.png"
    return spec


def _part_specs():
    specs = []
    bases = (("slab", 190, 26), ("pads", 196, 24), ("plinth", 150, 34),
             ("ringbeam", 200, 22))
    for shape, w, h in bases:
        for tone in ("mid", "light"):
            specs.append(_spec("base", shape, w, h, tone))

    legs = (("square", 22), ("tapered", 24), ("tube", 20), ("ibeam", 22))
    for shape, w in legs:
        for tone in ("mid", "dark"):
            specs.append(_spec("leg", shape, w, SECTION_H, tone))

    for shape in ("xbrace", "diagonal", "kbrace", "zigzag"):
        for tone in ("mid", "dark"):
            specs.append(_spec("brace", shape, LEG_SPAN, SECTION_H, tone))

    for shape in ("ring", "deck", "girder"):
        for tone in ("mid", "light"):
            specs.append(_spec("platform", shape, DECK_W, 22, tone))

    for shape in ("rail", "mesh", "cage"):
        for tone in ("dark", "mid"):
            specs.append(_spec("railing", shape, DECK_W, 30, tone))

    tanks = (("cylinder", 176, 130), ("barrel", 184, 128),
             ("frustum", 176, 138), ("sphere", 176, 150))
    for shape, w, h in tanks:
        for tone in ("mid", "light"):
            specs.append(_spec("tank", shape, w, h, tone))

    roofs = (("cone", 66), ("lowcone", 42), ("dome", 58), ("flat", 22))
    for shape, h in roofs:
        for span, w in (("wide", 182), ("narrow", 132)):
            height = h if span == "wide" else max(14, h * 0.76)
            for tone in ("mid", "dark"):
                specs.append(_spec("roof", shape, w, height, tone, span=span))

    vents = (("pipe", 18, 40), ("ball", 22, 36), ("antenna", 20, 52),
             ("hatch", 30, 22))
    for shape, w, h in vents:
        for tone in ("dark", "mid"):
            specs.append(_spec("vent", shape, w, h, tone))

    risers = (("elbow", 34, 72), ("valve", 36, 80), ("straight", 28, 76),
              ("conduit", 30, 66))
    for shape, w, h in risers:
        for tone in ("mid", "dark"):
            specs.append(_spec("riser", shape, w, h, tone))
    return specs


PARTS = _part_specs()
LIBRARY = {}
for _spec_entry in PARTS:
    LIBRARY.setdefault(_spec_entry["kind"], []).append(_spec_entry)
ROOF_BY_SPAN = {
    "wide": [spec for spec in LIBRARY["roof"] if spec["span"] == "wide"],
    "narrow": [spec for spec in LIBRARY["roof"] if spec["span"] == "narrow"],
}
# A spheroid is flat where the roof lands, so it needs the narrow roof span.
TANK_ROOF_SPAN = {"cylinder": "wide", "barrel": "wide", "frustum": "wide",
                  "sphere": "narrow"}


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
# Composition: real water-tower topology, random part choice.
def _fit_sections(base, platform, tank, roof, vent):
    """How many leg bays this tank stack needs to fill the canvas height."""
    stack = base["h"] + platform["h"] + tank["h"] + roof["h"] + vent["h"]
    room = CANVAS[1] - GROUND - TOP_MARGIN - stack
    return max(2, int(room // SECTION_H))


def random_choice(rng):
    """Pick one part from each family; reusable by the game at runtime."""
    base = rng.choice(LIBRARY["base"])
    platform = rng.choice(LIBRARY["platform"])
    tank = rng.choice(LIBRARY["tank"])
    span = TANK_ROOF_SPAN[tank["shape"]]
    roof = rng.choice(ROOF_BY_SPAN[span])
    vent = rng.choice(LIBRARY["vent"])
    sections = _fit_sections(base, platform, tank, roof, vent)
    return {
        "base": base,
        "leg": rng.choice(LIBRARY["leg"]),
        "brace": rng.choice(LIBRARY["brace"]),
        "sections": max(2, sections - rng.choice((0, 0, 1))),
        "platform": platform,
        "railing": rng.choice(LIBRARY["railing"]),
        "tank": tank,
        "roof": roof,
        "vent": vent,
        "riser": rng.choice(LIBRARY["riser"]),
        "riser_side": rng.choice(("left", "right")),
        "ladder_side": rng.choice(("left", "right")),
    }


def _layout(choice):
    """Return (kind, spec, x, y) placements plus the anchors pipes need."""
    base, leg, brace = choice["base"], choice["leg"], choice["brace"]
    platform, tank, roof = (choice["platform"], choice["tank"],
                            choice["roof"])
    railing, vent, riser = (choice["railing"], choice["vent"],
                            choice["riser"])

    width, height = CANVAS
    ground = height - GROUND
    base_top = ground - base["h"]
    leg_h = SECTION_H * choice["sections"]
    deck_bottom = base_top - leg_h
    deck_top = deck_bottom - platform["h"]

    cx = width / 2
    leg_x = LEG_SPAN / 2 + leg["w"] / 2

    pieces = [("base", base, cx, base_top)]
    for i in range(choice["sections"]):
        y = base_top - SECTION_H * i
        pieces.append(("leg", leg, cx - leg_x, y))
        pieces.append(("leg", leg, cx + leg_x, y))
        pieces.append(("brace", brace, cx - LEG_SPAN / 2, y))
    pieces.append(("platform", platform, cx, deck_top))
    pieces.append(("railing", railing, cx - DECK_W / 2, deck_top))
    pieces.append(("tank", tank, cx, deck_top))
    roof_y = deck_top - tank["h"]
    pieces.append(("roof", roof, cx, roof_y))
    pieces.append(("vent", vent, cx, roof_y - roof["h"]))

    riser_sign = -1 if choice["riser_side"] == "left" else 1
    riser_x = cx + riser_sign * (leg_x + leg["w"] / 2 + 4 + riser["w"] / 2)
    pieces.append(("riser", riser, riser_x, base_top))

    order = ["base", "leg", "brace", "riser", "platform", "railing", "tank",
             "roof", "vent"]
    pieces.sort(key=lambda piece: order.index(piece[0]))
    ladder_sign = -1 if choice["ladder_side"] == "left" else 1
    anchors = {
        "cx": cx,
        "cx_left": cx - LEG_SPAN / 2,
        "cx_right": cx + LEG_SPAN / 2,
        "leg_w": leg["w"],
        "leg_x": leg_x,
        "base_top": base_top,
        "deck_top": deck_top,
        "deck_bottom": deck_bottom,
        "tank_bottom": deck_top,
        "tank_h": tank["h"],
        "riser_x": riser_x,
        "riser_top": base_top - riser["h"],
        "riser_sign": riser_sign,
        "ladder_x": cx + ladder_sign * (LEG_SPAN / 2 - 12),
        "ladder_sign": ladder_sign,
        "ground": ground,
    }
    return pieces, anchors


def _draw_ladder(ctx, anchors):
    """A caged service ladder: length depends on the variant, so it is
    composed at run time instead of being baked into a fixed PNG."""
    x = anchors["ladder_x"]
    top = anchors["deck_top"] + 4
    bottom = anchors["ground"] + 4
    _set(ctx, 62, .92)
    ctx.set_line_width(3.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for dx in (-6.0, 6.0):
        _line(ctx, x + dx, top, x + dx, bottom)
    ctx.stroke()
    _set(ctx, 58, .88)
    ctx.set_line_width(2.4)
    for y in range(int(top) + 8, int(bottom) - 4, 14):
        _line(ctx, x - 6, y, x + 6, y)
    ctx.stroke()
    # Stand-offs keep the ladder off the bay, so it reads in front of the legs.
    _set(ctx, 74, .55)
    ctx.set_line_width(2.2)
    for y in range(int(top) + 22, int(bottom), 64):
        _line(ctx, x - 6, y, x - 12, y)
        _line(ctx, x + 6, y, x + 12, y)
    ctx.stroke()


def _draw_pipe(ctx, anchors):
    """Riser feed pipe: runs up the outside of a leg and elbows into the tank."""
    x = anchors["riser_x"]
    sign = anchors["riser_sign"]
    top = anchors["riser_top"]
    deck = anchors["deck_top"]
    _set(ctx, 70, .95)
    ctx.set_line_width(6.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    _line(ctx, x, top, x, deck + 6)
    ctx.stroke()
    _set(ctx, 104, 1.0)
    ctx.set_line_width(3.0)
    _line(ctx, x, top, x, deck + 6)
    ctx.stroke()
    # Elbow into the shell, plus wall brackets.
    _set(ctx, 70, .95)
    ctx.set_line_width(6.0)
    _line(ctx, x, deck + 6, x - sign * 12, deck + 6)
    ctx.stroke()
    _set(ctx, 88, .9)
    ctx.set_line_width(3.0)
    _line(ctx, x, deck + 6, x - sign * 12, deck + 6)
    ctx.stroke()
    _set(ctx, 58, .9)
    ctx.set_line_width(2.2)
    for y in range(int(top) + 18, int(deck), 46):
        _line(ctx, x - sign * 3, y, x - sign * 9, y)
    ctx.stroke()


def _compose(choice):
    width, height = CANVAS
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    pieces, anchors = _layout(choice)

    for _, spec, x, y in pieces:
        image = cairo.ImageSurface.create_from_png(str(spec["file"]))
        ox, oy = spec["origin"]
        ctx.set_source_surface(image, x - ox - PAD, y - oy - PAD)
        ctx.paint()
        if spec["kind"] == "riser":
            _draw_pipe(ctx, anchors)
        elif spec["kind"] == "platform":
            _draw_ladder(ctx, anchors)
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
    cell_w = 244
    cell_h = cell_w * CANVAS[1] / CANVAS[0]
    gap, label = 14, 20
    rows = math.ceil(len(records) / columns)
    width = gap + columns * (cell_w + gap)
    height = gap + rows * (cell_h + label + gap) + 18
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width),
                                 int(height))
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_NORMAL)
    for index, record in enumerate(records):
        column, row = index % columns, index // columns
        x = gap + column * (cell_w + gap)
        y = gap + row * (cell_h + label + gap)
        image = cairo.ImageSurface.create_from_png(
            str(TOWER_ROOT / record["file"]))
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
    ctx.show_text("Greyscale modular water towers - every part is a separate "
                  "PNG in parts/")
    surface.write_to_png(str(destination))


def _write_manifest(specs, records):
    part_index = {}
    for spec in specs:
        entry = {
            "name": spec["name"],
            "shape": spec["shape"],
            "tone": spec["tone"],
            "file": str(spec["file"].relative_to(TOWER_ROOT)),
            "width": spec["w"],
            "height": spec["h"],
            "origin": [spec["origin"][0], spec["origin"][1]],
        }
        if spec.get("span"):
            entry["span"] = spec["span"]
        part_index.setdefault(spec["kind"], []).append(entry)
    (TOWER_ROOT / "parts.json").write_text(json.dumps({
        "canvas": list(CANVAS),
        "ground_y": CANVAS[1] - GROUND,
        "greyscale": True,
        "section_height": SECTION_H,
        "leg_span": LEG_SPAN,
        "deck_width": DECK_W,
        "tank_roof_span": TANK_ROOF_SPAN,
        "parts": part_index,
    }, indent=2) + "\n", encoding="utf-8")
    (TOWER_ROOT / "variants.json").write_text(
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
        destination = VARIANT_ROOT / f"water-tower-{index + 1:02d}.png"
        _compose(choice).write_to_png(str(destination))
        written.append(destination)
        records.append({"file": str(destination.relative_to(TOWER_ROOT)),
                        "parts": _choice_record(choice)})

    _write_manifest(PARTS, records)
    preview = TOWER_ROOT / "preview.png"
    _preview(records, preview)
    written.append(preview)
    return written, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-render the whole part library as well as variants")
    parser.add_argument("--variants", type=int, default=24,
                        help="number of composed water-tower samples (default 24)")
    parser.add_argument("--seed", default="20261116",
                        help="seed for the sample composition (default 20261116)")
    parser.add_argument("--quiet", action="store_true",
                        help="only print the final summary")
    args = parser.parse_args(argv)
    if args.variants < 1:
        parser.error("--variants must be at least 1")
    _, records = generate(force=args.force, variants=args.variants,
                          seed=args.seed, quiet=args.quiet)
    print(f"Water-tower assets ready: {len(PARTS)} parts in {len(LIBRARY)} "
          f"categories, {len(records)} variants; "
          f"{TOWER_ROOT / 'preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
