"""Audio API: offline synthesis and the runtime Pygame player."""

from .player import Audio
from .synthesis import BEDS, GENERATED, RATE, ensure_generated

__all__ = ["Audio", "BEDS", "GENERATED", "RATE", "ensure_generated"]
