"""Ending scene."""

import pygame

import noor.config as C


class EndingScene:
    def __init__(self, game):
        self.game = game
        # the run is over: let the stage bed and its ambience fade under the ending theme
        self.game.audio.fade_out()
        self.game.audio.cue("music:L5")
        self.timer = 0.0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            from noor.scenes.education import EducationScene
            self.game.scenes.replace(EducationScene(self.game))

    def update(self, dt):
        self.timer += dt
        self.game.audio.update(dt)  # lets the stage bed crossfade into the ending

    def draw(self, surface):
        surface.fill((0, 0, 0))
        font = pygame.font.SysFont(None, 40)
        small = pygame.font.SysFont(None, 28)
        title = font.render(self.game.i18n.t("ending.title"), True, (255, 210, 122))
        surface.blit(title, (C.SCREEN_W // 2 - title.get_width() // 2, 200))
        e6 = small.render(self.game.i18n.t("ending.e6"), True, (230, 220, 200))
        surface.blit(e6, (C.SCREEN_W // 2 - e6.get_width() // 2, 300))
        e7 = small.render(self.game.i18n.t("ending.e7"), True, (200, 190, 170))
        surface.blit(e7, (C.SCREEN_W // 2 - e7.get_width() // 2, 350))
        cont = small.render(self.game.i18n.t("ending.continue"), True, (150, 140, 130))
        surface.blit(cont, (C.SCREEN_W // 2 - cont.get_width() // 2, 500))