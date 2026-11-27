"""Audio recipes: SFX, menu music loops and per-stage music beds."""

import numpy as np

import noor.config as C
from noor.audio import ambience, synth


def _norm(x):
    return synth.normalize(x, peak_dbfs=C.PEAK_DBFS)


WARM_PARTIALS = ((1.0, 1.0), (2.0, 0.16), (3.0, 0.05))


def _note(freq, dur, decay, attack=0.008, release=0.02, partials=WARM_PARTIALS):
    """Soft bell-ish note: sine partials, slow attack, exponential tail.

    A bare sine cut at full level reads as a beep or a click; ramping the attack
    and letting the tail decay keeps each hit warm instead of harsh.
    """
    n = int(C.SAMPLE_RATE * dur)
    t = np.arange(n) / C.SAMPLE_RATE
    x = np.zeros(n)
    for mult, gain in partials:
        x += gain * np.sin(2.0 * np.pi * freq * mult * t)
    y = x * np.exp(-t / max(1e-3, float(decay)))
    atk = max(1, min(n, int(attack * C.SAMPLE_RATE)))
    y[:atk] *= np.linspace(0.0, 1.0, atk)
    rel = max(1, min(n, int(release * C.SAMPLE_RATE)))
    y[-rel:] *= np.linspace(1.0, 0.0, rel)
    return np.column_stack([y, y])


def _hit(dur, freq, noise_amp=0.35, seed=3, decay=0.09, attack=0.004, cutoff=900.0):
    """Soft impact: low thump plus low-passed noise, no full-scale edge."""
    n = int(C.SAMPLE_RATE * dur)
    t = np.arange(n) / C.SAMPLE_RATE
    body = np.sin(2.0 * np.pi * freq * t) * np.exp(-t / max(1e-3, float(decay)))
    air = synth.noise("brown", dur, amp=1.0, seed=seed)[:, 0].astype(np.float64)
    air = synth.lowpass(air, cutoff) * np.exp(-t / max(1e-3, decay * 0.7)) * noise_amp
    x = body + air
    atk = max(1, min(n, int(attack * C.SAMPLE_RATE)))
    x[:atk] *= np.linspace(0.0, 1.0, atk)
    rel = max(1, min(n, int(0.015 * C.SAMPLE_RATE)))
    x[-rel:] *= np.linspace(1.0, 0.0, rel)
    return np.column_stack([x, x])


def sfx(name):
    if name in ("step", "A01"):
        return _norm(_hit(0.12, 85, noise_amp=0.45, seed=1, decay=0.05, cutoff=1200.0))
    if name in ("jump", "A02"):
        return _norm(_note(200.0, 0.15, 0.05))
    if name in ("land", "A03"):
        return _norm(_hit(0.2, 70, noise_amp=0.35, seed=2, decay=0.1, cutoff=600.0))
    if name in ("interact", "A04"):
        return _norm(_note(523.25, 0.14, 0.045))
    if name in ("fragment", "A05"):
        return _norm(synth.mix(_note(440.0, 1.6, 0.7),
                               0.6 * _note(659.25, 1.6, 0.7),
                               0.6 * _note(523.25, 1.6, 0.7)))
    if name in ("forget", "A06"):
        return _norm(_note(329.63, 1.4, 0.5, partials=((1.0, 1.0), (2.0, 0.25))))
    if name in ("flare", "A07"):
        return _norm(_note(783.99, 1.0, 0.4))
    if name in ("flare_fail", "A08"):
        return _norm(_note(196.0, 0.6, 0.3))
    if name in ("sting", "A10"):
        return _norm(_hit(0.7, 95, noise_amp=0.15, seed=4, decay=0.25, cutoff=400.0))
    if name in ("heartbeat", "A13"):
        return _norm(synth.mix(_hit(0.3, 60, noise_amp=0.05, decay=0.12, cutoff=200.0),
                               0.8 * _hit(0.3, 45, noise_amp=0.05, seed=5, decay=0.12, cutoff=200.0)))
    if name in ("checkpoint", "A19"):
        return _norm(synth.mix(_note(659.25, 1.0, 0.4), 0.7 * _note(440.0, 1.0, 0.4)))
    if name in ("death", "A17"):
        return _norm(_note(55.0, 2.5, 1.2, attack=0.03, partials=((1.0, 1.0), (2.0, 0.15))))
    if name in ("blankout", "A18"):
        return _norm(_note(392.0, 1.0, 0.5))
    # default click
    return _norm(_note(440.0, 0.1, 0.03))


