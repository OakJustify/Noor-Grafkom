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
from .synthesis import BEDS, GENERATED, RATE, ensure_generated


class Audio:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.available = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.beds: dict[str, pygame.mixer.Sound] = {}
        self.channels: dict[str, pygame.mixer.Channel] = {}
        self.cooldowns: dict[str, float] = {}
        self.music: dict[str, pygame.mixer.Sound] = {}
        self.music_channels: dict[str, pygame.mixer.Channel] = {}
        self.music_scene = "home"
        try:
            pygame.mixer.pre_init(RATE, -16, 2, 512)
            pygame.mixer.init()
            self.available = True
        except (pygame.error, NotImplementedError, AttributeError):
            self.available = False
        if not self.available:
            return
        ensure_generated()
        for scene, path in zip(TRACKS, ensure_music()):
            try:
                self.music[scene] = pygame.mixer.Sound(str(path))
            except pygame.error:
                continue
        pygame.mixer.set_num_channels(max(12, pygame.mixer.get_num_channels()))
        # Reserve every continuous voice: one-shot foley must never steal a
        # music, ambience or boss channel and interrupt its loop.
        pygame.mixer.set_reserved(len(TRACKS) + len(BEDS) + 1)
        self.music_channels = {scene: pygame.mixer.Channel(index) for index, scene in enumerate(TRACKS)}
        self.channels = {name: pygame.mixer.Channel(len(TRACKS) + index) for index, name in enumerate(BEDS)}
        self.channels["boss_pulse"] = pygame.mixer.Channel(len(TRACKS) + len(BEDS))
        for channel in (*self.music_channels.values(), *self.channels.values()):
            channel.set_volume(0)
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

    def update(self, dt: float, stage: int, illumination: float, boss: bool = False,
               phase: int = 0, ending: bool = False) -> None:
        self.music_scene = "return" if ending else "gaung" if phase or boss else "home"
        if not self.enabled or not self.available:
            return
        for scene, sound in self.music.items():
            channel = self.music_channels[scene]
            if not channel.get_busy():
                channel.set_volume(0)
                channel.play(sound, loops=-1)
            target = 0.32 if scene == self.music_scene else 0
            current = channel.get_volume()
            blend = min(1, dt * 1.2)
            value = current + (target - current) * blend
            # Mixer volume is quantised; snap tiny remaining deltas instead of
            # getting stuck just short of silence during a crossfade.
            channel.set_volume(target if abs(target - value) < 0.015 else value)
        for key in self.cooldowns:
            self.cooldowns[key] = max(0.0, self.cooldowns[key] - dt)
        targets = (0.08, 0.05, 0.0) if not boss else (0.0, 0.0, 0.16)
        if stage >= 2 and not boss:
            targets = (0.04, 0.0, 0.10)
        if ending:
            targets = (0.0, 0.0, 0.0)
        for name, target in zip(BEDS, targets):
            sound = self.beds.get(name)
            if sound is None:
                continue
            channel = self.channels[name]
            if not channel.get_busy():
                channel.set_volume(0)
                channel.play(sound, loops=-1)
            current = channel.get_volume()
            value = current + (target - current) * min(1.0, dt * 1.4)
            channel.set_volume(target if abs(target - value) < 0.015 else value)
        pulse = self.channels["boss_pulse"]
        if boss and not ending and "boss_pulse" in self.sounds:
            if not pulse.get_busy():
                pulse.play(self.sounds["boss_pulse"], loops=-1)
            pulse.set_volume(0.28)
        else:
            pulse.stop()
            pulse.set_volume(0)

    def set_muted(self, muted: bool) -> None:
        self.enabled = not muted
        if not self.available:
            return
        if muted:
            # A one-shot may already be playing when M is pressed. Stop it,
            # rather than just blocking the next call to play().
            for sound in self.sounds.values():
                sound.stop()
        for channel in self.channels.values():
            channel.set_volume(0)
        for channel in self.music_channels.values():
            channel.set_volume(0)

    def close(self) -> None:
        if not self.available:
            return
        for channel in self.channels.values():
            channel.stop()
        for channel in self.music_channels.values():
            channel.stop()
        for sound in self.sounds.values():
            sound.stop()
        self.channels.clear()
