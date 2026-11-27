"""Window creation helpers."""

import pygame


def create_window(title="NOOR", fullscreen=True, resizable=True):
    flags = 0
    if resizable and not fullscreen:
        flags |= pygame.RESIZABLE
    if fullscreen:
        flags |= pygame.FULLSCREEN
    # Prefer SCALED for automatic letterboxing
    flags |= pygame.SCALED
    screen = pygame.display.set_mode((1280, 720), flags)
    pygame.display.set_caption(title)
    return screen


def toggle_fullscreen(screen):
    """Toggle fullscreen; returns new screen."""
    is_full = bool(screen.get_flags() & pygame.FULLSCREEN)
    if is_full:
        return pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED)
    info = pygame.display.Info()
    return pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN | pygame.SCALED)