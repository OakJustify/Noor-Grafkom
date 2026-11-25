"""F3 adaptation: sanity resource, H toggle, visuals, phantoms and save."""

import json

import pygame
import pytest

from nur_game import config
from nur_game.engine import DT
from nur_game.light import LivingLantern
from nur_game.physics import NurInput
from nur_game.sanity import (HallucinationAudio, HallucinationVisuals,
                             PhantomDirector, SanityManager)


def test_q_equivalent_toggle_has_cooldown_and_early_exit():
    sanity = SanityManager()
    assert sanity.trigger_hallucination()
    assert sanity.hallucinating and sanity.hallucination_count == 1
    assert not sanity.trigger_hallucination()  # cooldown
    sanity.cooldown = 0
    assert sanity.trigger_hallucination()      # early exit is allowed
    assert not sanity.hallucinating
    assert sanity.hallucination_count == 1


def test_each_entry_permanently_raises_multiplier_up_to_cap():
    sanity = SanityManager()
    for expected in (1.7, 1.9, 2.1):
        sanity.cooldown = 0
        assert sanity.trigger_hallucination()
        sanity.cooldown = 0
        assert sanity.trigger_hallucination()  # exit
        assert sanity.lantern_multiplier == pytest.approx(expected)
    for _ in range(10):
        sanity.cooldown = 0
        sanity.trigger_hallucination()
        sanity.cooldown = 0
        sanity.trigger_hallucination()
    assert sanity.lantern_multiplier == 3.0

    lantern = LivingLantern()
    lantern.drain_multiplier = 3.0
    before = lantern.charge
    lantern.step(1.0)
    assert before - lantern.charge == pytest.approx(.00065 * 3, rel=1e-4)


def test_hallucination_drains_faster_and_zero_sanity_dies():
    calm = SanityManager(current_sanity=10)
    assert not calm.update(1.0)
    assert 9.9 < calm.current_sanity < 9.96

    stressed = SanityManager(current_sanity=1)
    stressed.trigger_hallucination()
    assert stressed.update(1.0)
    assert stressed.current_sanity == 0
    assert stressed.dead

    restore = SanityManager(current_sanity=90)
    restore.restore_sanity(50)
    assert restore.current_sanity == 100


def test_breakpoint_callbacks_fire_in_order():
    sanity = SanityManager(current_sanity=80)
    seen = []
    sanity.subscribe(breakpoint=seen.append)
    sanity.current_sanity = 74
    sanity.update(.01)
    sanity.current_sanity = 49
    sanity.update(.01)
    sanity.current_sanity = 24
    sanity.update(.01)
    sanity.current_sanity = .01
    sanity.update(.2)
    assert seen == [0, 1, 2, 3]


def test_hallucination_visuals_only_change_the_frame_when_sanity_is_low():
    visuals = HallucinationVisuals()
    screen = pygame.Surface((320, 180))
    screen.fill((90, 110, 120))
    before = pygame.image.tobytes(screen, 'RGB')
    visuals.apply(screen, 100, 100, 1.0)
    assert pygame.image.tobytes(screen, 'RGB') == before
    visuals.apply(screen, 10, 100, 1.0)
    assert pygame.image.tobytes(screen, 'RGB') != before


def test_phantoms_are_render_only_and_fade():
    director = PhantomDirector(seed=3)
    director.update(.01, 20, 100, (500, 430))
    assert 1 <= len(director.phantoms) <= 4
    assert director.snapshot()['collision'] is False
    screen = pygame.Surface((960, 540))
    director.draw(screen, 0)
    for _ in range(30):
        director.update(.1, 20, 100, (500, 430))
    assert len(director.phantoms) <= 4


def test_hallucination_audio_sets_soundscape_intensity():
    class FakeSoundscape:
        hallucination_intensity = 0.0

    sound = FakeSoundscape()
    HallucinationAudio().apply(sound, .7)
    assert sound.hallucination_intensity == pytest.approx(.7)


def test_game_h_key_toggles_and_station_restores_sanity(game):
    game.sanity.current_sanity = 50
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h))
    assert game.sanity.hallucinating
    before_lantern = game.lantern.charge
    for _ in range(30):
        game.update(DT, NurInput())
    assert game.sanity.current_sanity < 50
    assert game.lantern.charge < before_lantern
    assert game.lantern.drain_multiplier > 1.0

    game.sanity.current_sanity = 60
    game.world.player.position = (155, 438)
    game.update(DT, NurInput(action=True))
    assert game.sanity.current_sanity > 79


def test_sanity_is_saved_and_loaded(game, tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SAVE_PATH', tmp_path / 'nur-v4.json')
    game.sanity.current_sanity = 42.5
    game.sanity.hallucination_count = 2
    game.persist = True
    game._save()
    data = json.loads(config.SAVE_PATH.read_text())
    assert data['sanity']['current'] == pytest.approx(42.5)
    assert game.load_save()
    assert game.sanity.current_sanity == pytest.approx(42.5)
    assert game.sanity.hallucination_count == 2
    assert game.lantern.drain_multiplier == pytest.approx(1.9)
