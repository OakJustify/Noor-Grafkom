"""Content warning scene."""

import pygame

from noor.scenes.base import Scene
from noor.scenes.title import TitleScene


class WarningScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.game.scenes.replace(TitleScene(self.game))

    def update(self, dt):
        self.timer += dt

    def draw(self, surface):
        surface.fill((20, 18, 24))
        font = pygame.font.SysFont(None, 32)
        lines = [
            "PERINGATAN KONTEN",
            "Game ini membahas Alzheimer dan kehilangan.",
            "Tekan tombol apa saja untuk lanjut.",
        ]
        y = 200
        for ln in lines:
            t = font.render(ln, True, (230, 220, 200))
            surface.blit(t, (100, y))
            y += 40