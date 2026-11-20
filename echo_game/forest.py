"""Seeded monochrome forest presentation for procedural play.

Scenery lives in deterministic, lazily rendered world-space chunks. It never
consumes a gameplay RNG or registers collision geometry. Cairo runs only on
cache misses; the frame loop composites bounded Pygame surface caches.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import io
import math
import random

import cairo
import numpy as np
import pygame

from .environment import reserved_rects


ZOOM = 1.6
GROUND_LINE = 0.735
CHUNK_WIDTH = 1024
CHUNK_PAD = 280
CHUNK_HEIGHT = 800
CHUNK_TOP = -160
GROUND_PAD = 74
INK = (4, 4, 4)
LIGHT = (219, 219, 219)


def _canvas(width, height, scale=1):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, math.ceil(width * scale),
                                 math.ceil(height * scale))
    ctx = cairo.Context(surface)
    ctx.scale(scale, scale)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    return surface, ctx


def _image(surface):
    # PNG decoding correctly unpremultiplies Cairo's alpha at antialiased edges.
    encoded = io.BytesIO()
    surface.write_to_png(encoded)
    encoded.seek(0)
    return pygame.image.load(encoded).convert_alpha()


def _surface_image(surface):
    """Copy a white-on-alpha Cairo mask without the PNG round trip.

    Only the alpha channel is used, so Cairo's premultiplied BGRA buffer is
    safe to read directly. ``print_to_png`` was the single largest cost when a
    new chunk entered view.
    """
    width, height = surface.get_width(), surface.get_height()
    image = pygame.image.frombuffer(surface.get_data(), (width, height), "BGRA")
    return image.convert_alpha()


_GRADIENTS = OrderedDict()


def _gradient(width, height, top, bottom):
    key = (width, height, top, bottom)
    if key in _GRADIENTS:
        _GRADIENTS.move_to_end(key)
        return _GRADIENTS[key]
    strip = pygame.Surface((1, height))
    tones = np.linspace(top, bottom, height, dtype=np.uint8)
    pixels = pygame.surfarray.pixels3d(strip)
    pixels[:] = tones[None, :, None]
    del pixels
    image = pygame.transform.smoothscale(strip, (width, height))
    _GRADIENTS[key] = image
    _GRADIENTS.move_to_end(key)
    while len(_GRADIENTS) > 32:
        _GRADIENTS.popitem(last=False)
    return image


def _tone(ctx, value, alpha=1):
    ctx.set_source_rgba(value / 255, value / 255, value / 255, alpha)


def _poly(ctx, points, value=4):
    ctx.new_path()
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    ctx.close_path()
    _tone(ctx, value)
    ctx.fill()


def _stroke(ctx, points, value=4, width=1):
    ctx.new_path()
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    _tone(ctx, value)
    ctx.set_line_width(width)
    ctx.stroke()


def _circle(ctx, x, y, radius, value=4, alpha=1):
    ctx.new_path()
    ctx.arc(x, y, radius, 0, math.tau)
    _tone(ctx, value, alpha)
    ctx.fill()


def _mask_image(surface, top, bottom, blur=0):
    image = _surface_image(surface)
    width, height = image.get_size()
    # Recolour without touching per-pixel alpha: force every covered pixel to
    # white, soften the alpha silhouette, then multiply by a cached gradient.
    # A direct RGB write is much faster than a BLEND_RGB_MAX fill.
    pixels = pygame.surfarray.pixels3d(image)
    pixels[:] = 255
    del pixels
    if blur:
        factor = 2 if blur <= 2 else 4 if blur <= 5 else 8
        small = pygame.transform.smoothscale(
            image, (max(1, width // factor), max(1, height // factor)))
        image = pygame.transform.smoothscale(small, (width, height))
    image.blit(_gradient(width, height, top, bottom), (0, 0),
               special_flags=pygame.BLEND_RGBA_MULT)
    return image


def _remember(cache, key, image, maximum):
    cache[key] = image
    cache.move_to_end(key)
    while len(cache) > maximum:
        cache.popitem(last=False)
    return image


@dataclass(frozen=True)
class ForestLayer:
    name: str
    parallax: float
    top_gray: int
    bottom_gray: int
    blur: int


LAYERS = (
    ForestLayer("distant", .12, 114, 139, 7),
    ForestLayer("mist", .29, 70, 106, 5),
    ForestLayer("trunks", .62, 4, 26, 2),
)


def _bole(ctx, rng, x, ground, height, width, branches=True, root_scale=1.0,
          limb_scale=1.0):
    """A massive irregular bole, flared roots, and broken, tapered limbs."""
    top = ground - height
    lean = rng.uniform(-.15, .15) * width
    left, right = x - width / 2, x + width / 2
    ctx.new_path()
    ctx.move_to(x - width * 1.04, ground + 16)
    ctx.curve_to(left - width * .10, ground - 15, left + width * .09,
                 ground - height * .18, left + width * .07, ground - height * .31)
    ctx.curve_to(left + width * .04, ground - height * .51,
                 left + lean - width * .03, top + height * .19, left + lean, top)
    ctx.line_to(right + lean * .6, top)
    ctx.curve_to(right + lean + width * .04, top + height * .26,
                 right - width * .09, ground - height * .57,
                 right - width * .035, ground - height * .37)
    ctx.curve_to(right - width * .035, ground - height * .12,
                 right + width * .04, ground - 24, x + width * 1.18, ground + 18)
    ctx.close_path()
    _tone(ctx, 255)
    ctx.fill()
    # Roots spread into the leaf litter but must never close the luminous gap
    # between two foreground boles above the forest floor.
    for direction in (-1, 1):
        ctx.new_path()
        ctx.move_to(x + direction * width * .38, ground - height * .20)
        ctx.curve_to(x + direction * width * .58, ground - 40,
                     x + direction * width * .82, ground - 10,
                     x + direction * (width * .50 + width * .42 * root_scale), ground + 24)
        ctx.line_to(x + direction * width * .67, ground + 25)
        ctx.close_path()
        _tone(ctx, 255)
        ctx.fill()
    if not branches:
        return
    for side in (-1, 1):
        if rng.random() < .28:
            continue
        y = ground - height * rng.uniform(.40, .64)
        length = width * rng.uniform(.52, 1.02) * limb_scale
        thick = width * rng.uniform(.045, .085) if width > 160 else width * rng.uniform(.11, .18)
        thick = max(1.5, thick)
        start = x + side * width * .36
        # A snapped, tapered limb. It must never end in a clean rectangular cap
        # where a nearby chunk boundary cuts across the silhouette.
        tip = start + side * length - side * rng.uniform(8, 34)
        elbow = (start + side * length * .48, y - thick * rng.uniform(.2, .9))
        end = (tip, y - thick * rng.uniform(1.4, 3.4))
        ctx.new_path()
        ctx.move_to(start, y + thick)
        ctx.curve_to(start + side * length * .25, y + thick * .3,
                     elbow[0] - side * 8, elbow[1] + thick * .7, elbow[0], elbow[1])
        ctx.curve_to(elbow[0] + side * length * .18, elbow[1] - thick * .2,
                     end[0] - side * 9, end[1] + thick * .7, end[0], end[1])
        ctx.line_to(end[0] - side * rng.uniform(1, 5), end[1] + thick * 1.2)
        ctx.curve_to(elbow[0] + side * length * .2, elbow[1] + thick * .6,
                     start + side * length * .28, y - thick * .25, start, y - thick)
        ctx.close_path()
        _tone(ctx, 255)
        ctx.fill()
        if rng.random() < .38:
            fork = (elbow[0] + side * rng.uniform(9, 34), elbow[1] - rng.uniform(24, 58))
            _stroke(ctx, [elbow, fork], 255, max(2, thick * .23))
        for _ in range(rng.randrange(2, 5)):
            bx = start + side * length * rng.uniform(.30, .85)
            by = y - thick * rng.uniform(.5, 4)
            _stroke(ctx, [(bx, by), (bx + side * rng.uniform(10, 36), by - rng.uniform(16, 52))],
                    255, rng.uniform(1.5, 3.6))
    if width > 160:
        # Older trunks carry a few low, curved limbs. They break the smooth
        # wall-like silhouette without becoming horizontal sticks.
        for side in (-1, 1):
            if rng.random() < .52:
                continue
            y = ground - height * rng.uniform(.18, .34)
            length = width * rng.uniform(.24, .50)
            thick = max(2.4, width * rng.uniform(.018, .034))
            start = x + side * width * .43
            tip = (start + side * length, y - length * rng.uniform(.55, .95))
            ctx.new_path()
            ctx.move_to(start, y + thick)
            ctx.curve_to(start + side * length * .32, y - length * .06,
                         tip[0] - side * 12, tip[1] + length * .20, tip[0], tip[1])
            ctx.curve_to(tip[0] - side * 9, tip[1] + length * .13,
                         start + side * length * .42, y - thick * .6, start, y - thick)
            ctx.close_path()
            _tone(ctx, 255)
            ctx.fill()
            if rng.random() < .7:
                fork = (tip[0] + side * rng.uniform(8, 26), tip[1] - rng.uniform(14, 42))
                _stroke(ctx, [tip, (tip[0] + side * 6, tip[1] - 8), fork], 255,
                        max(1.6, thick * .55))


class ForestRenderer:
    """The endless game's forest art, view transform, and bounded visual caches."""

    zoom = ZOOM

    def __init__(self, seed, size=(960, 540)):
        self.seed = int(seed)
        self.size = tuple(size)
        self.chunks = OrderedDict()
        self.terrain = OrderedDict()
        self.props = OrderedDict()
        self.saws = OrderedDict()
        self.chunk_builds = 0
        self._players = self._player_frames()
        self._sky, self._veil, self._fog, self._vignette, self._atmosphere_overlay = self._atmosphere()
        self._canopy_surface = self._canopy()
        self._fringe_surface = self._fringe()
        self._halos = OrderedDict()
        self._shadows = OrderedDict()  # Cache for shadow zone surfaces
        # Pre-render wider strips for each parallax layer to reduce blit count
        self._layer_strips = self._pre_render_layer_strips()

    def _rng(self, domain, index):
        return random.Random((self.seed * 0x9E3779B1) ^ (domain * 0x85EBCA77)
                             ^ (int(index) * 0xC2B2AE3D))

    def _atmosphere(self):
        w, h = self.size
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        x, y = xx / w, yy / h
        light = 136 + 52 * np.exp(-((x - .71) / .31) ** 2 - ((y - .20) / .64) ** 2)
        light -= 37 * y ** 1.7
        rng = np.random.default_rng(self.seed & ((1 << 64) - 1))
        for size, strength in (((7, 5), 9), ((25, 17), 4), ((100, 56), 1.5)):
            noise = rng.integers(0, 255, (*size, 3), dtype=np.uint8)
            noise[:, :, 1:] = noise[:, :, :1]
            cloud = pygame.surfarray.make_surface(noise)
            cloud = pygame.transform.smoothscale(cloud, (w, h))
            light += (pygame.surfarray.array3d(cloud)[:, :, 0].T.astype(np.float32) / 255 - .5) * strength
        sky = pygame.surfarray.make_surface(np.repeat(np.clip(light.T, 0, 255)[:, :, None], 3, axis=2).astype(np.uint8))
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((169, 169, 169, 0))
        alpha = pygame.surfarray.pixels_alpha(veil)
        alpha[:] = (15 * np.exp(-((y.T - .64) / .30) ** 2)).astype(np.uint8)
        del alpha
        radius = ((x - .51) / .65) ** 2 + ((y - .46) / .82) ** 2
        vignette = np.clip(255 * (1 - .68 * np.clip(radius / 1.3, 0, 1) ** 1.25), 0, 255)
        vignette = pygame.surfarray.make_surface(np.repeat(vignette.T[:, :, None], 3, axis=2).astype(np.uint8))
        # A few soft horizontal banks sit in front of the midground, so the
        # bright gaps read as volumetric fog rather than flat cut-outs.
        fog_alpha = np.zeros((h, w), dtype=np.float32)
        fog_rng = random.Random(self.seed ^ 0xF06)
        for _ in range(15):
            cx, cy = fog_rng.uniform(.02, .98), fog_rng.uniform(.30, .82)
            rx, ry = fog_rng.uniform(.10, .40), fog_rng.uniform(.035, .12)
            fog_alpha += fog_rng.uniform(7, 24) * np.exp(
                -((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2)
        fog = pygame.Surface((w, h), pygame.SRCALPHA)
        fog.fill((203, 203, 203, 0))
        pixels = pygame.surfarray.pixels_alpha(fog)
        pixels[:] = np.clip(fog_alpha.T, 0, 28).astype(np.uint8)
        del pixels
        # Pre-compose veil and fog into a single atmosphere overlay for faster blitting.
        # The subtle vertical animation (3-4 pixels) is removed for performance.
        atmosphere = pygame.Surface((w, h), pygame.SRCALPHA)
        atmosphere.blit(veil, (0, 0))
        atmosphere.blit(fog, (0, 0))
        return sky.convert(), veil, fog, vignette.convert(), atmosphere

    def _pre_render_layer_strips(self):
        """Pre-render wide horizontal strips for each parallax layer.

        Each strip covers enough width to handle camera movement without needing
        to blit multiple chunks per frame. This reduces blits from 3-6 per layer
        to just 1 per layer per frame.
        """
        strips = []
        # Render enough chunks to cover the screen width plus movement buffer
        # At max parallax (0.62), camera moves ~480 world pixels per screen
        # We need: screen_width / zoom / parallax + padding
        max_parallax = max(layer.parallax for layer in LAYERS)
        needed_world_width = (self.size[0] / self.zoom / max_parallax) * 3  # 3x screen width for safety
        chunks_needed = int(needed_world_width / CHUNK_WIDTH) + 2

        for layer_index, layer in enumerate(LAYERS):
            chunk_width = CHUNK_WIDTH + CHUNK_PAD * 2
            strip_width = chunk_width * chunks_needed
            surface, ctx = _canvas(strip_width, CHUNK_HEIGHT)

            # Draw all chunks into one surface
            for i in range(chunks_needed):
                rng = self._rng(layer_index + 11, i)
                ctx.save()
                ctx.translate(CHUNK_PAD + i * chunk_width, 0)
                if layer_index == 0:
                    centers = [n * 88 + rng.uniform(-26, 26) for n in range(13)]
                    widths = (21, 57)
                    specs = [(x, rng.uniform(*widths)) for x in centers]
                    root_scale, limb_scale = .8, .9
                elif layer_index == 1:
                    centers = [62 + rng.uniform(-40, 40), 402 + rng.uniform(-68, 68),
                               744 + rng.uniform(-58, 58), 1024 + rng.uniform(-36, 36)]
                    widths = (54, 106)
                    specs = [(x, rng.uniform(*widths)) for x in centers]
                    root_scale, limb_scale = .85, .9
                else:
                    specs = [(220 + rng.uniform(-32, 32), rng.uniform(196, 254)),
                             (800 + rng.uniform(-32, 32), rng.uniform(196, 254))]
                    if rng.random() < .88:
                        specs.append((505 + rng.uniform(-95, 95), rng.uniform(54, 96)))
                    if rng.random() < .42:
                        specs.append((985 + rng.uniform(-30, 30), rng.uniform(42, 78)))
                    root_scale, limb_scale = .48, .82
                for x, width in specs:
                    _bole(ctx, rng, x, rng.uniform(625, 690), rng.uniform(790, 940),
                          width, layer_index > 0, root_scale, limb_scale)
                ctx.restore()

            # Apply gradient mask to entire strip
            strip_image = _mask_image(surface, layer.top_gray, layer.bottom_gray, layer.blur)
            self.chunk_builds += 1

            # Make strip opaque by compositing with sky background for faster blitting.
            # The strip is drawn at y ≈ CHUNK_TOP (-160), so strip row 0 corresponds to sky row 160.
            sky = self._sky
            strip_w, strip_h = strip_image.get_width(), strip_image.get_height()
            sky_h = sky.get_height()
            # Visible sky rows: 160 to 719 (560 rows), then 240 rows of sky bottom color
            sky_top = max(0, -CHUNK_TOP)  # 160
            visible_sky_h = min(strip_h, sky_h - sky_top)  # 560

            # Create opaque background by tiling sky horizontally
            opaque_strip = pygame.Surface((strip_w, strip_h))
            # Tile sky horizontally for the visible portion
            sky_slice = sky.subsurface((0, sky_top, sky.get_width(), visible_sky_h))
            for x in range(0, strip_w, sky.get_width()):
                w = min(sky.get_width(), strip_w - x)
                opaque_strip.blit(sky_slice, (x, 0), (0, 0, w, visible_sky_h))
            # Fill remaining rows with sky bottom color
            if strip_h > visible_sky_h:
                bottom_color = sky.get_at((0, sky_h - 1))
                pygame.draw.rect(opaque_strip, bottom_color, (0, visible_sky_h, strip_w, strip_h - visible_sky_h))

            # Blit the masked trees on top
            opaque_strip.blit(strip_image, (0, 0))
            # Convert to canvas format (no alpha) for fast blitting
            strips.append(opaque_strip.convert())

        # Pre-render forest floor as a wide strip
        floor_chunks_needed = chunks_needed
        chunk_width = CHUNK_WIDTH + CHUNK_PAD * 2
        floor_strip_width = chunk_width * floor_chunks_needed
        surface, ctx = _canvas(floor_strip_width, 260, 1.5)
        width = floor_strip_width
        rng = self._rng(83, 1)
        crests = [(rng.uniform(0, width), rng.uniform(210, 480), rng.uniform(5, 26))
                  for _ in range(8 * floor_chunks_needed)]
        points = [(0, 260)]
        for x in range(0, width + 13, 12):
            height = 14 + max(h * math.exp(-((x - c) / s) ** 2) for c, s, h in crests)
            height += 2.2 * math.sin(x * .037) + 1.5 * math.sin(x * .091 + 1)
            points.append((x, 260 - height))
        points.append((width, 260))
        _poly(ctx, points, 4)
        for _ in range(420 * floor_chunks_needed):
            x = rng.uniform(0, width)
            crest = 260 - (14 + max(h * math.exp(-((x - c) / s) ** 2)
                                    for c, s, h in crests))
            length = rng.uniform(3, 18) * (.4 + rng.random() ** 2)
            _stroke(ctx, [(x, crest + 2), (x + rng.uniform(-8, 8), crest - length)],
                    4, rng.uniform(.5, 1.4))
        floor_image = _mask_image(surface, 3, 15, 1)
        self.chunk_builds += 1
        self._floor_strip = floor_image

        # Pre-render canopy as wider strip
        canopy_chunks_needed = 4
        canopy_width = 1600 * canopy_chunks_needed
        surface, ctx = _canvas(canopy_width, 230, 1.5)
        rng = self._rng(97, 1)
        lower = []
        for x in range(0, canopy_width + 12, 12):
            edge = (28 + 13 * math.sin(x * math.tau * 3 / canopy_width + .7)
                    + 7 * math.sin(x * math.tau * 8 / canopy_width + 2.1)
                    + 4 * math.sin(x * math.tau * 17 / canopy_width + .3))
            lower.append((x, max(5, edge)))
        _poly(ctx, [(0, 0), (canopy_width, 0), *reversed(lower)], 3)

        def leaf_cluster(cx, cy, radius):
            _circle(ctx, cx, cy, radius * .30, 3)
            for _ in range(rng.randrange(6, 12)):
                angle = rng.uniform(0, math.tau)
                distance = radius * rng.uniform(0, .72)
                x = cx + math.cos(angle) * distance
                y = cy + math.sin(angle) * distance * .55
                size = radius * rng.uniform(.42, .72)
                _poly(ctx, [(x, y - size), (x + size * .72, y + size * .18),
                            (x, y + size * .55), (x - size * .72, y + size * .18)], 3)

        for _ in range(26 * canopy_chunks_needed):
            x = rng.uniform(0, canopy_width)
            reach = rng.uniform(40, 152)
            drift = rng.uniform(-70, 70)
            mid = (x + drift * .45, 44 + reach * .5)
            tip = (x + drift, 38 + reach)
            for wrap in (-canopy_width, 0, canopy_width):
                _stroke(ctx, [(x + wrap, 18), (mid[0] + wrap, mid[1]), (tip[0] + wrap, tip[1])],
                        3, rng.uniform(1.0, 2.8))
                for t in (.28, .5, .72, .95):
                    lx = x + drift * t
                    ly = 18 + (reach - 18) * t
                    leaf_cluster(lx + wrap, ly, rng.uniform(4, 9))
        for _ in range(30 * canopy_chunks_needed):
            x = rng.uniform(0, canopy_width)
            y = rng.uniform(35, 82)
            radius = rng.uniform(4, 9)
            for wrap in (-canopy_width, 0, canopy_width):
                _stroke(ctx, [(x + wrap, 10), (x + wrap + rng.uniform(-5, 5), y)],
                        3, rng.uniform(.7, 1.5))
                leaf_cluster(x + wrap, y, radius)
                if rng.random() < .55:
                    leaf_cluster(x + wrap + rng.uniform(-8, 8), y + rng.uniform(8, 30),
                                 radius * .8)
        for _ in range(22 * canopy_chunks_needed):
            x = rng.uniform(0, canopy_width)
            y = rng.uniform(46, 112)
            radius = rng.uniform(6, 12)
            for wrap in (-canopy_width, 0, canopy_width):
                _stroke(ctx, [(x + wrap, 14), (x + wrap + rng.uniform(-7, 7), y)],
                        3, rng.uniform(.6, 1.4))
                leaf_cluster(x + wrap, y, radius)
        canopy_image = _mask_image(surface, 3, 3, 1)
        self.chunk_builds += 1
        self._canopy_strip = canopy_image

        # Pre-render fringe as wider strip
        fringe_chunks_needed = 4
        fringe_width = 1600 * fringe_chunks_needed
        surface, ctx = _canvas(fringe_width, 200, 1.5)
        rng = self._rng(113, 1)
        for _ in range(185 * fringe_chunks_needed):
            x = rng.uniform(0, fringe_width)
            tall = rng.uniform(30, 142)
            spread = rng.uniform(4, 19)
            for blade in range(rng.randrange(4, 13)):
                bx = x + rng.uniform(-spread, spread)
                length = tall * rng.uniform(.30, 1)
                lean = rng.uniform(-.55, .7) * length
                for wrap in (-fringe_width, 0, fringe_width):
                    _stroke(ctx, [(bx + wrap, 200 + 4),
                                  (bx + wrap + lean * .4, 200 - length * .58),
                                  (bx + wrap + lean, 200 - length)], 3,
                            rng.uniform(.8, 2.3))
        fringe_image = _mask_image(surface, 3, 3, 1)
        self.chunk_builds += 1
        self._fringe_strip = fringe_image

        return strips

    def _chunk(self, layer_index, index):
        key = (layer_index, index)
        if key in self.chunks:
            self.chunks.move_to_end(key)
            return self.chunks[key]
        layer = LAYERS[layer_index]
        rng = self._rng(layer_index + 11, index)
        surface, ctx = _canvas(CHUNK_WIDTH + CHUNK_PAD * 2, CHUNK_HEIGHT)
        ctx.translate(CHUNK_PAD, 0)
        if layer_index == 0:
            # Many pale needles in the fog imply depth behind the play space.
            centers = [n * 88 + rng.uniform(-26, 26) for n in range(13)]
            widths = (21, 57)
            specs = [(x, rng.uniform(*widths)) for x in centers]
            root_scale, limb_scale = .8, .9
        elif layer_index == 1:
            centers = [62 + rng.uniform(-40, 40), 402 + rng.uniform(-68, 68),
                       744 + rng.uniform(-58, 58), 1024 + rng.uniform(-36, 36)]
            widths = (54, 106)
            specs = [(x, rng.uniform(*widths)) for x in centers]
            root_scale, limb_scale = .85, .9
        else:
            # Two monumental boles frame the fog in every tile; smaller trunks
            # subdivide the remaining light without turning it into a wall.
            specs = [(220 + rng.uniform(-32, 32), rng.uniform(196, 254)),
                     (800 + rng.uniform(-32, 32), rng.uniform(196, 254))]
            if rng.random() < .88:
                specs.append((505 + rng.uniform(-95, 95), rng.uniform(54, 96)))
            if rng.random() < .42:
                specs.append((985 + rng.uniform(-30, 30), rng.uniform(42, 78)))
            root_scale, limb_scale = .48, .82
        for x, width in specs:
            _bole(ctx, rng, x, rng.uniform(625, 690), rng.uniform(790, 940),
                  width, layer_index > 0, root_scale, limb_scale)
        image = _mask_image(surface, layer.top_gray, layer.bottom_gray, layer.blur)
        self.chunk_builds += 1
        return _remember(self.chunks, key, image, 12)

    def draw_background(self, game):
        screen, camera = game.canvas, game.camera
        # Sky blit is fast (no alpha). Layer strips now have sky baked in.
        screen.blit(self._sky, (0, 0))
        for index, layer in enumerate(LAYERS):
            offset = camera * self.zoom * layer.parallax
            y = CHUNK_TOP - (game.camera_y - 210) * self.zoom * layer.parallax * .16
            # Use pre-rendered opaque strip - just one blit per layer per frame
            strip = self._layer_strips[index]
            strip_width = strip.get_width()
            # Calculate source x within the strip
            src_x = (offset + CHUNK_PAD) % strip_width
            # Handle wrap-around if the source rect crosses the strip boundary
            if src_x + self.size[0] <= strip_width:
                src_rect = pygame.Rect(round(src_x), 0, self.size[0], strip.get_height())
                screen.blit(strip, (0, round(y)), src_rect)
            else:
                # Need two blits for wrap-around
                first_width = strip_width - src_x
                src_rect1 = pygame.Rect(round(src_x), 0, first_width, strip.get_height())
                screen.blit(strip, (0, round(y)), src_rect1)
                src_rect2 = pygame.Rect(0, 0, self.size[0] - first_width, strip.get_height())
                screen.blit(strip, (first_width, round(y)), src_rect2)
        # Single combined atmosphere overlay (veil + fog) instead of 3 separate blits.
        # The subtle vertical animation is removed for performance.
        screen.blit(self._atmosphere_overlay, (0, 0))
        self.draw_canopy(game)
        self._draw_forest_floor(game)

    def _floor(self):
        if "floor" in self.chunks:
            return self.chunks["floor"]
        rng = self._rng(83, 1)
        surface, ctx = _canvas(CHUNK_WIDTH + CHUNK_PAD * 2, 260, 1.5)
        width = CHUNK_WIDTH + CHUNK_PAD * 2
        crests = [(rng.uniform(0, width), rng.uniform(210, 480), rng.uniform(5, 26))
                  for _ in range(8)]
        points = [(0, 260)]
        for x in range(0, width + 13, 12):
            height = 14 + max(h * math.exp(-((x - c) / s) ** 2) for c, s, h in crests)
            height += 2.2 * math.sin(x * .037) + 1.5 * math.sin(x * .091 + 1)
            points.append((x, 260 - height))
        points.append((width, 260))
        _poly(ctx, points, 4)
        # Undergrowth is deliberately finer than the platform silhouette. It
        # closes the background without becoming a second playable surface.
        for _ in range(420):
            x = rng.uniform(0, width)
            crest = 260 - (14 + max(h * math.exp(-((x - c) / s) ** 2)
                                    for c, s, h in crests))
            length = rng.uniform(3, 18) * (.4 + rng.random() ** 2)
            _stroke(ctx, [(x, crest + 2), (x + rng.uniform(-8, 8), crest - length)],
                    4, rng.uniform(.5, 1.4))
        image = _mask_image(surface, 3, 15, 1)
        self.chunk_builds += 1
        return _remember(self.chunks, "floor", image, 12)

    def _canopy(self):
        """A wrapping, near-black leaf canopy that frames the fog and trunks."""
        if "canopy" in self.chunks:
            return self.chunks["canopy"]
        rng = self._rng(97, 1)
        width, height = 1600, 230
        surface, ctx = _canvas(width, height, 1.5)
        lower = []
        for x in range(0, width + 12, 12):
            edge = (28 + 13 * math.sin(x * math.tau * 3 / width + .7)
                    + 7 * math.sin(x * math.tau * 8 / width + 2.1)
                    + 4 * math.sin(x * math.tau * 17 / width + .3))
            lower.append((x, max(5, edge)))
        _poly(ctx, [(0, 0), (width, 0), *reversed(lower)], 3)

        def leaf_cluster(cx, cy, radius):
            # A compact core keeps the leaves reading as one clump rather than
            # a scatter of separate beads on a string.
            _circle(ctx, cx, cy, radius * .30, 3)
            for _ in range(rng.randrange(6, 12)):
                angle = rng.uniform(0, math.tau)
                distance = radius * rng.uniform(0, .72)
                x = cx + math.cos(angle) * distance
                y = cy + math.sin(angle) * distance * .55
                size = radius * rng.uniform(.42, .72)
                # A pointed leaf, wider at the base than the tip.
                _poly(ctx, [(x, y - size), (x + size * .72, y + size * .18),
                            (x, y + size * .55), (x - size * .72, y + size * .18)], 3)

        # Branches descend from the ceiling and break the pale negative space.
        for _ in range(26):
            x = rng.uniform(0, width)
            reach = rng.uniform(40, 152)
            drift = rng.uniform(-70, 70)
            mid = (x + drift * .45, 44 + reach * .5)
            tip = (x + drift, 38 + reach)
            for wrap in (-width, 0, width):
                _stroke(ctx, [(x + wrap, 18), (mid[0] + wrap, mid[1]), (tip[0] + wrap, tip[1])],
                        3, rng.uniform(1.0, 2.8))
                for t in (.28, .5, .72, .95):
                    lx = x + drift * t
                    ly = 18 + (reach - 18) * t
                    leaf_cluster(lx + wrap, ly, rng.uniform(4, 9))
        for _ in range(30):
            x = rng.uniform(0, width)
            y = rng.uniform(35, 82)
            radius = rng.uniform(4, 9)
            for wrap in (-width, 0, width):
                _stroke(ctx, [(x + wrap, 10), (x + wrap + rng.uniform(-5, 5), y)],
                        3, rng.uniform(.7, 1.5))
                leaf_cluster(x + wrap, y, radius)
                if rng.random() < .55:
                    leaf_cluster(x + wrap + rng.uniform(-8, 8), y + rng.uniform(8, 30),
                                 radius * .8)
        for _ in range(22):
            x = rng.uniform(0, width)
            y = rng.uniform(46, 112)
            radius = rng.uniform(6, 12)
            for wrap in (-width, 0, width):
                _stroke(ctx, [(x + wrap, 14), (x + wrap + rng.uniform(-7, 7), y)],
                        3, rng.uniform(.6, 1.4))
                leaf_cluster(x + wrap, y, radius)
        image = _mask_image(surface, 3, 3, 1)
        self.chunk_builds += 1
        return _remember(self.chunks, "canopy", image, 12)

    def _fringe(self):
        """Near-black grass at the bottom edge, closer than the courier."""
        if "fringe" in self.chunks:
            return self.chunks["fringe"]
        rng = self._rng(113, 1)
        width, height = 1600, 200
        surface, ctx = _canvas(width, height, 1.5)
        for _ in range(185):
            x = rng.uniform(0, width)
            tall = rng.uniform(30, 142)
            spread = rng.uniform(4, 19)
            for blade in range(rng.randrange(4, 13)):
                bx = x + rng.uniform(-spread, spread)
                length = tall * rng.uniform(.30, 1)
                lean = rng.uniform(-.55, .7) * length
                for wrap in (-width, 0, width):
                    _stroke(ctx, [(bx + wrap, height + 4),
                                  (bx + wrap + lean * .4, height - length * .58),
                                  (bx + wrap + lean, height - length)], 3,
                            rng.uniform(.8, 2.3))
        image = _mask_image(surface, 3, 3, 1)
        self.chunk_builds += 1
        return _remember(self.chunks, "fringe", image, 12)

    def draw_canopy(self, game):
        """Draw canopy using pre-rendered wide strip - single blit per frame."""
        strip = self._canopy_strip
        span = strip.get_width()
        shift = int(game.camera * self.zoom * .90) % span
        y = round(-14 - (game.camera_y - 210) * .035)
        # Handle wrap-around
        if shift + self.size[0] <= span:
            src_rect = pygame.Rect(shift, 0, self.size[0], strip.get_height())
            game.canvas.blit(strip, (0, y), src_rect)
        else:
            first_width = span - shift
            src_rect1 = pygame.Rect(shift, 0, first_width, strip.get_height())
            game.canvas.blit(strip, (0, y), src_rect1)
            src_rect2 = pygame.Rect(0, 0, self.size[0] - first_width, strip.get_height())
            game.canvas.blit(strip, (first_width, y), src_rect2)

    def _draw_forest_floor(self, game):
        """A closed horizon unifies the generated platforms without collision."""
        # Use pre-rendered wide floor strip - single blit per frame
        strip = self._floor_strip
        offset = game.camera * self.zoom * .84
        span = strip.get_width()
        shift = round(offset + CHUNK_PAD) % span
        ground_y = game._point((0, game.forest_ground))[1]
        y = ground_y - 238
        # Handle wrap-around
        if shift + self.size[0] <= span:
            src_rect = pygame.Rect(shift, 0, self.size[0], strip.get_height())
            game.canvas.blit(strip, (0, y), src_rect)
        else:
            first_width = span - shift
            src_rect1 = pygame.Rect(shift, 0, first_width, strip.get_height())
            game.canvas.blit(strip, (0, y), src_rect1)
            src_rect2 = pygame.Rect(0, 0, self.size[0] - first_width, strip.get_height())
            game.canvas.blit(strip, (first_width, y), src_rect2)

    def _ground(self, rect, reserved, density):
        # Simplified cache key - reserved areas only affect grass length near switches
        # which is a minor visual detail. This ensures terrain is cached per platform.
        density_key = round(density, 2)
        key = (rect.x, rect.y, rect.w, density_key)
        if key in self.terrain:
            self.terrain.move_to_end(key)
            return self.terrain[key]
        width = math.ceil(rect.w * self.zoom)
        pad = GROUND_PAD
        surface, ctx = _canvas(width + pad * 2, 800)
        rng = self._rng(40, round(rect.x * 17))
        ctx.translate(pad, 80)
        # The top edge is the exact collision surface (plus a two-pixel moss
        # lip). Below it the face erodes outward and dissolves into black earth,
        # so a platform never reads as a floating rectangular bar.
        flare = min(118, width * .24)
        left, right = [], []
        for y in range(0, 148, 12):
            wobble = rng.uniform(0, 9)
            left.append((-flare * y / 720 - wobble, y))
            right.append((width + flare * y / 720 + rng.uniform(0, 9), y))
        ctx.new_path()
        ctx.move_to(0, -2)
        ctx.line_to(width, -2)
        for x, y in right:
            ctx.line_to(x, y)
        ctx.line_to(width + flare, 720)
        ctx.line_to(-flare, 720)
        for x, y in reversed(left):
            ctx.line_to(x, y)
        ctx.close_path()
        _tone(ctx, 4)
        ctx.fill()
        # Barely separated strata and cracks keep the mass readable as earth
        # without lifting it off the black ground plane.
        for depth in (16, 34, 62, 104, 172, 280):
            points = [(0, depth)]
            for x in range(0, width + 16, 16):
                points.append((x, depth + 2.4 * math.sin(x * .031 + depth)
                               + 1.4 * math.sin(x * .087 + depth * .3)))
            _stroke(ctx, points, rng.choice((7, 8, 10)), rng.uniform(.8, 1.8))
        for _ in range(max(3, round(width / 150))):
            x = rng.uniform(4, width - 4)
            _stroke(ctx, [(x, 3), (x + rng.uniform(-5, 5), rng.uniform(16, 58)),
                          (x + rng.uniform(-9, 9), rng.uniform(40, 130))],
                    rng.choice((7, 9, 12)), rng.uniform(.6, 1.4))
        for _ in range(max(2, round(width / 210))):
            x = rng.uniform(2, width - 2)
            _stroke(ctx, [(x, 2), (x + rng.uniform(-2, 2), rng.uniform(14, 40)),
                          (x + rng.uniform(-5, 5), rng.uniform(30, 72))],
                    rng.choice((12, 15, 18)), .8)
        # Overhanging roots and grass reach into the luminous gap; they are
        # visual only and do not change the controller's collision surface.
        for side, direction in ((0, -1), (width, 1)):
            for _ in range(9):
                x = side + direction * rng.uniform(0, 8)
                reach = rng.uniform(6, 34)
                _stroke(ctx, [(x, rng.uniform(0, 7)),
                              (x + direction * reach * .55, rng.uniform(8, 22)),
                              (x + direction * reach, rng.uniform(24, 62))],
                        14, rng.uniform(.6, 1.5))
            for _ in range(8):
                _stroke(ctx, [(side + direction * rng.uniform(0, 14), 2),
                              (side + direction * rng.uniform(8, 40), -rng.uniform(6, 26))],
                        5, rng.uniform(.7, 1.6))
        clumps = [(rng.uniform(0, width), rng.uniform(17, 62), rng.uniform(24, 82))
                  for _ in range(max(3, round(width / 100)))]
        # A fine, continuous nap of short blades makes the collision lip read as
        # an overgrown verge instead of a cut rectangle.
        for x in np.arange(.5, width, 1.15):
            length = rng.uniform(.8, 5.2) + 5 * rng.random() ** 3
            lean = rng.uniform(-.7, .7) * length
            _stroke(ctx, [(x, 2), (x + lean, 2 - length)], rng.choice((5, 6, 8)), .55)
        for _ in range(max(1, int(width * 1.38 * density))):
            x = rng.uniform(1, width - 1)
            world_x = rect.x + x / self.zoom
            protected = any(r.x - 12 <= world_x <= r.x + r.w + 12 for r in reserved)
            clump = max(height * math.exp(-((x - center) / spread) ** 2)
                        for center, spread, height in clumps)
            length = rng.uniform(3, 9) + clump * rng.uniform(.18, 1)
            if protected:
                length = min(6, length)
            lean = rng.uniform(-.6, 1.15) * length
            tip = max(1, min(width - 1, x + lean))
            blade_width = rng.uniform(.35, 1.5)
            ctx.new_path()
            ctx.move_to(x - blade_width, 2)
            ctx.curve_to(x - 1, -length * .24, tip - lean * .38, -length * .76, tip, -length)
            ctx.curve_to(tip - lean * .10, -length * .59, x + blade_width, -length * .15,
                         x + blade_width, 2)
            ctx.close_path()
            _tone(ctx, rng.choice((4, 5, 7, 10)))
            ctx.fill()
        # Ferns interrupt long grass rows with recognisable soft silhouettes.
        for _ in range(max(1, round(width / 240))):
            x, base = rng.uniform(6, width - 6), rng.uniform(2, 7)
            for leaf in range(4):
                span = rng.uniform(11, 26) * (1 - leaf * .17)
                _stroke(ctx, [(x, base), (x - span, base - rng.uniform(4, 14)),
                              (x - span * .32, base - rng.uniform(7, 19))], 5, 1.3)
                _stroke(ctx, [(x, base), (x + span, base - rng.uniform(3, 12)),
                              (x + span * .30, base - rng.uniform(8, 21))], 5, 1.3)
        # Short torn roots retain the readable vertical lip at either edge.
        for side in (0, width - 1):
            for _ in range(8):
                x = side + (1 if side == 0 else -1) * rng.uniform(1, 14)
                _stroke(ctx, [(x, 1), (x + rng.uniform(-3, 3), rng.uniform(20, 55))], 14, .7)
        return _remember(self.terrain, key, _mask_image(surface, 4, 4, 1), 100)

    def draw_terrain(self, game):
        world = game.world
        player_x = world.player.position.x
        cleanup_distance = world.config.cleanup_distance
        threshold = player_x - cleanup_distance
        for key in list(self.terrain):
            # key = (rect.x, rect.y, rect.w, density_key)
            if key[0] + key[2] < threshold:
                del self.terrain[key]
        for rect in world.terrain_rects():
            x, y = game._point((rect.x, rect.y))
            if x + rect.w * self.zoom < 0 or x > self.size[0]:
                continue
            challenge = next((c for c in world.challenges
                              if any(p.id == c.platform_id and p.x == rect.x for p in world.generated_platforms)), None)
            hazards = [h for h in world.generated_hazards if rect.x <= h.x <= rect.x + rect.w]
            reserved = reserved_rects(challenge, hazards)
            density = round(world.config.environment_density, 2)
            image = self._ground(rect, reserved, density)
            game.canvas.blit(image, (x - GROUND_PAD, y - 80))

    def _prop(self, item):
        key = (item.kind, item.id, item.width, item.height)
        if key in self.props:
            self.props.move_to_end(key)
            return self.props[key]
        w, h = item.width * self.zoom, item.height * self.zoom
        surface, ctx = _canvas(w + 4, h + 4, 2)
        ctx.translate(2, 2)
        rng = self._rng(51, item.id)
        if item.kind == "tree":
            # A crooked solid sapling, not the old regular conifer line diagram.
            root, top = w * .48, w * rng.uniform(.40, .62)
            ctx.new_path()
            ctx.move_to(root - 8, h)
            ctx.curve_to(root - 3, h * .61, top - 5, h * .24, top, 0)
            ctx.curve_to(top + 4, h * .29, root + 4, h * .72, root + 11, h)
            ctx.close_path()
            _tone(ctx, 17)
            ctx.fill()
            for direction in (-1, 1):
                _stroke(ctx, [(root, h * .65), (root + direction * w * .26, h * .39),
                              (root + direction * w * .34, h * .16)], 17, 2)
        elif item.kind == "bamboo":
            for i in range(3 + item.variant):
                x = (i + 1) * w / (4 + item.variant)
                top = rng.uniform(0, h * .18)
                _stroke(ctx, [(x, h), (x - 3, h * .46), (x + 1, top)], 15, 2.1)
                for y in np.arange(top + 15, h, 24):
                    _poly(ctx, [(x, y), (min(w, x + 12), y - 12), (x + 4, y - 3)], 17)
        elif item.kind == "wood":
            _poly(ctx, [(0, h * .36), (w * .17, h * .21), (w * .77, 0), (w, h * .27),
                        (w * .92, h), (w * .05, h)], 5)
            _stroke(ctx, [(w * .16, h * .44), (w * .76, h * .19)], 20, .8)
        elif item.kind == "rock":
            _poly(ctx, [(0, h), (w * .08, h * .35), (w * .36, h * .10),
                        (w * .65, 0), (w * .89, h * .20), (w, h)], 4)
        elif item.kind == "grass":
            for _ in range(19):
                x = rng.uniform(1, w - 1)
                _poly(ctx, [(x - 1, h), (max(0, min(w, x + rng.uniform(-9, 9))), rng.uniform(0, h * .65)),
                            (x + 1, h)], 5)
        else:
            for _ in range(12):
                _stroke(ctx, [(rng.uniform(0, w), rng.uniform(0, h)),
                              (rng.uniform(0, w), rng.uniform(0, h))], 10, .65)
        image = pygame.transform.smoothscale(_image(surface), (math.ceil(w + 4), math.ceil(h + 4)))
        return _remember(self.props, key, image, 160)

    def draw_environment(self, game, layer):
        items = game.world.environment_objects
        live = {item.id for item in items}
        for key in list(self.props):
            if key[1] not in live:
                del self.props[key]
        for item in items:
            if item.layer != layer:
                continue
            x, y = game._point((item.x, item.y))
            if x + item.width * self.zoom < 0 or x > self.size[0]:
                continue
            game.canvas.blit(self._prop(item), (x - 2, y - 2))

    def _player_frames(self):
        frames = {}
        for frame in range(12):
            surface, ctx = _canvas(64, 88, 2)
            ctx.translate(32, 45)
            ctx.scale(self.zoom, self.zoom)
            walk = 2 <= frame <= 9
            phase = (frame - 2) / 8 * math.tau if walk else 0
            stride = math.sin(phase) * 4 if walk else .2
            airborne = frame >= 10
            for side in (-1, 1):
                knee = (side * 2 + stride * side * .6, 18)
                foot = (side * 2 + stride * side, 25 - max(0, -stride * side) * .32)
                if airborne:
                    knee, foot = (side * 5, 15), (side * 7 + 1, 21 if frame == 10 else 25)
                _stroke(ctx, [(side * 2, 10), knee, foot], 3, 2.2)
                _stroke(ctx, [foot, (foot[0] + 1.6, foot[1])], 3, 1.7)
            ctx.new_path()
            ctx.move_to(-3, -7)
            ctx.curve_to(-6, -2, -5, 9, -3.8, 12)
            ctx.line_to(3.5, 12)
            ctx.curve_to(5, 8, 4, -3, 2.5, -7)
            ctx.close_path()
            _tone(ctx, 3)
            ctx.fill()
            arm = math.sin(phase + math.pi) * 2 if walk else .4
            _stroke(ctx, [(3.1, -4), (4.5 + arm, 3), (4 + arm, 10)], 3, 2)
            _stroke(ctx, [(0, -7), (.3, -10)], 3, 3)
            ctx.save()
            ctx.translate(-.7, -15.9)
            ctx.rotate(-.09)
            ctx.scale(1.03, 1.08)
            _circle(ctx, 0, 0, 6.8, 3)
            ctx.restore()
            # Rounded hair and a small uneven forelock break a geometric head.
            _poly(ctx, [(-7, -18), (-5, -22), (-1, -24), (4, -24.3),
                        (7.1, -22.5), (5.4, -20.5), (6.4, -18.6), (1, -18)], 3)
            for x, y in ((1.7, -15.7), (5.3, -16.2)):
                _circle(ctx, x, y, 2.0, 220, .05)
                _circle(ctx, x, y, 1.2, 229, .13)
                _circle(ctx, x, y, .68, 239, .9)
                _circle(ctx, x + .1, y - .1, .32, 255)
            image = pygame.transform.smoothscale(_image(surface), (64, 88))
            for facing in (-1, 1):
                frames[(frame, facing)] = pygame.transform.flip(image, facing < 0, False)
        return frames

    def draw_player(self, game):
        w = game.world
        vx, vy = w.player.velocity
        if not w.grounded:
            frame = 10 if vy < 0 else 11
        elif abs(vx) > 12:
            frame = 2 + int(game.visual_time * min(13, 5 + abs(vx) / 24)) % 8
        else:
            frame = int(game.visual_time * 1.5) % 2
        x, y = game._point(w.player.position)
        game.canvas.blit(self._players[(frame, -1 if w.facing < 0 else 1)], (x - 32, y - 45))

    def draw_prompts(self, game):
        """Context prompts sit above the courier, never underneath them."""
        w, screen = game.world, game.canvas
        for challenge in w.challenges:
            for switch in challenge.switches:
                if w.player.position.get_distance((switch.x, switch.y)) >= switch.radius + 8:
                    continue
                sx, sy = game._point((switch.x, switch.y))
                if not -40 < sx < self.size[0] + 40:
                    continue
                active = switch.id in w.active_switches
                label = "Lit" if active else ("E · light" if w.lantern_on else "L · lantern")
                image = game.fonts[14].render(label, True, LIGHT)
                rect = image.get_rect(midbottom=(sx, sy - max(46, round(48 * self.zoom))))
                plate = pygame.Surface((rect.w + 16, rect.h + 8), pygame.SRCALPHA)
                plate.fill((0, 0, 0, 132))
                screen.blit(plate, (rect.x - 8, rect.y - 4))
                screen.blit(image, rect)

    def _halo(self, radius, opacity):
        key = (radius, opacity)
        if key not in self._halos:
            yy, xx = np.mgrid[-radius:radius, -radius:radius]
            falloff = np.maximum(0, 1 - np.sqrt(xx * xx + yy * yy) / radius) ** 2
            image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            image.fill((205, 205, 205, 0))
            pixels = pygame.surfarray.pixels_alpha(image)
            pixels[:] = (falloff.T * opacity).astype(np.uint8)
            del pixels
            _remember(self._halos, key, image, 16)
        return self._halos[key]

    def draw_lantern(self, game):
        if not game.world.lantern_on:
            return
        radius = round(game.world.lantern_radius * self.zoom / 12) * 12
        x, y = game._point(game.world.player.position)
        game.canvas.blit(self._halo(radius, 22), (x - radius, y - radius))

    def draw_saws(self, game):
        for x, y, radius in game.world.saw_positions():
            sx, sy = game._point((x, y))
            r = round(radius * self.zoom)
            if sx + r < 0 or sx - r > self.size[0]:
                continue
            # Use 60 pre-rendered angles (6° steps) instead of per-frame degree
            degree = round(game.visual_time * 240 / 6) * 6 % 360
            angle_index = degree // 6  # 0-59
            key = (r, angle_index)
            if key not in self.saws:
                surface, ctx = _canvas(r * 2 + 8, r * 2 + 8, 2)
                center = r + 4
                angle_deg = angle_index * 6
                teeth = []
                for tooth in range(20):
                    for offset, length in ((0, .84), (.2, 1), (.65, .91), (.75, .83)):
                        a = (tooth + offset) * math.tau / 20 + math.radians(angle_deg)
                        teeth.append((center + math.cos(a) * r * length,
                                      center + math.sin(a) * r * length))
                _poly(ctx, teeth, 8)
                _circle(ctx, center, center, r * .72, 37)
                _circle(ctx, center, center, r * .68, 7)
                _circle(ctx, center, center, r * .15, 106)
                image = pygame.transform.smoothscale(_image(surface), (r * 2 + 8, r * 2 + 8))
                _remember(self.saws, key, image, 180)
            image = self.saws[key]
            game.canvas.blit(image, image.get_rect(center=(sx, sy)))

    def draw_puzzles(self, game):
        """Render active multi-step puzzle objects and readable objectives."""
        for runtime in game.world.puzzle_runtimes.values():
            plate = runtime.plate
            px, py = game._point((plate.x, plate.y))
            pw, ph = max(2, round(plate.w * self.zoom)), max(3, round(plate.h * self.zoom))
            if px + pw < 0 or px > self.size[0]:
                continue

            active_color = (177, 211, 193) if runtime.solved else (114, 145, 133)
            plate_rect = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(game.canvas, (22, 30, 31), plate_rect)
            pygame.draw.rect(game.canvas, active_color, plate_rect, max(1, round(2 * self.zoom)))
            for offset in range(8, max(8, pw - 4), 12):
                pygame.draw.line(game.canvas, (49, 65, 62),
                                 (px + offset, py + ph - 1),
                                 (px + offset + 5, py + 1), 1)

            gate = runtime.gate
            gx, gy = game._point(runtime.gate_body.position)
            gw, gh = max(2, round(gate.w * self.zoom)), max(2, round(gate.h * self.zoom))
            if gx + gw / 2 >= 0 and gx - gw / 2 <= self.size[0]:
                gate_rect = pygame.Rect(round(gx - gw / 2), round(gy - gh / 2), gw, gh)
                pygame.draw.rect(game.canvas, (18, 24, 26), gate_rect)
                pygame.draw.rect(game.canvas, active_color if runtime.solved else (68, 83, 81),
                                 gate_rect, max(1, round(self.zoom)))
                for offset in range(8, max(8, gh - 4), 18):
                    pygame.draw.line(game.canvas, (43, 54, 53),
                                     (gate_rect.left + 3, gate_rect.top + offset),
                                     (gate_rect.right - 3, gate_rect.top + offset), 1)
                for dx in (4, gw - 4):
                    pygame.draw.line(game.canvas, (80, 99, 94),
                                     (gate_rect.left + dx, gate_rect.top),
                                     (gate_rect.left + dx, gate_rect.bottom), 2)

            label = "SEAL OPEN" if runtime.solved else "PULL CRATE ONTO PLATE"
            game.text(label, px + pw // 2, py - 28, 14, active_color, center=True)
            player = game.world.player.position
            crate_pos = runtime.crate.body.position
            if not runtime.solved and player.get_distance(crate_pos) < 112:
                sx, sy = game._point(player)
                instruction = ("HOLD E + PULL LEFT" if runtime.crate_was_grabbed
                               else "JUMP PAST IT · HOLD E TO GRAB")
                game.text(instruction, sx, sy - 58, 14, LIGHT, center=True)

    def draw_challenges(self, game):
        w, screen, z = game.world, game.canvas, self.zoom
        lantern_on = w.lantern_on
        for challenge in w.challenges:
            for shadow in challenge.shadows:
                x, y = game._point((shadow.x, shadow.y))
                width, height = round(shadow.width * z), round(shadow.height * z)
                if x + width < 0 or x > self.size[0]:
                    continue
                # Cache shadow surfaces by (width, height, lantern_on) to avoid per-frame allocation
                shadow_key = (width, height, lantern_on)
                if shadow_key not in self._shadows:
                    field = pygame.Surface((width, height), pygame.SRCALPHA)
                    strength = 30 if lantern_on else 145
                    for n in range(0, width, 5):
                        top = round(height * (.23 + .13 * math.sin(n * .37)))
                        pygame.draw.line(field, (4, 4, 4, strength), (n, height), (n + 5, top), 3)
                    self._shadows[shadow_key] = field
                    # Limit cache size
                    while len(self._shadows) > 64:
                        self._shadows.popitem(last=False)
                screen.blit(self._shadows[shadow_key], (x, y))
            for cache in challenge.caches:
                sx, sy = game._point((cache.x, cache.y))
                if not -40 < sx < self.size[0] + 40:
                    continue
                used = cache.id in w.used_caches
                if not used:
                    screen.blit(self._halo(48, 40), (sx - 48, sy - 48))
                pygame.draw.line(screen, (16, 16, 16), (sx, sy + 4), (sx, sy + round(19 * z)), 3)
                pygame.draw.circle(screen, (69, 69, 69) if used else LIGHT, (sx, sy), 3 if used else 4)
            for barrier in challenge.barriers:
                if not w._barrier_is_active(barrier):
                    continue
                r = barrier.rect
                x, y = game._point((r.x, r.y))
                width, height = round(r.w * z), round(r.h * z)
                if x + width < 0 or x > self.size[0]:
                    continue
                # A sealed monolith, not a ladder: a faint vertical seam fades
                # toward the base, and only irregular cracks interrupt it.
                pygame.draw.polygon(screen, INK, [
                    (x, y + 5), (x + width * .22, y), (x + width - 2, y + 4),
                    (x + width - 1, y + height), (x + 1, y + height)])
                for offset, tone in ((.16, 22), (.36, 34), (.64, 29), (.84, 18)):
                    sx = x + round(width * offset)
                    pygame.draw.line(screen, (tone, tone, tone),
                                     (sx, y + 9), (sx + round((offset - .5) * 4),
                                                   y + height - 7), 1)
                seam = x + width // 2
                span = max(1, height - 18)
                for step in range(0, span, 3):
                    fade = max(24, round(132 * (1 - step / span) ** .72))
                    pygame.draw.line(screen, (fade, fade, fade),
                                     (seam, y + 9 + step), (seam, y + 11 + step), 1)
                pygame.draw.line(screen, (57, 57, 57), (x + 2, y + 9),
                                 (x + width - 2, y + 9), 1)
                pygame.draw.line(screen, (57, 57, 57), (x + 2, y + height - 8),
                                 (x + width - 2, y + height - 8), 1)
                ward = y + round(height * .30)
                pygame.draw.polygon(screen, (122, 122, 122),
                                    [(seam, ward - 4), (seam + 3, ward),
                                     (seam, ward + 4), (seam - 3, ward)], 1)
                pygame.draw.line(screen, (37, 37, 37), (x + 3, y + round(height * .55)),
                                 (x + width - 3, y + round(height * .5) + 5), 1)
            for switch in challenge.switches:
                sx, sy = game._point((switch.x, switch.y))
                if not -40 < sx < self.size[0] + 40:
                    continue
                active = switch.id in w.active_switches
                pole = pygame.Rect(sx - max(2, round(2 * z)), sy,
                                   max(4, round(4 * z)), round(35 * z))
                pygame.draw.rect(screen, INK, pole)
                pygame.draw.line(screen, (62, 62, 62), (pole.x, pole.y),
                                 (pole.x, pole.bottom), 1)
                pygame.draw.circle(screen, LIGHT if active else (142, 142, 142),
                                   (sx, sy), max(5, round(6 * z)), max(1, round(1.2 * z)))
                pygame.draw.circle(screen, INK, (sx, sy), max(2, round(2.4 * z)))
                if active:
                    screen.blit(self._halo(30, 24), (sx - 30, sy - 30))
            for enemy in challenge.enemies:
                state = w.enemy_states.get(enemy.id)
                if state is None:
                    continue
                rect = enemy.rect_at(state.x)
                x, y = game._point((rect.x, rect.y))
                width, height = round(rect.w * z), round(rect.h * z)
                if x + width < 0 or x > self.size[0]:
                    continue
                pygame.draw.ellipse(screen, INK, (x, y, width, height))
                eye = (170, 170, 170) if state.stun else (226, 226, 226)
                for dx in (.32, .65):
                    pygame.draw.circle(screen, eye, (x + round(width * dx), y + height // 3), 2)

    def draw_foreground(self, game):
        # A near-black grass fringe gives the frame a foreground plane while
        # staying below the courier's feet.
        strip = self._fringe_strip
        span = strip.get_width()
        shift = int(game.camera * self.zoom * 1.18) % span
        # Single blit with wrap handling
        if shift + self.size[0] <= span:
            src_rect = pygame.Rect(shift, 0, self.size[0], strip.get_height())
            game.canvas.blit(strip, (0, 340), src_rect)
        else:
            first_width = span - shift
            src_rect1 = pygame.Rect(shift, 0, first_width, strip.get_height())
            game.canvas.blit(strip, (0, 340), src_rect1)
            src_rect2 = pygame.Rect(0, 0, self.size[0] - first_width, strip.get_height())
            game.canvas.blit(strip, (first_width, 340), src_rect2)
        # Vignette darkens the edges; film grain animation removed for performance.
        game.canvas.blit(self._vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def warm_chunks(self, camera_x, camera_y):
        """Pre-generate chunks visible at the given camera position to avoid frame hitches."""
        # Warm all three parallax layers for chunks in view range
        for layer_index, layer in enumerate(LAYERS):
            offset = camera_x * self.zoom * layer.parallax
            first = math.floor((offset - CHUNK_PAD) / CHUNK_WIDTH)
            last = math.floor((offset + self.size[0] + CHUNK_PAD) / CHUNK_WIDTH)
            for chunk in range(first, last + 1):
                self._chunk(layer_index, chunk)
        # Warm canopy, floor, and fringe
        self._canopy()
        self._floor()
        self._fringe()

    def snapshot(self):
        return {"style": "monochrome_forest", "seed": self.seed, "zoom": self.zoom,
                "chunk_builds": self.chunk_builds, "cached_chunks": len(self.chunks),
                "cached_terrain": len(self.terrain), "cached_props": len(self.props),
                "cached_saws": len(self.saws), "layers": [layer.name for layer in LAYERS]}
