"""Registry of implemented components and the factory used by the manager."""

from __future__ import annotations

from typing import Any

from .base import PuzzleComponent
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


COMPONENT_CLASSES: dict[str, type[PuzzleComponent]] = {
    "ColorCycler": ColorCycler,
    "SigilDetector": SigilDetector,
    "GateLock": GateLock,
    "SequenceMemory": SequenceMemory,
    "PressurePlate": PressurePlate,
    "PatternMatch": PatternMatch,
    "WeightBalance": WeightBalance,
    "TimeEcho": TimeEcho,
    "ShadowAligner": ShadowAligner,
    "TimingWindow": TimingWindow,
    "SoundTrigger": SoundTrigger,
    "SoundMemory": SoundMemory,
    "MirrorReflector": MirrorReflector,
    "LaserGrid": LaserGrid,
    "SymbolDecoder": SymbolDecoder,
    "RoomRotator": RoomRotator,
    "PerspectiveShift": PerspectiveShift,
    "FuelTrade": FuelTrade,
    "WaterLevel": WaterLevel,
    "WindCurrent": WindCurrent,
    "EnvironmentalCombo": EnvironmentalCombo,
    "MemoryPalace": MemoryPalace,
}


def create_component(name: str, params: dict[str, Any] | None = None, component_id: str | None = None) -> PuzzleComponent:
    cls = COMPONENT_CLASSES.get(name)
    if cls is None:
        raise ValueError(f"unknown puzzle component: {name}")
    return cls(component_id=component_id, params=params or {})
