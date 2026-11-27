"""Generate procedural audio WAV files."""

import argparse
import os
import wave

import numpy as np

import noor.config as C
from noor.audio import ambience, recipes


def write_wav(path, arr):
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 1:
        arr = np.column_stack([arr, arr])
    # peak normalize safety
    peak = np.max(np.abs(arr)) if np.max(np.abs(arr)) > 0 else 1.0
    target = 10 ** (C.PEAK_DBFS / 20.0)
    if peak > target:
        arr = arr / peak * target
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(C.CHANNELS)
        w.setsampwidth(2)
        w.setframerate(C.SAMPLE_RATE)
        pcm = (arr * 32767).astype(np.int16)
        w.writeframes(pcm.tobytes())


def render_intensity_ramp(stage, seconds=30.0):
    """Stitch the stems the way AudioManager mixes them, sweeping intensity 0->1."""
    stems = {name: ambience.stems_for_stage(stage)[name] for name in ambience.LAYERS}
    loop_n = next(iter(stems.values())).shape[0]
    total_n = int(seconds * C.SAMPLE_RATE)
    out = np.zeros((total_n, 2), dtype=np.float32)
    for start in range(0, total_n, loop_n):
        w = ambience.mix_weights(start / max(1.0, total_n - loop_n))
        seg = np.zeros((loop_n, 2), dtype=np.float32)
        for name, stem in stems.items():
            seg += stem * w[name]
        end = min(total_n, start + loop_n)
        out[start:end] = seg[: end - start]
    return out


def bake_ambience(out, preview=False):
    for stage in (1, 2, 3, 4):
        for name, data in ambience.stems_for_stage(stage).items():
            write_wav(os.path.join(out, "ambience", f"s{stage}_{name}.wav"), data)
        if preview:
            ramp = render_intensity_ramp(stage)
            write_wav(os.path.join(out, "ambience", f"s{stage}_intensity_ramp.wav"), ramp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ambience", action="store_true", help="only render the ambience stems")
    parser.add_argument("--preview", action="store_true", help="also render intensity ramp previews")
    args = parser.parse_args(argv)

    out = os.path.join("assets", "audio")
    os.makedirs(out, exist_ok=True)
    if not args.ambience:
        for sid, data in recipes.generate_all_sfx().items():
            write_wav(os.path.join(out, f"{sid}.wav"), data)
        for lid, data in recipes.generate_music().items():
            write_wav(os.path.join(out, f"{lid}.wav"), data)
    bake_ambience(out, preview=args.preview)
    print("generated audio")


if __name__ == "__main__":
    main()
