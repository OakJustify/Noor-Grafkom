"""Playable impossible-space puzzles: reveal, remember, align and stabilise."""

from __future__ import annotations

import itertools
import math
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

import pygame

from ..geometry import Rect
from .. import config
from ..quests import QuestPlan, QuestState
from ..wisp import PIVOT, facing_sprite
from ..materials import phantom_sprite


FAMILIES = frozenset({"absence", "parallax", "witness", "fold"})
PLANES = ("NYATA", "GAUNG")
OFFSETS = (-44, 0, 44)


@dataclass(frozen=True)
class HallucinationPlan(QuestPlan):
    dimension: int = 4
    platforms: tuple[Rect, ...] = ()


@lru_cache(maxsize=128)
def hypercube_projection(dimension: int, frame: int):
    if dimension not in (3, 4, 5):
        raise ValueError("Only 3D, 4D and 5D projections are authored")
    vertices = list(itertools.product((-1.0, 1.0), repeat=dimension))
    projected = []
    angle = frame * math.tau / 64
    for vertex in vertices:
        point = list(vertex)
        for a, b, speed in ((0, dimension - 1, 1), (1, 2, 0.7)):
            c, s = math.cos(angle * speed), math.sin(angle * speed)
            point[a], point[b] = point[a] * c - point[b] * s, point[a] * s + point[b] * c
        for axis in range(dimension - 1, 1, -1):
            factor = 3.8 / (3.8 - point[axis])
            point[:axis] = [value * factor for value in point[:axis]]
        projected.append((point[0] * 0.42, point[1] * 0.42))
    edges = tuple((index, index ^ (1 << bit)) for index in range(len(vertices))
                  for bit in range(dimension) if index < index ^ (1 << bit))
    return tuple(projected), edges


def draw_projection(screen, centre, dimension, frame, colour, radius=35):
    vertices, edges = hypercube_projection(dimension, frame % 64)
    points = [(centre[0] + x * radius, centre[1] + y * radius) for x, y in vertices]
    for a, b in edges:
        pygame.draw.aaline(screen, colour, points[a], points[b])


