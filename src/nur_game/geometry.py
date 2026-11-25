"""NUR's level geometry. No separate game or campaign dependency."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, x, y):
        return self.x <= x <= self.x + self.w and self.y <= y <= self.y + self.h


@dataclass(frozen=True)
class Level:
    title: str
    subtitle: str
    hint: str
    width: int
    spawn: tuple
    exit: tuple
    terrain: tuple
    crates: tuple = ()
    gate: Rect | None = None
    plate: Rect | None = None
    rope: tuple | None = None
    water: Rect | None = None
    water_raise: float = 0
    water_rate: float = 0
    valve: tuple | None = None
    cover: Rect | None = None
    cover_switch: tuple | None = None
    switches: tuple = ()
    gravity_duration: float = 0
    saws: tuple = ()
