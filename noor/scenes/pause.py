"""Pause scene."""

import pygame

import noor.config as C


class PauseScene:
    def __init__(self, game, gameplay):
        self.game = game
        self.gameplay = gameplay

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.scenes.pop()

    def update(self, dt):
        pass

    def draw(self, surface):
        overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))
        font = pygame.font.SysFont(None, 48)
        t = font.render("JEDA", True, (230, 220, 200))
        surface.blit(t, (C.SCREEN_W // 2 - 40, 300))