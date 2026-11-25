"""Deterministic state objects for the lantern, memories and narrative drift."""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field

from . import config
from .story import ANCHOR_LINES, INTRUSIONS


@dataclass
class Stamina:
    """Short sprint bursts; exhaustion must recover before another burst."""

    amount: float = 1.0
    recovery_delay: float = 0.0
    exhausted: bool = False

    def step(self, dt: float, requested: bool, moving: bool, eligible: bool = True) -> bool:
        running = bool(requested and eligible and self.amount > 0 and not self.exhausted)
        if running and moving:
            self.amount = max(0.0, self.amount - config.STAMINA_DRAIN * dt)
            self.recovery_delay = config.STAMINA_RECOVERY_DELAY
            if self.amount <= 1e-8:
                self.amount = 0.0
                self.exhausted = True
                running = False
        else:
            recovery_dt = max(0.0, dt - self.recovery_delay)
            self.recovery_delay = max(0.0, self.recovery_delay - dt)
            rate = config.STAMINA_WALK_RECOVERY if moving else config.STAMINA_IDLE_RECOVERY
            self.amount = min(1.0, self.amount + rate * recovery_dt)
            if self.amount >= config.STAMINA_RESTART:
                self.exhausted = False
        return running

    def snapshot(self) -> dict:
        return {"amount": round(self.amount, 6), "recovery_delay": round(self.recovery_delay, 6),
                "exhausted": self.exhausted}

    @classmethod
    def restore(cls, saved: dict) -> "Stamina":
        if not isinstance(saved, dict):
            raise ValueError("Invalid stamina checkpoint")
        amount = float(saved.get("amount", 1.0))
        delay = float(saved.get("recovery_delay", 0.0))
        exhausted = saved.get("exhausted", False)
        if (not math.isfinite(amount) or not math.isfinite(delay) or not 0 <= amount <= 1
                or not 0 <= delay <= config.STAMINA_RECOVERY_DELAY or not isinstance(exhausted, bool)):
            raise ValueError("Invalid stamina checkpoint")
        return cls(amount, delay, exhausted or amount == 0)


class Lantern:
    """A candle that only ever loses capacity.

    Collecting a fragment does not refill the candle. It permanently removes a
    quarter of what the flame could ever be: 100 -> 75 -> 50 -> 25 -> 0.
    Time drains the remaining charge linearly. The visual floor keeps the room
    readable; it is not a recharge.
    """

    def __init__(self) -> None:
        self.capacity = 1.0
        self.charge = 1.0
        self.collections = 0
        self.deaths = 0
        # Possession, not brightness, is the contract for monster protection.
        # Even the last ember wards off shadows; charge only limits visibility.
        self.carried = True

    @property
    def illumination(self) -> float:
        return max(0.0, min(1.0, self.charge))

    @property
    def radius(self) -> float:
        return 58.0 + 285.0 * self.illumination

    @property
    def protects(self) -> bool:
        return self.carried

    def step(self, dt: float) -> None:
        self.charge = max(0.0, self.charge - config.LIGHT_DECAY_PER_SECOND * dt)

    def collect_fragment(self) -> None:
        self.collections += 1
        self.capacity = max(0.0, self.capacity - config.LIGHT_STEP)
        self.charge = min(self.charge, self.capacity)

    def die(self) -> None:
        """Death costs charge, never capacity, so progress stays recoverable."""
        self.deaths += 1
        self.charge = max(0.0, self.charge - 0.08)

    def snapshot(self) -> dict:
        return {
            "capacity": round(self.capacity, 4),
            "charge": round(self.charge, 4),
            "collections": self.collections,
            "deaths": self.deaths,
            "carried": self.carried,
        }


class Memory:
    """Collected fragments plus the single item that can restore a false one."""

    def __init__(self) -> None:
        self.found: set[str] = set()
        self.false: set[str] = set()
        self.candles = 0
        self.truth = 0

    def add(self, key: str, false: bool = False) -> None:
        if key in self.found:
            return
        self.found.add(key)
        if false:
            self.false.add(key)

    def gain_candle(self) -> bool:
        if self.candles:
            return False
        self.candles += 1
        return True

    def restore(self) -> bool:
        """Spend the memory candle. It repairs meaning, never the flame."""
        if not self.candles or not self.false:
            return False
        key = sorted(self.false)[0]
        self.false.remove(key)
        self.truth += 1
        self.candles -= 1
        return True

    def coherent(self) -> bool:
        return bool(self.found) and not self.false

    def snapshot(self) -> dict:
        return {
            "found": sorted(self.found),
            "false": sorted(self.false),
            "candles": self.candles,
            "truth": self.truth,
        }


@dataclass
class Narrative:
    """Seeded caption director. Never uses the global ``random`` module."""

    seed: int
    rng: random.Random = field(init=False)
    elapsed: float = 0.0
    stage: int = 0
    cooldown: float = 4.0
    line: str = ""
    line_age: float = 0.0
    shown: tuple[str, ...] = ()
    anchor_index: int = 0

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)
        self.elapsed = 0.0
        self.stage = 0
        self.cooldown = 4.0
        self.line = ""
        self.line_age = 0.0
        self.shown = ()
        self.anchor_index = 0

    def _next_line(self) -> str:
        if self.anchor_index < len(ANCHOR_LINES):
            line = ANCHOR_LINES[self.anchor_index]
            self.anchor_index += 1
            return line
        pool = [line for line in INTRUSIONS if line not in self.shown[-4:]]
        if not pool:
            pool = list(INTRUSIONS)
        return self.rng.choice(pool)

    def update(self, dt: float, illumination: float, room: int, boss: bool = False,
               longform: bool = False) -> str | None:
        """Advance drift and return a new caption when one should appear."""
        self.elapsed += dt
        self.line_age += dt
        if boss:
            self.stage = 3
        elif illumination <= 0.25 or room >= config.BOSS_ARENA_ROOM:
            self.stage = 3
        elif illumination <= 0.5:
            self.stage = 2
        elif illumination <= 0.75:
            self.stage = 1
        else:
            self.stage = 0

        self.cooldown -= dt
        if self.cooldown > 0:
            return None
        self.line = self._next_line()
        self.shown = (*self.shown[-11:], self.line)
        self.line_age = 0.0
        self.cooldown = config.DIALOGUE_COOLDOWN[self.stage] + self.rng.uniform(-0.6, 1.1)
        if longform:
            self.cooldown *= 5
        return self.line

    def snapshot(self) -> dict:
        return {
            "elapsed": round(self.elapsed, 3),
            "anchor_index": self.anchor_index,
            "stage": self.stage,
            "line": self.line,
            "shown": list(self.shown),
        }