# --- menu / ending pad ------------------------------------------------------
# A low A-minor pad: root octave, minor third and minor sixth, plus a quiet
# detuned sixth for width. Only sines and no bright partials, so it stays calm
# and sits dark rather than buzzing; the slow two-cycle swell keeps it breathing.
# Every frequency is snapped to whole cycles per loop, so the seam needs no
# crossfade and cannot click.
MENU_CHORD = (2.0, 2.4, 3.2, 4.0)  # ratios of C.MUSIC_ROOT: A2, C3, F3, A3
MENU_DETUNE = 0.375  # Hz on one side only: slow, gentle width


def _breath(t, cycles, depth, phase=0.0):
    """Amplitude LFO that ends each loop exactly where it started."""
    return 1.0 + depth * np.sin(2.0 * np.pi * cycles * t / ambience.LOOP_SECONDS + phase)


def music_loop(name):
    """Dark, calm menu pad (also used for the ending theme)."""
    t, _n = _loop_time()
    root = C.MUSIC_ROOT
    sub = 0.85 * _partial(root, t) + 0.25 * _partial(root * 2.0, t)
    body = (0.40 * _partial(root * MENU_CHORD[0], t)
            + 0.26 * _partial(root * MENU_CHORD[1], t)
            + 0.14 * _partial(root * MENU_CHORD[3], t))
    shade = 0.30 * _partial(root * MENU_CHORD[2], t)  # the minor sixth: the dark edge
    shade_wide = 0.30 * _partial(root * MENU_CHORD[2] + MENU_DETUNE, t)
    swell = _breath(t, 1, 0.15) * _breath(t, 2, 0.06, -np.pi / 3.0)
    pad = body * swell
    left = sub + pad + shade * swell
    right = sub + pad + shade_wide * swell
    return _norm(np.column_stack([left, right]))


# --- stage music beds -------------------------------------------------------
# One bed per stage. It uses the same loop length and the same root note as the
# stage's ambience stems, so pad + ambience lock together instead of drifting
# against each other. Every partial holds a whole number of cycles per loop,
# which makes the loop click-free without a crossfade.

STAGE_CHORDS = {
    1: (1.0, 1.5, 2.0),                    # open fifth: unresolved, calm
    2: (1.0, 1.2, 1.5, 2.0),               # minor triad
    3: (1.0, 1.2, 1.5, 2.0 * 2 ** (1 / 12)),  # minor + semitone rub on top
    4: (1.0, 2 ** (1 / 12), 1.2, 1.5),     # cluster instead of a chord
}
# Melodic cells in semitones above root*8; stage 4 keeps a single low toll.
STAGE_MOTIF = {1: (0, 7, 12, 7), 2: (0, 3, 5, 7, 3), 3: (12, 7, 3, 0, 3), 4: (0,)}
MOTIF_TIMES = (2.4, 5.0, 7.8, 10.6, 13.2)


def _loop_time():
    t = np.arange(ambience.loop_samples()) / C.SAMPLE_RATE
    return t, len(t)


def _partial(freq, t, kind="sine", harmonics=5):
    """Loopable partial: the frequency is snapped to whole cycles per loop."""
    cycles = max(1, round(float(freq) * ambience.LOOP_SECONDS))
    ph = 2.0 * np.pi * (cycles / ambience.LOOP_SECONDS) * t
    if kind == "saw":
        return sum(np.sin(k * ph) / k for k in range(1, harmonics + 1))
    if kind == "tri":
        return sum(((-1) ** k) * np.sin((2 * k + 1) * ph) / (2 * k + 1) ** 2
                   for k in range(harmonics))
    return np.sin(ph)


