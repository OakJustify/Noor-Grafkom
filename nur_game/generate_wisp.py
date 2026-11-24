"""Export the exact in-game wisp frames as transparent PNG sprite sheets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pygame

from . import config
from .wisp import ANIMATIONS, FRAME_COUNT, FRAME_SIZE, PIVOT, wisp_sprite

SPRITE_DIR = config.ROOT / "assets" / "nur" / "sprites" / "wisp"


def export_wisp(output: Path = SPRITE_DIR) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    width, height = FRAME_SIZE
    manifest = {
        "character": "cloaked wisp",
        "generator": "nur_game.generate_wisp",
        "frame_size": list(FRAME_SIZE),
        "pivot": list(PIVOT),
        "mirrored_pivot": [width - 1 - PIVOT[0], PIVOT[1]],
        "facing": "right; mirror horizontally for left",
        "layout": "one horizontal row, frames left to right",
        "animations": {},
    }
    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.Font(None, 24)
    small = pygame.font.Font(None, 19)
    preview = pygame.Surface((width * FRAME_COUNT + 152, (height + 26) * len(ANIMATIONS)))
    preview.fill((24, 35, 43))
    for row, (pose, spec) in enumerate(ANIMATIONS.items()):
        filename = f"wisp_{pose}.png"
        sheet = pygame.Surface((width * FRAME_COUNT, height), pygame.SRCALPHA)
        frames = []
        y = row * (height + 26)
        preview.blit(font.render(pose.upper(), True, (207, 230, 210)), (16, y + 34))
        preview.blit(small.render(f"{spec.frames} frames / {spec.fps} fps", True, (146, 169, 162)), (16, y + 58))
        preview.blit(small.render("loop" if spec.loop else "takeoff > landing", True, (188, 160, 112)), (16, y + 80))
        for frame in range(spec.frames):
            image = wisp_sprite(pose, frame)
            sheet.blit(image, (frame * width, 0))
            frames.append([frame * width, 0, width, height])
            px = 152 + frame * width
            for ty in range(0, height, 13):
                for tx in range(0, width, 13):
                    value = 39 if (tx // 13 + ty // 13) % 2 else 44
                    pygame.draw.rect(preview, (value, value + 12, value + 19), (px + tx, y + ty, 13, 13))
            preview.blit(image, (px, y))
            preview.blit(small.render(f"{frame + 1:02d}", True, (171, 187, 178)), (px + 44, y + height + 5))
        pygame.image.save(sheet, str(output / filename))
        manifest["animations"][pose] = {
            "sheet": filename,
            "frame_count": spec.frames,
            "fps": spec.fps,
            "loop": spec.loop,
            "frame_rects": frames,
        }
    manifest["animations"]["jump"]["playback"] = "Frames follow vertical velocity from takeoff to descent; never loop in midair."
    pygame.image.save(preview, str(output / "preview.png"))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SPRITE_DIR)
    args = parser.parse_args(argv)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    export_wisp(args.output)
    print(f"Exported {len(ANIMATIONS)} sets / {FRAME_COUNT * len(ANIMATIONS)} frames to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
