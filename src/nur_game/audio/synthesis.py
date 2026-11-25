"""Audio: original three-scene score, CC0 ambience and procedural foley."""

from __future__ import annotations

import math
import io
import random
import struct
import wave
from pathlib import Path

import pygame

from .. import config
from ..music import TRACKS, ensure_music


BEDS = (
    "creepy_vocal_ambience.ogg",
    "creepy_ambience.ogg",
    "creepy_dungeon_ambience.ogg",
)
GENERATED = ("tick.wav", "breath.wav", "glitch.wav", "memory.wav", "heartbeat.wav", "boss_pulse.wav", "door.wav",
             "jump.wav", "land.wav")
RATE = 22050


def _write_wav(path: Path, samples: list[float]) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = bytearray()
        for sample in samples:
            frames.extend(struct.pack("<h", max(-32768, min(32767, int(sample * 32767)))))
        handle.writeframes(frames)


def _sample(name: str) -> list[float]:
    if name in ("jump", "land"):
        from ..foley import render_foley

        return render_foley(name).tolist()
    rng = random.Random(config.SEED + sum(map(ord, name)))
    seconds = {
        "tick": 0.10,
        "breath": 0.85,
        "glitch": 0.28,
        "memory": 0.55,
        "heartbeat": 1.10,
        "boss_pulse": 1.60,
        "door": 0.75,
    }[name]
    count = int(RATE * seconds)
    out: list[float] = []
    for i in range(count):
        t = i / RATE
        p = i / count
        if name == "tick":
            value = math.sin(2 * math.pi * (1180 - 500 * p) * t) * math.exp(-18 * p)
        elif name == "breath":
            noise = rng.uniform(-1, 1)
            value = noise * math.sin(math.pi * p) ** 2 * (0.22 + 0.12 * math.sin(2 * math.pi * 3 * t))
        elif name == "glitch":
            step = int(t * 37) % 5
            value = rng.uniform(-1, 1) * (0.10 if step else 0.30) * (1 - p)
            value += math.sin(2 * math.pi * (61 + step * 19) * t) * 0.12 * (1 - p)
        elif name == "memory":
            value = (math.sin(2 * math.pi * 392 * t) + 0.5 * math.sin(2 * math.pi * 587 * t)) * math.exp(-4 * p)
            value += rng.uniform(-1, 1) * 0.015
        elif name == "heartbeat":
            beat = math.exp(-28 * ((t % 0.55) ** 2))
            value = math.sin(2 * math.pi * 48 * t) * beat * 0.7
            value += math.sin(2 * math.pi * 34 * t) * beat * 0.3
        elif name == "boss_pulse":
            value = math.sin(2 * math.pi * (44 + 8 * math.sin(t * 2)) * t) * (0.25 + 0.15 * math.sin(t * 3))
            value += rng.uniform(-1, 1) * 0.03
        else:  # door
            value = math.sin(2 * math.pi * (180 - 90 * p) * t) * 0.22 * (1 - p)
            value += rng.uniform(-1, 1) * 0.06 * math.sin(math.pi * p)
        out.append(max(-1.0, min(1.0, value)))
    return out


def ensure_generated() -> None:
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for name in GENERATED:
        path = config.AUDIO_DIR / name
        if not path.exists():
            _write_wav(path, _sample(Path(name).stem))


