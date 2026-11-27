"""Procedural Audio Generator & Cache Manager

Generates creature vocal calls using PyWav / NumPy synthesis,
saves WAV files deterministically to cache on initial spawn,
and plays cached audio on demand.
"""

from __future__ import annotations
import math
import wave
import struct
import random
from pathlib import Path
from dataclasses import dataclass
import numpy as np

from .morphology_generator import VocalParams


CACHE_DIR = Path("assets/audio/cache/creatures")


class CreatureAudioGenerator:
    """Synthesizes creature vocal calls and manages on-disk cache."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get_or_generate_audio(
        self,
        creature_id: str,
        call_type: str,
        vocal: VocalParams,
        seed: int = 42
    ) -> Path:
        """Return path to cached WAV file, synthesizing on first call."""
        filename = f"{creature_id}_{call_type}_{seed}.wav"
        file_path = CACHE_DIR / filename

        if file_path.exists():
            return file_path

        # Generate audio buffer
        call_config = vocal.call_types.get(call_type, vocal.call_types.get("idle"))
        samples = self._synthesize_call(vocal, call_config, seed)

        # Write WAV file
        self._write_wav(file_path, samples)
        return file_path

    def _synthesize_call(self, vocal: VocalParams, call_config: dict, seed: int) -> np.ndarray:
        """Synthesize vocal call using additive synthesis + formants + noise."""
        rng = np.random.RandomState(seed)

        pattern = call_config.get("pattern", "drone")
        dur_range = call_config.get("duration", (1.0, 2.0))
        duration = rng.uniform(dur_range[0], dur_range[1])

        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # 1. Fundamental Frequency with Pitch Modulation
        f0 = vocal.fundamental_freq
        pitch_range = call_config.get("pitch_range", (-2, 2))
        semitone_shift = rng.uniform(pitch_range[0], pitch_range[1])
        f0_actual = f0 * (2.0 ** (semitone_shift / 12.0))

        # Pattern-specific pitch modulation
        if pattern == "trill":
            f0_mod = f0_actual + 15.0 * np.sin(2 * np.pi * 12.0 * t)
        elif pattern == "chirp":
            f0_mod = f0_actual * (1.0 + 0.5 * np.exp(-5.0 * t))
        elif pattern == "scream":
            f0_mod = f0_actual * (1.0 + 0.8 * (t / duration))
        else:  # drone / pulse / click
            f0_mod = np.full_like(t, f0_actual)

        phase = 2 * np.pi * np.cumsum(f0_mod) / self.sample_rate

        # 2. Additive Harmonics with Formant Filtering
        harmonicity = call_config.get("harmonicity", 0.8)
        audio = np.zeros(num_samples, dtype=np.float32)

        for formant_ratio in vocal.formant_ratios:
            formant_freq = f0_actual * formant_ratio
            for h in range(1, 8):
                h_freq = h * f0_actual
                # Distance to formant peak determines amplitude gain
                dist = abs(h_freq - formant_freq) / formant_freq
                gain = math.exp(-3.0 * dist) * (1.0 / (h ** 0.7))

                if rng.rand() < harmonicity:
                    audio += gain * np.sin(h * phase)

        # 3. Noise / Breathiness Component
        breathiness = vocal.breathiness
        noise = rng.normal(0, 0.1, num_samples)
        audio += breathiness * noise

        # 4. Amplitude Envelope
        envelope = np.ones(num_samples, dtype=np.float32)
        fade_samples = int(0.05 * self.sample_rate)
        if fade_samples > 0 and fade_samples < num_samples // 2:
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

        if pattern == "pulse":
            pulse_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)
            envelope *= pulse_mod
        elif pattern == "click":
            envelope *= np.exp(-30.0 * t)

        audio *= envelope

        # Normalize to [-0.9, 0.9]
        max_val = np.max(np.abs(audio))
        if max_val > 1e-5:
            audio = (audio / max_val) * 0.9

        return audio

    def _write_wav(self, path: Path, samples: np.ndarray):
        """Save mono float32 samples to 16-bit PCM WAV."""
        pcm_samples = (samples * 32767.0).astype(np.int16)

        with wave.open(str(path), 'wb') as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_samples.tobytes())
