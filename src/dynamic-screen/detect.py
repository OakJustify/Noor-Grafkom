"""Monitor detection helpers."""

import pygame


def get_monitor_size(index=0):
    """Return (width, height) of monitor `index`."""
    try:
        infos = pygame.display.get_desktop_sizes() if hasattr(pygame.display, "get_desktop_sizes") else []
        if infos and 0 <= index < len(infos):
            return infos[index]
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        info = pygame.display.Info()
        return info.current_w, info.current_h
    except Exception:  # noqa: BLE001
        return 1280, 720


def get_display_modes():
    """Return list of available (w, h) modes."""
    try:
        return pygame.display.list_modes()
    except Exception:  # noqa: BLE001
        return []