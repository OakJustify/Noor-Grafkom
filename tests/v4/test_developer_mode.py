"""Opt-in fragment practice through the live controller and launcher."""
import pygame
import pytest

from nur_game import config
from nur_game.game import Game
from nur_game.cinematics.fragments import STORY_FRAGMENTS
from nur_game.cinematics.progress import StoryProgress
from nur_game.physics import NurInput


def test_developer_session_never_overwrites_player_checkpoint(tmp_path, monkeypatch):
    path = tmp_path / 'player-checkpoint.json'
    original = b'existing player checkpoint'
    path.write_bytes(original)
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    game = Game(developer_mode=True, muted=True, persist=True)
    try:
        assert game.developer_mode is True
        assert game.persist is False
        assert game._save() is False
        game.start(0)
        game.event(pygame.event.Event(pygame.QUIT))
        assert path.read_bytes() == original
    finally:
        game.audio.close()


@pytest.mark.parametrize('fragment', STORY_FRAGMENTS, ids=lambda f: f.key)
def test_each_fragment_jump_uses_same_world_and_live_collection(fragment):
    game = Game(developer_mode=True, muted=True, persist=False)
    try:
        space, player = game.world.space, game.world.player
        assert game.developer_jump(fragment.key) is True
        assert game.state == 'playing' and game.story.active is None
        assert game.world.space is space and game.world.player is player
        assert game.room == game.world.chapter == game.last_refuge == fragment.region
        assert game.world.quest is game.world.quests.get(fragment.region)
        assert game._player_xy() == (fragment.position[0] - 90, fragment.position[1])
        assert game.world.player.velocity == (0, 0)
        assert game.lantern.charge == 1 and game.lantern.carried
        assert game.planted is None
        index = STORY_FRAGMENTS.index(fragment)
        assert game.story.collected == {f.key for f in STORY_FRAGMENTS[:index]}
        assert game.story.seen == {'CS00', *(f.scene for f in STORY_FRAGMENTS[:index])}
        assert StoryProgress.restore(game.story.snapshot()).snapshot() == game.story.snapshot()
        game.update(.02, NurInput())
        assert fragment.key not in game.story.collected
        for _ in range(90):
            game.update(.02, NurInput(move=1))
            if game.state == 'cutscene':
                break
        assert not game.world.dead
        assert game.state == 'cutscene' and game.story.active == fragment.scene
        assert fragment.key in game.story.collected
        assert game.world.space is space
    finally:
        game.audio.close()


@pytest.mark.parametrize('number,fragment', tuple(enumerate(STORY_FRAGMENTS, 1)), ids=lambda value: getattr(value, 'key', str(value)))
def test_function_keys_jump_even_during_an_active_cutscene(number, fragment):
    game = Game(developer_mode=True, muted=True, persist=False)
    try:
        assert game.story.active == 'CS00'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f'K_F{number}')))
        assert game.state == 'playing'
        assert game._player_xy() == (fragment.position[0] - 90, fragment.position[1])
    finally:
        game.audio.close()


def test_developer_shortcuts_are_disabled_in_normal_game():
    game = Game(muted=True, persist=False)
    try:
        before = game.snapshot(), game.story.snapshot()
        assert game.developer_mode is False
        assert game.developer_jump('F06') is False
        for number in range(1, 7):
            game.event(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f'K_F{number}')))
        assert (game.snapshot(), game.story.snapshot()) == before
    finally:
        game.audio.close()


