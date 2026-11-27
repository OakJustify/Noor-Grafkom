import numpy as np

import noor.config as C
from noor.audio import recipes, synth


def test_no_nan():
    x = recipes.sfx("A01")
    assert not np.isnan(x).any()


def test_peak():
    x = recipes.sfx("A05")
    peak_db = 20 * np.log10(np.max(np.abs(x)) + 1e-9)
    assert peak_db <= C.PEAK_DBFS + 0.5


def test_loop_smooth():
    x = recipes.music_loop("L1")
    diff = np.abs(x[0] - x[-1])
    assert np.max(diff) < 0.5


def test_sfx_never_start_or_end_on_a_hard_edge():
    # a full-level first/last sample is heard as a click before the sound itself
    for sid in ("A01", "A02", "A03", "A04", "A05", "A06", "A10", "A17", "A18", "A19"):
        x = recipes.sfx(sid)
        assert np.max(np.abs(x[0])) < 0.01, sid
        assert np.max(np.abs(x[-1])) < 0.01, sid


def test_menu_loop_is_dark_calm_and_click_free():
    x = recipes.music_loop("L1")
    mono = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono))
    freqs = np.fft.rfftfreq(len(mono), 1.0 / C.SAMPLE_RATE)
    centroid = float((spec * freqs).sum() / spec.sum())
    assert centroid < 400  # low pad: no buzzy saw harmonics
    assert spec[freqs > 2000].sum() / spec.sum() < 0.01
    assert np.max(np.abs(x[0] - x[-1])) < 0.02  # loops without a click
    assert np.max(np.abs(x)) <= 10 ** (C.PEAK_DBFS / 20.0) + 1e-6
    assert np.corrcoef(x[:, 0], x[:, 1])[0, 1] < 0.99  # some width, not mono twice


def test_title_theme_is_a_seamless_40s_loop_that_goes_somewhere():
    x = recipes.title_theme()
    bar = recipes.TITLE_BEATS_PER_BAR * recipes.TITLE_BEAT
    assert x.shape == (round(recipes.TITLE_BARS * bar * C.SAMPLE_RATE), 2)
    assert abs(len(x) / C.SAMPLE_RATE - 40.0) < 0.01
    assert np.max(np.abs(x)) <= 10 ** (C.PEAK_DBFS / 20.0) + 1e-6

    mono = x.mean(axis=1)
    steps = np.abs(np.diff(mono))
    # the seam must be as ordinary as any other sample step, not a jump
    assert abs(mono[-1] - mono[0]) < 0.01
    assert abs(mono[-1] - mono[0]) < np.percentile(steps, 99)

    # it is a piece, not a drone: the sections differ and the level breathes
    sec = [mono[int(i * 40 / 3 * C.SAMPLE_RATE):int((i + 1) * 40 / 3 * C.SAMPLE_RATE)]
           for i in range(3)]
    for a, b in ((0, 1), (1, 2)):
        spectra = [np.abs(np.fft.rfft(s)) / np.abs(np.fft.rfft(s)).sum() for s in (sec[a], sec[b])]
        assert np.corrcoef(spectra[0], spectra[1])[0, 1] < 0.99
    levels = [np.sqrt(np.mean(mono[i:i + C.SAMPLE_RATE * 4] ** 2))
              for i in range(0, len(mono), C.SAMPLE_RATE * 4)]
    assert max(levels) / min(levels) > 1.1


def test_title_theme_has_a_moving_low_counter_line():
    x = recipes.title_theme().mean(axis=1)
    bar = recipes.TITLE_BEATS_PER_BAR * recipes.TITLE_BEAT

    def low_peak(bar_no):
        start = (bar_no - 1) * bar
        seg = x[int(start * C.SAMPLE_RATE):int((start + 0.6) * C.SAMPLE_RATE)]
        spec = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(len(seg), 1.0 / C.SAMPLE_RATE)
        band = (freqs > 120.0) & (freqs < 180.0)
        return float(freqs[band][np.argmax(spec[band])])

    # F3 (174.6) in bar 5 against E3 (164.8) in bar 8: a real line, not a drone
    assert low_peak(5) > low_peak(8) + 4.0
    assert 160.0 < low_peak(8) < 170.0


def test_stage_beds_match_the_ambience_loop():
    from noor.audio import ambience

    beds = {s: recipes.stage_music_loop(s) for s in (1, 2, 3, 4)}
    ceiling = 10 ** (C.PEAK_DBFS / 20.0)
    for x in beds.values():
        assert x.shape == (ambience.loop_samples(), 2)
        assert np.max(np.abs(x[0] - x[-1])) < 0.02
        assert np.max(np.abs(x)) <= ceiling + 1e-6
    assert np.max(np.abs(beds[1] - beds[4])) > 0.05


def test_synth_basic():
    x = synth.sine(440, 0.5)
    assert x.shape[1] == 2
    assert not np.isnan(x).any()