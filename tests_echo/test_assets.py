import hashlib
import wave

import numpy as np
import pygame

from echo_game.art import ART_ROOT, PLAYER_CELL, PLAYER_FRAMES, ensure_art_assets
from echo_game.audio import AUDIO_ROOT, Audio, ensure_audio_assets


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_art_is_deterministically_regenerable(tmp_path):
    paths = ensure_art_assets(root=tmp_path / "art")
    assert len(paths) == 30
    assert all(digest(p) == digest(ART_ROOT / p.name) for p in paths)
    sheet = pygame.image.load(str(ART_ROOT / "courier_sheet.png"))
    assert sheet.get_size() == (PLAYER_CELL[0] * PLAYER_FRAMES, PLAYER_CELL[1])


def test_original_audio_is_deterministically_regenerable_and_not_clipped(tmp_path):
    paths = ensure_audio_assets(root=tmp_path / "audio")
    assert len(paths) == 15
    assert all(digest(p) == digest(AUDIO_ROOT / p.name) for p in paths)
    for path in paths:
        with wave.open(str(path)) as sound:
            assert sound.getnchannels() == 2
            assert sound.getsampwidth() == 2
            assert sound.getframerate() == 22050
            samples = np.frombuffer(sound.readframes(sound.getnframes()), dtype="<i2").astype(np.int32)
            assert 0 < np.abs(samples).max() < 32767
            if path.stem in ("ambience", "music"):
                assert sound.getnframes() / sound.getframerate() == 32


def test_initially_muted_audio_can_be_enabled():
    pygame.init()
    audio = Audio(enabled=False)
    try:
        assert audio.muted and not audio.enabled
        audio.set_muted(False)
        assert audio.enabled and not audio.muted and audio.available
        audio.play("jump")
        audio.update(100, True, 0.1)
        audio.set_muted(True)
    finally:
        audio.close()
        pygame.quit()
