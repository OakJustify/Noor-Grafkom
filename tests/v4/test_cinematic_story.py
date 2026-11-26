"""Live narrative contracts: subtitle cutscenes, ordered fragments and finale."""

from nur_game.game import Game
import pygame

from nur_game.physics import NurInput
from nur_game.continuum import REGIONS
from nur_game.continuum import WORLD_WIDTH


def test_new_game_starts_with_opening_cutscene():
    game = Game(muted=True, persist=False)
    try:
        assert game.state == "cutscene"
    finally:
        game.audio.close()


def test_opening_is_frozen_and_skip_records_it_once():
    game = Game(muted=True, persist=False)
    try:
        assert hasattr(game, 'story'), 'Opening needs persistent story state'
        assert game.story.active == 'CS00'
        before = (game.world.time, game.play_seconds, game.lantern.charge,
                  game.stamina.amount, game.sanity.current_sanity)
        game.update(.1, NurInput(move=1, focus=True, shift=True))
        assert before == (game.world.time, game.play_seconds, game.lantern.charge,
                          game.stamina.amount, game.sanity.current_sanity)
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'playing'
        assert game.story.active is None and 'CS00' in game.story.seen
        game.update(.1, NurInput())
        assert game.story.active is None
    finally:
        game.audio.close()


def test_touching_first_story_object_plays_one_cutscene_without_consuming_light():
    game = Game(muted=True, persist=False)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.world.player.position = (REGIONS[1].start + 255, 438)
        game.world.player.velocity = (0, 0)
        game.update(.02, NurInput())
        assert game.state == 'cutscene', 'The red ribbon must trigger CS01'
        assert game.story.active == 'CS01'
        assert game.story.collected == {'F01'}
        light = game.lantern.charge
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.update(.02, NurInput())
        assert game.state == 'playing' and game.story.active is None
        assert game.story.collected == {'F01'}
        assert game.lantern.charge <= light
    finally:
        game.audio.close()


def test_space_pauses_cutscene_clock_without_entering_gameplay():
    game = Game(muted=True, persist=False)
    try:
        game.update(.1, NurInput())
        elapsed = game.story.scene_elapsed
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        game.update(.1, NurInput())
        assert game.story.scene_elapsed == elapsed
        assert game.state == 'cutscene'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        game.update(.1, NurInput())
        assert game.story.scene_elapsed > elapsed
    finally:
        game.audio.close()


def test_world_fade_follows_story_even_with_fully_refilled_lantern():
    game = Game(muted=True, persist=False)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.notice_timer = 0
        luminances = []
        for number in range(7):
            if number:
                game.story.collect(f'F{number:02d}')
                game.story.skip()
            game.lantern.charge = 1
            pixels = pygame.surfarray.array3d(game.draw())
            luminances.append(pixels[180:780, 180:480].mean())
        assert all(a > b for a, b in zip(luminances, luminances[1:]))
        fade = game.story.fade
        game.lantern.kindle('fresh-fuel')
        assert game.story.fade == fade and game.lantern.charge == 1
    finally:
        game.audio.close()


def test_last_road_starts_void_then_real_world_instead_of_boss_fight():
    game = Game(muted=True, persist=False)
    try:
        game.story.skip()
        game.state = 'playing'
        for number in range(1, 7):
            game.story.collect(f'F{number:02d}')
            game.story.skip()
        game.world.player.position = (WORLD_WIDTH - 140, 438)
        game.world.player.velocity = (0, 0)
        game.update(.02, NurInput())
        assert game.state == 'cutscene' and game.story.active == 'CS07'
        assert game.boss is None
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'cutscene' and game.story.active == 'CS08'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'ending' and game.story.completed
    finally:
        game.audio.close()


def test_opening_advances_automatically_to_playable_world_after_fifteen_seconds():
    game = Game(muted=True, persist=False)
    try:
        for _ in range(151):
            game.update(.1, NurInput(move=1))
        assert game.state == 'playing' and game.story.active is None
        assert 'CS00' in game.story.seen
        assert game.play_seconds <= .11
    finally:
        game.audio.close()


