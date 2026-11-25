import wave

import numpy as np
import pygame
import pytest

from nur_game.audio import Audio
from nur_game.music import RATE, SECONDS, TRACKS, ensure_music, render_track


@pytest.mark.parametrize("scene", TRACKS)
def test_score_is_original_deterministic_stereo_and_click_free(scene):
    samples = render_track(scene, seconds=3)
    assert samples.shape == (3 * RATE, 2) and samples.dtype == np.dtype("<i2")
    assert np.array_equal(samples, render_track(scene, seconds=3))
    assert np.all(samples[0] == 0) and np.all(samples[-1] == 0)
    assert np.max(np.abs(samples.astype(np.int32))) < 32767
    assert np.std(samples) > 100
    assert not np.array_equal(samples[:, 0], samples[:, 1])


def test_three_music_scenes_have_different_compositions():
    tracks = [render_track(scene, seconds=3).tobytes() for scene in TRACKS]
    assert len(set(tracks)) == 3


def test_exported_music_has_expected_format_and_does_not_overwrite_existing_files(tmp_path):
    paths = ensure_music(tmp_path)
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    assert len(paths) == 3
    for path in paths:
        with wave.open(str(path), "rb") as handle:
            assert handle.getnchannels() == 2 and handle.getsampwidth() == 2
            assert handle.getframerate() == RATE and handle.getnframes() == SECONDS * RATE
    ensure_music(tmp_path)
    assert before == [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]


def test_music_crossfades_with_reality_and_muting_silences_all_channels():
    if not pygame.get_init():
        pygame.init()
    audio = Audio(enabled=True)
    try:
        assert audio.available
        assert set(audio.music) == set(TRACKS)
        for _ in range(60):
            audio.update(0.1, 0, 1, phase=0)
        assert audio.music_scene == "home"
        assert audio.music_channels["home"].get_volume() > 0.25
        assert audio.music_channels["gaung"].get_volume() == 0
        for _ in range(60):
            audio.update(0.1, 0, 1, phase=1)
        assert audio.music_scene == "gaung"
        assert audio.music_channels["gaung"].get_volume() > 0.25
        assert audio.music_channels["home"].get_volume() == 0
        audio.set_muted(True)
        assert all(channel.get_volume() == 0 for channel in audio.music_channels.values())
        assert all(channel.get_volume() == 0 for channel in audio.channels.values())
        audio.update(0.1, 0, 1, ending=True)
        assert all(channel.get_volume() == 0 for channel in audio.music_channels.values())
        audio.set_muted(False)
        for _ in range(60):
            audio.update(0.1, 0, 1, ending=True)
        assert audio.music_scene == "return"
        assert audio.music_channels["return"].get_volume() > 0.25
    finally:
        audio.close()


def test_game_m_key_mutes_and_unmutes_music(game):
    assert not game.audio.enabled  # fixture starts muted
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    assert game.audio.enabled
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    assert not game.audio.enabled


def test_reserved_loops_are_not_stolen_by_effects_and_m_stops_active_foley():
    audio = Audio(enabled=True)
    try:
        audio.update(0.1, 0, 1)
        assert all(channel.get_busy() for channel in audio.music_channels.values())
        assert all(channel.get_sound() == audio.music[scene] for scene, channel in audio.music_channels.items())
        for _ in range(20):
            for name in ("breath", "door", "memory", "tick", "glitch"):
                audio.cooldowns[name] = 0
                audio.play(name)
        assert all(channel.get_sound() == audio.music[scene] for scene, channel in audio.music_channels.items())
        assert any(sound.get_num_channels() > 0 for sound in audio.sounds.values())
        audio.set_muted(True)
        assert all(sound.get_num_channels() == 0 for sound in audio.sounds.values())
        assert all(channel.get_volume() == 0 for channel in audio.music_channels.values())
    finally:
        audio.close()


def test_music_loop_requests_repeat_indefinitely_and_ending_stops_boss_pulse():
    audio = Audio(enabled=True)
    calls = []

    class RecordingChannel:
        def __init__(self, channel):
            self.channel = channel

        def __getattr__(self, name):
            return getattr(self.channel, name)

        def play(self, sound, loops=0):
            calls.append(loops)
            self.channel.play(sound, loops=loops)

    try:
        audio.music_channels = {scene: RecordingChannel(channel) for scene, channel in audio.music_channels.items()}
        audio.update(0.1, 0, 1, boss=True)
        assert calls == [-1, -1, -1]
        assert audio.music_scene == "gaung"
        assert audio.channels["boss_pulse"].get_busy()
        for _ in range(60):
            audio.update(0.1, 0, 1, boss=True, ending=True)
        assert audio.music_scene == "return"
        assert not audio.channels["boss_pulse"].get_busy()
        assert all(channel.get_volume() == 0 for channel in audio.channels.values())
    finally:
        audio.close()
