import wave

import numpy as np
import pytest

from nur_game import config
from nur_game.audio import ensure_generated
from nur_game.foley import RATE, render_foley
from nur_game.game import EVENT_SOUNDS


@pytest.mark.parametrize("event", ("jump", "land"))
def test_movement_foley_is_deterministic_nonclipping_and_not_tv_static(event):
    samples = render_foley(event)
    assert np.array_equal(samples, render_foley(event))
    assert samples[0] == samples[-1] == 0
    assert 0.08 < np.max(np.abs(samples)) < 0.8
    power = np.abs(np.fft.rfft(samples)) ** 2
    frequencies = np.fft.rfftfreq(len(samples), 1 / RATE)
    assert power[frequencies > 2000].sum() / power.sum() < 0.01
    assert power[(frequencies > 50) & (frequencies < 1400)].sum() / power.sum() > 0.9


def test_jump_is_a_rising_pitch_swoop_not_the_ambience_breath():
    samples = render_foley("jump")
    peaks = []
    for start in (0.025, 0.10, 0.17):
        section = samples[int(start * RATE):int((start + 0.035) * RATE)]
        spectrum = np.abs(np.fft.rfft(section * np.hanning(len(section))))
        peaks.append(np.fft.rfftfreq(len(section), 1 / RATE)[spectrum.argmax()])
    assert peaks[0] < peaks[1] < peaks[2]
    assert EVENT_SOUNDS["jump"] == "jump" and EVENT_SOUNDS["land"] == "land"


def test_generated_movement_files_exist_and_are_not_rewritten_during_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIO_DIR", tmp_path)
    ensure_generated()
    for event in ("jump", "land"):
        path = tmp_path / f"{event}.wav"
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with wave.open(str(path), "rb") as wav:
            assert wav.getframerate() == RATE and wav.getnchannels() == 1
        ensure_generated()
        assert before == (path.read_bytes(), path.stat().st_mtime_ns)
