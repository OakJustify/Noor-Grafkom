"""Sanity, hallucination pressure and phantom presentation (Python F3)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from ..encounters import creature_sprite


class HallucinationAudio:
    """Lightweight adapter over the existing Soundscape.

    It does not create a second mixer.  Soundscape reads the intensity on its
    next update and shifts the original stems toward a muffled, dissonant bed.
    """

    def __init__(self):
        self.intensity = 0.0

    def apply(self, soundscape, intensity: float) -> None:
        self.intensity = max(0.0, min(1.0, float(intensity)))
        if soundscape is not None:
            soundscape.hallucination_intensity = self.intensity


class HallucinationVisuals:
    """CPU post-process approximating the requested shader steps."""

    def __init__(self, seed: int = 0x4E00):
        self.rng = random.Random(seed)
        self._scanlines: pygame.Surface | None = None

    def _lines(self, size) -> pygame.Surface:
        if self._scanlines is None or self._scanlines.get_size() != size:
            width, height = size
            surface = pygame.Surface(size, pygame.SRCALPHA)
            for y in range(0, height, 5):
                pygame.draw.line(surface, (0, 0, 0, 55), (0, y), (width, y), 1)
            self._scanlines = surface
        return self._scanlines

    def apply(self, screen: pygame.Surface, current: float, maximum: float,
              time: float) -> None:
        intensity = 0.0 if maximum <= 0 else max(0.0, min(1.0, 1.0 - current / maximum))
        if intensity < 0.02:
            return
        width, height = screen.get_size()
        veil = pygame.Surface((width, height), pygame.SRCALPHA)
        veil.fill((24, 8, 28, round(24 + 70 * intensity)))
        screen.blit(veil, (0, 0))
        if intensity > 0.15:
            scan = self._lines((width, height)).copy()
            scan.set_alpha(round(40 + 120 * intensity))
            screen.blit(scan, (0, 0))
        if intensity > 0.45:
            copy = screen.copy()
            offset = max(1, round(4 * intensity))
            screen.blit(copy, (offset, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(copy, (-offset, 0), special_flags=pygame.BLEND_RGB_ADD)
        if intensity > 0.62:
            copy = screen.copy()
            for y in range(0, height, 9):
                dx = round(math.sin(time * 17 + y * 0.31) * 5 * intensity)
                screen.blit(copy, (dx, y), pygame.Rect(0, y, width, 7))
        if intensity > 0.82:
            screen.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_SUB)