def _bed_pad(stage, t):
    """Slow chord pad, swelling once per loop, with two detuned outer voices."""
    root = ambience.stage_root(stage)
    swell = 1.0 + 0.25 * np.sin(2.0 * np.pi * t / ambience.LOOP_SECONDS - np.pi / 2)
    body = 0.9 * _partial(root, t, "saw", 4)
    for i, ratio in enumerate(STAGE_CHORDS[stage]):
        body = body + (0.45 - 0.08 * i) * _partial(root * 2.0 * ratio, t)
    body = body * swell
    left = body + 0.22 * _partial(root * 1.004, t)
    right = body + 0.22 * _partial(root * 0.996, t)
    return np.column_stack([left, right])


def _bed_motif(stage, n):
    """Sparse decaying bells; silent at both loop edges so the seam stays clean."""
    root = ambience.stage_root(stage)
    out = np.zeros((n, 2), dtype=np.float64)
    for i, semis in enumerate(STAGE_MOTIF[stage]):
        start = MOTIF_TIMES[i % len(MOTIF_TIMES)]
        if semis == 0 and stage == 4:
            start = 1.0
        start_n = int(start * C.SAMPLE_RATE)
        m = min(int(2.2 * C.SAMPLE_RATE), n - start_n)
        if m <= 0:
            continue
        tt = np.arange(m) / C.SAMPLE_RATE
        env = np.exp(-tt * 1.8) * np.minimum(1.0, tt / 0.02)
        f = root * 8.0 * 2.0 ** (semis / 12.0) * (0.5 if (semis == 0 and stage == 4) else 1.0)
        tone = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt) * np.exp(-tt * 3.0)
        hit = tone * env * 0.45
        pan_l, pan_r = (0.85, 0.45) if i % 2 == 0 else (0.45, 0.85)
        out[start_n:start_n + m, 0] += hit * pan_l
        out[start_n:start_n + m, 1] += hit * pan_r
    return out


def stage_music_loop(stage):
    """Render a stage's music bed (same length and root as its ambience)."""
    stage = min(4, max(1, int(stage)))
    t, n = _loop_time()
    x = _bed_pad(stage, t) * 0.55 + _bed_motif(stage, n)
    return _norm(x)


# --- title theme -----------------------------------------------------------
# A real 12-bar piece instead of a static pad: low root-held pad, one bass note
# per bar, and a sparse bell melody. Harmony walks i - VI - III (Am - F - C) and
# falls back to the minor tonic on the loop point, so the music keeps a dark
# pull but lifts in the middle instead of droning on one chord.
# Everything is placed on a whole-bar grid and wrapped at the loop end, which
# makes the file exactly periodic: the seam is just the next sample.
TITLE_BPM = 72.0
TITLE_BEAT = 60.0 / TITLE_BPM
TITLE_BEATS_PER_BAR = 4
TITLE_BARS = 12
TITLE_CHORDS = {  # bar -> midi notes, root first (low passed to the bass)
    0: (45, 57, 60, 64),        # Am: A2 A3 C4 E4
    4: (41, 53, 57, 60),        # F:  F2 F3 A3 C4
    8: (36, 48, 55, 60, 64),    # C:  C2 C3 G3 C4 E4
}
# Low counter-line: slow, stepwise, and deliberately kept in A2-E3 (110-165 Hz),
# the register the pad and bass leave open. Higher than this and it doubles the
# pad chord tones instead of singing against them.
TITLE_COUNTER = (
    (1, 0.0, 2.0, 45), (1, 2.0, 2.0, 48),
    (2, 0.0, 2.0, 47), (2, 2.0, 2.0, 45),
    (3, 0.0, 2.0, 48), (3, 2.0, 2.0, 52),
    (4, 0.0, 2.0, 50), (4, 2.0, 2.0, 47),
    (5, 0.0, 2.0, 53), (5, 2.0, 2.0, 48),
    (6, 0.0, 2.0, 45), (6, 2.0, 2.0, 48),
    (7, 0.0, 2.0, 53), (7, 2.0, 2.0, 50),
    (8, 0.0, 4.0, 52),
    (9, 0.0, 2.0, 52), (9, 2.0, 2.0, 50),
    (10, 0.0, 2.0, 48), (10, 2.0, 2.0, 50),
    (11, 0.0, 2.0, 52), (11, 2.0, 2.0, 53),
    (12, 0.0, 2.0, 50), (12, 2.0, 2.0, 52),  # suspension that resolves into Am
)
# (bar, beat, length in beats, midi note); bar 12 is the last bar of the loop.
TITLE_MELODY = (
    (1, 0.0, 2.0, 64), (1, 2.0, 2.0, 69),
    (2, 0.0, 2.5, 72), (2, 2.5, 1.5, 71),
    (3, 0.0, 1.5, 69), (3, 1.5, 1.5, 67), (3, 3.0, 1.0, 64),
    (4, 0.0, 4.0, 64),
    (5, 0.0, 2.0, 77), (5, 2.0, 1.0, 74), (5, 3.0, 1.0, 72),
    (6, 0.0, 2.5, 72), (6, 2.5, 1.5, 69),
    (7, 0.0, 1.5, 69), (7, 1.5, 1.0, 67), (7, 2.5, 1.5, 65),
    (8, 0.0, 4.0, 64),
    (9, 0.0, 2.0, 72), (9, 2.0, 2.0, 76),
    (10, 0.0, 2.0, 74), (10, 2.0, 1.0, 72), (10, 3.0, 1.0, 71),
    (11, 0.0, 1.5, 69), (11, 1.5, 1.5, 72), (11, 3.0, 1.0, 76),
    (12, 0.0, 2.0, 74), (12, 2.0, 1.0, 71), (12, 3.0, 1.0, 69),
)


