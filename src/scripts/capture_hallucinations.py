"""Capture perceptual puzzle states reached with real movement/Q/E inputs.

No player positions, camera values, solver settings or quest stages are assigned.
The two world layers are compared by actually pressing/releasing Q in place.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from nur_game.engine import DT
from nur_game import config
from nur_game.game import Game
from nur_game.physics import NurInput
from scripts.playtest_nur import JourneyPilot


def until(game, condition, control, limit=20000):
    for _ in range(limit):
        if condition(game):
            return
        game.update(DT, control(game))
        if game.world.dead:
            raise RuntimeError(game.world.death_reason)
    raise RuntimeError(f"Capture pilot stalled: {game.snapshot()}")


def shift(game):
    game.update(DT, NurInput(shift=True))
    game.update(DT, NurInput())


def main():
    output = config.ROOT / "docs" / "verification" / "nur" / "hallucinations"
    output.mkdir(parents=True, exist_ok=True)
    images, records = [], []

    def capture(game, name):
        image = game.draw().copy()
        pygame.image.save(image, str(output / f"{name}.png"))
        images.append(image)
        records.append({"file": f"{name}.png", "simulation": game.snapshot()})

    pilot = JourneyPilot()
    game = Game(room=4, muted=True, persist=False)
    try:
        target = game.world.quest.current.x
        until(game, lambda g: abs(g.world.player.position.x - target) < 5,
              lambda g: NurInput(move=1 if g.world.player.position.x < target else -1))
        capture(game, "01-source-nyata")
        shift(game)
        capture(game, "02-source-gaung")
        game.update(DT, NurInput(action=True))
        game.update(DT, NurInput())
        target = game.world.quest.current.x
        until(game, lambda g: abs(g.world.player.position.x - target) < 8 and abs(g.world.player.position.y - 430) < 20,
              lambda g: replace(pilot.control(g), shift=False, action=False))
        capture(game, "03-object-present")
        shift(game)
        capture(game, "04-object-gone")
    finally:
        game.audio.close()

    game = Game(room=5, muted=True, persist=False)
    try:
        until(game, lambda g: g.world.quest.stage == 1, pilot.control)
        target = game.world.quest.interaction_x
        until(game, lambda g: abs(g.world.player.position.x - target) < 8,
              lambda g: replace(pilot.control(g), action=False))
        capture(game, "05-parallax-aligned")
    finally:
        game.audio.close()

    game = Game(room=6, muted=True, persist=False)
    try:
        until(game, lambda g: g.world.quest.stage == 3, pilot.control)
        target = game.world.quest.current.x
        until(game, lambda g: abs(g.world.player.position.x - target) < 64,
              lambda g: replace(pilot.control(g), shift=False, action=False))
        capture(game, "06-witness-gaung")
        shift(game)
        capture(game, "07-witness-nyata")
    finally:
        game.audio.close()

    game = Game(room=7, muted=True, persist=False)
    try:
        until(game, lambda g: g.world.quest.stage == 1, pilot.control)
        target = game.world.quest.current.x - 210
        until(game, lambda g: abs(g.world.player.position.x - target) < 8,
              lambda g: replace(pilot.control(g), shift=False, action=False))
        capture(game, "08-phantom-stairs")
        until(game, lambda g: g.world.quest.stage == 2, pilot.control)
        capture(game, "09-phantom-summit")
    finally:
        game.audio.close()

    sheet = pygame.Surface((1440, 810))
    for index, image in enumerate(images):
        sheet.blit(pygame.transform.smoothscale(image, (480, 270)), ((index % 3) * 480, (index // 3) * 270))
    pygame.image.save(sheet, str(output / "preview.png"))
    (output / "captures.json").write_text(json.dumps({
        "kind": "actual movement/Q/E input captures; no staged positions or quest state",
        "records": records,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured {len(images)} actual puzzle states in {output}")
    pygame.quit()


if __name__ == "__main__":
    main()
