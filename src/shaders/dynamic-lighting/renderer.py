"""CPU fallback for dynamic sunlight shader."""

import os

import pygame


def _shader_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_shader_text():
    d = _shader_dir()
    try:
        with open(os.path.join(d, "vertex.glsl"), encoding="utf-8") as f:
            v = f.read()
        with open(os.path.join(d, "fragment.glsl"), encoding="utf-8") as f:
            fr = f.read()
        return v, fr
    except OSError:
        return "", ""


def apply(surface, t=0.0):
    """Apply a warm sunlight overlay (placeholder for real shader)."""
    w, h = surface.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 4):
        alpha = int(12 * (1.0 - y / h))
        pygame.draw.rect(overlay, (255, 230, 180, alpha), (0, y, w, 4))
    surface.blit(overlay, (0, 0))
    return surface