def _hz(midi):
    return 440.0 * 2.0 ** ((float(midi) - 69.0) / 12.0)


def _ramped(n, attack, release):
    """Linear attack/release ramp, so no event starts or stops on an edge."""
    env = np.ones(n)
    a = min(n, max(1, int(attack * C.SAMPLE_RATE)))
    env[:a] = np.linspace(0.0, 1.0, a)
    r = min(n, max(1, int(release * C.SAMPLE_RATE)))
    env[-r:] *= np.linspace(1.0, 0.0, r)
    return env


def _place(buf, sig, start, gain, pan):
    """Add a mono event into a stereo buffer, wrapping past the loop end."""
    n = len(buf)
    i = round(start * C.SAMPLE_RATE) % n
    m = len(sig)
    if i + m <= n:
        buf[i:i + m, 0] += sig * gain * pan[0]
        buf[i:i + m, 1] += sig * gain * pan[1]
        return
    head = n - i
    buf[i:, 0] += sig[:head] * gain * pan[0]
    buf[i:, 1] += sig[:head] * gain * pan[1]
    buf[:m - head, 0] += sig[head:] * gain * pan[0]
    buf[:m - head, 1] += sig[head:] * gain * pan[1]


def _pad_voice(midi, dur, detune=0.0, bright=0.0):
    n = int(dur * C.SAMPLE_RATE)
    t = np.arange(n) / C.SAMPLE_RATE
    freq = _hz(midi)
    ph = 2.0 * np.pi * freq * t
    sig = np.sin(ph)
    if bright:
        sig += bright * np.sin(2.0 * ph)
    if detune:
        sig += 0.5 * np.sin(2.0 * np.pi * (freq + detune) * t)
    return sig * _ramped(n, 1.0, 1.0)


def _bell_voice(midi, dur):
    """Struck bell: fast attack, two decaying partials, tail fades to silence."""
    n = int(dur * C.SAMPLE_RATE)
    t = np.arange(n) / C.SAMPLE_RATE
    freq = _hz(midi)
    tone = (np.sin(2.0 * np.pi * freq * t)
            + 0.24 * np.sin(2.0 * np.pi * freq * 2.002 * t) * np.exp(-t * 1.1)
            + 0.08 * np.sin(2.0 * np.pi * freq * 3.01 * t) * np.exp(-t * 2.4))
    return tone * np.exp(-t * 0.75) * _ramped(n, 0.012, 0.12)


