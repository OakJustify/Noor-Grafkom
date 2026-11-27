"""Layered ambience stems that loop seamlessly and mix by sanity intensity.

Each stage has four stems. Every stem is rendered as a periodic signal (whole
number of cycles per loop, or spectrally synthesised noise), so looping it in
pygame needs no crossfade and never clicks. The stems are played together at
constant volume; only their gains move, which is what makes the bed follow the
intensity smoothly.
"""

from functools import lru_cache

import numpy as np

import noor.config as C

LAYERS = ("drone", "pulse", "breath", "shimmer")
LOOP_SECONDS = 16.0

# Per-layer bake level (peak) and intensity mix curve:
#   (onset, full, weight) -> layer fades in from `onset` to `full`, then holds
#   `weight` of the ambience budget. Sum of weights <= 1 by construction.
STEM_PEAK = {"drone": 0.62, "pulse": 0.70, "breath": 0.30, "shimmer": 0.30}
MIX = {
    "drone": (0.00, 0.00, 0.42),
    "breath": (0.10, 0.55, 0.21),
    "pulse": (0.16, 0.60, 0.27),
    "shimmer": (0.45, 0.90, 0.12),
}
# the drone steps back a little as the other layers arrive, so they stay audible
TAPER = {"drone": 0.12}


# --- primitives -------------------------------------------------------------


def loop_samples():
    return round(C.SAMPLE_RATE * LOOP_SECONDS)


def _q(freq, dur=LOOP_SECONDS):
    """Snap a frequency so the loop holds a whole number of cycles."""
    cycles = max(1, round(float(freq) * dur))
    return cycles / dur


def _wave(freq, n, kind="sine", phase=0.0):
    t = np.arange(n) / C.SAMPLE_RATE
    ph = 2.0 * np.pi * freq * t + phase
    if kind == "triangle":
        return (2.0 / np.pi) * np.arcsin(np.sin(ph))
    if kind == "saw":
        # harmonic (band-limited) saw so it stays loopable and not aliased
        x = np.zeros(n)
        for h in range(1, 9):
            if freq * h >= C.SAMPLE_RATE / 2:
                break
            x += np.sin(h * ph) / h
        return x * (2.0 / np.pi)
    return np.sin(ph)


def _lfo(cycles, n, depth=0.5, offset=1.0, phase=0.0):
    t = np.arange(n) / n
    return offset + depth * np.sin(2.0 * np.pi * cycles * t + phase)


def _loop_noise(n, alpha=1.2, seed=0, lo=40.0, hi=4000.0):
    """Band-limited noise built in the frequency domain: exactly periodic."""
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1.0 / C.SAMPLE_RATE)
    mag = np.zeros_like(freqs)
    band = (freqs >= lo) & (freqs <= hi)
    mag[band] = 1.0 / np.maximum(freqs[band], 1.0) ** alpha
    spec = spec / np.maximum(np.abs(spec), 1e-12) * mag
    spec[0] = 0.0
    x = np.fft.irfft(spec, n)
    peak = np.max(np.abs(x))
    return x / peak if peak > 0 else x


def _to_stereo(x, pan=0.0):
    """Constant-power pan; x is mono."""
    p = max(-1.0, min(1.0, float(pan)))
    angle = (p + 1.0) * np.pi / 4.0
    return np.column_stack([x * np.cos(angle), x * np.sin(angle)]).astype(np.float32)


def _finalize(x, peak):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = np.column_stack([x, x])
    mx = float(np.max(np.abs(x))) if x.size else 0.0
    if mx > 0:
        x = x / mx * peak
    return np.ascontiguousarray(x, dtype=np.float32)


def stage_root(stage):
    """Root sinks one semitone per stage: 55.0 -> 46.25 Hz.

    Shared with the stage music beds so pads and ambience stay in tune.
    """
    return C.MUSIC_ROOT * 2.0 ** (-(max(1, int(stage)) - 1) / 12.0)


# --- layers -----------------------------------------------------------------


def _drone(stage, n):
    root = stage_root(stage)
    swell = _lfo(1, n, depth=0.22, phase=0.0)
    body = _wave(_q(root), n, "sine") * 1.0
    body += 0.35 * _wave(_q(root * 1.5), n, "triangle")
    body += 0.18 * _wave(_q(root * 2.0), n, "sine", phase=0.7)
    if stage >= 3:
        # semitone rub: unease without becoming a melody
        body += (0.10 if stage == 3 else 0.18) * _wave(_q(root * 2.0 * 2 ** (1 / 12)), n, "sine")
    body *= swell
    # two detuned voices hard-ish panned = slow beating across the field
    left = body + 0.30 * _wave(_q(root * 1.004), n, "sine") * swell
    right = body + 0.30 * _wave(_q(root * 0.996), n, "sine") * swell
    return np.column_stack([left, right])


