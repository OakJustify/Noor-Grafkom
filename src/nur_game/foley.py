"""Band-limited, original jump/landing sounds: a rising swoop, not white static."""

import numpy as np
from scipy.signal import butter, sosfilt

RATE = 22050


def render_foley(event: str, rate: int = RATE) -> np.ndarray:
    if event not in ("jump", "land"):
        raise ValueError(f"Unknown movement sound: {event}")
    seconds = 0.27 if event == "jump" else 0.18
    t = np.arange(int(seconds * rate)) / rate
    rng = np.random.default_rng(0x4E55 + (event == "land"))
    # Cloth/air is low-pass filtered twice; the pitched movement is dominant.
    noise = sosfilt(butter(4, 850, fs=rate, output="sos"), rng.normal(0, 1, len(t)))
    if event == "jump":
        frequency = 180 + 420 * np.sin(np.minimum(t / 0.21, 1) * np.pi / 2)
        phase = np.cumsum(frequency) * 2 * np.pi / rate
        tone = np.sin(phase) * 0.55 + np.sin(phase * 2) * 0.10
        envelope = (1 - np.exp(-t * 140)) * np.exp(-t * 9)
        body = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 55) * 0.18
        sound = (tone + noise * 0.055) * envelope + body
    else:
        phase = 2 * np.pi * (95 * t - 90 * t * t)
        envelope = (1 - np.exp(-t * 300)) * np.exp(-t * 28)
        sound = (np.sin(phase) * 0.55 + np.sin(phase * 1.7) * 0.10 + noise * 0.08) * envelope
    # Raised-cosine release and zero endpoints avoid clicks on each takeoff.
    release = np.clip((seconds - t) / 0.055, 0, 1)
    sound *= 0.5 - 0.5 * np.cos(np.pi * release)
    sound[0] = sound[-1] = 0
    return np.clip(sound, -0.8, 0.8)
