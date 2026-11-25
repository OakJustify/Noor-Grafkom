"""Original loopable score: gentle felt-key motif, breathy pads and spirit bells.

Locally synthesised with NumPy; no samples, downloads, copyrighted songs or new
dependencies. Each 24-second loop ends at silence for click-free playback.
"""

from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

from . import config

RATE = 22050
SECONDS = 24
TRACKS = ("home", "gaung", "return")


def frequency(note):
    return 440 * 2 ** ((note - 69) / 12)


def render_track(scene: str, seconds: float = SECONDS, rate: int = RATE) -> np.ndarray:
    if scene not in TRACKS:
        raise ValueError(f"Unknown music scene: {scene}")
    count = int(seconds * rate)
    mix = np.zeros((count, 2), dtype=np.float64)
    rng = np.random.default_rng(404 + TRACKS.index(scene))

    def add(note, onset, duration, kind="key", gain=0.12, pan=0):
        start = int(onset * rate)
        end = min(count, start + int(duration * rate))
        if end <= start:
            return
        t = np.arange(end - start) / rate
        f = frequency(note)
        if kind == "pad":
            tone = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.002 * t)
                    + 0.2 * np.sin(2 * np.pi * f * 2 * t)) / 1.7
            envelope = np.minimum(1, t / 0.7) * np.minimum(1, np.maximum(0, duration - t) / 1.2)
            tone *= 0.9 + 0.1 * np.sin(2 * np.pi * 0.23 * t)
        elif kind == "bell":
            tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.01 * t)
                    + 0.14 * np.sin(2 * np.pi * f * 3.97 * t)) / 1.44
            envelope = np.minimum(1, t / 0.008) * np.exp(-t * 1.7)
        else:
            tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t)
                    + 0.12 * np.sin(2 * np.pi * f * 3 * t)) / 1.47
            envelope = np.minimum(1, t / 0.012) * np.exp(-t * 1.9)
            tone += rng.normal(0, 0.01, len(t)) * np.exp(-t * 40)
        signal = tone * envelope * gain
        mix[start:end, 0] += signal * (0.75 - pan * 0.2)
        mix[start:end, 1] += signal * (0.75 + pan * 0.2)

    harmony = {
        "home": ((50, 57, 62, 65), (46, 53, 58, 62), (48, 55, 60, 64), (45, 52, 57, 60)),
        "gaung": ((50, 57, 61, 65), (46, 53, 59, 62), (48, 55, 61, 64), (45, 52, 58, 60)),
        "return": ((50, 57, 62, 66), (55, 62, 67, 71), (52, 59, 64, 67), (57, 64, 69, 73)),
    }[scene]
    melody = (74, 77, 76, 69, 72, 74, 77, 81, 79, 76, 74, 72)
    if scene == "gaung":
        melody = (74, 73, 77, 69, 75, 74, 80, 77, 73, 76, 74, 70)
    elif scene == "return":
        melody = (74, 78, 81, 76, 79, 78, 83, 81, 78, 76, 74, 78)
    for bar, chord in enumerate(harmony):
        onset = bar * 6
        for index, note in enumerate(chord):
            add(note, onset, 6.5, "pad", 0.04 if scene != "gaung" else 0.045, (index - 1.5) / 2)
        for step in range(4):
            add(chord[step % len(chord)] + 12, onset + step * 1.5, 3, gain=0.09, pan=(-1) ** step * 0.5)
    for index, note in enumerate(melody):
        add(note, index * 1.8 + 0.65, 3.2, "bell", 0.065, np.sin(index * 1.3))
    # Stereo reflections sound spacious without an external reverb plugin.
    for delay, gain in ((0.21, 0.16), (0.43, 0.10), (0.81, 0.06)):
        shift = int(delay * rate)
        if shift < count:
            mix[shift:] += mix[:-shift, ::-1].copy() * gain
    t = np.arange(count) / rate
    fade = np.minimum(1, t / 0.5) * np.minimum(1, np.maximum(0, seconds - t) / 0.8)
    mix *= fade[:, None]
    mix[0] = mix[-1] = 0
    return (np.clip(mix, -0.75, 0.75) * 32767).astype("<i2")


def ensure_music(directory: Path = config.AUDIO_DIR, overwrite=False) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for scene in TRACKS:
        path = directory / f"music_{scene}.wav"
        if overwrite or not path.exists():
            samples = render_track(scene)
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(RATE)
                handle.writeframes(samples.tobytes())
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=config.AUDIO_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for path in ensure_music(args.output, args.overwrite):
        print(path)


if __name__ == "__main__":
    main()
