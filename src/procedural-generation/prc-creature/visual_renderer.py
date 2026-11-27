"""Procedural Visual Renderer — pycairo-based texture/pattern generation

Generates deterministic creature textures/sprites from VisualParams.
Matches FR-08: generated assets saved to assets/nur/creatures/.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import random
import hashlib

try:
    import cairo
except ImportError:
    cairo = None  # Will raise at runtime if used

from .morphology_generator import VisualParams


CREATURE_ASSET_DIR = Path("assets/nur/creatures")


@dataclass
class RenderedCreatureVisuals:
    """Paths to generated visual assets for a creature instance."""
    body_texture: Path          # Main body sprite
    limb_textures: dict[str, Path]  # Per-limb textures
    palette_swatch: Path        # 16x16 palette reference


class VisualRenderer:
    """Generate creature visual assets using pycairo (deterministic)."""

    def __init__(self, seed: int = 42, asset_dir: Path = CREATURE_ASSET_DIR):
        if cairo is None:
            raise RuntimeError("pycairo not installed. Run: pip install pycairo")
        self.seed = seed
        self.asset_dir = asset_dir
        self.asset_dir.mkdir(parents=True, exist_ok=True)

    def render_creature(self, creature_id: str, visual: VisualParams, size: tuple[int, int] = (256, 256)) -> RenderedCreatureVisuals:
        """Generate all visual assets for a creature."""
        rng = random.Random(self.seed + hash(creature_id))

        # Body texture
        body_path = self.asset_dir / f"{creature_id}_body.png"
        self._render_body(body_path, visual, size, rng)

        # Limb textures (simplified - 1 shared texture for all limbs of same type)
        limb_textures = {}
        for limb_type in ["leg", "arm", "wing", "tail", "tendril", "pseudopod"]:
            limb_path = self.asset_dir / f"{creature_id}_{limb_type}.png"
            self._render_limb(limb_path, visual, (64, 64), limb_type, rng)
            limb_textures[limb_type] = limb_path

        # Palette swatch for reference
        palette_path = self.asset_dir / f"{creature_id}_palette.png"
        self._render_palette(palette_path, visual)

        return RenderedCreatureVisuals(
            body_texture=body_path,
            limb_textures=limb_textures,
            palette_swatch=palette_path
        )

    def _render_body(self, path: Path, visual: VisualParams, size: tuple[int, int], rng: random.Random):
        """Render main body texture."""
        w, h = size
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)

        # Background transparent
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()

        # Generate base color from palette
        base_h = rng.uniform(*visual.base_hue_range)
        base_s = rng.uniform(*visual.base_sat_range)
        base_v = rng.uniform(*visual.base_val_range)
        base_rgb = self._hsv_to_rgb(base_h, base_s, base_v)

        # Accent color
        acc_h = rng.uniform(*visual.accent_hue_range)
        acc_s = rng.uniform(*visual.accent_sat_range)
        acc_v = rng.uniform(*visual.accent_val_range)
        acc_rgb = self._hsv_to_rgb(acc_h, acc_s, acc_v)

        # Draw based on pattern type
        cx, cy = w // 2, h // 2
        body_radius = min(w, h) * 0.35

        ctx.arc(cx, cy, body_radius, 0, 2 * math.pi)

        # Pattern-specific rendering
        if visual.pattern_type == "scales":
            self._draw_scales(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "fur":
            self._draw_fur(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "chitin":
            self._draw_chitin(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "slime":
            self._draw_slime(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "feathers":
            self._draw_feathers(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "shadow":
            self._draw_shadow(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        elif visual.pattern_type == "membrane":
            self._draw_membrane(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)
        else:  # skin
            self._draw_skin(ctx, cx, cy, body_radius, base_rgb, acc_rgb, rng)

        surface.write_to_png(str(path))

    def _render_limb(self, path: Path, visual: VisualParams, size: tuple[int, int], limb_type: str, rng: random.Random):
        """Render limb texture."""
        w, h = size
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)

        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()

        # Simplified limb rendering - elongated shape
        base_h = rng.uniform(*visual.base_hue_range)
        base_s = rng.uniform(*visual.base_sat_range)
        base_v = rng.uniform(*visual.base_val_range)
        base_rgb = self._hsv_to_rgb(base_h, base_s, base_v)

        ctx.rectangle(16, 8, w - 32, h - 16)
        ctx.set_source_rgb(*base_rgb)
        ctx.fill()

        surface.write_to_png(str(path))

    def _render_palette(self, path: Path, visual: VisualParams):
        """Render 16x16 palette swatch."""
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 16, 16)
        ctx = cairo.Context(surface)

        # Base color
        base_h = (visual.base_hue_range[0] + visual.base_hue_range[1]) / 2
        base_s = (visual.base_sat_range[0] + visual.base_sat_range[1]) / 2
        base_v = (visual.base_val_range[0] + visual.base_val_range[1]) / 2
        base_rgb = self._hsv_to_rgb(base_h, base_s, base_v)

        ctx.set_source_rgb(*base_rgb)
        ctx.rectangle(0, 0, 8, 16)
        ctx.fill()

        # Accent color
        acc_h = (visual.accent_hue_range[0] + visual.accent_hue_range[1]) / 2
        acc_s = (visual.accent_sat_range[0] + visual.accent_sat_range[1]) / 2
        acc_v = (visual.accent_val_range[0] + visual.accent_val_range[1]) / 2
        acc_rgb = self._hsv_to_rgb(acc_h, acc_s, acc_v)

        ctx.set_source_rgb(*acc_rgb)
        ctx.rectangle(8, 0, 8, 16)
        ctx.fill()

        surface.write_to_png(str(path))

    # ──────────────────────────────────────────────────────────────
    # Pattern Rendering Helpers
    # ──────────────────────────────────────────────────────────────

    def _hsv_to_rgb(self, h: float, s: float, v: float) -> tuple[float, float, float]:
        """Convert HSV (0-1) to RGB (0-1)."""
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i %= 6
        if i == 0: r, g, b = v, t, p
        elif i == 1: r, g, b = q, v, p
        elif i == 2: r, g, b = p, v, t
        elif i == 3: r, g, b = p, q, v
        elif i == 4: r, g, b = t, p, v
        else: r, g, b = v, p, q
        return (r, g, b)

    def _draw_scales(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        ctx.set_source_rgb(*base)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Scale pattern overlay
        for row in range(-2, 3):
            for col in range(-2, 3):
                x = cx + col * r * 0.3
                y = cy + row * r * 0.3
                if (x - cx)**2 + (y - cy)**2 <= r**2:
                    ctx.set_source_rgb(*accent)
                    ctx.arc(x, y, r * 0.15, 0, 2 * math.pi)
                    ctx.fill()

    def _draw_fur(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        ctx.set_source_rgb(*base)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Fur strokes
        for _ in range(80):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0, r * 0.8)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            length = rng.uniform(r * 0.1, r * 0.3)
            ex = x + math.cos(angle) * length
            ey = y + math.sin(angle) * length
            ctx.move_to(x, y)
            ctx.line_to(ex, ey)
            ctx.set_source_rgb(*accent)
            ctx.set_line_width(1.0)
            ctx.stroke()

    def _draw_chitin(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        ctx.set_source_rgb(*base)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Segmented plates
        for i in range(6):
            angle = i * math.pi / 3
            x = cx + math.cos(angle) * r * 0.5
            y = cy + math.sin(angle) * r * 0.5
            ctx.set_source_rgb(*accent)
            ctx.arc(x, y, r * 0.25, 0, 2 * math.pi)
            ctx.fill()

    def _draw_slime(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        # Amorphous blob with highlights
        points = []
        for i in range(12):
            angle = i * 2 * math.pi / 12
            dist = r * rng.uniform(0.6, 1.0)
            points.append((cx + math.cos(angle) * dist, cy + math.sin(angle) * dist))
        ctx.move_to(*points[0])
        for p in points[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.set_source_rgb(*base)
        ctx.fill()

        # Highlight blob
        ctx.arc(cx - r * 0.2, cy - r * 0.2, r * 0.25, 0, 2 * math.pi)
        ctx.set_source_rgba(*accent, 0.6)
        ctx.fill()

    def _draw_feathers(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        ctx.set_source_rgb(*base)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Feather barbs
        for i in range(12):
            angle = i * math.pi / 6
            x = cx + math.cos(angle) * r * 0.4
            y = cy + math.sin(angle) * r * 0.4
            ex = cx + math.cos(angle) * r * 0.9
            ey = cy + math.sin(angle) * r * 0.9
            ctx.move_to(x, y)
            ctx.line_to(ex, ey)
            ctx.set_source_rgb(*accent)
            ctx.set_line_width(2.0)
            ctx.stroke()

    def _draw_shadow(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        # Dark base with shifting edges
        ctx.set_source_rgba(*base, 0.9)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Noise edges
        for _ in range(200):
            angle = rng.uniform(0, 2 * math.pi)
            dist = r * rng.uniform(0.7, 1.0)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            ctx.set_source_rgba(*base, 0.3)
            ctx.arc(x, y, 3, 0, 2 * math.pi)
            ctx.fill()

    def _draw_membrane(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        # Translucent membrane with veins
        ctx.set_source_rgba(*base, 0.5)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Veins
        for _ in range(10):
            angle = rng.uniform(0, 2 * math.pi)
            x = cx + math.cos(angle) * r * 0.5
            y = cy + math.sin(angle) * r * 0.5
            ex = cx + math.cos(angle) * r * 0.9
            ey = cy + math.sin(angle) * r * 0.9
            ctx.move_to(x, y)
            ctx.line_to(ex, ey)
            ctx.set_source_rgba(*accent, 0.7)
            ctx.set_line_width(1.5)
            ctx.stroke()

    def _draw_skin(self, ctx: cairo.Context, cx: float, cy: float, r: float, base: tuple, accent: tuple, rng: random.Random):
        ctx.set_source_rgb(*base)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        # Subtle spots
        for _ in range(15):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0, r * 0.6)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            ctx.arc(x, y, r * 0.08, 0, 2 * math.pi)
            ctx.set_source_rgb(*accent)
            ctx.fill()


def generate_creature_visuals(creature_id: str, visual: VisualParams, seed: int = 42) -> RenderedCreatureVisuals:
    """Convenience function for one-shot visual generation."""
    renderer = VisualRenderer(seed)
    return renderer.render_creature(creature_id, visual)