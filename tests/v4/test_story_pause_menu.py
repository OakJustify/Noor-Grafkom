"""Returning to the main menu from the pause screen.

The pause screen previously offered only 'resume' and 'retry from the last
station', so leaving a journey required quitting the whole process.  Returning
to the menu must keep the checkpoint (C resumes it) and must not disturb the
world, the story state, or a real save file.
"""
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import pytest

from nur_game import config
from nur_game.game import Game
from nur_game.physics import NurInput


def _started_game(**kwargs):
    """A game whose opening cutscene is already over, so ESC reaches pause."""
    kwargs.setdefault('persist', False)
    game = Game(seed=1234, muted=True, **kwargs)
    if game.state == 'cutscene':
        game.story.skip()
        game._sync_story_state()
    assert game.state == 'playing'
    return game


def _paused_game(**kwargs):
    game = _started_game(**kwargs)
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert game.state == 'paused'
    return game


def test_pause_offers_a_way_back_to_the_main_menu():
    game = _paused_game()
    labels = []
    original = game._caption

    def record(text, *args, **kwargs):
        labels.append(text)
        return original(text, *args, **kwargs)

    game._caption = record
    try:
        game.draw()
        assert any('B simpan & kembali ke menu utama' in text for text in labels), labels
    finally:
        game.audio.close()


def test_b_in_pause_returns_to_the_main_menu_without_touching_the_world(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'previous checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = _started_game(persist=True)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'paused'
        before = ({k: v for k, v in game.snapshot().items() if k != 'state'},
                  game.story.snapshot(), game._player_xy())
        assert game.return_to_menu() is True
        assert game.state == 'menu'
        after = ({k: v for k, v in game.snapshot().items() if k != 'state'},
                 game.story.snapshot(), game._player_xy())
        assert after == before
        assert not game.session_started
        # Leaving via the menu must not rewrite a file that was already saved.
        game.event(pygame.event.Event(pygame.QUIT))
        assert path.exists()
    finally:
        game.audio.close()


def test_return_to_menu_saves_the_checkpoint_first(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = _started_game(persist=True)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        position = game._player_xy()
        game.return_to_menu()
        assert path.is_file()
        assert game.state == 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
        assert game.state == 'playing' and game.session_started
        assert game._player_xy() == position
    finally:
        game.audio.close()


def test_b_elsewhere_does_nothing():
    game = _started_game()
    try:
        assert game.state == 'playing'
        before = game.snapshot(), game.story.snapshot()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b))
        assert game.state == 'playing'
        assert (game.snapshot(), game.story.snapshot()) == before
        assert game.return_to_menu() is False
    finally:
        game.audio.close()


def test_return_to_menu_ends_developer_practice_and_restores_saving(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'normal checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(seed=1234, start=False, muted=True, persist=True)
    try:
        game.start_developer_mode()
        assert game.developer_mode and not game.persist
        if game.state == 'cutscene':
            game.story.skip()
            game._sync_story_state()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'paused'
        assert game.return_to_menu() is True
        assert game.state == 'menu'
        assert not game.developer_mode and game.persist is True
        assert path.read_bytes() == b'normal checkpoint'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        assert game.developer_mode and not game.persist
    finally:
        game.audio.close()


def test_pause_does_not_fire_on_the_very_first_frame_and_freezes_simulation():
    game = _paused_game()
    try:
        before = (game.world.time, game.play_seconds, game._player_xy())
        for _ in range(20):
            game.update(.05, NurInput(move=1, action=True))
        assert (game.world.time, game.play_seconds, game._player_xy()) == before
    finally:
        game.audio.close()


def test_escape_still_toggles_back_to_playing_after_using_the_menu_option():
    game = _paused_game()
    try:
        game.return_to_menu()
        assert game.state == 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'cutscene' and game.story.active == 'CS00'
        game.story.skip()
        game._sync_story_state()
        assert game.state == 'playing'
    finally:
        game.audio.close()