def test_live_cutscene_renderer_shows_controls_and_void_has_no_surviving_hud():
    game = Game(muted=True, persist=False)
    try:
        assert hasattr(game, 'cinema'), 'Cinematic illustrations must reach the live draw path'
        game.draw()
        assert game.cinema.last_hint_text == 'Enter lanjut / Space jeda / Esc lewati'
        game.story.skip()
        for number in range(1, 7):
            game.story.collect(f'F{number:02d}')
            game.story.skip()
        game.story.request_finale()
        game.state = 'cutscene'
        for _ in range(95):
            game.update(.1, NurInput())
        assert game.story.active == 'CS07'
        assert not pygame.surfarray.array3d(game.draw()).any()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.story.active == 'CS08'
        assert pygame.surfarray.array3d(game.draw()).mean() > 30
    finally:
        game.audio.close()


def test_enter_advances_one_subtitle_cue_without_restarting_the_game():
    game = Game(muted=True, persist=False)
    try:
        assert game.story.cue_index == 0
        for index in (1, 2):
            game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            assert game.story.cue_index == index
            assert game.state == 'cutscene'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'playing' and 'CS00' in game.story.seen
        assert game.play_seconds == 0
    finally:
        game.audio.close()


def test_gallery_replays_unlocked_memory_without_progress_or_light_changes():
    game = Game(muted=True, persist=False)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        game.story.collect('F01')
        game.story.skip()
        before = game.story.snapshot()
        light = game.lantern.snapshot()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k))
        assert game.state == 'gallery', 'K must open the fragment replay gallery'
        game.draw()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'cutscene' and game.story.active == 'CS01' and game.story.replay
        for _ in range(3):
            game.update(.1, NurInput(move=1))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'gallery'
        assert game.story.snapshot() == before and game.lantern.snapshot() == light
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'gallery', 'Locked scenes may not expose the ending'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k))
        assert game.state == 'playing'
    finally:
        game.audio.close()


def test_ending_cards_are_readable_before_new_journey_resets_story():
    game = Game(muted=True, persist=False)
    try:
        game.story.skip()
        for number in range(1, 7):
            game.story.collect(f'F{number:02d}')
            game.story.skip()
        game.story.request_finale()
        game.state = 'cutscene'
        for _ in range(2):
            game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        before = game.story.snapshot()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'ending' and game.ending_page == 1
        assert game.story.snapshot() == before
        game.draw()
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.state == 'menu'
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert game.state == 'cutscene' and game.story.active == 'CS00'
        assert game.room == 0 and not game.story.collected and game.story.fade == 0
    finally:
        game.audio.close()


def test_cinematic_mute_toggle_and_void_silence_do_not_change_user_preference():
    game = Game(muted=False, persist=False)
    try:
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        assert game.muted and not game.audio.enabled
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        assert not game.muted and game.audio.enabled
        game.story.skip()
        for number in range(1, 7):
            game.story.collect(f'F{number:02d}')
            game.story.skip()
        game.story.request_finale()
        game._sync_story_state()
        assert not game.muted and not game.audio.enabled
        game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert game.story.active == 'CS08' and game.audio.enabled and not game.muted
    finally:
        game.audio.close()


def test_menu_keeps_premise_hidden_but_gameplay_hud_exposes_fragment_controls(monkeypatch):
    game = Game(start=False, muted=True, persist=False)
    captions, labels = [], []
    caption, text = game._caption, game._text

    def record_caption(value, *args, **kwargs):
        captions.append(value)
        return caption(value, *args, **kwargs)

    def record_text(value, *args, **kwargs):
        labels.append(value)
        return text(value, *args, **kwargs)

    monkeypatch.setattr(game, '_caption', record_caption)
    monkeypatch.setattr(game, '_text', record_text)
    try:
        game.draw()
        assert not any(word in ' '.join(captions).lower() for word in ('ingatan', 'alzheimer'))
        game.state = 'playing'
        game.draw()
        assert any('0/6' in label and 'K FRAGMEN' in label for label in labels)
    finally:
        game.audio.close()


def test_failed_continue_does_not_replace_existing_checkpoint_on_quit(tmp_path, monkeypatch):
    from nur_game import config
    from nur_game.game import main

    path = tmp_path/'existing-checkpoint.json'
    path.write_text('unreadable checkpoint', encoding='utf-8')
    monkeypatch.setattr(config, 'SAVE_PATH', path)
    monkeypatch.setattr(pygame.event, 'get', lambda: [pygame.event.Event(pygame.QUIT)])
    assert main(['--continue', '--headless', '--frames', '1', '--mute']) == 0
    assert path.read_text(encoding='utf-8') == 'unreadable checkpoint'
