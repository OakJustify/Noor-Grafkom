"""Hand-authored, original puzzle rooms; coordinates use pixels, Y points down."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.w and self.y <= y <= self.y + self.h


@dataclass(frozen=True)
class MagneticPuzzle:
    """Guided iron blocks with separate ceiling power and box-field controls."""

    ceilings: tuple[float, ...]
    magnet_switch: tuple[float, float]
    gravity_switch: tuple[float, float]
    floor_y: float
    crate_indices: tuple[int, ...] = (0, 1)


@dataclass(frozen=True)
class Level:
    title: str
    subtitle: str
    hint: str
    width: int
    spawn: tuple[float, float]
    exit: tuple[float, float]
    terrain: tuple[Rect, ...]
    crates: tuple[tuple[float, float, int, float], ...] = ()
    gate: Rect | None = None
    plate: Rect | None = None
    rope: tuple[float, float, int, float] | None = None
    water: Rect | None = None
    water_raise: float = 0
    water_rate: float = 0
    valve: tuple[float, float] | None = None
    cover: Rect | None = None
    cover_switch: tuple[float, float] | None = None
    seesaw: tuple[float, float, float] | None = None
    switches: tuple[tuple[float, float], ...] = ()
    gravity_duration: float = 0
    saws: tuple[tuple[float, float, float, float, float], ...] = ()
    magnet: MagneticPuzzle | None = None


LEVELS = (
    Level(
        "01 / THE WEIGHT OF SILENCE", "Leave something behind to open the way.",
        "Hold E beside the crate to pull it. Leave it on the pressure plate.",
        1600, (140, 430), (1510, 430), (Rect(-80, 460, 1760, 160),),
        crates=((470, 431, 54, 6),), gate=Rect(1170, 260, 28, 200),
        plate=Rect(940, 451, 190, 9),
    ),
    Level(
        "02 / A THREAD ACROSS THE DARK", "Momentum is a bridge you cannot see.",
        "Hold E to catch it. Climb a little with W; swing right, then Space to the high ledge.",
        1700, (150, 430), (1580, 210),
        (Rect(-80, 460, 680, 160), Rect(1090, 240, 690, 400)),
        rope=(840, 100, 12, 28),
    ),
    Level(
        "03 / WHAT THE WATER CARRIES", "The flood remembers every footstep.",
        "E at the cover handle opens the gap. Push the box in; E at the valve raises the water.",
        1450, (140, 430), (1330, 270),
        (Rect(-80, 460, 580, 180), Rect(780, 300, 750, 340), Rect(500, 610, 280, 60)),
        crates=((420, 421, 72, 5),), water=Rect(500, 500, 280, 110),
        water_raise=170, water_rate=20, valve=(470, 425),
        cover=Rect(500, 340, 280, 16), cover_switch=(375, 425),
    ),
    Level(
        "04 / THE RETURNING TIDE", "A small life can move a heavy world.",
        "Run and jump between the ends to build motion. Leap right when the far end is highest.",
        1700, (140, 380), (1580, 270),
        (Rect(-80, 420, 695, 220), Rect(1090, 300, 690, 340)),
        seesaw=(840, 440, 440),
    ),
    Level(
        "05 / THE HOLLOW SIGNAL", "Turn the world over. Bring the light home.",
        "Tap E to invert gravity briefly. Cross above the saw; wait before the ceiling blade.",
        1650, (140, 430), (1530, 430),
        (Rect(-80, 460, 1810, 180), Rect(300, 110, 1180, 35)),
        crates=((440, 430, 54, 6),),
        switches=((350, 426),), gravity_duration=5,
        saws=((760, 427, 31, 190, 0.85), (1170, 158, 34, 0, 0)),
    ),
    Level(
        "06 / WHAT THE CEILING KEEPS", "One must stay. One must return.",
        "Power the magnet. Lift the blocks; reverse their gravity as the first catches. Use the low block to climb out.",
        1560, (140, 430), (1460, 290),
        (Rect(-80, 460, 1130, 180), Rect(1050, 320, 590, 320)),
        crates=((720, 383, 150, 36), (940, 418, 80, 20)),
        magnet=MagneticPuzzle((230, 140), (345, 426), (465, 426), 460),
    ),
)
