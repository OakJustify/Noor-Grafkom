"""Generate ECHO-owned original assets and a reproducible authorship manifest.

Usage: .venv-echo/bin/python -m echo_game.generate_assets [--force]
This command does not initialize a display, mixer, network or external tools.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path

import cairo
import numpy as np

from .art import (ART_VERSION, ASSET_ROOT, CHAPTERS, PLAYER_CELL,
                  PLAYER_FRAMES, SEED, ensure_art_assets)
from .audio import AUDIO_VERSION, ensure_audio_assets


def _metadata(path: Path):
    entry = {"path": path.relative_to(ASSET_ROOT).as_posix(),
             "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if path.suffix == ".png":
        image = cairo.ImageSurface.create_from_png(str(path))
        entry.update(type="image/png", width=image.get_width(), height=image.get_height(),
                     generator="Cairo vector paths / original procedural geometry")
    elif path.suffix == ".wav":
        with wave.open(str(path), "rb") as source:
            pcm = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2")
            entry.update(type="audio/wav", channels=source.getnchannels(),
                         sample_rate=source.getframerate(), sample_width=source.getsampwidth(),
                         frames=source.getnframes(),
                         duration_seconds=source.getnframes() / source.getframerate(),
                         peak_dbfs=round(20 * np.log10(max(1, int(np.abs(pcm.astype(np.int32)).max())) / 32768), 3),
                         rms_dbfs=round(20 * np.log10(max(1e-10, float(np.sqrt(np.mean((pcm.astype(np.float64) / 32768) ** 2))))), 3),
                         generator="numpy spectral noise and original oscillator/bell composition",
                         seamless_loop=path.stem in ("ambience", "music"))
    else:
        entry.update(type="text/markdown")
    return entry


def generate(force=False):
    """Generate missing assets and always refresh the deterministic manifest."""
    paths = ensure_art_assets(force=force) + ensure_audio_assets(force=force)
    philosophy = ASSET_ROOT / "ART_PHILOSOPHY.md"
    if philosophy.is_file():
        paths.append(philosophy)
    manifest = {
        "project": "ECHO: The Hollow Signal",
        "schema_version": 1,
        "generation_seed": SEED,
        "generator_versions": {"art": ART_VERSION, "audio": AUDIO_VERSION},
        "generator_sources": {
            f"echo_game/{name}": hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
            for name in ("art.py", "audio.py", "generate_assets.py")
        },
        "authorship": {
            "kind": "Original procedural artwork and original synthesized audio",
            "created_for": "ECHO: The Hollow Signal",
            "method": "Project-authored Cairo vector geometry and numpy/stdlib-wave synthesis",
            "external_assets": [],
            "target_game_assets_copied": False,
            "music": "Original sparse nine-event bell phrase, bowed sine modes and periodic drones",
            "notes": "No samples, photographed textures, stock sprites, external music or target-game assets.",
        },
        "palette": {"silhouette": "#061015", "ivory": "#eeefda", "signal": "#b3d5d1"},
        "sprite_sheets": {
            "art/courier_sheet.png": {"cell_size": list(PLAYER_CELL), "frames": PLAYER_FRAMES,
                                       "rendered_cell_size": [48, 56], "body_size": [22, 44],
                                       "anchor": [24, 28],
                                       "poses": {"idle": [0, 1], "walk": list(range(2, 10)),
                                                 "jump": [10], "fall": [11]}},
            "art/moth_guide.png": {"cell_size": [64, 64], "frames": 4},
        },
        "landscapes": {"chapters": CHAPTERS, "tile_size": [1920, 540],
                       "parallax": {"far": .075, "works": .18, "mid": .32, "foliage": .61}},
        "assets": [_metadata(path) for path in sorted(paths)],
    }
    destination = ASSET_ROOT / "manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="deterministically regenerate all ECHO-owned PNGs/WAVs")
    parser.add_argument("--quiet", action="store_true", help="write assets without listing individual paths")
    args = parser.parse_args(argv)
    destination, manifest = generate(force=args.force)
    if not args.quiet:
        for entry in manifest["assets"]:
            print(f"{ASSET_ROOT / entry['path']}  {entry['bytes']:,} bytes")
    print(f"Original ECHO assets ready: {len(manifest['assets'])} assets; {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
