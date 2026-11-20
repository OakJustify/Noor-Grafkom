"""A deterministic test player. Uses only ordinary controls, never teleports."""

from .physics import Input, World
from .seesaw import SeesawPilot
from .magnet import MagnetPilot


class Pilot:
    def __init__(self, chapter: int):
        self.chapter = chapter
        self.phase = ("gate", "approach", "push", "approach", "first", "power")[chapter]
        self.seesaw = SeesawPilot() if chapter == 3 else None
        self.magnet = MagnetPilot() if chapter == 5 else None
        self.catch_distance = None

    def control(self, w: World) -> Input:
        x, _ = w.player.position
        move, jump, grab, action, climb = 1, False, False, False, 0
        if self.chapter == 0:
            jump = w.grounded and w.crates[0].body.position.x > 960 and x < 1070
        elif self.chapter == 1:
            tip = w.ropes[-1]
            if self.phase == "approach" and x > 570:
                self.phase = "wait"
            if self.phase == "wait":
                move = 0
                if tip.position.x < 775 and tip.velocity.x < 0:
                    self.phase = "catch"
                    jump = True
            if self.phase == "catch":
                move, grab = 1, True
                if w.grab_kind == "rope":
                    self.phase = "swing"
                    self.catch_distance = w.rope_distance
            if self.phase == "swing":
                grab = True
                climb = 1 if w.rope_distance > self.catch_distance - 45 else 0
                if x > 1020 and w.player.velocity.x > 0:
                    jump = True
                    self.phase = "land"
        elif self.chapter == 2:
            crate = w.crates[0].body
            if x > 340 and not w.cover_open:
                action = True
            if self.phase == "push" and crate.position.x > 545 and w.grounded:
                move, action, grab = 0, True, False
                self.phase = "board"
                jump = True
            if self.phase == "board":
                move = 1 if x < crate.position.x else 0
            if self.phase == "board" and w.support == crate:
                self.phase = "float"
            if self.phase == "float":
                # Ordinary movement balances on the box. There is no rowing.
                move = max(-0.2, min(0.2, (crate.position.x - x) * 0.02))
                if w.water_surface < 340 and w.grounded:
                    move, jump = 1, True
                    self.phase = "exit"
        elif self.chapter == 3:
            control = self.seesaw.control(w)
            self.phase = self.seesaw.phase
            return control
        elif self.chapter == 5:
            control = self.magnet.control(w)
            self.phase = self.magnet.phase
            return control
        elif self.chapter == 4:
            if self.phase == "first" and x > 325:
                action = True
                self.phase = "rise"
            if self.phase == "rise" and w.grounded and w.gravity == -1:
                self.phase = "ceiling"
            if self.phase == "ceiling" and x > 1030:
                move = 0
                if w.gravity == 1:
                    self.phase = "exit"
            if self.phase == "rise":
                move = 0
        return Input(move, jump, grab, action, climb)
