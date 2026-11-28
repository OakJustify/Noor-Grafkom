"""Procedural audio generator for creature vocal calls.

The runtime path synthesises NumPy buffers in memory so the game never has to
ship or write creature audio.  ``generate_audio_cache`` is kept for offline
baking and the legacy tests that expect WAV files on disk.
"""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .morphology_generator import VocalParams

ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = ROOT / "assets" / "audio" / "cache" / "creatures"

CALL_TYPES = ("idle", "alert", "aggressive", "pain", "death")


@dataclass
class AudioCache:
    """Container for cached audio file paths of a creature."""

    idle: Path
    alert: Path
    aggressive: Path
    pain: Path
    death: Path


class CreatureAudioGenerator:
    """Synthesize deterministic creature vocal calls."""

    def __init__(self, seed: int = 42, sample_rate: int = 44100):
        self.seed = seed
        self.sample_rate = sample_rate

    def synthesize_call(
        self,
        call_type: str,
        vocal: VocalParams,
        seed: int | None = None,
    ) -> np.ndarray:
        """Return one mono float32 vocal call.  Never touches the filesystem."""
        call_config = vocal.call_types.get(call_type, vocal.call_types.get("idle"))
        base_seed = self.seed if seed is None else seed
        # Stable offset so different call types do not share the same RNG stream.
        call_seed = base_seed + sum(ord(ch) for ch in call_type)
        return self._synthesize_call(vocal, call_config, call_seed)

    def synthesize_vocalizations(
        self,
        vocal: VocalParams,
        seed: int | None = None,
    ) -> dict[str, np.ndarray]:
        """Synthesize every call type defined for a creature, in memory."""
        return {
            call_type: self.synthesize_call(call_type, vocal, seed)
            for call_type in vocal.call_types
        }

    def generate_audio_cache(
        self,
        creature_id: str,
        vocal: VocalParams,
        seed: int | None = None,
    ) -> AudioCache:
        """Pre-generate and cache all core vocal calls as WAV files."""
        actual_seed = seed if seed is not None else self.seed
        cache_paths = {}
        for call_type in CALL_TYPES:
            path = self.get_or_generate_audio(
                creature_id, call_type, vocal, seed=actual_seed
            )
            cache_paths[call_type] = path
        return AudioCache(**cache_paths)

    def get_or_generate_audio(
        self,
        creature_id: str,
        call_type: str,
        vocal: VocalParams,
        seed: int = 42,
    ) -> Path:
        """Return path to a cached WAV file, synthesizing it on first call."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{creature_id}_{call_type}_{seed}.wav"
        file_path = CACHE_DIR / filename
        if file_path.exists():
            return file_path
        samples = self.synthesize_call(call_type, vocal, seed=seed)
        self._write_wav(file_path, samples)
        return file_path

    def _synthesize_call(
        self, vocal: VocalParams, call_config: dict, seed: int
    ) -> np.ndarray:
        """Synthesize a vocal call using additive synthesis + formants + noise."""
        rng = np.random.RandomState(seed)

        pattern = call_config.get("pattern", "drone")
        dur_range = call_config.get("duration", (1.0, 2.0))
        duration = rng.uniform(dur_range[0], dur_range[1])

        num_samples = max(1, int(self.sample_rate * duration))
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # 1. Fundamental frequency with pitch modulation.
        f0 = vocal.fundamental_freq
        pitch_range = call_config.get("pitch_range", (-2, 2))
        semitone_shift = rng.uniform(pitch_range[0], pitch_range[1])
        f0_actual = f0 * (2.0 ** (semitone_shift / 12.0))

        if pattern == "trill":
            f0_mod = f0_actual + 15.0 * np.sin(2 * np.pi * 12.0 * t)
        elif pattern == "chirp":
            f0_mod = f0_actual * (1.0 + 0.5 * np.exp(-5.0 * t))
        elif pattern == "scream":
            f0_mod = f0_actual * (1.0 + 0.8 * (t / duration))
        else:  # drone / pulse / click
            f0_mod = np.full_like(t, f0_actual)

        phase = 2 * np.pi * np.cumsum(f0_mod) / self.sample_rate

        # 2. Additive harmonics with formant filtering.
        harmonicity = call_config.get("harmonicity", 0.8)
        audio = np.zeros(num_samples, dtype=np.float32)

        for formant_ratio in vocal.formant_ratios:
            formant_freq = f0_actual * formant_ratio
            for h in range(1, 8):
                h_freq = h * f0_actual
                dist = abs(h_freq - formant_freq) / max(1e-6, formant_freq)
                gain = math.exp(-3.0 * dist) * (1.0 / (h ** 0.7))
                if rng.rand() < harmonicity:
                    audio += gain * np.sin(h * phase)

        # 3. Noise / breathiness component.
        noise = rng.normal(0, 0.1, num_samples)
        audio += vocal.breathiness * noise

        # 4. Amplitude envelope.
        envelope = np.ones(num_samples, dtype=np.float32)
        fade_samples = int(0.05 * self.sample_rate)
        if 0 < fade_samples < num_samples // 2:
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

        if pattern == "pulse":
            envelope *= 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)
        elif pattern == "click":
            envelope *= np.exp(-30.0 * t)

        audio *= envelope
        max_val = np.max(np.abs(audio))
        if max_val > 1e-5:
            audio = (audio / max_val) * 0.9
        return audio.astype(np.float32)

    def _write_wav(self, path: Path, samples: np.ndarray):
        """Save mono float32 samples to a 16-bit PCM WAV."""
        pcm_samples = (samples * 32767.0).astype(np.int16)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_samples.tobytes())
