import hashlib

import pygame

from nur_game.illustration import player_sprite, prop_sprite, shadow_sprite
from nur_game.levels import room_count


def digest(surface):
    return hashlib.sha256(pygame.image.tobytes(surface, "RGBA")).hexdigest()


def test_sprites_are_cached_and_animation_changes_silhouette():
    assert player_sprite("walk", 0) is player_sprite("walk", 0)
    assert digest(player_sprite("walk", 0)) != digest(player_sprite("walk", 2))
    assert digest(shadow_sprite(0, 0)) != digest(shadow_sprite(1, 0))
    assert prop_sprite("crate", 58) is prop_sprite("crate", 58)


def test_each_room_has_distinct_cached_art(game):
    signatures = []
    for room in range(room_count()):
        layers = game.art.background(room)
        assert layers is game.art.background(room)
        signatures.append(digest(layers[1]))
    assert len(set(signatures)) == room_count()


def test_light_mask_is_soft_and_cache_is_bounded(game):
    mask = game.art._radial(240)
    assert mask.get_at((240, 240)).a > mask.get_at((360, 240)).a
    assert mask.get_at((360, 240)).a > mask.get_at((479, 240)).a
    assert mask.get_at((240, 240))[:3] == (0, 0, 0)
    for radius in range(24, 520, 8):
        game.art._radial(radius)
    assert len(game.art._radials) <= 16


def test_all_rooms_render_at_zero_light(game):
    for room in range(room_count()):
        game.start(room=room)
        game.lantern.charge = 0
        game.draw()
        pixels = pygame.surfarray.array3d(game.canvas)
        assert pixels.std() > 12


def test_gate_drawing_matches_physics_fraction(game):
    game.start(room=2)
    screen = pygame.Surface((960, 540))
    screen.fill((0, 0, 0))
    game.world.gate_fraction = 0
    game.art.draw_terrain(screen, game.world, 900, 1)
    closed_pixel = screen.get_at((228, 265))[:3]
    screen.fill((0, 0, 0))
    game.world.gate_fraction = 1
    game.art.draw_terrain(screen, game.world, 900, 1)
    assert closed_pixel == (91, 111, 110)
    assert screen.get_at((228, 265))[:3] != closed_pixel
