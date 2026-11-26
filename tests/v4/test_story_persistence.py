"""Real-game checkpoint safety; every save path is isolated from player data."""

import json

import pytest

from nur_game import config
from nur_game.game import Game


@pytest.fixture
def live_game(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SAVE_PATH', tmp_path / 'story-v4.json')
    game = Game(seed=1234, muted=True, persist=False)
    yield game
    game.audio.close()


def test_story_checkpoint_roundtrip_keeps_collected_and_skipped_scene(live_game):
    game = live_game
    game.story.skip()  # Opening.
    game.story.collect('F01')
    game.story.skip()
    game.persist = True
    game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    assert 'story' in saved
    assert saved['version'] == 4
    assert saved['story']['version'] == 1
    assert saved['story']['collected'] == ['F01']
    assert saved['story']['seen'] == ['CS00', 'CS01']
    game.story.collected.clear()
    game.story.seen.clear()
    assert game.load_save()
    assert game.story.collected == {'F01'}
    assert game.story.seen == {'CS00', 'CS01'}
    assert game.story.active is None
    assert game.state == 'playing'


def test_no_save_returns_false(live_game):
    assert live_game._save() is False
    assert not config.SAVE_PATH.exists()


def test_menu_only_quit_does_not_overwrite_checkpoint(live_game):
    import pygame

    original = b'previous player checkpoint'
    config.SAVE_PATH.write_bytes(original)
    menu = Game(seed=1234, start=False, muted=True, persist=True)
    try:
        assert menu._save() is False
        menu.event(pygame.event.Event(pygame.QUIT))
        assert config.SAVE_PATH.read_bytes() == original
    finally:
        menu.audio.close()


def test_legacy_checkpoint_collects_passed_fragments_and_queues_memories(live_game):
    from nur_game.cinematics.fragments import STORY_FRAGMENTS
    from nur_game.continuum import REGIONS

    game = live_game
    game.world.player.position = (REGIONS[15].start + 155, 438)
    game.room = game.last_refuge = 15
    game.world.set_phase(1)
    game.lantern.charge = .44
    game.journal['kept'] = 'old journal'
    from nur_game.story import FRAGMENTS
    game.memory.found = {FRAGMENTS[0].key}
    game.persist = True
    game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    saved.pop('story')
    config.SAVE_PATH.write_text(json.dumps(saved))
    assert game.load_save()
    expected = {f.key for f in STORY_FRAGMENTS if f.position[0] < saved['position'][0]}
    assert game.story.collected == expected
    assert game.story.seen == {'CS00'}
    assert game.story.active == 'CS01'
    assert game.state == 'cutscene'
    assert game.world.player.position.x == saved['position'][0]
    assert game.world.phase == 1
    assert game.lantern.charge == .44
    assert game.journal == {'kept': 'old journal'}
    assert game.memory.found == {FRAGMENTS[0].key}
    while game.story.active:
        game.story.skip()
    assert game.story.seen == {'CS00', 'CS01', 'CS02', 'CS03'}


def test_completed_legacy_finale_migrates_to_completed_story(live_game):
    from nur_game.cinematics.fragments import STORY_FRAGMENTS

    legacy = Game(room=28, seed=1234, muted=True, persist=False, cinematics=False)
    try:
        legacy.boss.local.phase = 2
        legacy.boss.local.name_presses = 3
        legacy.boss.local.done = True
        for echo in legacy.boss.echoes:
            echo['taken'] = True
        legacy.persist = True
        legacy._save()
        saved = json.loads(config.SAVE_PATH.read_text())
        saved.pop('story')
        config.SAVE_PATH.write_text(json.dumps(saved))
    finally:
        legacy.audio.close()
    assert live_game.load_save()
    assert live_game.story.collected == {f.key for f in STORY_FRAGMENTS}
    assert live_game.story.seen == {f'CS{i:02d}' for i in range(9)}
    assert live_game.story.completed is True
    assert live_game.story.finale_requested is True
    assert live_game.story.active is None
    assert live_game.state == 'ending'
    assert live_game.boss is None


def test_art_seed_failure_does_not_partially_restore_game(live_game, monkeypatch):
    game = live_game
    game.story.skip()
    game.persist = True
    game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    saved['seed'] += 1
    config.SAVE_PATH.write_text(json.dumps(saved))
    game.art.background(0)
    before = game.snapshot()
    identities = {key: getattr(game, key) for key in ('world', 'memory', 'story', 'art', 'hallucination_visuals')}
    art_seed = game.art.seed
    backgrounds = dict(game.art._backgrounds)

    def fail_after_mutating(art, seed):
        art.seed = seed
        art._backgrounds.clear()
        raise RuntimeError('simulated scenery generation failure')

    monkeypatch.setattr(type(game.art), 'set_seed', fail_after_mutating)
    assert game.load_save() is False
    assert game.snapshot() == before
    assert all(getattr(game, key) is value for key, value in identities.items())
    assert game.art.seed == art_seed
    assert game.art._backgrounds == backgrounds


@pytest.mark.parametrize('path,value', [
    (('seed',), 10 ** 400),
    (('seed',), True),
    (('seed',), '1234'),
    (('lantern', 'collections'), 10 ** 400),
    (('lantern', 'deaths'), 10 ** 400),
    (('lantern', 'recoveries'), 10 ** 400),
    (('sanity', 'count'), 10 ** 400),
    (('props', 0, 'velocity'), [1e308, 0]),
    (('props', 0, 'angle'), 1e308),
    (('play_seconds',), 1e308),
])
def test_unsafe_simulation_numbers_reject_without_mutation(live_game, path, value):
    game = live_game
    game.persist = True
    game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    target = saved
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    config.SAVE_PATH.write_text(json.dumps(saved))
    before = game.snapshot()
    story_before = game.story.snapshot()
    identities = {key: getattr(game, key) for key in ('world', 'memory', 'story', 'art', 'hallucination_visuals')}
    assert game.load_save() is False
    assert game.snapshot() == before
    assert game.story.snapshot() == story_before
    assert all(getattr(game, key) is obj for key, obj in identities.items())


def test_successful_save_returns_true(live_game):
    live_game.persist = True
    assert live_game._save() is True
    assert json.loads(config.SAVE_PATH.read_text())['story'] == live_game.story.snapshot()


@pytest.mark.parametrize('bad', ['position', 'prop_position', 'prop_velocity', 'non_json'])
def test_invalid_outgoing_checkpoint_preserves_previous_save(live_game, bad):
    game = live_game
    game.persist = True
    assert game._save()
    previous = config.SAVE_PATH.read_bytes()
    if bad == 'position':
        game.world.player.position = (130, 700)
    elif bad == 'prop_position':
        game.world.crates[0].body.position = (-1000, 431)
    elif bad == 'prop_velocity':
        game.world.crates[0].body.velocity = (1e308, 0)
    else:
        game.journal['invalid'] = b'not JSON'
    assert game._save() is False
    assert config.SAVE_PATH.read_bytes() == previous


def test_dead_fall_saves_last_refuge_with_safe_props_without_moving_live_player(live_game):
    from nur_game.continuum import REGIONS

    game = live_game
    game.story.skip()
    game.story.collect('F01')
    game.story.skip()
    game.last_refuge = 5
    game.world.player.position = (REGIONS[5].start + 200, 900)
    game.world.kill('fall')
    game.world.crates[0].body.position = (500, 2000)
    game.world.crates[0].body.velocity = (1e308, 0)
    game.planted = (500, 900)
    game.lantern.carried = False
    game.sanity.current_sanity = 0
    game.sanity.dead = True
    game.persist = True
    position = tuple(game.world.player.position)
    assert game._save() is True
    assert tuple(game.world.player.position) == position
    assert game.world.dead
    saved = json.loads(config.SAVE_PATH.read_text())
    assert saved['position'] == list(REGIONS[5].refuge)
    assert saved['room'] == 5
    assert saved['props'] == []
    assert saved['planted'] is None
    assert game.load_save()
    assert tuple(game.world.player.position) == REGIONS[5].refuge
    assert not game.world.dead
    assert not game.sanity.dead
    assert game.lantern.carried
    assert game.story.seen == {'CS00', 'CS01'}


def test_story_checkpoint_retains_legacy_memory_inventory(live_game):
    from nur_game.story import FRAGMENTS

    game = live_game
    game.memory.found = {FRAGMENTS[0].key, FRAGMENTS[1].key}
    game.memory.false = {FRAGMENTS[0].key}
    game.memory.candles = 1
    game.memory.truth = 2
    before = game.memory.snapshot()
    game.persist = True
    assert game._save()
    assert game.load_save()
    assert game.memory.snapshot() == before


def test_active_cutscene_resumes_from_start_and_unpauses(live_game):
    game = live_game
    game.story.skip()
    game.story.collect('F01')
    game.story.tick(7.5)
    game.story.paused = True
    game.persist = True
    assert game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    assert saved['story']['active'] == 'CS01'
    assert game.load_save()
    assert game.story.active == 'CS01'
    assert game.story.scene_elapsed == 0
    assert game.story.paused is False
    assert game.state == 'cutscene'
    game.story.skip()
    assert game._save()
    assert game.load_save()
    assert 'CS01' in game.story.seen
    assert game.story.active is None
    assert game.state == 'playing'


def test_completed_story_roundtrip_returns_to_ending(live_game):
    from nur_game.cinematics.fragments import STORY_FRAGMENTS

    game = live_game
    game.story.skip()
    for fragment in STORY_FRAGMENTS:
        game.story.collect(fragment.key)
        game.story.skip()
    assert game.story.request_finale()
    game.story.skip()
    game.story.skip()
    game.persist = True
    assert game._save()
    assert game.load_save()
    assert game.story.completed
    assert game.story.active is None
    assert game.story.seen == {f'CS{i:02d}' for i in range(9)}
    assert game.state == 'ending'
    assert game.boss is None


@pytest.mark.parametrize('field,value', [
    ('version', True), ('version', 2), ('collected', ['F99']),
    ('collected', [1]), ('collected', ['F01', 'F01']),
    ('seen', ['CS99']), ('seen', ['CS00', 'CS02']),
    ('seen', ['CS00', 'CS01']), ('seen', ['CS00', 'CS00']),
    ('active', 'CS02'), ('active', 'CS99'), ('active', True),
    ('finale_requested', 1), ('finale_requested', True),
    ('completed', 'false'), ('completed', True),
])
def test_malformed_story_rejected_without_mutating_any_live_state(live_game, field, value):
    game = live_game
    game.persist = True
    assert game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    saved['story'][field] = value
    config.SAVE_PATH.write_text(json.dumps(saved))
    before = game.snapshot()
    story_before = vars(game.story).copy()
    identities = {key: getattr(game, key) for key in ('world', 'memory', 'story', 'art', 'hallucination_visuals')}
    assert game.load_save() is False
    assert game.snapshot() == before
    assert vars(game.story) == story_before
    assert all(getattr(game, key) is obj for key, obj in identities.items())


@pytest.mark.parametrize('failure', ['write', 'replace'])
def test_io_failure_returns_false_and_preserves_previous_checkpoint(live_game, monkeypatch, failure):
    from pathlib import Path

    game = live_game
    game.persist = True
    assert game._save()
    previous = config.SAVE_PATH.read_bytes()

    def fail(*args, **kwargs):
        raise OSError('simulated full disk or denied permission')

    monkeypatch.setattr(Path, 'write_text' if failure == 'write' else 'replace', fail)
    assert game._save() is False
    assert config.SAVE_PATH.read_bytes() == previous


def test_nonfinite_outgoing_value_is_not_written_as_json(live_game):
    game = live_game
    game.persist = True
    assert game._save()
    previous = config.SAVE_PATH.read_bytes()
    game.play_seconds = float('nan')
    assert game._save() is False
    assert config.SAVE_PATH.read_bytes() == previous


@pytest.mark.parametrize('contents', ['{broken JSON', '[]', 'null', '{"version": 4}'])
def test_corrupt_checkpoint_is_rejected_without_mutation(live_game, contents):
    config.SAVE_PATH.write_text(contents)
    before = live_game.snapshot()
    story = live_game.story
    assert live_game.load_save() is False
    assert live_game.snapshot() == before
    assert live_game.story is story


def test_accepted_numeric_limits_survive_simulation_and_render(live_game):
    import math

    from nur_game.game.persistence import MAX_COUNTER, MAX_PROP_ANGLE, MAX_PROP_SPEED, MAX_SECONDS
    from nur_game.physics import NurInput

    game = live_game
    game.story.skip()
    game.persist = True
    assert game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    saved['seed'] = MAX_COUNTER
    saved['play_seconds'] = MAX_SECONDS
    saved['sanity']['count'] = MAX_COUNTER
    saved['lantern']['collections'] = MAX_COUNTER
    saved['props'][0]['velocity'] = [MAX_PROP_SPEED, -MAX_PROP_SPEED]
    saved['props'][0]['angle'] = MAX_PROP_ANGLE
    config.SAVE_PATH.write_text(json.dumps(saved))
    assert game.load_save()
    game.update(1 / 120, NurInput())
    assert game.draw().get_size() == config.SIZE
    assert math.isfinite(game.sanity.lantern_multiplier)
    for crate in game.world.crates:
        assert all(math.isfinite(n) for n in (*crate.body.position, *crate.body.velocity, crate.body.angle))


def test_collected_pending_memory_is_queued_on_load(live_game):
    game = live_game
    game.story.skip()
    game.persist = True
    assert game._save()
    saved = json.loads(config.SAVE_PATH.read_text())
    saved['story']['collected'] = ['F01', 'F02']
    saved['story']['active'] = None
    config.SAVE_PATH.write_text(json.dumps(saved))
    assert game.load_save()
    assert game.story.active == 'CS01'
    assert game.state == 'cutscene'
    game.story.skip()
    assert game.story.active == 'CS02'


def test_menu_can_load_existing_story_checkpoint_and_then_save(live_game):
    live_game.story.skip()
    live_game.persist = True
    assert live_game._save()
    menu = Game(start=False, muted=True, persist=True)
    try:
        assert not menu.session_started
        assert menu.load_save()
        assert menu.session_started
        assert menu.state == 'playing'
        assert menu._save() is True
    finally:
        menu.audio.close()


def test_loading_void_checkpoint_is_silent_without_changing_player_mute_choice(live_game):
    import pygame
    from nur_game.cinematics.fragments import STORY_FRAGMENTS

    game = live_game
    game.muted = False
    game.audio.set_muted(False)
    game.story.skip()
    for fragment in STORY_FRAGMENTS:
        game.story.collect(fragment.key)
        game.story.skip()
    assert game.story.request_finale()
    game.persist = True
    assert game._save()
    assert game.load_save()
    assert game.state == 'cutscene' and game.story.active == 'CS07'
    assert game.muted is False
    assert game.audio.enabled is False
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert game.story.active == 'CS08'
    assert game.audio.enabled is True
