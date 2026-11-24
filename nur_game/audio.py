"""Audio: three CC0 Freesound beds plus small original procedural foley.

The downloaded beds are credited in ``assets/nur/CREDITS.md``. Everything
generated here is authored for NÜR and released CC0 alongside the game.
"""

from __future__ import annotations

import math
import io
import random
import struct
import wave
from pathlib import Path

import pygame

from . import config

BEDS = (
    "creepy_vocal_ambience.ogg",
    "creepy_ambience.ogg",
    "creepy_dungeon_ambience.ogg",
)
GENERATED = ("tick.wav", "breath.wav", "glitch.wav", "memory.wav", "heartbeat.wav", "boss_pulse.wav", "door.wav")
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


class Audio:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.available = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.beds: dict[str, pygame.mixer.Sound] = {}
        self.channels: dict[str, pygame.mixer.Channel] = {}
        self.cooldowns: dict[str, float] = {}
        try:
            pygame.mixer.pre_init(RATE, -16, 2, 512)
            pygame.mixer.init()
            self.available = True
        except (pygame.error, NotImplementedError, AttributeError):
            self.available = False
        if not self.available:
            return
        ensure_generated()
        for name in GENERATED:
            try:
                self.sounds[Path(name).stem] = pygame.mixer.Sound(str(config.AUDIO_DIR / name))
            except pygame.error:
                continue
        for name in BEDS:
            path = config.AUDIO_DIR / name
            if path.exists():
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(0.0)
                    self.beds[name] = sound
                except pygame.error:
                    continue
        for key in self.sounds:
            self.cooldowns[key] = 0.0

    def play(self, key: str, volume: float = 0.55) -> None:
        if not self.enabled or not self.available or self.cooldowns.get(key, 0.0) > 0:
            return
        sound = self.sounds.get(key)
        if sound is None:
            return
        sound.set_volume(max(0.0, min(1.0, volume)))
        sound.play()
        self.cooldowns[key] = 0.08

    def play_note(self, note: int) -> None:
        if not self.available:
            return
        key = f"note_{note}"
        if key not in self.sounds:
            frequency = (261.63, 329.63, 392.0, 440.0)[note]
            frames = bytearray()
            for i in range(int(RATE * 0.35)):
                t = i / RATE
                envelope = min(1, t * 80) * math.exp(-8 * t)
                value = (math.sin(math.tau * frequency * t) + 0.25 * math.sin(math.tau * frequency * 2 * t)) * envelope * 0.5
                frames.extend(struct.pack("<h", int(value * 32767)))
            stream = io.BytesIO()
            with wave.open(stream, "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(RATE)
                handle.writeframes(frames)
            stream.seek(0)
            self.sounds[key] = pygame.mixer.Sound(file=stream)
        self.play(key, 0.65)

    def update(self, dt: float, stage: int, illumination: float, boss: bool = False) -> None:
        if not self.enabled or not self.available:
            return
        for key in self.cooldowns:
            self.cooldowns[key] = max(0.0, self.cooldowns[key] - dt)
        targets = (0.16, 0.10, 0.0) if not boss else (0.0, 0.0, 0.30)
        if stage >= 2 and not boss:
            targets = (0.06, 0.0, 0.22)
        for name, target in zip(BEDS, targets):
            sound = self.beds.get(name)
            if sound is None:
                continue
            channel = self.channels.get(name)
            if channel is None or not channel.get_busy():
                channel = sound.play(loops=-1)
                if channel is not None:
                    self.channels[name] = channel
            if channel is not None:
                current = channel.get_volume()
                channel.set_volume(current + (target - current) * min(1.0, dt * 1.4))
        if boss and "boss_pulse" not in self.channels:
            channel = self.sounds["boss_pulse"].play(loops=-1) if "boss_pulse" in self.sounds else None
            if channel is not None:
                channel.set_volume(0.28)
                self.channels["boss_pulse"] = channel

    def set_muted(self, muted: bool) -> None:
        self.enabled = not muted
        if not self.available:
            return
        for channel in self.channels.values():
            channel.set_volume(0.0 if muted else 0.2)

    def close(self) -> None:
        if not self.available:
            return
        for channel in self.channels.values():
            channel.stop()
        self.channels.clear()
