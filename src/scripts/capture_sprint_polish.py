"""Record revised scenery and walk/run/jump using inputs, without staging physics."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from nur_game.engine import DT
from nur_game import config
from nur_game.game import Game, _source_hashes
from nur_game.physics import NurInput
from scripts.playtest_nur import JourneyPilot


def main():
    output = config.ROOT / "docs" / "verification" / "nur" / "sprint-polish"
    output.mkdir(parents=True, exist_ok=True)
    images, records = [], []

    def capture(game, name):
        image = game.draw().copy()
        pygame.image.save(image, str(output / f"{name}.png"))
        images.append(image)
        records.append({"file": f"{name}.png", "simulation": game.snapshot()})

    for name, sprint in (("01-walk", False), ("02-run", True)):
        game = Game(muted=True, persist=False)
        try:
            for _ in range(72):
                game.update(DT, NurInput(move=1, sprint=sprint))
            capture(game, name)
        finally:
            game.audio.close()

    game = Game(muted=True, persist=False)
    try:
        for _ in range(36):
            game.update(DT, NurInput(move=1))
        game.update(DT, NurInput(move=1, jump=True))
        for _ in range(15):
            game.update(DT, NurInput(move=1))
        capture(game, "03-jump")
    finally:
        game.audio.close()

    for room, name, condition in (
        (1, "04-blade-platforms", lambda g: g.world.player.position.x > 730),
        (4, "05-garden", lambda g: g.world.quest.stage == 1),
        (10, "06-library", lambda g: g.world.quest.stage == 1),
        (16, "07-forest", lambda g: g.world.quest.stage == 1),
        (7, "08-phantom-climb", lambda g: g.world.quest.stage == 2),
        (4, "09-exhausted", lambda g: g.stamina.exhausted),
    ):
        game = Game(room=room, muted=True, persist=False)
        pilot = JourneyPilot(sprint=True)
        try:
            for _ in range(20000):
                game.update(DT, pilot.control(game))
                if game.world.dead:
                    raise RuntimeError(game.world.death_reason)
                if condition(game):
                    break
            else:
                raise RuntimeError(f"Capture stalled: {game.snapshot()}")
            capture(game, name)
        finally:
            game.audio.close()

    sheet = pygame.Surface((1440, 810))
    for index, image in enumerate(images):
        sheet.blit(pygame.transform.smoothscale(image, (480, 270)),
                   ((index % 3) * 480, (index // 3) * 270))
    pygame.image.save(sheet, str(output / "preview.png"))
    (output / "captures.json").write_text(json.dumps({
        "kind": "real movement, jump, Q, E and Shift inputs; no assigned positions, cameras or quest stages",
        "records": records, "sources": _source_hashes(),
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(images)} input-driven captures in {output}")
    pygame.quit()


if __name__ == "__main__":
    main()
