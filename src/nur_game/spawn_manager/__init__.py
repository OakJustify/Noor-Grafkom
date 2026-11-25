"""Monster spawn API: data records/curves and the deterministic manager."""

from .manager import MonsterSpawnManager
from .types import (
    MonsterLibrary, MonsterType, PiecewiseCurve,
    SpawnedMonster, SpawnStats, library_from_specs,
)

__all__ = [
    "MonsterLibrary", "MonsterSpawnManager", "MonsterType", "PiecewiseCurve",
    "SpawnedMonster", "SpawnStats", "library_from_specs",
]