def _counter_voice(midi, dur):
    """Low sustaining line: a little saw edge and gentle vibrato, never harsh."""
    n = int(dur * C.SAMPLE_RATE)
    t = np.arange(n) / C.SAMPLE_RATE
    freq = _hz(midi)
    ph = 2.0 * np.pi * freq * t + 0.30 * np.sin(2.0 * np.pi * 4.2 * t)
    tone = (np.sin(ph) + 0.26 * np.sin(2.0 * ph) + 0.10 * np.sin(3.0 * ph))
    return tone * _ramped(n, 0.16, 0.30)


def title_theme():
    """Render the 40 s title/menu theme; returns a stereo, seamless loop."""
    bar = TITLE_BEATS_PER_BAR * TITLE_BEAT
    n = round(TITLE_BARS * bar * C.SAMPLE_RATE)
    out = np.zeros((n, 2), dtype=np.float64)

    # pad: one chord per four bars, swelling slowly across its section
    for start_bar, chord in TITLE_CHORDS.items():
        start = start_bar * bar
        dur = 4.0 * bar - 0.15  # a hair short, so sections breathe instead of stacking
        for i, midi in enumerate(chord[1:]):
            voice = _pad_voice(midi, dur, detune=(0.35 if i % 2 else -0.35),
                               bright=0.10 if i == len(chord) - 2 else 0.0)
            pan = (0.5 - 0.05 * i, 0.5 + 0.05 * i)
            _place(out, voice, start, 0.30 - 0.04 * i, pan)

    # bass: the chord root on every bar, plus a quiet sub octave for weight
    for start_bar, chord in TITLE_CHORDS.items():
        for b in range(4):
            midi = chord[0]
            dur = bar - 0.1
            start = (start_bar + b) * bar
            _place(out, _pad_voice(midi, dur, bright=0.18), start,
                   0.42 if b % 2 == 0 else 0.36, (0.5, 0.5))
            _place(out, _pad_voice(midi - 12, dur), start, 0.22, (0.5, 0.5))

    # counter-line: slightly left of centre, so it stays apart from the bells
    for bar_no, beat, length, midi in TITLE_COUNTER:
        start = ((bar_no - 1) * TITLE_BEATS_PER_BAR + beat) * TITLE_BEAT
        sig = _counter_voice(midi, length * TITLE_BEAT + 0.35)
        _place(out, sig, start, 0.30, (0.44, 0.56))

    # melody: alternating pan keeps it floating instead of pasted on top
    for i, (bar_no, beat, length, midi) in enumerate(TITLE_MELODY):
        start = ((bar_no - 1) * TITLE_BEATS_PER_BAR + beat) * TITLE_BEAT
        tail = min(3.2, 1.2 + length * TITLE_BEAT)
        sig = _bell_voice(midi, length * TITLE_BEAT + tail)
        pan = (-1.0, 1.0) if i % 2 else (1.0, -1.0)
        width = (0.5 - 0.16 * pan[0], 0.5 - 0.16 * pan[1])
        _place(out, sig, start, 0.46, width)

    # slow global breath, two cycles per loop so it ends where it starts
    t = np.arange(n) / C.SAMPLE_RATE
    breath = 1.0 + 0.07 * np.sin(2.0 * np.pi * 2.0 * t / (TITLE_BARS * bar) - np.pi / 2)
    out *= breath[:, None]

    # two wrapped echoes: a small room, and still exactly periodic
    d1 = int(0.30 * C.SAMPLE_RATE)
    d2 = int(0.62 * C.SAMPLE_RATE)
    out = out + 0.20 * np.roll(out, d1, axis=0) + 0.07 * np.roll(out, d2, axis=0)
    return _norm(out)


def generate_all_sfx():
    ids = ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10",
           "A11", "A12", "A13", "A14", "A15", "A16", "A17", "A18", "A19", "A20", "A21"]
    return {i: sfx(i) for i in ids}


def generate_music():
    beds = {"L0": title_theme(), "L1": music_loop("L1"), "L5": music_loop("L5")}
    for stage in (1, 2, 3, 4):
        beds[f"S{stage}"] = stage_music_loop(stage)
    return beds