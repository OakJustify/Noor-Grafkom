"""Staged artwork preview for the live v4 renderer; not gameplay/traversal evidence.

Run from v4 with PYTHONPATH=. .venv-nur/bin/python scripts/capture_nur_polish.py.
Actual-input evidence lives in docs/verification/captures and the input campaigns.
"""

from __future__ import annotations

import json
import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from nur_game import config
from nur_game.continuum import REGIONS
from nur_game.game import Game


def main():
    output = config.ROOT / "docs" / "verification" / "nur"
    output.mkdir(parents=True, exist_ok=True)
    sheet = pygame.Surface((1440, 540))
    game = Game(muted=True, persist=False)
    previews = (
        (0, 0, (130, 435), 1.0),
        (1, 550, (820, 334), 0.72),
        (2, 550, (1000, 435), 0.48),
        (3, 520, (700, 376), 0.23),
        (config.BOSS_ARENA_ROOM, 600, (1000, 435), 0.0),
    )
    samples = []
    try:
        for index, (room, local_camera, local_position, charge) in enumerate(previews):
            game.start(room)
            offset = REGIONS[room].start
            position = (offset + local_position[0], local_position[1])
            game.world.player.position = position
            game.camera = offset + local_camera
            game.lantern.charge = charge
            game.visual_time = 3
            game.threats.update(0.1, position, game.lantern, game.light_origin,
                                elapsed=charge * 200)
            if room == 2:
                game.memory.add("key", false=True)
            canvas = game.draw()
            thumb = pygame.transform.smoothscale(canvas, (480, 270))
            sheet.blit(thumb, ((index % 3) * 480, (index // 3) * 270))
            samples.append({"room": room + 1, "charge": charge,
                            "camera": round(game.camera, 2)})
        game.start(0)
        game.state = "menu"
        sheet.blit(pygame.transform.smoothscale(game.draw(), (480, 270)), (960, 270))
        pygame.image.save(sheet, str(output / "polish.png"))
        game.state = "playing"
        for _ in range(8):
            game.draw()
        start = time.perf_counter()
        for _ in range(120):
            game.draw()
        draw_ms = (time.perf_counter() - start) * 1000 / 120
        (output / "render.json").write_text(json.dumps({
            "kind": "staged v4 artwork preview; not traversal evidence",
            "samples": samples,
            "warmed_home_draw_ms": round(draw_ms, 3),
            "timing_scope": "headless rendering only; excludes window, input and simulation",
        }, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {output / 'polish.png'}; warmed home draw {draw_ms:.2f} ms")
    finally:
        game.audio.close()
        pygame.quit()


if __name__ == "__main__":
    main()
