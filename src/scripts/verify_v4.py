"""Runtime renderer timings, foundation integrity, and original sound-bed excerpts.

Timings use debug-spawn fixtures, not campaign/traversal evidence. WAV excerpts
are offline stem mixes at the live target gains, not a recording of the mixer.
"""

import json
import os
import platform
import time
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from nur_game import config
from nur_game.engine import DT
from nur_game.game import Game, _source_hashes
from nur_game.physics import NurInput
from nur_game.soundscape import RATE, render_drift


def main():
    output = config.ROOT / "docs" / "verification"
    output.mkdir(parents=True, exist_ok=True)
    timings = []
    for region in (0, 10, 16, 28):
        game = Game(room=region, muted=True, persist=False)
        try:
            for label, target in (("bright", 1), ("dim", 0.12)):
                while game.lantern.charge > target:
                    game.update(0.1, NurInput(focus=True))
                begin = time.perf_counter()
                game.draw()
                cold = (time.perf_counter() - begin) * 1000
                samples = []
                for _ in range(80):
                    begin = time.perf_counter()
                    game.update(DT, NurInput())
                    game.draw()
                    samples.append((time.perf_counter() - begin) * 1000)
                timings.append({
                    "region": region + 1, "band": label,
                    "first_draw_ms": round(cold, 3),
                    "cached_update_draw_p50_ms": round(float(np.median(samples)), 3),
                    "cached_update_draw_p95_ms": round(float(np.percentile(samples, 95)), 3),
                })
        finally:
            game.audio.close()

    removed = [name for name in ('echo_game','tests_echo','assets/echo','requirements-echo.txt')
               if (config.ROOT / name).exists()]
    notes = []
    stems = [render_drift(kind) for kind in range(3)]
    audio = Game(muted=True, persist=False)
    try:
        for amount, name in ((1, "sound-bed-bright.wav"), (0.12, "sound-bed-dim.wav")):
            audio.audio.update(0.1, 0, amount)
            gains = audio.audio.drift_targets
            mixed = sum(stem.astype(float) * gain for stem, gain in zip(stems, gains))
            pcm = np.clip(mixed, -32767, 32767).astype("<i2")
            with wave.open(str(output / name), "wb") as handle:
                handle.setnchannels(2)
                handle.setsampwidth(2)
                handle.setframerate(RATE)
                handle.writeframes(pcm.tobytes())
            notes.append({"file": name, "charge": amount, "gains": gains,
                          "peak": int(np.abs(pcm.astype(int)).max())})
    finally:
        audio.audio.close()

    report = {
        "kind": "Headless debug-spawn timing fixtures; offline sound-bed mixes (music/foley not included)",
        "platform": platform.platform(), "python": platform.python_version(),
        "pygame": pygame.version.ver, "resolution": config.SIZE,
        "renderer": timings, "unwanted_game_paths": removed,
        "audio_excerpts": notes, "sources": _source_hashes(),
    }
    (output / "runtime.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cached_p95_max_ms": max(row["cached_update_draw_p95_ms"] for row in timings),
                      "first_draw_max_ms": max(row["first_draw_ms"] for row in timings),
                      "unwanted_game_paths": removed}))
    pygame.quit()


if __name__ == "__main__":
    main()
