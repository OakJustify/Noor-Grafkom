"""Population & Territory Manager

Tracks creature populations, carrying capacities, and spatial territories
per stage/biome across the game world.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
import random
from typing import Dict, List, Tuple

from .archetype_definition import ArchetypeType, SocialStructure, PopulationParams


@dataclass
class TerritoryZone:
    """Territory zone for a group or solitary creature."""
    zone_id: str
    center: tuple[float, float]
    radius: float
    owner_id: str
    archetype: ArchetypeType
    capacity: int
    current_occupants: list[str] = field(default_factory=list)

    def is_inside(self, pos: tuple[float, float]) -> bool:
        dx = pos[0] - self.center[0]
        dy = pos[1] - self.center[1]
        return (dx * dx + dy * dy) <= (self.radius * self.radius)


class PopulationManager:
    """Manages population counts and territory allocations for procedural creatures."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.territories: dict[str, TerritoryZone] = {}
        self.stage_population_limits: dict[int, int] = {
            1: 8,    # Max total creatures in Stage 1
            2: 14,   # Max total creatures in Stage 2
            3: 20,   # Max total creatures in Stage 3
            4: 12    # Stage 4: corrupted climax
        }

    def can_spawn_creature(
        self,
        archetype: ArchetypeType,
        stage: int,
        current_active_count: int,
        pop_params: PopulationParams
    ) -> bool:
        """Check if population limits allow spawning another creature of this archetype."""
        max_stage_limit = self.stage_population_limits.get(stage, 15)
        if current_active_count >= max_stage_limit:
            return False

        # Check carrying capacity per archetype
        archetype_active = sum(1 for t in self.territories.values() if t.archetype == archetype for _ in t.current_occupants)
        return archetype_active < pop_params.carrying_capacity

    def allocate_territory(
        self,
        creature_id: str,
        archetype: ArchetypeType,
        spawn_pos: tuple[float, float],
        pop_params: PopulationParams
    ) -> TerritoryZone:
        """Allocate or assign creature to a territory zone."""
        # Look for existing territory with space
        for zone in self.territories.values():
            if zone.archetype == archetype and len(zone.current_occupants) < zone.capacity:
                if zone.is_inside(spawn_pos):
                    zone.current_occupants.append(creature_id)
                    return zone

        # Create new territory
        zone_id = f"zone_{archetype.value}_{len(self.territories)}"
        new_zone = TerritoryZone(
            zone_id=zone_id,
            center=spawn_pos,
            radius=pop_params.territory_size,
            owner_id=creature_id,
            archetype=archetype,
            capacity=pop_params.carrying_capacity,
            current_occupants=[creature_id]
        )
        self.territories[zone_id] = new_zone
        return new_zone

    def remove_creature(self, creature_id: str):
        """Remove creature from its territory upon despawn/death."""
        for zone in self.territories.values():
            if creature_id in zone.current_occupants:
                zone.current_occupants.remove(creature_id)
