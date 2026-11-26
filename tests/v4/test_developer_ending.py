"""Developer finale practice must use valid production story transitions."""
import pygame
import pytest

from nur_game import config
from nur_game.cinematics.fragments import STORY_FRAGMENTS
from nur_game.cinematics.progress import StoryProgress
from nur_game.continuum import REGIONS, WORLD_WIDTH
from nur_game.game import Game
from nur_game.physics import NurInput


@pytest.mark.parametrize('stage,active,state', [
    ('void', 'CS07', 'cutscene'), ('realworld', 'CS08', 'cutscene'),
    ('cards', None, 'ending'),
])
def test_developer_finale_stages_prepare_valid_story_and_same_world(stage, active, state):
    game = Game(developer_mode=True, muted=True, persist=False)
    try:
        space, player = game.world.space, game.world.player
        assert game.developer_ending(stage)
        assert game.story.active == active and game.state == state
        assert game.story.collected == {f.key for f in STORY_FRAGMENTS}
        assert {f'fragment:{f.key}': f.title for f in STORY_FRAGMENTS}.items() <= game.journal.items()
        assert game.story.seen >= {'CS00', *(f.scene for f in STORY_FRAGMENTS)}
        assert game.story.finale_requested and game.story.completed == (stage == 'cards')
        assert StoryProgress.restore(game.story.snapshot()).snapshot() == game.story.snapshot()
        assert game.room == game.world.chapter == game.last_refuge == len(REGIONS)-1
        assert game._player_xy() == (WORLD_WIDTH-140, 438)
        assert game.world.player.velocity == (0, 0)
        assert game.world.space is space and game.world.player is player
        assert game.camera == WORLD_WIDTH-config.SIZE[0]
        assert game._save() is False and game.persist is False
        game.draw()
    finally:
        game.audio.close()


@pytest.mark.parametrize('key,active,state', [
    (pygame.K_F7, 'CS07', 'cutscene'), (pygame.K_F8, 'CS08', 'cutscene'),
    (pygame.K_F9, None, 'ending'),
])
def test_finale_function_keys_work_from_cutscenes_and_can_repeat(key, active, state):
    game = Game(developer_mode=True, muted=True, persist=False)
    try:
        for _ in range(2):
            game.event(pygame.event.Event(pygame.KEYDOWN, key=key))
            assert game.story.active == active and game.state == state
            assert game.ending_page == 0
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
        assert game.state == 'playing' and not game.story.finale_requested
        assert not game.story.completed and not game.story.collected
    finally:
        game.audio.close()


def test_finale_preview_auto_plays_void_then_realworld_without_saving(tmp_path, monkeypatch):
    path = tmp_path/'existing.json'
    path.write_bytes(b'preserve real checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(developer_mode=True, muted=True, persist=True)
    try:
        game.developer_ending()
        before = (game.world.time, game.play_seconds, game.lantern.charge)
        observed = set()
        for _ in range(1030):
            observed.add(game.story.active)
            game.update(.1, NurInput(move=1, action=True))
            if game.state == 'ending':
                break
        assert {'CS07', 'CS08'} <= observed
        assert game.state == 'ending' and game.story.completed
        assert (game.world.time, game.play_seconds, game.lantern.charge) == before
        game.event(pygame.event.Event(pygame.QUIT))
        assert path.read_bytes() == b'preserve real checkpoint'
    finally:
        game.audio.close()


def test_void_preview_is_black_and_silent_then_restores_audio_for_realworld():
    game = Game(developer_mode=True, muted=False, persist=False)
    try:
        game.developer_ending('void')
        assert not game.audio.enabled and not game.muted
        game.story.scene_elapsed = 9.5
        assert not pygame.surfarray.array3d(game.draw()).any()
        game.developer_ending('realworld')
        assert game.audio.enabled and not game.muted
        assert pygame.surfarray.array3d(game.draw()).any()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'ending'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.ending_page == 1
    finally:
        game.audio.close()


def test_finale_preview_is_opt_in_and_invalid_stage_does_not_mutate():
    game = Game(muted=True, persist=False)
    try:
        before = game.snapshot(), game.story.snapshot()
        assert game.developer_ending() is False
        for key in (pygame.K_F7, pygame.K_F8, pygame.K_F9):
            game.event(pygame.event.Event(pygame.KEYDOWN, key=key))
        assert (game.snapshot(), game.story.snapshot()) == before
        game.developer_mode = True
        with pytest.raises(ValueError, match='Unknown developer ending stage'):
            game.developer_ending('CS08')
        assert (game.snapshot(), game.story.snapshot()) == before
    finally:
        game.audio.close()


@pytest.mark.parametrize('option,active,state', [
    ([], 'CS07', 'cutscene'), (['realworld'], 'CS08', 'cutscene'),
    (['cards'], None, 'ending'),
])
def test_launcher_can_start_each_ending_stage(option, active, state, monkeypatch, tmp_path):
    from nur_game.game import cli

    created = []

    def create_game(**kwargs):
        game = Game(**kwargs)
        created.append(game)
        return game

    path = tmp_path/'save.json'
    path.write_bytes(b'keep checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    monkeypatch.setattr(cli, 'Game', create_game)
    assert cli.main(['--dev', '--ending', *option, '--headless', '--frames', '1', '--mute']) == 0
    assert created[0].story.active == active and created[0].state == state
    assert created[0].persist is False
    assert path.read_bytes() == b'keep checkpoint'


@pytest.mark.parametrize('args', [
    ['--ending'], ['--dev', '--ending', 'CS08'],
    ['--dev', '--ending', '--fragment', 'F01'], ['--dev', '--ending', '--continue'],
])
def test_ending_cli_rejects_invalid_or_ambiguous_options(args):
    from nur_game.game import main

    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


def test_developer_hud_lists_new_ending_shortcuts(monkeypatch):
    game = Game(developer_mode=True, muted=True, persist=False)
    labels = []
    original = game._text

    def record(text, *args, **kwargs):
        labels.append(text)
        return original(text, *args, **kwargs)

    monkeypatch.setattr(game, '_text', record)
    try:
        game.developer_jump('F01')
        game.draw()
        assert any('F7 void' in text and 'F8 ending' in text and 'F9 penutup' in text for text in labels)
    finally:
        game.audio.close()
