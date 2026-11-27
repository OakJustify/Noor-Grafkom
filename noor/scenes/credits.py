"""Credits scene."""

import pygame

import noor.config as C


class CreditsScene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            from noor.scenes.title import TitleScene
            self.game.scenes.replace(TitleScene(self.game))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((10, 10, 14))
        font = pygame.font.SysFont(None, 36)
        small = pygame.font.SysFont(None, 24)
        title = font.render(self.game.i18n.t("credits.title"), True, (235, 225, 205))
        surface.blit(title, (C.SCREEN_W // 2 - title.get_width() // 2, 220))
        body = small.render(self.game.i18n.t("credits.body"), True, (210, 200, 185))
        surface.blit(body, (C.SCREEN_W // 2 - body.get_width() // 2, 300))
        cont = small.render(self.game.i18n.t("credits.continue"), True, (150, 140, 130))
        surface.blit(cont, (C.SCREEN_W // 2 - cont.get_width() // 2, 400))