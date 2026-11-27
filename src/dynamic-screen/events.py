"""Event helpers for resize handling."""

import pygame


def handle_resize(event, state):
    if event.type != pygame.VIDEORESIZE:
        return state
    state["phys_w"] = event.w
    state["phys_h"] = event.h
    try:
        from .scale import compute_scale
    except Exception:  # noqa: BLE001
        from scale import compute_scale

    state["scale"] = compute_scale(event.w, event.h)
    return state