def test_developer_jump_clears_physics_input_and_rearms_a_seen_fragment():
    import pymunk

    game = Game(developer_mode=True, muted=True, persist=False)
    try:
        game.developer_jump('F06')
        game.story.collect('F06')
        game.story.skip()
        game.story.request_finale()
        game._sync_story_state()
        game.story.paused = True
        joint = pymunk.PivotJoint(game.world.player, game.world.crates[0].body, (0, 0), (0, 0))
        game.world.space.add(joint)
        game.world.grab_joint = joint
        game.world.flip_gravity(-1)
        game.world.space.add(joint)
        game.world.grab_joint = joint
        game.world.player.velocity = (500, -300)
        game.world.dead = True
        game.world.jump_buffer = game.world.coyote = .1
        game.world.set_phase(1)
        game.pending_action = game.pending_shift = game.phase_held = True
        game.interaction_held = game.plant_held = game.free_shift_held = True
        game.accumulator = .1
        game.planted = game._player_xy()
        game.lantern.charge = 0
        game.stamina.amount = 0
        game.stamina.exhausted = True
        space = game.world.space
        assert game.developer_jump('F06')
        assert joint not in space.constraints and game.world.grab_joint is None
        assert not game.world.dead and not game.world.death_reason
        assert game.world.gravity == 1 and space.gravity.y > 0 and game.world.phase == 0
        assert game.world.jump_buffer == game.world.coyote == game.accumulator == 0
        assert not any((game.pending_action, game.pending_shift, game.phase_held,
                        game.interaction_held, game.plant_held, game.free_shift_held))
        assert not game.story.paused and not game.story.finale_requested and not game.story.completed
        assert 'F06' not in game.story.collected and 'CS06' not in game.story.seen
        assert game.lantern.charge == game.stamina.amount == 1
        assert game.world.stamina is game.stamina and not game.stamina.exhausted
        assert game.world.space is space and game.story.active is None
        before = game.snapshot(), game.story.snapshot()
        for invalid in ('F6', 'f06', 'F07', None):
            with pytest.raises(ValueError, match='Unknown developer fragment'):
                game.developer_jump(invalid)
            assert (game.snapshot(), game.story.snapshot()) == before
    finally:
        game.audio.close()


def test_launcher_developer_flags_start_at_selected_fragment_without_saving(tmp_path, monkeypatch):
    import json
    from nur_game.game import main

    path = tmp_path / 'player-checkpoint.json'
    path.write_bytes(b'untouched player checkpoint')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    report = tmp_path / 'developer-report.json'
    assert main(['--dev', '--fragment', 'F06', '--headless', '--frames', '1',
                 '--mute', '--report', str(report)]) == 0
    data = json.loads(report.read_text(encoding='utf-8'))['simulation']
    assert data['region'] == STORY_FRAGMENTS[-1].region + 1
    assert data['state'] == 'playing'
    assert path.read_bytes() == b'untouched player checkpoint'


@pytest.mark.parametrize('args', [
    ['--fragment', 'F01'], ['--dev', '--fragment', 'F1'], ['--dev', '--continue'],
])
def test_launcher_rejects_ambiguous_or_invalid_developer_flags(args):
    from nur_game.game import main

    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


def test_developer_hud_exposes_all_shortcuts_without_overlaying_black_void(monkeypatch):
    game = Game(developer_mode=True, muted=True, persist=False)
    labels = []
    text = game._text

    def record_text(value, *args, **kwargs):
        labels.append(value)
        return text(value, *args, **kwargs)

    monkeypatch.setattr(game, '_text', record_text)
    try:
        game.developer_jump('F01')
        game.draw()
        assert any('DEVELOPER' in value and 'Save nonaktif' in value for value in labels)
        assert any('F1 pita' in value and 'F6 kain' in value for value in labels)
        game.developer_jump('F06')
        game.story.collect('F06')
        game.story.skip()
        game.story.request_finale()
        game._sync_story_state()
        game.story.scene_elapsed = 9.5
        assert not pygame.surfarray.array3d(game.draw()).any()
    finally:
        game.audio.close()


@pytest.mark.parametrize('state', ['playing', 'paused', 'journal', 'gallery', 'menu', 'ending'])
def test_developer_shortcut_returns_from_real_navigation_states(state):
    game = Game(developer_mode=True, start=state != 'menu', muted=True, persist=False)
    try:
        key = lambda value: game.event(pygame.event.Event(pygame.KEYDOWN, key=value))
        if state != 'menu':
            key(pygame.K_ESCAPE)
        if state == 'paused':
            key(pygame.K_ESCAPE)
        elif state == 'journal':
            key(pygame.K_j)
        elif state == 'gallery':
            key(pygame.K_k)
        elif state == 'ending':
            game.developer_jump('F06')
            game.story.collect('F06')
            game.story.skip()
            game.story.request_finale()
            game._sync_story_state()
            key(pygame.K_ESCAPE)
            key(pygame.K_ESCAPE)
        assert game.state == state
        key(pygame.K_F4)
        assert game.state == 'playing' and game.story.active is None
        assert game.room == STORY_FRAGMENTS[3].region
    finally:
        game.audio.close()