def _pulse(stage, n):
    """Heartbeat layer; tempo follows HEARTBEAT_BPM, density follows stage."""
    idx = min(max(1, int(stage)) - 1, len(C.HEARTBEAT_BPM) - 1)
    beats = max(1, round(C.HEARTBEAT_BPM[idx] * LOOP_SECONDS / 60.0))
    period = LOOP_SECONDS / beats
    beat_n = round(period * C.SAMPLE_RATE)
    root = stage_root(stage) * 0.9

    hit_n = min(beat_n, int(0.45 * C.SAMPLE_RATE))
    t = np.arange(hit_n) / C.SAMPLE_RATE
    hit = np.sin(2.0 * np.pi * root * t) * np.exp(-t * 9.0)
    hit += 0.45 * np.sin(2.0 * np.pi * root * 2.0 * t) * np.exp(-t * 22.0)
    # short click so the beat cuts through the pad on small speakers
    rng = np.random.default_rng(90 + stage)
    click = np.convolve(rng.standard_normal(hit_n), np.ones(8) / 8.0, mode="same")
    hit += 0.25 * click * np.exp(-t * 55.0)
    # softer second beat (lub-dub)
    off = int(0.22 * period * C.SAMPLE_RATE)
    if 0 < off < hit_n:
        dub = np.zeros(hit_n)
        seg = hit_n - off
        dub[off:] = 0.55 * hit[:seg] * np.exp(-np.arange(seg) / C.SAMPLE_RATE * 3.0)
        hit = hit + dub

    out = np.zeros(n)
    for b in range(beats):
        i = b * beat_n
        seg = min(hit_n, n - i)
        out[i:i + seg] += hit[:seg]
    return _to_stereo(out, pan=0.0)


def _breath(stage, n):
    """Air/exhale texture: swells a few times per loop, wider on later stages."""
    alpha = 1.05 + 0.12 * (stage - 1)
    body = _loop_noise(n, alpha=alpha, seed=7 * stage + 1, lo=70.0, hi=1400.0)
    swells = _lfo(2 if stage < 3 else 3, n, depth=0.45, offset=0.55)
    body = body * swells
    if stage >= 3:
        air = _loop_noise(n, alpha=0.6, seed=7 * stage + 5, lo=2000.0, hi=7000.0)
        body = body + (0.25 if stage == 3 else 0.4) * air * _lfo(5, n, depth=0.5, offset=0.5)
    return _to_stereo(body, pan=-0.15) * 0.5 + _to_stereo(np.roll(body, 97), pan=0.15) * 0.5


def _shimmer(stage, n):
    """High, dissonant partials; barely there on stage 1, a rub on stage 4."""
    root = stage_root(stage)
    trem = np.clip(_lfo(5, n, depth=0.9, offset=0.1), 0.0, None)
    x = _wave(_q(root * 12.0), n, "sine") * trem
    x += 0.55 * _wave(_q(root * 18.0), n, "sine") * np.clip(_lfo(3, n, 0.9, 0.1, 1.7), 0.0, None)
    if stage >= 3:
        rub = _wave(_q(root * 12.0 * 2 ** (1 / 12)), n, "sine")
        x += (0.55 if stage == 3 else 0.9) * rub * np.clip(_lfo(2, n, 0.9, 0.1, 0.8), 0.0, None)
    if stage >= 4:
        x += 0.6 * _wave(_q(root * 12.0 * 2 ** (6 / 12)), n, "sine") * np.clip(_lfo(4, n, 0.9), 0.0, None)
    gate = _lfo(2, n, depth=0.45, offset=0.55)
    return _to_stereo(x * gate, pan=0.1)


# --- public API -------------------------------------------------------------


@lru_cache(maxsize=2)
def stems_for_stage(stage):
    """Render every stem for a stage. Keys match LAYERS.

    Rendering one stage takes ~0.8 s, so the cache keeps the previous stage
    around for quick back-and-forth. Treat the returned arrays as read-only.
    """
    stage = max(1, int(stage))
    n = loop_samples()
    return {
        "drone": _finalize(_drone(stage, n), STEM_PEAK["drone"]),
        "pulse": _finalize(_pulse(stage, n), STEM_PEAK["pulse"]),
        "breath": _finalize(_breath(stage, n), STEM_PEAK["breath"]),
        "shimmer": _finalize(_shimmer(stage, n), STEM_PEAK["shimmer"]),
    }


def mix_weights(intensity):
    """Layer gain targets for an intensity in [0, 1]; total never exceeds 1."""
    I = max(0.0, min(1.0, float(intensity)))
    weights = {}
    for name in LAYERS:
        onset, full, weight = MIX[name]
        if full > onset:
            k = (I - onset) / (full - onset)
        else:
            k = 1.0 if I >= onset else 0.0
        k = max(0.0, min(1.0, k))
        k = k * k * (3.0 - 2.0 * k)  # smoothstep: no audible step at onset
        weights[name] = weight * k * (1.0 - TAPER.get(name, 0.0) * I)
    return weights
