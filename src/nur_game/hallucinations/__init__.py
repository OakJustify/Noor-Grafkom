"""Perception-puzzle API: projection geometry and playable states."""

from .projection import FAMILIES, OFFSETS, PLANES, draw_projection, hypercube_projection
from .state import HallucinationPlan, HallucinationState

__all__ = [
    "FAMILIES", "OFFSETS", "PLANES", "HallucinationPlan", "HallucinationState",
    "draw_projection", "hypercube_projection",
]
