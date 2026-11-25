"""F4 puzzle framework: components, registry, catalog and manager.

Public names stay at ``nur_game.puzzles.<name>``; the implementation is split
into :mod:`base`, :mod:`components`, :mod:`registry`, :mod:`catalog` and
:mod:`manager` so each concern can be changed independently.
"""

from .base import PuzzleComponent, PuzzleEvent
from .catalog import load_puzzle_catalog
from .components import (
    GateLock,
    ColorCycler,
    SigilDetector,
    SequenceMemory,
    PressurePlate,
    PatternMatch,
    WeightBalance,
    TimeEcho,
    ShadowAligner,
    TimingWindow,
    SoundTrigger,
    SoundMemory,
    MirrorReflector,
    LaserGrid,
    SymbolDecoder,
    RoomRotator,
    PerspectiveShift,
    FuelTrade,
    WaterLevel,
    WindCurrent,
    EnvironmentalCombo,
    MemoryPalace,
)
from .manager import GeneratedPuzzle, PuzzleManager
from .registry import COMPONENT_CLASSES, create_component

__all__ = [
    "COMPONENT_CLASSES",
    "ColorCycler",
    "EnvironmentalCombo",
    "FuelTrade",
    "GateLock",
    "GeneratedPuzzle",
    "LaserGrid",
    "MemoryPalace",
    "MirrorReflector",
    "PatternMatch",
    "PerspectiveShift",
    "PressurePlate",
    "PuzzleComponent",
    "PuzzleEvent",
    "PuzzleManager",
    "RoomRotator",
    "SequenceMemory",
    "ShadowAligner",
    "SigilDetector",
    "SoundMemory",
    "SoundTrigger",
    "SymbolDecoder",
    "TimeEcho",
    "TimingWindow",
    "WaterLevel",
    "WeightBalance",
    "WindCurrent",
    "create_component",
    "load_puzzle_catalog",
]
