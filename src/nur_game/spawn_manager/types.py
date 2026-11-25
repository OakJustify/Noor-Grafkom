"""Data-oriented monster spawning, caps and pooling (Python v4 adaptation of F2)."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PiecewiseCurve:
    """Small AnimationCurve equivalent: sorted (x, y) points, linear between."""

    points: tuple[tuple[float, float], ...]

    def evaluate(self, x: float) -> float:
        if not self.points:
            return 0.0
        value = max(self.points[0][0], min(self.points[-1][0], float(x)))
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if value <= x1:
                if x1 == x0:
                    return y1
                t = (value - x0) / (x1 - x0)
                return y0 + (y1 - y0) * t
        return self.points[-1][1]


@dataclass(frozen=True)
class MonsterType:
    type_id: str
    variants: tuple[str, ...]
    base_weight: float = 1.0
    unlock_level: int = 0


@dataclass(frozen=True)
class MonsterLibrary:
    types: tuple[MonsterType, ...]


@dataclass
class SpawnedMonster:
    type_id: str
    variant: str
    kind: int
    x: float
    y: float
    active: bool = True

    def reset(self, x: float, y: float, variant: str) -> None:
        self.x, self.y, self.variant = x, y, variant
        self.active = True


@dataclass
class SpawnStats:
    spawned_total: int = 0
    attempts: int = 0
    rejected: int = 0
    cap_skips: int = 0
    active: int = 0
    alive_by_type: dict[str, int] = field(default_factory=dict)

def library_from_specs(entries: Iterable[dict]) -> MonsterLibrary:
    """Build a library from JSON-shaped entries (O3/F2 integration point)."""
    return MonsterLibrary(tuple(
        MonsterType(str(entry["typeId"]), tuple(entry.get("variants", ())),
                    float(entry.get("baseWeight", 1.0)), int(entry.get("unlockLevel", 0)))
        for entry in entries))
