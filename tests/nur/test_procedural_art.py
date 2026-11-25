import hashlib

import numpy as np
import pygame
import pytest

from nur_game import config
from nur_game.materials import MATERIALS, material_tile, platform_sprite, phantom_sprite
from nur_game.procedural import coherent_field


def digest(surface):
    return hashlib.sha256(pygame.image.tobytes(surface, "RGBA")).hexdigest()


def test_coherent_noise_is_seeded_smooth_and_supports_signed_seeds():
    a = coherent_field((128, 96), -123)
    assert np.array_equal(a, coherent_field((128, 96), -123))
    assert not np.array_equal(a, coherent_field((128, 96), 124))
    assert a.std() > 0.1
    # Neighbour differences are far smaller than white-noise standard deviation.
    assert np.abs(np.diff(a, axis=0)).mean() < a.std() * 0.4
    assert np.abs(a[0] - a[-1]).mean() < a.std() * 0.4


def test_actual_game_seed_changes_art_and_invalidates_background_cache(game):
    first = digest(game.art.background(0)[0])
    game.start(seed=22)
    second = digest(game.art.background(0)[0])
    assert first != second
    game.start(seed=22)
    assert digest(game.art.background(0)[0]) == second


def test_scrolling_layers_are_wide_cached_and_far_has_atmospheric_detail(game):
    layers = game.art.background(4)
    assert layers is game.art.background(4)
    assert all(image.get_size() == (config.SIZE[0] * 2, config.SIZE[1]) for image in layers)
    # Far scenery is intentionally low contrast; the landing edges own contrast.
    assert pygame.surfarray.array3d(layers[0]).std() > 8
    assert layers[1].get_at((0, 0)).a == 0


@pytest.mark.parametrize("material", MATERIALS)
def test_platform_top_is_exactly_the_collision_top_and_textures_are_cached(material):
    sprite = platform_sprite(120, 18, material, 400)
    assert sprite is platform_sprite(120, 18, material, 400)
    assert sprite.get_at((0, 0)).a == 0
    assert sprite.get_at((66, 4)).a > 200  # pivot (6,4), not an offset fake ledge
    assert sprite.get_at((66, 2)).a < 20
    tile = material_tile(material, 400)
    assert tile is material_tile(material, 400)
    assert pygame.surfarray.array3d(tile).std() > 8


def test_phantom_stairs_are_a_distinct_cached_skin():
    image = phantom_sprite(120, 16)
    assert image is phantom_sprite(120, 16)
    assert digest(image) != digest(platform_sprite(120, 16, "metal", 404))
