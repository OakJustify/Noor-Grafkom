"""NÜR-specific fairness rules; the shared ECHO simulation stays unchanged."""

from echo_game.physics import DT, Input, World
from . import config


class NurWorld(World):
    quest = None

    def _gate(self, dt):
        if self.quest is None:
            return super()._gate(dt)
        self.gate_open = self.quest.complete
        target = float(self.gate_open)
        delta = max(-dt * 1.4, min(dt * 1.4, target - self.gate_fraction))
        self.gate_fraction += delta
        self.gate_body.velocity = (0, -delta * (self.level.gate.h + 20) / dt)

    def step(self, control: Input = Input(), dt: float = DT):
        super().step(control, dt)
        if self.quest is not None and not self.quest.complete:
            self.complete = False
            self.events = [event for event in self.events if event != "checkpoint"]
        # The final room ends through mercy, not the campaign's x-coordinate
        # trigger. Reaching the far wall must never freeze an unfinished boss.
        if self.chapter == config.BOSS_ARENA_ROOM and self.complete:
            self.complete = False
            self.events = [event for event in self.events if event != "checkpoint"]

    def kill(self, reason: str) -> None:
        # A closed door is a puzzle boundary, not a contact-damage enemy.
        # Its existing solid Pymunk shape still prevents walking through it.
        if reason == "Keep a weight on the plate.":
            return
        super().kill(reason)
