"""Procedural audio synthesis primitives."""

import numpy as np

import noor.config as C


def _sr(sr=None):
    return sr or C.SAMPLE_RATE


def _tone(freq, dur, sr=None, amp=0.5, kind="sine"):
    sr = _sr(sr)
    n = int(sr * dur)
    t = np.arange(n) / sr
    if kind == "sine":
        x = np.sin(2 * np.pi * freq * t)
    elif kind == "saw":
        x = 2 * (t * freq - np.floor(0.5 + t * freq))
    elif kind == "square":
        x = np.sign(np.sin(2 * np.pi * freq * t))
    elif kind == "triangle":
        x = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
    else:
        x = np.sin(2 * np.pi * freq * t)
    x = x * amp
    return np.column_stack([x, x]).astype(np.float32)


def osc(kind, freq, dur, sr=None, amp=0.5):
    sr = _sr(sr)
    n = int(sr * dur)
    t = np.arange(n) / sr
    freq = np.atleast_1d(freq).astype(float)
    if kind == "sine":
        phase = 2 * np.pi * np.cumsum(np.full(n, freq[0])) / sr
        x = np.sin(phase)
    elif kind == "saw":
        x = 2 * (t * freq[0] - np.floor(0.5 + t * freq[0]))
    elif kind == "square":
        x = np.sign(np.sin(2 * np.pi * freq[0] * t))
    elif kind == "triangle":
        x = 2 * np.abs(2 * (t * freq[0] - np.floor(t * freq[0] + 0.5))) - 1
    else:
        x = np.sin(2 * np.pi * freq[0] * t)
    x = x * amp
    # simple env
    env = np.ones(n)
    atk = min(int(0.01 * sr), n)
    rel = min(int(0.05 * sr), n)
    env[:atk] = np.linspace(0, 1, atk)
    env[-rel:] = np.linspace(1, 0, rel)
    x = x * env
    return np.column_stack([x, x]).astype(np.float32)


def noise(kind="white", dur=1.0, sr=None, amp=0.3, seed=0):
    sr = _sr(sr)
    n = int(sr * dur)
    rng = np.random.default_rng(seed)
    if kind == "white":
        x = rng.standard_normal(n)
    elif kind == "pink":
        # Voss approximation
        x = rng.standard_normal(n)
        # simple lowpass
        b = np.ones(10) / 10
        x = np.convolve(x, b, mode="same")
    elif kind == "brown":
        x = np.cumsum(rng.standard_normal(n))
        x = x - np.mean(x)
    else:
        x = rng.standard_normal(n)
    # normalize
    mx = np.max(np.abs(x)) if np.max(np.abs(x)) > 0 else 1.0
    x = x / mx * amp
    return np.column_stack([x, x]).astype(np.float32)


def env(adsr, n, sr=None):
    sr = _sr(sr)
    a, d, s, r = adsr
    an = int(a * sr); dn = int(d * sr); rn = int(r * sr); sn = n - an - dn - rn
    sn = max(sn, 0)
    e = np.concatenate([
        np.linspace(0, 1, max(1, an)),
        np.linspace(1, s, max(1, dn)),
        np.full(max(1, sn), s),
        np.linspace(s, 0, max(1, rn)),
    ])
    e = e[:n]
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e.astype(np.float32)


def lowpass(x, cutoff, sr=None):
    sr = _sr(sr)
    # one-pole
    rc = 1.0 / (2 * np.pi * cutoff)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = np.zeros_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + alpha * (x[i] - out[i - 1])
    return out


def highpass(x, cutoff, sr=None):
    return x - lowpass(x, cutoff, sr)


def normalize(x, peak_dbfs=-3):
    peak = np.max(np.abs(x)) if np.max(np.abs(x)) > 0 else 1.0
    target = 10 ** (peak_dbfs / 20.0)
    return (x / peak * target).astype(np.float32)


def seamless_loop(x, xfade=0.05):
    sr = C.SAMPLE_RATE
    n = len(x)
    xf = int(sr * xfade)
    if xf <= 0 or xf * 2 >= n:
        return x
    # crossfade tail into head
    head = x[:xf].copy()
    tail = x[-xf:].copy()
    fade = np.linspace(0, 1, xf)[:, None]
    mixed = tail * (1 - fade) + head * fade
    out = x.copy()
    out[:xf] = mixed
    out[-xf:] = mixed
    return out


def mix(*tracks):
    if not tracks:
        return np.zeros((0, 2), dtype=np.float32)
    n = max(len(t) for t in tracks)
    out = np.zeros((n, 2), dtype=np.float64)
    for t in tracks:
        arr = np.asarray(t, dtype=np.float64)
        if arr.ndim == 1:
            arr = np.column_stack([arr, arr])
        if len(arr) < n:
            arr = np.pad(arr, ((0, n - len(arr)), (0, 0)))
        out += arr
    return out.astype(np.float32)


def pan(x, p=0.0):
    # p in [-1,1]
    l = x * (1 - max(0, p))
    r = x * (1 + min(0, p))
    if x.ndim == 1:
        return np.column_stack([l, r]).astype(np.float32)
    out = x.copy()
    out[:, 0] = x[:, 0] * (1 - max(0, p))
    out[:, 1] = x[:, 1] * (1 + min(0, p))
    return out.astype(np.float32)


# Aliases commonly expected
def sine(freq, dur, sr=None, amp=0.5):
    return osc("sine", freq, dur, sr=sr, amp=amp)


def generate(duration=1.0, freq=440.0, sr=None, amp=0.3):
    return sine(freq, duration, sr=sr, amp=amp)


def test_signal(duration=1.0, sr=None):
    return generate(duration=duration, sr=sr)


def saw(freq, dur, sr=None, amp=0.5):
    return osc("saw", freq, dur, sr=sr, amp=amp)


def square(freq, dur, sr=None, amp=0.5):
    return osc("square", freq, dur, sr=sr, amp=amp)


def triangle(freq, dur, sr=None, amp=0.5):
    return osc("triangle", freq, dur, sr=sr, amp=amp)