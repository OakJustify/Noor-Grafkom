"""Input-only campaign playtest, reporting game time rather than execution time."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from echo_game.physics import DT, Input
import pygame
from nur_game.game import Game


class SlicePilot:
    def __init__(self):
        self.room = -1
        self.mode = "approach"

    def control(self, game):
        if self.room != game.room:
            self.room, self.mode = game.room, "approach"
        x, y = game.world.player.position
        jump, grab = False, False
        if game.room == 0:
            jump = 400 < x < 980
        elif game.room == 1:
            jump = 520 < x < 900 or 1030 < x < 1410
        elif game.room == 2:
            jump = game.world.crates[0].body.position.x > 925 and x < 1060
            jump = jump or 1130 < x < 1450
        elif game.room == 3:
            if self.mode == "approach":
                jump, grab = 550 < x < 557, x > 675
                if game.world.grab_kind == "rope":
                    self.mode = "swing"
                elif x > 733 and game.world.grounded:
                    self.mode = "launch"
            if self.mode == "launch":
                jump, grab, self.mode = True, False, "swing"
            elif self.mode == "swing":
                jump, grab = False, True
                if game.world.grab_kind == "rope" and x > 925:
                    jump, grab, self.mode = True, False, "released"
            elif self.mode == "released":
                jump = 1110 < x < 1410
        else:
            if game.boss is None:
                return JourneyPilot.control(self, game)
            if game.boss.phase == 0:
                jump = 190 < x < 500 or 1020 < x < 1130
            elif game.boss.phase == 1:
                return Input(move=-1 if x > 1090 else 1 if x < 1070 else 0, action=True)
            else:
                return Input()
        return Input(move=1, jump=jump, grab=grab)


class JourneyPilot(SlicePilot):
    """Known-solution navigation; never edits position, quest state or physics."""

    def control(self, game):
        quest = game.world.quest
        if quest is None:
            return super().control(game)
        world = game.world
        x, y = world.player.position
        node = quest.current
        target = world.level.exit[0] + 25 if node is None else node.x
        if node and node.kind in ("circuit", "valve"):
            different = quest.values[quest.plan.order[quest.stage]] ^ node.target
            bit = next((bit for bit in range(3) if different & (1 << bit)), 1)
            target += (bit - 1) * 42
        elif node and node.kind == "match":
            target += (node.target - 1.5) * 32
        elif node and node.kind == "melody":
            target += (node.pattern[quest.values[quest.plan.order[quest.stage]]] - 1.5) * 32
        crate = None
        if node and node.kind == "weight":
            crate = world.crates[quest.plan.order[quest.stage] - 3].body
            if crate.position.x < node.plate[0] + 35 and abs(crate.position.x - x) < 115:
                return Input(move=1, grab=True)
            if crate.position.x < node.plate[0] + 35:
                target = crate.position.x - 38
        move = 1 if target - x > 5 else -1 if target - x < -5 else 0
        jump = False
        if move:
            for rect in world.level.terrain[1:]:
                edge = rect.x if move > 0 else rect.x + rect.w
                distance = (edge - x) * move
                if -12 < distance < 68 and rect.y < y + 24:
                    jump = True
            if crate and crate.position.x >= node.plate[0] + 35 and abs(x - crate.position.x) < 95:
                jump = True
        close = node is not None and abs(x - target) < 10 and abs(y - node.y) < 60
        # Every E press is released before the next press, just like a keyboard.
        return Input(move=move, jump=jump, action=bool(close and not quest.pressed))


def run_playtest(output: Path, max_seconds=1800, pilot=None, captures: Path | None = None):
    game = Game(muted=True, persist=False)
    pilot = pilot or JourneyPilot()
    elapsed = moving = 0.0
    room_start = 0.0
    previous_room = game.room
    records = []
    distance = 0.0
    solved = 0
    previous_x = game.world.player.position.x
    stall_anchor = (game.room, round(previous_x / 5), 0)
    stall_seconds = 0.0
    wall_start = time.perf_counter()
    error = None
    capture_points = {(4, 1), (5, 2), (6, 4), (7, 2), (10, 1), (14, 4), (23, 2)}
    images = []
    capture_records = []
    if captures:
        captures.mkdir(parents=True, exist_ok=True)
    try:
        for _ in range(int(max_seconds / DT)):
            control = pilot.control(game)
            previous_stage = game.world.quest.stage if game.world.quest else 0
            game.update(DT, control)
            elapsed += DT
            if control.move or control.grab or control.action or control.jump:
                moving += DT
            if game.world.dead:
                error = game.world.death_reason
                break
            key = (game.room, game.world.quest.stage if game.world.quest else -1)
            if captures and key in capture_points:
                filename = f"chapter-{game.room + 1:02d}.png"
                image = game.draw().copy()
                pygame.image.save(image, str(captures / filename))
                images.append(image)
                capture_records.append({"file": filename, "gameplay_seconds": round(elapsed, 3), "room": game.room + 1})
                capture_points.remove(key)
                if game.room == 23:
                    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
                    image = game.draw().copy()
                    pygame.image.save(image, str(captures / "journal.png"))
                    images.append(image)
                    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
            if game.room == previous_room:
                distance += abs(game.world.player.position.x - previous_x)
                if game.world.quest:
                    solved += max(0, game.world.quest.stage - previous_stage)
            previous_x = game.world.player.position.x
            anchor = (game.room, round(previous_x / 5), game.world.quest.stage if game.world.quest else 0)
            stall_seconds = stall_seconds + DT if anchor == stall_anchor else 0.0
            stall_anchor = anchor
            if stall_seconds > 10 and game.state == "playing" and game.boss is None:
                error = "Pilot stalled for 10 seconds without position or puzzle progress; not counted as content."
                break
            if game.room != previous_room or game.state == "ending":
                records.append({"room": previous_room + 1, "seconds": round(elapsed - room_start, 3)})
                previous_room, room_start = game.room, elapsed
            if game.state == "ending":
                break
        if captures:
            if game.state == "ending":
                images.append(game.draw().copy())
            sheet = pygame.Surface((1440, 810))
            sheet.fill((16, 30, 40))
            for index, image in enumerate(images[:9]):
                sheet.blit(pygame.transform.smoothscale(image, (480, 270)), ((index % 3) * 480, (index // 3) * 270))
            pygame.image.save(sheet, str(captures / "journey.png"))
        payload = {
            "kind": "accelerated input-only live Pymunk playtest, not human wall-clock play",
            "completed": game.state == "ending",
            "gameplay_seconds": round(elapsed, 3),
            "active_input_seconds": round(moving, 3),
            "distance_pixels": round(distance, 1),
            "quest_steps_solved": solved,
            "waiting_policy": "no reading delays, no idle padding; known solutions and maximum normal speed",
            "execution_seconds": round(time.perf_counter() - wall_start, 3),
            "error": error,
            "rooms": records,
            "captures": capture_records,
            "simulation": game.snapshot(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({key: payload[key] for key in ("completed", "gameplay_seconds", "active_input_seconds", "execution_seconds", "error")}))
        return payload
    finally:
        game.audio.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/nur/verification/playtest.json"))
    parser.add_argument("--captures", type=Path, help="Save screenshots from the actual input-only run")
    args = parser.parse_args()
    return 0 if run_playtest(args.output, captures=args.captures)["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
