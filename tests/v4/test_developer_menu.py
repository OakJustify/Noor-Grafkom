"""Enter unsaved developer practice from the ordinary --menu launcher."""
import pygame
import pytest

from nur_game import config
from nur_game.cinematics.fragments import STORY_FRAGMENTS
from nur_game.game import Game


def test_menu_d_starts_developer_practice_without_overwriting_checkpoint(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'keep normal checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(start=False, muted=True, persist=True)
    try:
        assert game.state == 'menu' and not game.developer_mode
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        assert game.developer_mode and not game.persist
        assert game.state == 'playing' and game.story.active is None
        fragment = STORY_FRAGMENTS[0]
        assert game._player_xy() == (fragment.position[0]-90, fragment.position[1])
        assert game.session_started and game._save() is False
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F7))
        assert game.story.active == 'CS07'
        game.event(pygame.event.Event(pygame.QUIT))
        assert path.read_bytes() == b'keep normal checkpoint'
    finally:
        game.audio.close()


@pytest.mark.parametrize('size', [(960, 540), (1280, 720), (480, 270)])
def test_menu_button_click_starts_practice_at_resized_window_sizes(size):
    game = Game(start=False, muted=True, persist=False)
    try:
        game.display = pygame.display.set_mode(size, pygame.RESIZABLE)
        point = (round(480*size[0]/960), round(402*size[1]/540))
        game.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        assert game.developer_mode and game.state == 'playing'
        assert not game.persist and game.story.active is None
    finally:
        game.audio.close()


def test_menu_draws_developer_button_with_hover_feedback(monkeypatch):
    game = Game(start=False, muted=True, persist=False)
    labels = []
    original = game._text

    def record(text, *args, **kwargs):
        labels.append(text)
        return original(text, *args, **kwargs)

    monkeypatch.setattr(game, '_text', record)
    try:
        monkeypatch.setattr(pygame.mouse, 'get_pos', lambda: (0, 0))
        idle = game.draw().copy()
        assert any('D · MODE DEVELOPER' in text for text in labels)
        assert any('tanpa save' in text for text in labels)
        monkeypatch.setattr(pygame.mouse, 'get_pos', lambda: (480, 402))
        hover = game.draw()
        assert idle.get_at((350, 390)) != hover.get_at((350, 390))
        assert not game.developer_mode and game.state == 'menu'
    finally:
        game.audio.close()


@pytest.mark.parametrize('button,point', [(1, (0, 0)), (3, (480, 402)), (2, (480, 402))])
def test_other_menu_mouse_clicks_do_not_start_practice(button, point):
    game = Game(start=False, muted=True, persist=False)
    try:
        game.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=point))
        assert not game.developer_mode and game.state == 'menu'
    finally:
        game.audio.close()


def test_developer_button_and_d_key_do_not_activate_outside_production_menu():
    game = Game(muted=True, persist=False)
    try:
        before = game.snapshot(), game.story.snapshot()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        game.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 402)))
        assert (game.snapshot(), game.story.snapshot()) == before
        assert game.start_developer_mode() is False
        game.cinematics_enabled = False
        game.state = 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        assert not game.developer_mode and game.start_developer_mode() is False
    finally:
        game.audio.close()


@pytest.mark.parametrize('persist', [True, False])
@pytest.mark.parametrize('key', [pygame.K_RETURN, pygame.K_SPACE])
def test_normal_start_from_menu_restores_original_save_setting(persist, key, tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'normal checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(start=False, muted=True, persist=persist)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F9))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=key))
        assert not game.developer_mode and game.persist is persist
        assert game.story.active == 'CS00' and not game.story.collected
        if not persist:
            assert path.read_bytes() == b'normal checkpoint'
    finally:
        game.audio.close()


def test_failed_continue_after_practice_cannot_save_practice_over_checkpoint(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'invalid original checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(start=False, muted=True, persist=True)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F9))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
        assert not game.developer_mode and game.persist
        assert not game.session_started and game.state == 'menu'
        game.event(pygame.event.Event(pygame.QUIT))
        assert path.read_bytes() == b'invalid original checkpoint'
    finally:
        game.audio.close()


def test_continue_after_practice_loads_original_campaign(tmp_path, monkeypatch):
    path = tmp_path/'checkpoint.json'
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(start=False, muted=True, persist=True)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game._save()
        original = path.read_bytes()
        position = game._player_xy()
        game.state = 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F9))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
        assert not game.developer_mode and game.persist and game.session_started
        assert game.state == 'playing' and not game.story.collected
        assert game._player_xy() == position
        assert path.read_bytes() == original
    finally:
        game.audio.close()


def test_ordinary_menu_launcher_handles_real_click_without_dev_flag(tmp_path, monkeypatch):
    from nur_game.game import cli

    created = []

    def create_game(**kwargs):
        game = Game(**kwargs)
        created.append(game)
        return game

    path = tmp_path/'checkpoint.json'
    path.write_bytes(b'keep checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    monkeypatch.setattr(cli, 'Game', create_game)
    events = iter([
        [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 402))],
        [pygame.event.Event(pygame.QUIT)],
    ])
    monkeypatch.setattr(pygame.event, 'get', lambda: next(events, []))
    assert cli.main(['--menu', '--headless', '--frames', '2', '--mute']) == 0
    assert created[0].developer_mode and not created[0].persist
    assert created[0].state == 'playing'
    assert path.read_bytes() == b'keep checkpoint'
