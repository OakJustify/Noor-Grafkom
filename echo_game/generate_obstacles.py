"""Generate ECHO's obstacle assets by composing the block primitives.

Usage: .venv-echo/bin/python -m echo_game.generate_obstacles [--force] [--size 256]

Obstacles are primitive-based models: each one is a short, fixed list of
transformed copies of the PNGs in assets/block (solid, flat and outline).
Layers are tinted with a grey multiply, so every output pixel stays greyscale
and the game can colour whole obstacles at runtime with a seeded RNG. Nothing
here initializes a display, mixer, network or external tools.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import cairo
import numpy as np

from . import generate_blocks

CANVAS = 256
OBSTACLE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "obstacle"
BLOCK_ROOT = generate_blocks.BLOCK_ROOT


class Layer:
    """One primitive placed on the canvas: shape, position, rotation, shade."""

    __slots__ = ("shape", "style", "x", "y", "size", "rotation", "shade", "aspect")

    def __init__(self, shape, style="solid", x=128, y=128, size=256,
                 rotation=0.0, shade=1.0, aspect=1.0):
        self.shape = shape
        self.style = style
        self.x = x
        self.y = y
        self.size = size
        self.rotation = rotation
        self.shade = shade
        self.aspect = aspect


def L(shape, style="solid", x=128, y=128, size=256, rotation=0.0, shade=1.0,
      aspect=1.0):
    return Layer(shape, style, x, y, size, rotation, shade, aspect)


def _layers(*groups):
    return list(groups)


# Every obstacle is a stack of block primitives. Rotations are authored in
# degrees; shades below 1.0 push a layer back, above 1.0 lift it forward.
OBSTACLES = (
    # --- Barricades: horizontal beams held by posts ------------------------
    {"folder": "barikade", "name": "silang", "layers": _layers(
        L("persegi", "flat", 52, 178, 132, shade=.72),
        L("persegi", "flat", 204, 178, 132, shade=.72),
        L("persegi-panjang", "solid", 128, 116, 340, rotation=30, shade=.94, aspect=.52),
        L("persegi-panjang", "solid", 128, 116, 340, rotation=-30, shade=.82, aspect=.52),
    )},
    {"folder": "barikade", "name": "ganda", "layers": _layers(
        L("persegi-panjang", "solid", 128, 86, 300, shade=.96),
        L("persegi-panjang", "solid", 128, 170, 300, rotation=-3, shade=.82),
        L("persegi", "flat", 50, 132, 190, shade=.68),
        L("persegi", "flat", 206, 132, 190, shade=.68),
    )},
    {"folder": "barikade", "name": "duri", "layers": _layers(
        L("persegi-panjang", "flat", 128, 178, 300, shade=.52),
        L("segitiga", "solid", 48, 118, 96, shade=.80),
        L("segitiga", "solid", 104, 112, 104, shade=.96),
        L("segitiga", "solid", 160, 112, 104, shade=.96),
        L("segitiga", "solid", 214, 118, 96, shade=.80),
    )},
    {"folder": "barikade", "name": "tingkat", "layers": _layers(
        L("persegi-panjang", "solid", 120, 188, 210, shade=.64),
        L("persegi-panjang", "solid", 138, 132, 250, shade=.82),
        L("persegi-panjang", "solid", 118, 76, 290, shade=.99),
    )},
    {"folder": "barikade", "name": "lingkaran", "layers": _layers(
        L("lingkaran", "flat", 58, 148, 110, shade=.63),
        L("lingkaran", "flat", 198, 148, 110, shade=.63),
        L("persegi-panjang", "solid", 128, 124, 300, rotation=-2, shade=.92),
        L("lingkaran", "solid", 128, 124, 86, shade=1.08),
    )},
    {"folder": "barikade", "name": "berat", "layers": _layers(
        L("persegi-panjang", "solid", 128, 152, 320, shade=.76),
        L("persegi", "flat", 68, 180, 104, shade=.56),
        L("persegi", "flat", 188, 180, 104, shade=.56),
        L("bintang", "solid", 128, 112, 96, shade=1.08),
    )},

    # --- Spikes: triangles as the damaging silhouette ----------------------
    {"folder": "duri", "name": "baris", "layers": _layers(
        L("persegi-panjang", "flat", 128, 208, 300, shade=.52),
        L("segitiga", "flat", 34, 168, 92, shade=.82),
        L("segitiga", "solid", 84, 162, 100, shade=.96),
        L("segitiga", "flat", 134, 168, 92, shade=.82),
        L("segitiga", "solid", 184, 162, 100, shade=.96),
        L("segitiga", "flat", 230, 168, 92, shade=.82),
    )},
    {"folder": "duri", "name": "ganda", "layers": _layers(
        L("segitiga", "solid", 54, 98, 100, shade=.72),
        L("segitiga", "solid", 112, 92, 108, shade=.84),
        L("segitiga", "solid", 170, 92, 108, shade=.84),
        L("segitiga", "solid", 224, 98, 100, shade=.72),
        L("segitiga", "flat", 34, 176, 96, shade=.98),
        L("segitiga", "flat", 90, 182, 88, shade=1.04),
        L("segitiga", "flat", 146, 182, 88, shade=1.04),
        L("segitiga", "flat", 202, 176, 96, shade=.98),
    )},
    {"folder": "duri", "name": "persegi", "layers": _layers(
        L("persegi-panjang", "solid", 128, 194, 300, shade=.58),
        L("segitiga", "solid", 66, 120, 116, shade=.86),
        L("segitiga", "solid", 128, 110, 128, shade=.98),
        L("segitiga", "solid", 190, 120, 116, shade=.86),
        L("segitiga", "flat", 30, 184, 86, rotation=-90, shade=.74),
        L("segitiga", "flat", 226, 184, 86, rotation=90, shade=.74),
    )},
    {"folder": "duri", "name": "lingkaran", "layers": _layers(
        L("lingkaran", "outline", 128, 150, 196, shade=.62),
        *[L("segitiga", "solid", 128 + 98 * math.cos(a),
             150 + 98 * math.sin(a), 76, rotation=math.degrees(a) + 90,
             shade=.96) for a in (i * math.tau / 8 for i in range(8))],
        L("lingkaran", "solid", 128, 150, 74, shade=.88),
    )},
    {"folder": "duri", "name": "raksasa", "layers": _layers(
        L("segitiga", "solid", 128, 128, 236, shade=.96),
        L("segitiga", "outline", 44, 196, 120, rotation=-18, shade=.70),
        L("segitiga", "outline", 212, 196, 120, rotation=18, shade=.70),
        L("persegi", "flat", 128, 208, 180, shade=.44),
    )},
    {"folder": "duri", "name": "campur", "layers": _layers(
        L("persegi", "solid", 58, 192, 94, rotation=8, shade=.60),
        L("persegi", "solid", 198, 192, 94, rotation=-8, shade=.60),
        L("segitiga", "solid", 58, 124, 118, rotation=-6, shade=.92),
        L("segitiga", "solid", 198, 124, 118, rotation=6, shade=.92),
        L("lingkaran", "outline", 128, 158, 118, shade=1.02),
        L("bintang", "flat", 128, 158, 70, shade=.72),
    )},

    # --- Towers: stacked primitives that read as a structure --------------
    {"folder": "menara", "name": "kotak", "layers": _layers(
        L("persegi", "solid", 128, 198, 184, shade=.66),
        L("persegi", "solid", 128, 138, 150, shade=.82),
        L("persegi", "solid", 128, 84, 118, shade=.96),
        L("persegi", "outline", 128, 38, 88, shade=1.02),
    )},
    {"folder": "menara", "name": "piramida", "layers": _layers(
        L("segitiga", "solid", 128, 198, 244, shade=.62),
        L("segitiga", "solid", 128, 154, 198, shade=.78),
        L("segitiga", "solid", 128, 110, 152, shade=.92),
        L("segitiga", "outline", 128, 68, 108, shade=1.02),
    )},
    {"folder": "menara", "name": "lingkaran", "layers": _layers(
        L("persegi-panjang", "outline", 128, 206, 286, shade=.55),
        L("lingkaran", "solid", 128, 156, 172, shade=.74),
        L("lingkaran", "solid", 128, 100, 142, shade=.88),
        L("lingkaran", "outline", 128, 48, 112, shade=1.01),
    )},
    {"folder": "menara", "name": "benteng", "layers": _layers(
        L("persegi-panjang", "solid", 128, 190, 300, shade=.68),
        L("trapesium", "solid", 128, 104, 246, shade=.90),
        L("persegi", "outline", 92, 168, 62, shade=.44),
        L("persegi", "outline", 164, 168, 62, shade=.44),
        L("bintang", "flat", 128, 168, 48, shade=1.04),
    )},
    {"folder": "menara", "name": "miring", "layers": _layers(
        L("persegi-panjang", "solid", 112, 192, 280, rotation=-7, shade=.62),
        L("persegi-panjang", "solid", 142, 132, 236, rotation=6, shade=.80),
        L("persegi-panjang", "outline", 122, 76, 200, rotation=-4, shade=.97),
    )},
    {"folder": "menara", "name": "kristal", "layers": _layers(
        L("belah-ketupat", "solid", 128, 194, 236, shade=.60),
        L("layang-layang", "solid", 128, 126, 178, shade=.80),
        L("belah-ketupat", "solid", 128, 66, 118, shade=.96),
        L("bintang", "outline", 128, 62, 62, shade=1.06),
    )},

    # --- Gates: paired supports and a lintel ------------------------------
    {"folder": "gerbang", "name": "kotak", "layers": _layers(
        L("persegi-panjang", "solid", 50, 128, 268, rotation=90, shade=.68),
        L("persegi-panjang", "solid", 206, 128, 268, rotation=90, shade=.68),
        L("persegi-panjang", "solid", 128, 40, 312, shade=.92),
        L("persegi-panjang", "flat", 128, 68, 220, shade=.50),
    )},
    {"folder": "gerbang", "name": "lengkung", "layers": _layers(
        L("setengah-lingkaran", "solid", 128, 128, 300, shade=.92),
        L("setengah-lingkaran", "flat", 128, 136, 216, shade=.26),
        L("persegi", "solid", 40, 182, 112, shade=.68),
        L("persegi", "solid", 216, 182, 112, shade=.68),
    )},
    {"folder": "gerbang", "name": "bintang", "layers": _layers(
        L("persegi-panjang", "solid", 128, 36, 316, shade=.90),
        L("persegi-panjang", "solid", 44, 136, 264, rotation=90, shade=.70),
        L("persegi-panjang", "solid", 212, 136, 264, rotation=90, shade=.70),
        L("bintang", "solid", 128, 124, 130, shade=1.06),
    )},
    {"folder": "gerbang", "name": "trapesium", "layers": _layers(
        L("persegi", "solid", 40, 174, 132, shade=.62),
        L("persegi", "solid", 216, 174, 132, shade=.62),
        L("trapesium", "solid", 128, 72, 330, rotation=180, shade=.90),
        L("trapesium", "flat", 128, 104, 188, rotation=180, shade=.26),
    )},
    {"folder": "gerbang", "name": "segi-enam", "layers": _layers(
        L("segi-enam", "solid", 128, 126, 246, shade=.78),
        L("segi-enam", "flat", 128, 126, 158, shade=.30),
        L("segi-enam", "outline", 128, 126, 108, shade=.94),
        L("persegi-panjang", "flat", 128, 220, 250, shade=.50),
    )},
    {"folder": "gerbang", "name": "runtuh", "layers": _layers(
        L("persegi-panjang", "solid", 58, 142, 262, rotation=8, shade=.68),
        L("persegi-panjang", "solid", 198, 142, 262, rotation=-10, shade=.68),
        L("persegi", "solid", 132, 202, 122, rotation=28, shade=.82),
        L("segitiga", "outline", 196, 60, 96, rotation=32, shade=.96),
    )},

    # --- Traps: wheels, pincers and weights -------------------------------
    {"folder": "perangkap", "name": "gergaji", "layers": _layers(
        L("bintang", "outline", 128, 128, 288, shade=.90),
        L("lingkaran", "solid", 128, 128, 196, shade=.68),
        L("lingkaran", "outline", 128, 128, 104, shade=.50),
        L("lingkaran", "solid", 128, 128, 66, shade=.96),
        L("bintang", "flat", 128, 128, 34, shade=.60),
    )},
    {"folder": "perangkap", "name": "roda", "layers": _layers(
        L("lingkaran", "solid", 128, 132, 232, shade=.78),
        L("segi-delapan", "outline", 128, 132, 174, shade=.48),
        L("lingkaran", "flat", 128, 132, 92, shade=.92),
        L("segi-enam", "solid", 128, 132, 56, shade=.62),
    )},
    {"folder": "perangkap", "name": "jepit", "layers": _layers(
        L("segitiga", "solid", 24, 106, 170, rotation=-90, shade=.90),
        L("segitiga", "solid", 232, 106, 170, rotation=90, shade=.90),
        L("lingkaran", "outline", 128, 146, 118, shade=.64),
        L("persegi-panjang", "flat", 128, 214, 210, shade=.46),
    )},
    {"folder": "perangkap", "name": "bandul", "layers": _layers(
        L("lingkaran", "outline", 128, 34, 66, shade=.70),
        L("lingkaran", "outline", 128, 82, 58, shade=.62),
        L("lingkaran", "outline", 128, 126, 50, shade=.54),
        L("oval", "solid", 128, 182, 128, shade=.92),
        L("segitiga", "outline", 128, 224, 92, rotation=180, shade=.70),
    )},
    {"folder": "perangkap", "name": "tarian", "layers": _layers(
        L("belah-ketupat", "solid", 128, 124, 218, shade=.84),
        L("segitiga", "flat", 34, 124, 108, rotation=-90, shade=.66),
        L("segitiga", "flat", 222, 124, 108, rotation=90, shade=.66),
        L("segitiga", "flat", 128, 24, 108, rotation=180, shade=.74),
        L("segitiga", "flat", 128, 224, 108, shade=.74),
        L("lingkaran", "outline", 128, 124, 82, shade=1.02),
    )},
    {"folder": "perangkap", "name": "timpa", "layers": _layers(
        L("lingkaran", "outline", 128, 28, 62, shade=.72),
        L("persegi", "solid", 128, 108, 196, rotation=4, shade=.84),
        L("segitiga", "outline", 76, 210, 96, shade=.92),
        L("segitiga", "outline", 128, 218, 96, shade=.98),
        L("segitiga", "outline", 180, 210, 96, shade=.92),
    )},

    # --- Rubble: irregular piles of broken primitives ---------------------
    {"folder": "runtuhan", "name": "batu", "layers": _layers(
        L("lingkaran", "solid", 84, 174, 142, shade=.58),
        L("persegi", "solid", 176, 166, 140, rotation=15, shade=.72),
        L("segi-lima", "solid", 120, 94, 126, rotation=-10, shade=.88),
        L("segitiga", "outline", 204, 82, 106, rotation=32, shade=.98),
    )},
    {"folder": "runtuhan", "name": "balok", "layers": _layers(
        L("persegi-panjang", "solid", 128, 184, 286, rotation=6, shade=.66),
        L("persegi-panjang", "solid", 126, 122, 258, rotation=-12, shade=.82),
        L("persegi-panjang", "outline", 140, 60, 204, rotation=20, shade=.96),
    )},
    {"folder": "runtuhan", "name": "pilar", "layers": _layers(
        L("persegi-panjang", "solid", 70, 138, 250, rotation=90, shade=.66),
        L("persegi-panjang", "solid", 190, 146, 250, rotation=97, shade=.72),
        L("persegi", "solid", 130, 84, 138, rotation=12, shade=.88),
        L("segitiga", "outline", 130, 204, 92, rotation=6, shade=.96),
    )},
    {"folder": "runtuhan", "name": "kubah", "layers": _layers(
        L("setengah-lingkaran", "solid", 128, 152, 266, shade=.72),
        L("lingkaran", "outline", 128, 84, 104, shade=.84),
        L("segitiga", "flat", 66, 208, 92, shade=.96),
        L("segitiga", "flat", 128, 214, 92, shade=1.02),
        L("segitiga", "flat", 190, 208, 92, shade=.96),
    )},
    {"folder": "runtuhan", "name": "kristal", "layers": _layers(
        L("belah-ketupat", "solid", 96, 156, 184, rotation=-8, shade=.78),
        L("layang-layang", "solid", 182, 116, 162, rotation=18, shade=.92),
        L("belah-ketupat", "outline", 138, 210, 112, rotation=10, shade=.66),
        L("bintang", "outline", 202, 54, 62, shade=1.06),
    )},
    {"folder": "runtuhan", "name": "lingkaran", "layers": _layers(
        L("lingkaran", "solid", 92, 154, 152, shade=.62),
        L("lingkaran", "solid", 172, 170, 132, shade=.74),
        L("lingkaran", "outline", 138, 90, 102, shade=.86),
        L("lingkaran", "outline", 208, 96, 82, shade=.94),
    )},
)


_PRIMITIVES = {}


def _primitive(shape, style):
    key = (shape, style)
    if key not in _PRIMITIVES:
        path = BLOCK_ROOT / shape / f"{shape}_{style}.png"
        if not path.is_file():
            generate_blocks.generate()
        _PRIMITIVES[key] = cairo.ImageSurface.create_from_png(str(path))
    return _PRIMITIVES[key]


def _shaded(surface, shade):
    """Multiply luminance while preserving alpha, so pixels stay r = g = b."""
    width, height = surface.get_width(), surface.get_height()
    stride = surface.get_stride()
    rows = np.frombuffer(surface.get_data(), dtype=np.uint8).reshape(height, stride).copy()
    pixels = rows[:, :width * 4].reshape(height, width, 4)
    pixels[:, :, :3] = (pixels[:, :, :3].astype(np.uint16) * shade).clip(0, 255)
    return cairo.ImageSurface.create_for_data(rows, cairo.FORMAT_ARGB32, width, height, stride)


def _draw_layer(ctx, surface, layer):
    """Place one primitive, centred on its position and rotated about centre."""
    ctx.save()
    ctx.translate(layer.x, layer.y)
    if layer.rotation:
        ctx.rotate(math.radians(layer.rotation))
    ctx.scale(layer.size / CANVAS, layer.size * layer.aspect / CANVAS)
    ctx.translate(-CANVAS / 2, -CANVAS / 2)
    image = surface if layer.shade == 1.0 else _shaded(surface, layer.shade)
    ctx.set_source_surface(image, 0, 0)
    ctx.paint()
    ctx.restore()


SHAPE_INDEX = {shape["folder"]: shape for shape in generate_blocks.SHAPES}


def _shape_box(shape):
    """Content bounds of one block inside its 256px canvas."""
    spec = SHAPE_INDEX[shape]
    kind = spec["kind"]
    if kind == "poly":
        xs = [p[0] for p in spec["points"]]
        ys = [p[1] for p in spec["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    if kind in ("circle", "semicircle"):
        r = spec["r"]
        return spec["cx"] - r, spec["cy"] - r, spec["cx"] + r, spec["cy"] + r
    rx, ry = spec["rx"], spec["ry"]
    return spec["cx"] - rx, spec["cy"] - ry, spec["cx"] + rx, spec["cy"] + ry


def _bounds(obstacle):
    """Union of every rotated primitive's content box."""
    xs, ys = [], []
    for layer in obstacle["layers"]:
        scale = layer.size / CANVAS
        angle = math.radians(layer.rotation)
        cos, sin = math.cos(angle), math.sin(angle)
        x0, y0, x1, y1 = _shape_box(layer.shape)
        for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            dx = (px - CANVAS / 2) * scale
            dy = (py - CANVAS / 2) * scale * layer.aspect
            xs.append(layer.x + dx * cos - dy * sin)
            ys.append(layer.y + dx * sin + dy * cos)
    return min(xs), min(ys), max(xs), max(ys)


