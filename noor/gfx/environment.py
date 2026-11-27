"""Placeholder environment layers (pycairo assets will replace these)."""

import pygame

import noor.config as C


def draw_layer4(surface, camera, t):
    """Background: sky, clouds, floating islands."""
    w, h = C.SCREEN_W, C.SCREEN_H
    # sky gradient
    for y in range(0, h, 4):
        c = (180 - y // 8, 200 - y // 10, 230)
        pygame.draw.rect(surface, c, (0, y, w, 4))
    # clouds
    for i in range(5):
        cx = int((i * 300 - camera.x * 0.1) % (w + 200)) - 100
        cy = 80 + i * 30
        pygame.draw.ellipse(surface, (245, 245, 255), (cx, cy, 160, 40))
    # floating islands silhouette
    for i in range(3):
        ix = int(i * 420 - camera.x * 0.3) % (w + 300) - 150
        iy = 520 + (i % 2) * 40
        pygame.draw.ellipse(surface, (90, 120, 90), (ix, iy, 220, 60))


def draw_layer3(surface, camera, t):
    """Mid background (clone of foreground silhouettes, darker)."""
    w, _h = C.SCREEN_W, C.SCREEN_H
    for i in range(4):
        tx = int(i * 360 - camera.x * 0.5) % (w + 200) - 100
        ty = 480
        pygame.draw.rect(surface, (60, 70, 80), (tx, ty, 30, 160))


def draw_layer1(surface, camera, t):
    """Foreground (covers player): subtle silhouettes only."""
    w, h = C.SCREEN_W, C.SCREEN_H
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(3):
        tx = int(i * 500 - camera.x * 1.2) % (w + 200) - 100
        pygame.draw.rect(overlay, (30, 50, 40, 70), (tx, h - 180, 40, 180))
    surface.blit(overlay, (0, 0))