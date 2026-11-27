import pygame

from noor.core.input import InputState
from noor.entities.player import Player


def test_jump_height_consistent():
    pygame.init()
    p = Player(100, 600)
    inp = InputState()
    # land first
    p.update(1 / 60, inp, [(0, 640, 10000, 80)])
    assert p.on_ground
    # press jump then release immediately
    inp.jump_pressed = True
    inp.jump_held = True
    p.update(1 / 60, inp, [])
    inp.jump_pressed = False
    inp.jump_held = False
    # one more frame: velocity should not be halved by jump cut
    vy_after_jump = p.vy
    p.update(1 / 60, inp, [])
    # gravity only; no extra cut beyond gravity*dt
    expected = vy_after_jump + 2000 / 60
    assert abs(p.vy - expected) < 1e-3