def _render(obstacle, size=CANVAS):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    # Fit the composed bounds to the canvas so no obstacle is clipped and every
    # variant keeps the same visual weight regardless of how many layers it has.
    x0, y0, x1, y1 = _bounds(obstacle)
    margin = 10
    fit = min((CANVAS - 2 * margin) / max(1e-6, x1 - x0),
              (CANVAS - 2 * margin) / max(1e-6, y1 - y0))
    ctx.translate(CANVAS / 2 - (x0 + x1) / 2 * fit,
                  CANVAS / 2 - (y0 + y1) / 2 * fit)
    ctx.scale(fit, fit)
    ctx.scale(size / CANVAS, size / CANVAS)
    for layer in obstacle["layers"]:
        _draw_layer(ctx, _primitive(layer.shape, layer.style), layer)
    return surface


def _preview(obstacles, destination, fit=128):
    columns, gap, cell = 6, 10, 150
    label = 22
    rows = (len(obstacles) + columns - 1) // columns
    width = gap + columns * (cell + gap)
    height = gap + rows * (cell + label) + 30
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    for index, obstacle in enumerate(obstacles):
        column, row = index % columns, index // columns
        x = gap + column * (cell + gap)
        y = gap + row * (cell + label)
        image = _render(obstacle)
        ctx.save()
        ctx.translate(x + (cell - fit) / 2, y)
        ctx.scale(fit / CANVAS, fit / CANVAS)
        ctx.set_source_surface(image, 0, 0)
        ctx.paint()
        ctx.restore()
        ctx.set_font_size(9)
        ctx.set_source_rgb(.2, .2, .2)
        text = f"{obstacle['folder']}/{obstacle['name']}"
        extents = ctx.text_extents(text)
        ctx.move_to(x + (cell - extents.width) / 2, y + fit + 14)
        ctx.show_text(text)
    ctx.set_font_size(10)
    ctx.set_source_rgb(.35, .35, .35)
    ctx.move_to(gap, height - 10)
    ctx.show_text("Primitive-built obstacles - greyscale source, tint with BLEND_MULT")
    surface.write_to_png(str(destination))


def generate(force=False, size=CANVAS):
    paths = []
    written = []
    for obstacle in OBSTACLES:
        folder = OBSTACLE_ROOT / obstacle["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"{obstacle['name']}.png"
        paths.append(destination)
        if force or not destination.is_file():
            _render(obstacle, size).write_to_png(str(destination))
            written.append(destination)
    preview = OBSTACLE_ROOT / "preview.png"
    _preview(OBSTACLES, preview)
    written.append(preview)
    return written, paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="deterministically regenerate every obstacle PNG")
    parser.add_argument("--size", type=int, default=CANVAS,
                        help=f"PNG edge length in pixels (default {CANVAS})")
    parser.add_argument("--quiet", action="store_true",
                        help="write assets without listing individual paths")
    args = parser.parse_args(argv)
    if args.size < 64:
        parser.error("--size must be at least 64")
    written, paths = generate(force=args.force, size=args.size)
    if not args.quiet:
        for path in written:
            print(f"{path}  {path.stat().st_size:,} bytes")
    print(f"Obstacle assets ready: {len(paths)} variants in "
          f"{len({o['folder'] for o in OBSTACLES})} categories; "
          f"{OBSTACLE_ROOT / 'preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
