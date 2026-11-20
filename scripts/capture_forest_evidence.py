"""Capture reproducible evidence for the procedural monochrome forest.

Run from the project root:

    TMPDIR=/tmp/opencode .venv-echo/bin/python -m scripts.capture_forest_evidence

The script uses the real application, real `EndlessPilot` input and real seeded
generation. Challenge/hazard frames move the camera/player only for inspection;
no collision or generation state is fabricated.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from echo_game.forest import GROUND_LINE
from echo_game.game import Game, SIZE
from echo_game.procedural import EndlessPilot, GenerationConfig


CAPTURE_FRAMES = (150, 400, 900)
INSPECTION_CONFIG = GenerationConfig(environment_density=2, obstacle_density=3,
                                     puzzle_density=3)


def _save(game, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(game.canvas, path)


def _stage(game, platform, player_x):
    """Align a platform under the camera and place the courier on its surface."""
    game.camera = platform.x - 60
    game.forest_ground = platform.y
    game.camera_y = platform.y - SIZE[1] * GROUND_LINE / game.forest.zoom
    game.world.player.position = (player_x, platform.y - 28)
    game.world.facing = 1
    game.visual_time = 3.0
    game.draw()


def _record(game, seed, frame):
    return {"seed": seed, "frame": frame, "distance": round(game.world.distance, 2),
            "difficulty": round(game.world.difficulty, 2),
            "camera": [round(game.camera, 2), round(game.camera_y, 2)],
            "presentation": game.forest.snapshot()}


def _play_seed(output, seed, last_frame, targets):
    game = Game(muted=True, persist=False)
    game.start_endless(seed)
    pilot = EndlessPilot()
    started = time.perf_counter()
    records = []
    try:
        for frame in range(1, last_frame + 1):
            game.update(1 / 60, pilot.control(game.world))
            game.draw()
            if frame in targets:
                _save(game, output / f"seed-{seed}-frame-{frame}.png")
                records.append(_record(game, seed, frame))
    finally:
        game.close()
    return records, time.perf_counter() - started


def _challenge_capture(output):
    game = Game(muted=True, persist=False, endless_config=INSPECTION_CONFIG)
    game.start_endless(11)
    try:
        challenge = game.world.challenges[0]
        platform = next(p for p in game.world.generated_platforms
                        if p.id == challenge.platform_id)
        _stage(game, platform, platform.x + platform.width * .55)
        _save(game, output / "challenge-light-gate.png")
        return {"kind": challenge.kind, "platform": challenge.platform_id,
                "x": round(platform.x, 2), "y": round(platform.y, 2)}
    finally:
        game.close()


def _hazard_capture(output):
    game = Game(muted=True, persist=False, endless_config=INSPECTION_CONFIG)
    game.start_endless(11)
    pilot = EndlessPilot()
    try:
        hazard = None
        for frame in range(1, 7000):
            game.update(1 / 60, pilot.control(game.world))
            if (game.world.generated_hazards
                    and game.world.generated_hazards[-1].x > game.camera + 150):
                hazard = game.world.generated_hazards[-1]
                break
        if hazard is None:
            raise RuntimeError("no saw hazard reached the inspection window")
        platform = min(game.world.generated_platforms,
                       key=lambda p: abs(p.x + p.width / 2 - hazard.x))
        game.endless_hud = False
        _stage(game, platform, min(platform.x + platform.width - 30,
                                   max(platform.x + 30, hazard.x - 40)))
        _save(game, output / "hazard-saw.png")
        game.endless_hud = True
        game.draw()
        _save(game, output / "hud-on.png")
        # With the overlay off, damaged health/low lantern must reveal status.
        game.endless_hud = False
        game.world.health = max(1, game.world.max_health - 1)
        game.world.lantern_energy = .12
        game.draw()
        _save(game, output / "warning-auto.png")
        return {"id": hazard.id, "frame": frame, "x": round(hazard.x, 2),
                "y": round(hazard.y, 2), "distance": round(game.world.distance, 2)}
    finally:
        game.close()


def _contact_sheet(output, names):
    pygame.font.init()
    font = pygame.font.Font(None, 22)
    cell_w, cell_h, gap, caption = 480, 270, 16, 24
    columns = 3
    rows = (len(names) + columns - 1) // columns
    sheet = pygame.Surface((gap + columns * (cell_w + gap),
                            gap + rows * (cell_h + caption + gap)))
    sheet.fill((11, 11, 11))
    for index, (name, label) in enumerate(names):
        image = pygame.image.load(output / name)
        image = pygame.transform.smoothscale(image, (cell_w, cell_h))
        x = gap + (index % columns) * (cell_w + gap)
        y = gap + (index // columns) * (cell_h + caption + gap)
        sheet.blit(image, (x, y))
        sheet.blit(font.render(label, True, (185, 185, 185)), (x, y + cell_h + 4))
    _save_surface(sheet, output / "contact-sheet.png")


def _save_surface(surface, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path("docs/echo/verification/generation-repair/forest"))
    args = parser.parse_args()
    pygame.display.set_mode(SIZE)
    started = time.perf_counter()

    records = []
    seed_timings = {}
    for seed, last_frame in ((7, 900), (11, 400), (23, 400)):
        seed_records, elapsed = _play_seed(args.output, seed, last_frame, CAPTURE_FRAMES)
        records.extend(seed_records)
        seed_timings[str(seed)] = round(elapsed, 3)
    challenge = _challenge_capture(args.output)
    hazard = _hazard_capture(args.output)

    _contact_sheet(args.output, [
        ("seed-7-frame-150.png", "seed 7 · frame 150"),
        ("seed-7-frame-400.png", "seed 7 · frame 400"),
        ("seed-7-frame-900.png", "seed 7 · frame 900"),
        ("seed-11-frame-400.png", "seed 11 · frame 400"),
        ("seed-23-frame-400.png", "seed 23 · frame 400"),
        ("challenge-light-gate.png", "light-gate challenge"),
        ("hazard-saw.png", "saw hazard"),
        ("hud-on.png", "F1 status overlay"),
        ("warning-auto.png", "automatic low-resource warning"),
    ])
    summary = {
        "style": "monochrome_forest",
        "captures": records,
        "seed_wall_seconds": seed_timings,
        "challenge": challenge,
        "hazard": hazard,
        "total_wall_seconds": round(time.perf_counter() - started, 3),
    }
    (args.output / "capture.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
