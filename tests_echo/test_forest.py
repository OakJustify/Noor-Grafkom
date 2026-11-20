"""Presentation gates for the endless mode's campaign-style renderer."""

import pygame
import pytest

from echo_game.forest import ForestRenderer
from echo_game.game import Game, SIZE
from echo_game.physics import Input
from echo_game.procedural import GenerationConfig


@pytest.fixture(autouse=True)
def display():
    pygame.display.set_mode(SIZE)
    yield


def test_forest_chunks_are_seeded_deterministic_and_cached():
    first = ForestRenderer(7, SIZE)
    again = ForestRenderer(7, SIZE)
    other = ForestRenderer(8, SIZE)

    chunk = first._chunk(2, 0)
    builds = first.chunk_builds
    assert first._chunk(2, 0) is chunk
    assert first.chunk_builds == builds
    assert pygame.image.tobytes(chunk, "RGBA") == pygame.image.tobytes(
        again._chunk(2, 0), "RGBA")
    assert pygame.image.tobytes(chunk, "RGBA") != pygame.image.tobytes(
        other._chunk(2, 0), "RGBA")
    assert first._sky.get_size() == SIZE
    assert pygame.image.tobytes(first._sky, "RGB") == pygame.image.tobytes(
        again._sky, "RGB")


def test_endless_camera_uses_campaign_scale_and_fixed_vertical_frame():
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(7)
        assert game.view_width == SIZE[0]
        assert game._point((0, 460)) == (0, 460)
        for _ in range(20):
            game.update(1 / 60, Input())
        assert game.camera_y == 0
        assert game._point((0, 460))[1] == 460
    finally:
        game.close()


def _bright_pixels(surface, rect):
    area = pygame.surfarray.array3d(surface.subsurface(pygame.Rect(rect)))
    return int((area[:, :, 0] > 100).sum())


def test_endless_draw_uses_campaign_art_and_campaign_style_hud():
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(7)
        assert not game.endless_hud
        game.draw()
        pixels = pygame.surfarray.array3d(game.canvas)
        assert pixels.max() > 100
        assert pixels.min() < 20
        assert game._visual_chapter() == game.world.room_theme.palette_index
        assert game.world.room_number == 1
        # The campaign-style title and bottom instruction strip are always on.
        assert _bright_pixels(game.canvas, (20, 15, 430, 92)) > 80
        assert _bright_pixels(game.canvas, (140, 500, 680, 40)) > 80
        detail_area = pygame.Rect(320, 45, 320, 24)
        compact_details = pygame.image.tobytes(game.canvas.subsurface(detail_area), "RGB")

        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
        assert game.endless_hud
        game.draw()
        expanded_details = pygame.image.tobytes(game.canvas.subsurface(detail_area), "RGB")
        assert expanded_details != compact_details

        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
        assert not game.endless_hud
    finally:
        game.close()


def test_procedural_terrain_and_environment_use_campaign_world_rendering():
    game = Game(persist=False, muted=True)
    try:
        game.start_endless(7)
        # The legacy streaming generator remains directly testable, while its
        # generated decorations now pass through the Campaign-style renderer.
        from echo_game.procedural import EndlessWorld
        game.world = EndlessWorld(7, config=GenerationConfig(environment_density=3))
        game.draw()
        game.canvas.fill((90, 90, 90))
        game._terrain()
        assert pygame.image.tobytes(game.canvas, "RGB") != bytes([90]) * (960 * 540 * 3)
        front = next((item for item in game.world.environment_objects
                      if item.layer == "front"), None)
        assert front is not None
        game.camera = front.x - 200
        game.canvas.fill((90, 90, 90))
        game._environment("front")
        assert pygame.image.tobytes(game.canvas, "RGB") != bytes([90]) * (960 * 540 * 3)
    finally:
        game.close()
