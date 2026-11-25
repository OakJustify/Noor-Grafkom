"""Controller input snapshot and dynamic prop record."""

from __future__ import annotations

from dataclasses import dataclass

import pymunk

@dataclass(frozen=True)
class Input:
    move: float = 0
    jump: bool = False
    grab: bool = False
    action: bool = False
    climb: float = 0
    lantern: bool = False


@dataclass
class Prop:
    body: pymunk.Body
    shape: pymunk.Shape
    size: tuple[float, float]
    heavy: bool = False


