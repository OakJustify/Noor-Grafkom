"""Original seeded Cairo scenery, generated once per room, never per frame."""

from collections import OrderedDict
import math
import random

import cairo
import pygame

from .art import _circle, _line, _poly, _rect, _surface, _tree


def _pygame(surface):
    surface.flush()
    # Cairo is native little-endian premultiplied BGRA. These layers use opaque
    # silhouettes on transparent pixels, so no unpremultiplication is needed.
    return pygame.image.frombuffer(bytes(surface.get_data()),
                                  (surface.get_width(), surface.get_height()), "BGRA").convert_alpha()


class RoomBackgrounds:
    """Bounded panorama cache; eviction cannot change deterministic scenery."""
    def __init__(self):
        self.cache = OrderedDict()
        self.builds = 0

    def layers(self, theme, size):
        key = (theme, tuple(size))
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        rng = random.Random(theme.scenery_seed)
        width, height = 1920, 540
        sky, ctx = _surface(width, height)
        rgb = theme.sky_tint
        brightness = .6 if theme.time_of_day == "night" else 1.0
        gradient = cairo.LinearGradient(0, 0, 0, height)
        for stop, scale in ((0, .40), (.48, 1.10), (.82, 1.8), (1, .6)):
            gradient.add_color_stop_rgb(stop, *(min(.65, c * scale * brightness / 255) for c in rgb))
        ctx.set_source(gradient)
        ctx.paint()
        light_x, light_y = rng.uniform(180, 1720), rng.uniform(75, 190)
        halo = cairo.RadialGradient(light_x, light_y, 0, light_x, light_y, rng.uniform(240, 400))
        halo.add_color_stop_rgba(0, .65, .77, .74, .12)
        halo.add_color_stop_rgba(1, .65, .77, .74, 0)
        ctx.set_source(halo)
        ctx.paint()
        _circle(ctx, light_x, light_y, rng.uniform(12, 24), (153, 172, 170), .18)
        layers = [_pygame(sky)]
        for depth in range(3):
            surface, ctx = _surface(width, height)
            color = ((53, 68, 71), (32, 47, 49), (23, 35, 38))[depth]
            baseline = 360 + depth * 55
            amplitude = rng.uniform(18, 45)
            phase = rng.uniform(0, math.tau)
            points = [(0, 560)]
            for x in range(0, width + 20, 20):
                points.append((x, baseline + math.sin(x / 190 + phase) * amplitude + rng.uniform(-7, 7)))
            points.append((width, 560))
            _poly(ctx, points, color)
            # Different biome structures, not just six recolored PNGs. All
            # silhouettes vary in position, count, height and construction.
            for _ in range(rng.randint(12, 23)):
                x = rng.uniform(-80, width + 40)
                base = baseline + rng.uniform(-12, 24)
                h = rng.uniform(65, 230) * (.75 + depth * .14)
                w = rng.uniform(28, 120)
                if theme.palette_index in (1, 3):
                    _tree(ctx, rng, x, base, h, h / 38, color,
                          conifer=theme.palette_index == 1 and rng.random() < .65)
                elif theme.palette_index == 4:
                    _poly(ctx, [(x, 0), (x + w * .3, h), (x + w, h * .65), (x + w * 1.4, 0)], color)
                    _poly(ctx, [(x, base + 20), (x + w * .4, base - h * .4),
                                (x + w, base + 20)], color)
                else:
                    _rect(ctx, x, base - h, w, h + 20, color)
                    _poly(ctx, [(x - 5, base - h), (x + w * .35, base - h - 20),
                                (x + w + 7, base - h + 4)], color)
                    if theme.palette_index == 2:
                        _rect(ctx, x + w * .7, base - h - rng.uniform(30, 100), 12, h, color)
                    elif theme.palette_index == 5:
                        for y in range(round(base - h), round(base), 32):
                            _line(ctx, [(x - 7, y), (x + w + 7, y + 32)], color, 3)
                    else:
                        for y in range(round(base - h + 15), round(base - 15), 28):
                            _rect(ctx, x + w * .3, y, w * .4, 11, (71, 91, 88))
            layers.append(_pygame(surface))
        scaled = tuple(pygame.transform.smoothscale(layer, (round(1920 * size[1] / 540), size[1]))
                       for layer in layers)
        self.cache[key] = scaled
        self.builds += 1
        while len(self.cache) > 2:
            self.cache.popitem(last=False)
        return scaled

    def draw(self, screen, camera, time, theme, art):
        layers = self.layers(theme, screen.get_size())
        for image, speed in zip(layers, (0, .07, .18, .32)):
            width = image.get_width()
            offset = -round(camera * speed) % width - width
            for x in range(offset, screen.get_width(), width):
                screen.blit(image, (x, 0))
        # Reuse Campaign's soft fog texture, with this room's opacity and phase.
        fog = art._landscapes["fog"]
        previous_alpha = fog.get_alpha()
        fog.set_alpha(round(255 * theme.fog_density))
        art._tile(screen, "fog", camera * .1 + time * 7 + theme.scenery_seed % 1920)
        fog.set_alpha(previous_alpha)
        colors = {"dust": (146, 163, 159), "mist": (104, 142, 152),
                  "embers": (174, 121, 78), "leaves": (104, 135, 90)}
        rng = random.Random(theme.scenery_seed ^ 0xD057)
        for _ in range(20):
            x = (rng.uniform(0, screen.get_width()) - camera * .23 + time * rng.uniform(2, 5)) % screen.get_width()
            y = (rng.uniform(80, 400) + math.sin(time * .4 + x / 100) * 9)
            pygame.draw.circle(screen, colors[theme.particle_type], (round(x), round(y)),
                               2 if theme.particle_type == "leaves" else 1)
