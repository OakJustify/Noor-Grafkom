"""Generate ECHO's greyscale block-library assets with Cairo.

Usage: .venv-echo/bin/python -m echo_game.generate_blocks [--force] [--size 256]

Every category owns a subfolder under assets/block/. Blocks are rendered on a
transparent 256x256 canvas in three styles (solid, flat, outline) using only
greyscale pixels, so a game can tint them at runtime with a seeded RNG via
pygame's BLEND_MULT and keep the bevel/outline shading readable. Nothing here
initializes a display, mixer, network or external tools.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import random
from pathlib import Path

import cairo

BLOCK_VERSION = 1
CANVAS = 256
STYLES = ("solid", "flat", "outline")
BLOCK_ROOT = Path(__file__).resolve().parent.parent / "assets" / "block"

# Every coordinate below is authored for the 256x256 canvas and scaled on
# output. Shapes stay inside a 20px safe margin for the outline stroke.
def _regular(cx, cy, radius, sides, rotation=-90.0):
    step = math.tau / sides
    angle = math.radians(rotation)
    return [(cx + math.cos(angle + i * step) * radius,
             cy + math.sin(angle + i * step) * radius) for i in range(sides)]


def _star(cx, cy, outer, inner, points=5, rotation=-90.0):
    result = []
    step = math.pi / points
    angle = math.radians(rotation)
    for i in range(points * 2):
        radius = outer if i % 2 == 0 else inner
        result.append((cx + math.cos(angle + i * step) * radius,
                       cy + math.sin(angle + i * step) * radius))
    return result


SHAPES = (
    {"folder": "persegi", "label": "Persegi", "kind": "poly",
     "points": [(30, 30), (226, 30), (226, 226), (30, 226)]},
    {"folder": "segitiga", "label": "Segitiga", "kind": "poly",
     "points": [(128, 26), (230, 226), (26, 226)]},
    {"folder": "lingkaran", "label": "Lingkaran", "kind": "circle",
     "cx": 128, "cy": 128, "r": 104},
    {"folder": "persegi-panjang", "label": "Persegi panjang", "kind": "poly",
     "points": [(20, 50), (236, 50), (236, 206), (20, 206)]},
    {"folder": "jajar-genjang", "label": "Jajar genjang", "kind": "poly",
     "points": [(62, 40), (234, 40), (194, 216), (22, 216)]},
    {"folder": "belah-ketupat", "label": "Belah ketupat", "kind": "poly",
     "points": [(128, 18), (236, 128), (128, 238), (20, 128)]},
    {"folder": "layang-layang", "label": "Layang-layang", "kind": "poly",
     "points": [(128, 16), (218, 92), (128, 240), (38, 92)]},
    {"folder": "trapesium", "label": "Trapesium", "kind": "poly",
     "points": [(71, 36), (185, 36), (232, 220), (24, 220)]},
    {"folder": "segi-lima", "label": "Segi lima", "kind": "poly",
     "points": _regular(128, 132, 106, 5)},
    {"folder": "segi-enam", "label": "Segi enam", "kind": "poly",
     "points": _regular(128, 128, 108, 6, 0)},
    {"folder": "segi-delapan", "label": "Segi delapan", "kind": "poly",
     "points": _regular(128, 128, 108, 8, 22.5)},
    {"folder": "oval", "label": "Oval", "kind": "ellipse",
     "cx": 128, "cy": 128, "rx": 110, "ry": 76},
    {"folder": "setengah-lingkaran", "label": "Setengah lingkaran",
     "kind": "semicircle", "cx": 128, "cy": 234, "r": 106},
    {"folder": "bintang", "label": "Bintang", "kind": "poly",
     "points": _star(128, 130, 112, 46)},
)


def _grey(ctx, value, alpha=1.0):
    """Only luminance is authored; the game multiplies its own colour in."""
    ctx.set_source_rgba(value / 255.0, value / 255.0, value / 255.0, alpha)


def _bbox(shape):
    if shape["kind"] == "poly":
        xs = [p[0] for p in shape["points"]]
        ys = [p[1] for p in shape["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    if shape["kind"] == "circle":
        r = shape["r"]
        return shape["cx"] - r, shape["cy"] - r, shape["cx"] + r, shape["cy"] + r
    if shape["kind"] == "ellipse":
        rx, ry = shape["rx"], shape["ry"]
        return shape["cx"] - rx, shape["cy"] - ry, shape["cx"] + rx, shape["cy"] + ry
    r, cx, cy = shape["r"], shape["cx"], shape["cy"]
    return cx - r, cy - r, cx + r, cy


def _path(ctx, shape):
    """Build the shape outline. Points are fixed at construction time."""
    ctx.new_path()
    ctx.save()
    kind = shape["kind"]
    if kind == "poly":
        ctx.move_to(*shape["points"][0])
        for x, y in shape["points"][1:]:
            ctx.line_to(x, y)
        ctx.close_path()
    elif kind == "circle":
        ctx.arc(shape["cx"], shape["cy"], shape["r"], 0, math.tau)
    elif kind == "ellipse":
        ctx.save()
        ctx.translate(shape["cx"], shape["cy"])
        ctx.scale(shape["rx"], shape["ry"])
        ctx.arc(0, 0, 1, 0, math.tau)
        ctx.restore()
    elif kind == "semicircle":
        ctx.arc(shape["cx"], shape["cy"], shape["r"], math.pi, math.tau)
        ctx.close_path()
    ctx.restore()


def _outline(ctx, shape, value=40, width=5.0, alpha=.95):
    _path(ctx, shape)
    _grey(ctx, value, alpha)
    ctx.set_line_width(width)
    ctx.stroke()


def _draw_solid(ctx, shape, rng):
    """Shaded block: gradient body, directional bevel and clipped grain."""
    gradient = cairo.LinearGradient(44, 22, 214, 236)
    for stop, value in ((0.0, 206), (.5, 176), (1.0, 132)):
        gradient.add_color_stop_rgb(stop, value / 255, value / 255, value / 255)
    _path(ctx, shape)
    ctx.set_source(gradient)
    ctx.fill()

    ctx.save()
    _path(ctx, shape)
    ctx.clip()
    # A uniform inner rim plus one diagonal light/shade sweep keeps the bevel
    # free of seams on narrow and concave silhouettes (kite, star).
    _path(ctx, shape)
    _grey(ctx, 52, .38)
    ctx.set_line_width(20)
    ctx.stroke()
    x0, y0, x1, y1 = _bbox(shape)
    shade = cairo.LinearGradient(x0, y0, x1, y1)
    shade.add_color_stop_rgba(0.0, 1, 1, 1, .30)
    shade.add_color_stop_rgba(.42, 1, 1, 1, .10)
    shade.add_color_stop_rgba(.55, 0, 0, 0, 0)
    shade.add_color_stop_rgba(1.0, 0, 0, 0, .24)
    ctx.set_source(shade)
    ctx.paint()

    for _ in range(240):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        value = rng.choice((24, 248))
        _grey(ctx, value, rng.uniform(.025, .065))
        ctx.arc(x, y, rng.uniform(.6, 1.7), 0, math.tau)
        ctx.fill()
    ctx.restore()
    _outline(ctx, shape)


def _draw_flat(ctx, shape, rng):
    _path(ctx, shape)
    _grey(ctx, 178)
    ctx.fill()
    _outline(ctx, shape)


def _draw_outline(ctx, shape, rng):
    _path(ctx, shape)
    _grey(ctx, 190, .14)
    ctx.fill()
    _path(ctx, shape)
    _grey(ctx, 170, .92)
    ctx.set_line_width(15)
    ctx.stroke()
    _outline(ctx, shape, value=46, width=3.5)


def _render(shape, style, size=CANVAS):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.scale(size / CANVAS, size / CANVAS)
    seed = int.from_bytes(hashlib.sha256(shape["folder"].encode()).digest()[:8], "big")
    rng = random.Random(seed)
    {"solid": _draw_solid, "flat": _draw_flat, "outline": _draw_outline}[style](ctx, shape, rng)
    return surface


def _preview(paths, destination):
    """Contact sheet: one column per shape, one row per style, for inspection."""
    cell, gap, label = 140, 8, 18
    width = gap + len(SHAPES) * (cell + gap)
    height = label + len(STYLES) * (cell + 24) + 34
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.select_font_face("sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

    def centered(text, x, y, size=10, value=.25):
        ctx.set_font_size(size)
        extents = ctx.text_extents(text)
        _grey(ctx, value * 255)
        ctx.move_to(x + (cell - extents.width) / 2, y)
        ctx.show_text(text)

    for column, shape in enumerate(SHAPES):
        x = gap + column * (cell + gap)
        centered(shape["label"], x, 13, 9)
        for row, style in enumerate(STYLES):
            y = label + row * (cell + 24) + 4
            image = cairo.ImageSurface.create_from_png(str(paths[shape["folder"]][style]))
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(cell / CANVAS, cell / CANVAS)
            ctx.set_source_surface(image, 0, 0)
            ctx.paint()
            ctx.restore()
            centered(style, x, y + cell + 13, 9)

    ctx.set_font_size(10)
    _grey(ctx, 70)
    ctx.move_to(gap, height - 12)
    ctx.show_text("Greyscale source - tint in-game with BLEND_MULT and a seeded RNG")
    surface.write_to_png(str(destination))


def generate(force=False, size=CANVAS):
    """Render any missing block PNGs and return every asset path."""
    paths = {}
    written = []
    for shape in SHAPES:
        folder = BLOCK_ROOT / shape["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        paths[shape["folder"]] = {}
        for style in STYLES:
            destination = folder / f"{shape['folder']}_{style}.png"
            paths[shape["folder"]][style] = destination
            if force or not destination.is_file():
                _render(shape, style, size).write_to_png(str(destination))
                written.append(destination)
    preview = BLOCK_ROOT / "preview.png"
    _preview(paths, preview)
    written.append(preview)
    return written, paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="deterministically regenerate every block PNG")
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
    print(f"Original block assets ready: {len(paths)} categories x {len(STYLES)} styles; "
          f"{BLOCK_ROOT / 'preview.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
