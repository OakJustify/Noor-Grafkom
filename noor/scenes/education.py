"""Education scene."""

import pygame


class EducationScene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            from noor.scenes.credits import CreditsScene
            self.game.scenes.replace(CreditsScene(self.game))

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((12, 12, 18))
        font = pygame.font.SysFont(None, 36)
        small = pygame.font.SysFont(None, 24)
        title = font.render(self.game.i18n.t("education.title"), True, (235, 225, 205))
        surface.blit(title, (80, 120))
        y = 190
        for key in ("education.body", "education.caregiver"):
            for line in self._wrap(self.game.i18n.t(key), 70):
                t = small.render(line, True, (210, 200, 185))
                surface.blit(t, (80, y))
                y += 32
            y += 16
        cont = small.render(self.game.i18n.t("education.continue"), True, (150, 140, 130))
        surface.blit(cont, (80, y + 40))

    def _wrap(self, text, width):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        return lines