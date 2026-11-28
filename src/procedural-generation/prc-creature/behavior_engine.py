"""Behavior state machine and drive-based utility AI.

Integrates with prc-creature ArchetypeDef and SanityModifiers.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any
import math
import random

from .archetype_definition import ArchetypeType, SocialStructure, ActivityCycle, SanityModifiers


class CreatureState(str, Enum):
    IDLE = "idle"
    PATROL = "patrol"
    STALK = "stalk"
    CHASE = "chase"
    ATTACK = "attack"
    FEED = "feed"
    REST = "rest"
    FLEE = "flee"
    HIDE = "hide"
    HERD = "herd"
    SCAVENGE = "scavenge"
    HOARD = "hoard"
    INVESTIGATE = "investigate"
    FOLLOW = "follow"
    PLAY = "play"
    MIMIC = "mimic"
    ATTACH = "attach"
    DRAIN = "drain"
    PROTECT = "protect"
    JUDGE = "judge"
    CAMOUFLAGE = "camouflage"
    STRIKE = "strike"
    RELOCATE = "relocate"
    CORRUPT = "corrupt"
    VOID_WALK = "void_walk"
    SCRIPTED_SEQUENCE = "scripted_sequence"
    # Additional states referenced in archetype JSON
    THREATEN = "threaten"
    RETURN = "return"
    MARK = "mark"
    LAY_EGGS = "lay_eggs"
    APPROACH = "approach"
    SING = "sing"
    ASCEND = "ascend"
    INTERCEPT = "intercept"
    SHIELD = "shield"
    CALL = "call"
    RALLY = "rally"
    MERGE = "merge"
    WAIT = "wait"
    LURE = "lure"
    HUNT = "hunt"
    SPREAD = "spread"
    STEAL = "steal"
    DETACH = "detach"
    RETREAT = "retreat"
    HEAL = "heal"
    GUIDE = "guide"


@dataclass
class EnvironmentalContext:
    """Context passed to utility evaluation on each update frame."""
    dt: float
    time_of_day: float                  # 0.0 to 1.0 (0=midnight, 0.5=noon)
    player_pos: tuple[float, float]
    player_distance: float
    player_sanity: float                # 0 to 100
    player_moving: bool
    player_crouching: bool
    nearby_creatures: list[dict]        # [{pos, archetype, state, distance}]
    nearby_fragments: list[dict]        # [{pos, type, distance}]
    territory_center: tuple[float, float]
    current_sanity_stage: int           # 1 to 4
    world_sanity: float                 # 0 to 100 global level


@dataclass
class BehaviorDrive:
    """A single internal drive (hunger, fear, curiosity, territory, dominance)."""
    name: str
    value: float = 0.0               # 0.0 to 1.0
    decay_rate: float = 0.01          # Increase per second
    satisfaction_rate: float = 0.1    # Decrease per second when acting
    weight: float = 1.0               # Multiplier for utility calculation

    def update(self, dt: float, acting: bool):
        if acting:
            self.value = max(0.0, self.value - self.satisfaction_rate * dt)
        else:
            self.value = min(1.0, self.value + self.decay_rate * dt)


class BehaviorStateMachine:
    """State machine for a single procedural creature instance."""

    def __init__(
        self,
        creature_id: str,
        archetype: ArchetypeType,
        base_drives: list[str],
        state_priorities: list[str],
        sanity_mods: SanityModifiers,
        social: SocialStructure,
        activity_cycle: ActivityCycle,
        seed: int = 42
    ):
        self.creature_id = creature_id
        self.archetype = archetype
        self.social = social
        self.activity_cycle = activity_cycle
        self.sanity_mods = sanity_mods
        self.state_priorities = [CreatureState(s) for s in state_priorities]
        self.rng = random.Random(seed)

        # Current state
        self.current_state: CreatureState = self.state_priorities[0] if self.state_priorities else CreatureState.IDLE
        self.state_timer: float = 0.0

        # Drives setup
        self.drives: dict[str, BehaviorDrive] = {}
        for drive_name in base_drives:
            self.drives[drive_name] = BehaviorDrive(
                name=drive_name,
                value=self.rng.uniform(0.1, 0.4),
                decay_rate=self.rng.uniform(0.005, 0.02),
                satisfaction_rate=self.rng.uniform(0.05, 0.15)
            )

        # Internal variables
        self.alert_level: float = 0.0       # 0.0 to 1.0
        self.fear_level: float = 0.0        # 0.0 to 1.0
        self.aggression: float = 1.0        # Sanity-modified multiplier
        self.awareness: float = 1.0         # Sanity-modified multiplier
        self.target_pos: tuple[float, float] | None = None

    def update(self, ctx: EnvironmentalContext) -> CreatureState:
        """Update behavior state for current frame."""
        self.state_timer += ctx.dt

        # 1. Apply Sanity Modifiers
        mods = self.sanity_mods.get_modifiers(ctx.player_sanity)
        self.aggression = mods.get("aggression", 1.0)
        self.awareness = mods.get("awareness", 1.0)
        skittish = mods.get("skittish", 1.0)

        # 2. Update Drives
        for name, drive in self.drives.items():
            is_acting = (name in self.current_state.value)
            drive.update(ctx.dt, is_acting)

        # 3. Evaluate Utilities for state transition
        utilities: dict[CreatureState, float] = {}
        for state in self.state_priorities:
            utilities[state] = self._evaluate_state_utility(state, ctx, skittish)

        # Pick highest utility state
        best_state = max(utilities.items(), key=lambda item: item[1])[0]

        # State transition with hysteresis to prevent oscillation
        if best_state != self.current_state and self.state_timer > 1.5:
            self.current_state = best_state
            self.state_timer = 0.0

        return self.current_state

    def _evaluate_state_utility(self, state: CreatureState, ctx: EnvironmentalContext, skittish: float) -> float:
        """Calculate utility score for a given state (0.0 to 1.0+)."""
        dist = ctx.player_distance * (1.0 / self.awareness)

        # Chase / Hunt
        if state == CreatureState.CHASE:
            if dist < 400.0 and self.aggression > 0.8:
                return (1.0 - dist / 400.0) * self.aggression
            return 0.0

        # Flee
        elif state == CreatureState.FLEE:
            if dist < 300.0 * skittish:
                return (1.0 - dist / (300.0 * skittish)) * skittish
            return 0.0

        # Stalk
        elif state == CreatureState.STALK:
            if 300.0 < dist < 600.0:
                return 0.6 * self.aggression
            return 0.0

        # Investigate
        elif state == CreatureState.INVESTIGATE:
            if ctx.player_moving and dist < 500.0:
                return 0.5 * self.drives.get("investigate", BehaviorDrive("def")).value
            return 0.0

        # Patrol
        elif state == CreatureState.PATROL:
            return 0.3

        # Rest
        elif state == CreatureState.REST:
            return self.drives.get("rest", BehaviorDrive("def")).value * 0.4

        # Herd
        elif state == CreatureState.HERD:
            return 0.5 if len(ctx.nearby_creatures) > 2 else 0.1

        # Scavenge
        elif state == CreatureState.SCAVENGE:
            return 0.7 if len(ctx.nearby_fragments) > 0 else 0.1

        # Hoard
        elif state == CreatureState.HOARD:
            return 0.6 if len(ctx.nearby_fragments) > 2 else 0.2

        # Attack / Strike
        elif state in (CreatureState.ATTACK, CreatureState.STRIKE):
            if dist < 80.0 and self.aggression > 0.5:
                return 0.9 * self.aggression
            return 0.0

        # Feed
        elif state == CreatureState.FEED:
            return 0.6 if dist < 100.0 else 0.1

        # Hide
        elif state == CreatureState.HIDE:
            if dist < 200.0 * skittish:
                return 0.7 * skittish
            return 0.0

        # Follow
        elif state == CreatureState.FOLLOW:
            if dist < 600.0 and self.drives.get("follow", BehaviorDrive("def")).value > 0.3:
                return 0.5
            return 0.0

        # Play
        elif state == CreatureState.PLAY:
            if dist < 400.0 and len(ctx.nearby_creatures) > 1:
                return 0.4 * self.drives.get("play", BehaviorDrive("def")).value
            return 0.0

        # Mimic
        elif state == CreatureState.MIMIC:
            if ctx.player_moving and dist < 500.0:
                return 0.5 * self.drives.get("mimic", BehaviorDrive("def")).value
            return 0.0

        # Attach (parasitic)
        elif state == CreatureState.ATTACH:
            if dist < 100.0:
                return 0.8 * self.drives.get("attach", BehaviorDrive("def")).value
            return 0.0

        # Drain (parasitic)
        elif state == CreatureState.DRAIN:
            return 0.7 if dist < 50.0 else 0.0

        # Protect / Shield / Intercept (guardian)
        elif state in (CreatureState.PROTECT, CreatureState.SHIELD, CreatureState.INTERCEPT):
            return 0.6 if len(ctx.nearby_creatures) > 0 else 0.2

        # Judge (territorial)
        elif state == CreatureState.JUDGE:
            if dist < 500.0:
                return 0.5 * self.aggression
            return 0.0

        # Camouflage (ambush)
        elif state == CreatureState.CAMOUFLAGE:
            if dist < 400.0:
                return 0.7
            return 0.0

        # Relocate
        elif state == CreatureState.RELOCATE:
            return 0.3 if self.state_timer > 10.0 else 0.0

        # Corrupt (void_walker)
        elif state == CreatureState.CORRUPT:
            return 0.8 * (1.0 - ctx.player_sanity / 100.0)

        # Void Walk
        elif state == CreatureState.VOID_WALK:
            return 0.5 if ctx.world_sanity < 50.0 else 0.1

        # Scripted Sequence
        elif state == CreatureState.SCRIPTED_SEQUENCE:
            return 0.9 if self.archetype.value == "gentle_light" else 0.0

        # Additional states from archetype JSON
        elif state == CreatureState.THREATEN:
            if dist < 400.0:
                return 0.6 * self.aggression
            return 0.0
        elif state == CreatureState.RETURN:
            if dist > 600.0:
                return 0.7
            return 0.0
        elif state == CreatureState.MARK:
            if dist < 800.0:
                return 0.4
            return 0.0
        elif state == CreatureState.LAY_EGGS:
            if self.drives.get("reproduce", BehaviorDrive("def")).value > 0.5:
                return 0.8
            return 0.0
        elif state == CreatureState.APPROACH:
            if dist > 200.0:
                return 0.5
            return 0.0
        elif state == CreatureState.SING:
            return 0.4 if ctx.time_of_day > 0.4 and ctx.time_of_day < 0.8 else 0.1
        elif state == CreatureState.ASCEND:
            if ctx.world_sanity > 75.0:
                return 0.9
            return 0.0
        elif state == CreatureState.INTERCEPT:
            if dist < 300.0:
                return 0.7
            return 0.0
        elif state == CreatureState.SHIELD:
            if len(ctx.nearby_creatures) > 0:
                return 0.8
            return 0.0
        elif state == CreatureState.CALL:
            if len(ctx.nearby_creatures) > 1:
                return 0.6
            return 0.0
        elif state == CreatureState.RALLY:
            if len(ctx.nearby_creatures) > 2:
                return 0.7
            return 0.0
        elif state == CreatureState.MERGE:
            if len(ctx.nearby_creatures) > 3:
                return 0.8 * (1.0 - ctx.player_sanity / 100.0)
            return 0.0
        elif state == CreatureState.WAIT:
            return 0.5 if self.state_timer < 5.0 else 0.3
        elif state == CreatureState.LURE:
            if dist < 500.0 and not ctx.player_moving:
                return 0.6
            return 0.0
        elif state == CreatureState.HUNT:
            if dist < 600.0 and self.aggression > 0.6:
                return 0.7 * self.aggression
            return 0.0
        elif state == CreatureState.SPREAD:
            if ctx.world_sanity < 50.0:
                return 0.9
            return 0.0

        elif state == CreatureState.STEAL:
            if len(ctx.nearby_creatures) > 0 and len(ctx.nearby_fragments) > 0:
                return 0.7
            return 0.1
        elif state == CreatureState.DETACH:
            if self.drives.get("detach", BehaviorDrive("def")).value > 0.5:
                return 0.8
            return 0.1
        elif state == CreatureState.RETREAT:
            if dist < 200.0 or self.fear_level > 0.7:
                return 0.9
            return 0.0
        elif state == CreatureState.HEAL:
            if self.drives.get("heal", BehaviorDrive("def")).value > 0.4:
                return 0.8
            return 0.1
        elif state == CreatureState.GUIDE:
            if ctx.player_sanity < 75.0 and dist < 800.0:
                return 0.9
            return 0.0

        return 0.1  # Default baseline utility
