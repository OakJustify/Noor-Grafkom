"""Cairo helpers."""

import cairo
import numpy as np
import pygame


def new_canvas(w, h):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return surf, cairo.Context(surf)


def to_pygame(surf):
    w, h = surf.get_width(), surf.get_height()
    stride = surf.get_stride() // 4
    raw = np.frombuffer(surf.get_data(), dtype=np.uint8)
    buf = raw.reshape(h, stride, 4)[:, :w, :].copy()
    a = buf[..., 3:4].astype(np.float32)
    rgb = buf[..., :3].astype(np.float32)
    rgb = np.where(a > 0, np.minimum(rgb * 255.0 / np.maximum(a, 1), 255), 0)
    out = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], a[..., 0]])
    out = out.astype(np.uint8)
    img = pygame.image.frombuffer(out.tobytes(), (w, h), "RGBA")
    return img.convert_alpha()