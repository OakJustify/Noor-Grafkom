"""Title scene."""

import pygame

import noor.config as C


class TitleScene:
    def __init__(self, game):
        self.game = game
        # leaving a run: let the stage bed and its ambience fade under the title theme
        self.game.audio.fade_out()
        self.game.audio.cue("music:L0")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                from noor.scenes.gameplay import GameplayScene
                self.game.scenes.replace(GameplayScene(self.game, "prolog"))
            elif event.key == pygame.K_g:
                from noor.scenes.gameplay import GameplayScene
                self.game.scenes.replace(GameplayScene(self.game, "procedural"))
            elif event.key == pygame.K_ESCAPE:
                self.game.running = False

    def update(self, dt):
        self.game.audio.update(dt)  # keep bed fades and duck decay running

    def draw(self, surface):
        surface.fill((10, 10, 14))
        font = pygame.font.SysFont(None, 64)
        t = font.render("NOOR", True, (255, 210, 122))
        surface.blit(t, (C.SCREEN_W // 2 - t.get_width() // 2, 200))
        font2 = pygame.font.SysFont(None, 28)
        t2 = font2.render("ENTER: Prolog  |  G: Level Prosedural", True, (200, 190, 170))
        surface.blit(t2, (C.SCREEN_W // 2 - t2.get_width() // 2, 400))