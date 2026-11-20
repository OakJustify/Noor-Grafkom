"""Constraint-based endless level generation for ECHO.

The hand-authored campaign remains untouched.  This module builds a separate
streaming world from the courier's real controller constants: every accepted
platform is checked against the measured jump velocity, gravity, horizontal
speed and collision box imported from :mod:`echo_game.physics`.

Generation is data-only.  :class:`EndlessWorld` registers the returned
platform/hazard data with Pymunk and removes old sections as the player moves.
Rendering stays in :mod:`echo_game.game`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional
import math
import random

import heapq
import pymunk

from .challenges import (
    Challenge,
    ChallengeConfig,
    ChallengeContext,
    LOW_LANTERN,
    LightBarrier,
    LightSwitch,
    PuzzleGenerator as ChallengePuzzleGenerator,
    player_rect,
    rects_overlap,
)
from .levels import LEVELS, Level, Rect
from .environment import EnvironmentConfig, EnvironmentGenerator, EnvironmentSpec, reserved_rects
from .physics import (
    GRAVITY, JUMP_SPEED, MOVE_SPEED, PLAYER_SIZE, Input, World, DT,
    PlayerCapabilities, Prop, SOLID,
)
from .puzzle_archetypes import (
    PuzzleArchetype, PuzzleGenerator, PuzzleInstance,
    PuzzleVerifier, puzzle_to_endless_world_objects
)
from .rooms import (
    GeneratedRoom, RoomTheme, ProceduralRoom, ProceduralRoomGenerator,
    ProceduralRoomWorld, EndlessRoomGenerator, EndlessRoomWorld,
)


@dataclass(frozen=True)
class DifficultyManager:
    """Bounded logarithmic difficulty based on horizontal progress."""

    base: float = 1.0
    growth: float = 2.0
    scale: float = 1800.0
    maximum: float = 10.0

    def calculate(self, distance: float) -> float:
        value = self.base + self.growth * math.log1p(max(0.0, distance) / self.scale)
        return min(self.maximum, value)


@dataclass(frozen=True)
class GenerationProfile:
    """Explicit, bounded ranges produced from one difficulty value."""

    difficulty: float
    platform_width_range: tuple[float, float]
    gap_range: tuple[float, float]
    height_delta_range: tuple[float, float]
    hazard_probability: float
    max_hazards: int
    recovery_spacing: int
    challenge_probability: float = 0.26
    challenge_damage_cap: int = 1
    combo_probability: float = 0.0
    obstacle_probability: float = 0.20
    arena_spacing: int = 8
    arena_width_range: tuple[float, float] = (360.0, 420.0)

    @classmethod
    def create(cls, difficulty: float) -> "GenerationProfile":
        t = max(0.0, min(1.0, (difficulty - 1.0) / 9.0))
        return cls(
            difficulty=difficulty,
            platform_width_range=(235 - 15 * t, 335 - 25 * t),
            gap_range=(50 + 14 * t, 88 + 20 * t),
            height_delta_range=(-48 - 28 * t, 58 + 42 * t),
            hazard_probability=0.18 + 0.42 * t,
            max_hazards=1 if t < 0.55 else 2,
            recovery_spacing=6 if t < 0.5 else 7,
            challenge_probability=0.22 + 0.30 * t,
            challenge_damage_cap=1 if t < 0.62 else 2,
            combo_probability=0.0 if t < 0.28 else 0.18 + 0.34 * t,
            obstacle_probability=0.14 + 0.38 * t,
            arena_spacing=max(3, 8 - int(5 * t)),
            arena_width_range=(360 + 180 * t, 420 + 240 * t),
        )


@dataclass(frozen=True)
class GenerationConfig:
    generation_distance: float = 1500.0
    cleanup_distance: float = 1100.0
    max_attempts: int = 18
    platform_thickness: float = 28.0
    min_gap: float = 38.0
    max_gap: float = 150.0
    minimum_landing_width: float = 104.0
    landing_margin: float = 8.0
    safe_reach_ratio: float = 0.74
    vertical_min: float = 190.0
    vertical_max: float = 470.0
    initial_width: float = 840.0
    spawn: tuple[float, float] = (140.0, 430.0)
    hazard_min_platform_width: float = 205.0
    hazard_left_clearance: float = 150.0
    hazard_right_clearance: float = 90.0
    enemy_types: tuple[str, ...] = ("sentry",)
    challenge_enabled: bool = True
    challenge_min_width: float = 195.0
    max_health: int = 5
    invulnerability_time: float = 0.95
    knockback_x: float = 210.0
    knockback_y: float = 150.0
    lantern_drain: float = 0.0105
    lantern_recharge: float = 0.115
    lantern_start: float = 1.0
    enemy_light_radius: float = 132.0
    enemy_stun_time: float = 0.75
    environment_density: float = 1.0
    obstacle_density: float = 1.0
    puzzle_density: float = 1.0

    def __post_init__(self):
        for name in ("environment_density", "obstacle_density", "puzzle_density"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 3:
                raise ValueError(f"{name} must be a finite multiplier between 0 and 3")
        if any(kind != "sentry" for kind in self.enemy_types):
            raise ValueError("Only the implemented sentry enemy type is supported")
        if self.challenge_min_width < 0 or self.max_attempts < 1:
            raise ValueError("Invalid challenge width or structural retry limit")


@dataclass(frozen=True)
class Platform:
    id: int
    x: float
    y: float
    width: float
    height: float
    generation_index: int
    difficulty: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class SawHazard:
    id: int
    x: float
    y: float
    radius: float
    travel: float
    rate: float
    generation_index: int
    platform_id: int


@dataclass(frozen=True)
class Validation:
    attempts: int
    rejection_reasons: tuple[str, ...]
    fallback_used: bool
    is_valid: bool


@dataclass(frozen=True)
class Segment:
    platform: Platform
    hazards: tuple[SawHazard, ...]
    enemies: tuple[tuple, ...]
    difficulty: float
    generation_index: int
    validation: Validation
    challenge: Challenge | None = None
    environment: tuple[EnvironmentSpec, ...] = ()
    puzzle_instance: Optional[PuzzleInstance] = None


class ProceduralGenerator:
    """Generate one reachable platform plus valid hazards at a time.

    A retry loop is bounded.  If no sampled candidate passes, the generator
    returns a flat, close fallback rather than accepting an impossible path.
    """

    def __init__(self, seed: int, capabilities: PlayerCapabilities | None = None,
                 config: GenerationConfig | None = None,
                 previous: Platform | None = None,
                 difficulty: DifficultyManager | None = None,
                 challenge_generator: PuzzleGenerator | None = None):
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        # Density/resource decisions must not perturb structural coordinates.
        self.hazard_rng = random.Random(self.seed ^ 0x5A770B)
        self.puzzle_roll_rng = random.Random(self.seed ^ 0xA7E51E)
        self.capabilities = capabilities or PlayerCapabilities.from_controller()
        self.config = config or GenerationConfig()
        self.difficulty_manager = difficulty or DifficultyManager()
        self.previous = previous
        self.index = 0
        self.next_platform_id = 1 if previous is None else previous.id + 1
        self.next_hazard_id = 1
        self._free_hazard_ids: list[int] = []  # min-heap for O(log n) allocation
        self.rejections: list[dict] = []
        self.fallback_count = 0
        # Legacy challenge generator (light gates, sentries, etc.)
        self.challenge_generator = challenge_generator or ChallengePuzzleGenerator(self.seed)
        # New procedural puzzle archetype generator
        self.puzzle_archetype_generator = PuzzleGenerator(
            self.seed ^ 0x1A2B3C, self.capabilities, self.config)
        self.environment_generator = EnvironmentGenerator(
            self.seed, EnvironmentConfig(density=self.config.environment_density))
        self.challenge_context = ChallengeContext(
            difficulty=1.0, capabilities=self.capabilities)

    def reclaim_hazard_ids(self, ids: list[int]) -> None:
        """Return hazard IDs to the free heap for reuse."""
        for hazard_id in ids:
            # Use a set-like check to avoid duplicates; heap membership is O(n) but rare
            if hazard_id not in self._free_hazard_ids:
                heapq.heappush(self._free_hazard_ids, hazard_id)

    def profile(self, distance: float) -> GenerationProfile:
        profile = GenerationProfile.create(self.difficulty_manager.calculate(distance))
        return replace(profile,
                       hazard_probability=min(1.0, profile.hazard_probability * self.config.obstacle_density),
                       obstacle_probability=min(1.0, profile.obstacle_probability * self.config.obstacle_density),
                       challenge_probability=min(1.0, profile.challenge_probability * self.config.puzzle_density))

    def _candidate(self, previous: Platform, profile: GenerationProfile,
                   recovery: bool) -> Platform:
        rng = self.rng
        if recovery:
            width = rng.uniform(max(self.config.minimum_landing_width + 60, profile.platform_width_range[0]),
                                max(profile.platform_width_range[1], 270))
            gap = rng.uniform(48, min(70, self.config.max_gap))
        else:
            arena = self.index % profile.arena_spacing == profile.arena_spacing - 1
            width = rng.uniform(*(profile.arena_width_range if arena else profile.platform_width_range))
            gap = rng.uniform(*profile.gap_range)
        x = previous.right + gap
        # Sample within a reachable height interval instead of accumulating
        # clamped samples at Y=470. Keep validate_platform as the final authority.
        caps = self.capabilities
        flight = (gap + caps.width + 2 * self.config.landing_margin) / (
            caps.horizontal_speed * self.config.safe_reach_ratio)
        minimum_delta = (caps.gravity * flight * flight / 2 - caps.jump_speed * flight
                         if flight > caps.jump_speed / caps.gravity else -caps.max_jump_height)
        delta_range = (-8.0, 18.0) if recovery else profile.height_delta_range
        low = max(self.config.vertical_min - previous.y, delta_range[0], minimum_delta + 1e-6)
        high = min(self.config.vertical_max - previous.y, delta_range[1])
        if high < low:
            y = previous.y + delta_range[0]  # final validator rejects; bounded fallback remains
        else:
            y = previous.y + rng.uniform(low, high)
        return Platform(self.next_platform_id, x, y, width,
                        self.config.platform_thickness, self.index + 1,
                        profile.difficulty)

    def validate_platform(self, previous: Platform, candidate: Platform,
                          profile: GenerationProfile | None = None) -> tuple[bool, list[str]]:
        caps, config = self.capabilities, self.config
        reasons: list[str] = []
        gap = candidate.x - previous.right
        if gap < config.min_gap:
            reasons.append(f"gap {gap:.1f} below minimum")
        if gap > config.max_gap:
            reasons.append(f"gap {gap:.1f} above maximum")
        if candidate.width < config.minimum_landing_width:
            reasons.append("landing too narrow")
        if not config.vertical_min <= candidate.y <= config.vertical_max:
            reasons.append("outside vertical bounds")
        delta = candidate.y - previous.y
        reach = caps.horizontal_reach(delta)
        if reach is None:
            reasons.append("higher than maximum jump")
        else:
            # Best takeoff centre is one half-width behind the old edge; the
            # landing centre needs a half-width plus a safety margin.
            required = gap + caps.width + 2 * config.landing_margin
            if required > reach * config.safe_reach_ratio:
                reasons.append("jump arc cannot reach landing")
        # Trajectory simulation: verify the player can actually land on the
        # platform's top surface from the previous platform's right edge.
        if not reasons:  # only simulate if basic checks pass
            if not caps.can_land_on(previous, candidate):
                reasons.append("trajectory misses platform top")
        if profile is not None:
            if candidate.width < profile.platform_width_range[0] - 1e-6:
                reasons.append("width below difficulty bounds")
        return not reasons, reasons

    def _hazards(self, platform: Platform, profile: GenerationProfile,
                 context: ChallengeContext | None = None,
                 challenge: Challenge | None = None) -> list[SawHazard]:
        cfg = self.config
        rng = self.hazard_rng
        context = context or self.challenge_context
        if (not context.fair_for_damage() or context.lantern_fraction <= LOW_LANTERN
                or profile.challenge_damage_cap < 1 or (challenge and challenge.damage_cost)):
            return []
        if platform.width < cfg.hazard_min_platform_width:
            return []
        if rng.random() >= profile.hazard_probability:
            return []
        radius = rng.uniform(17, 24)
        # A landing from the previous platform can overshoot well past its
        # near edge.  Keep a generous clear landing run on the left and a
        # takeoff run on the right, so a saw is never hidden in the landing
        # zone.  If the platform is too short for that geometry, skip it.
        left_limit = platform.x + cfg.hazard_left_clearance + radius
        right_limit = platform.right - cfg.hazard_right_clearance - radius
        if right_limit - left_limit < 8:
            return []
        intervals = [(left_limit, right_limit)]
        if challenge:
            reserved = [s.rect for s in challenge.switches] + [b.rect for b in challenge.barriers]
            reserved += [c.rect for c in challenge.caches]
            for rect in reserved:
                blocked_left, blocked_right = rect.x - radius - 12, rect.x + rect.w + radius + 12
                intervals = [(a, b) for low, high in intervals
                             for a, b in ((low, min(high, blocked_left)),
                                          (max(low, blocked_right), high)) if b - a >= 8]
        if not intervals:
            return []
        # Pick a genuine free slot; travel is bounded by that slot as well.
        left_limit, right_limit = max(intervals, key=lambda interval: interval[1] - interval[0])
        count = 1
        if (min(profile.max_hazards, profile.challenge_damage_cap) > 1
                and right_limit - left_limit >= 228 and rng.random() < 0.45):
            count = 2
        if count == 1:
            slots = [rng.uniform(left_limit, right_limit)]
        else:
            # Separate hops need actual landing/run-up space between sweeps.
            slots = [left_limit + 4, right_limit - 4]
        hazards = []
        difficulty_t = max(0.0, min(1.0, (profile.difficulty - 1) / 9))
        for x in slots:
            travel_cap = min(
                32.0,
                max(0.0, x - left_limit),
                max(0.0, right_limit - x),
            )
            travel = 0.0 if difficulty_t < 0.15 else rng.uniform(0, travel_cap)
            rate = rng.uniform(0.65, 1.45) if travel else 0.0
            # Reuse freed hazard IDs first (heap allocator for O(log n) performance)
            if self._free_hazard_ids:
                hazard_id = heapq.heappop(self._free_hazard_ids)
            else:
                hazard_id = self.next_hazard_id
                self.next_hazard_id += 1
            hazards.append(SawHazard(
                id=hazard_id, x=x, y=platform.y - radius - 2,
                radius=radius, travel=travel, rate=rate,
                generation_index=platform.generation_index, platform_id=platform.id))
        return hazards

    def validate_segment(self, segment: Segment,
                         context: ChallengeContext | None = None) -> tuple[bool, list[str]]:
        platform, cfg = segment.platform, self.config
        context = context or self.challenge_context
        reasons: list[str] = []
        if segment.enemies and not cfg.enemy_types:
            reasons.append("enemy generated without an implemented type")
        puzzle = segment.puzzle_instance
        if puzzle is not None:
            if puzzle.archetype is not PuzzleArchetype.CRATE_PLATE:
                reasons.append("unsupported puzzle archetype")
            if not puzzle.verified_solvable:
                reasons.append("puzzle lacks a successful physics verification")
            if puzzle.platform_id != platform.id:
                reasons.append("puzzle platform mismatch")
            if not (len(puzzle.crates) == len(puzzle.plates) == len(puzzle.gates) == 1):
                reasons.append("crate-plate puzzle requires one crate, plate, and gate")
            if segment.challenge is not None or segment.hazards:
                reasons.append("puzzle platform contains conflicting content")
        if segment.challenge is not None:
            reasons.extend(self.challenge_generator.validator.validate(
                segment.challenge, platform, context,
                hazards=segment.hazards))
        damage_cost = len(segment.hazards) + (segment.challenge.damage_cost if segment.challenge else 0)
        if damage_cost > context.damage_cap:
            reasons.append("segment exceeds damage budget")
        if segment.hazards and (not context.fair_for_damage() or context.lantern_fraction <= LOW_LANTERN):
            reasons.append("standalone hazard at low resources")
        
        # Build reserved rects from challenge elements for hazard overlap check
        challenge_rects = []
        if segment.challenge:
            challenge_rects.extend(s.rect for s in segment.challenge.switches)
            challenge_rects.extend(b.rect for b in segment.challenge.barriers)
            challenge_rects.extend(z.rect for z in segment.challenge.shadows)
            challenge_rects.extend(c.rect for c in segment.challenge.caches)
        
        for hazard in segment.hazards:
            if hazard.y >= platform.y:
                reasons.append("hazard below platform surface")
            left = hazard.x - hazard.travel - hazard.radius
            right = hazard.x + hazard.travel + hazard.radius
            if left < platform.x + cfg.hazard_left_clearance:
                reasons.append("hazard invades landing zone")
            if right > platform.right - cfg.hazard_right_clearance:
                reasons.append("hazard invades takeoff run")
            if left < platform.x + 1 or right > platform.right - 1:
                reasons.append("hazard leaves platform")
            # Check hazard vs challenge element overlap
            hazard_rect = Rect(hazard.x - hazard.travel - hazard.radius,
                              hazard.y - hazard.radius,
                              2 * (hazard.radius + hazard.travel),
                              2 * hazard.radius)
            for crect in challenge_rects:
                if (hazard_rect.x < crect.x + crect.w and hazard_rect.x + hazard_rect.w > crect.x and
                    hazard_rect.y < crect.y + crect.h and hazard_rect.y + hazard_rect.h > crect.y):
                    reasons.append(f"hazard overlaps challenge element at ({crect.x:.0f},{crect.y:.0f})")
        
        if len(segment.hazards) > 1:
            hazards = sorted(segment.hazards, key=lambda h: h.x)
            for first, second in zip(hazards, hazards[1:]):
                if second.x - second.travel - second.radius - (first.x + first.travel + first.radius) < 120:
                    reasons.append("hazards leave no safe intermediate landing")
        accepted_environment = []
        reserved = reserved_rects(segment.challenge, segment.hazards)
        for item in segment.environment:
            reasons.extend(self.environment_generator.validate(item, platform, accepted_environment, reserved))
            accepted_environment.append(item)
        return not reasons, reasons

    def create_safe_fallback(self, previous: Platform, difficulty: float) -> Platform:
        gap = min(48.0, self.config.max_gap)
        width = max(self.config.minimum_landing_width + 96, 200.0)
        # Respect vertical bounds. If previous.y is within bounds and a flat
        # platform is reachable, use it. Otherwise find a reachable height.
        caps = self.capabilities
        flight = (gap + caps.width + 2 * self.config.landing_margin) / (
            caps.horizontal_speed * self.config.safe_reach_ratio)
        minimum_delta = (caps.gravity * flight * flight / 2 - caps.jump_speed * flight
                         if flight > caps.jump_speed / caps.gravity else -caps.max_jump_height)
        # Check if flat (same Y) is valid
        flat_reachable = caps.can_land_on(previous, Platform(0, previous.right + gap, previous.y,
                                                             width, self.config.platform_thickness, 0, difficulty))
        if (self.config.vertical_min <= previous.y <= self.config.vertical_max and flat_reachable):
            y = previous.y
        else:
            # Clamp to vertical bounds, but prefer a reachable height
            y = max(self.config.vertical_min, min(self.config.vertical_max, previous.y + minimum_delta))
        return Platform(self.next_platform_id, previous.right + gap, y,
                        width, self.config.platform_thickness, self.index + 1,
                        difficulty)

    def generate_next(self, distance: float,
                      context: ChallengeContext | None = None) -> Segment:
        if self.previous is None:
            raise ValueError("A previous platform is required")
        profile = self.profile(distance)
        recovery = self.index % profile.recovery_spacing == 0
        if context is None:
            context = ChallengeContext(
                difficulty=profile.difficulty,
                capabilities=self.capabilities, distance=distance)
        context = replace(context, difficulty=profile.difficulty,
                          damage_cap=profile.challenge_damage_cap, enemy_types=self.config.enemy_types)
        self.challenge_context = context
        reasons: list[str] = []
        attempts = 0
        for _ in range(self.config.max_attempts):
            attempts += 1
            candidate = self._candidate(self.previous, profile, recovery)
            valid, why = self.validate_platform(self.previous, candidate, profile)
            if valid:
                puzzle_instance = None
                if (not recovery and self.config.puzzle_density > 0
                        and candidate.width >= 400
                        and self.puzzle_roll_rng.random()
                        < min(0.9, self.config.puzzle_density * 0.30)):
                    puzzle_instance = self.puzzle_archetype_generator.generate(
                        candidate, profile, context)

                # Keep a multi-step puzzle isolated from one-step challenges
                # and saws. Generated scenery is non-collidable and renders
                # underneath the puzzle objects, so it does not alter solving.
                challenge = None
                if (puzzle_instance is None and not recovery
                        and self.config.challenge_enabled
                        and candidate.width >= self.config.challenge_min_width):
                    challenge = self.challenge_generator.generate(
                        candidate, profile, context, previous=self.previous,
                        hazards=())
                hazards = (() if recovery or puzzle_instance is not None else
                           tuple(self._hazards(candidate, profile, context, challenge)))

                segment = Segment(
                    platform=candidate,
                    hazards=hazards,
                    enemies=(),
                    difficulty=profile.difficulty,
                    generation_index=self.index + 1,
                    validation=Validation(attempts, tuple(reasons), False, True),
                    challenge=challenge,
                    environment=(),
                    puzzle_instance=puzzle_instance
                )
                
                valid, why = self.validate_segment(segment, context)
                if not valid and challenge is not None:
                    # A challenge is optional.  Never discard a reachable
                    # platform (or its saws) because its decoration failed.
                    segment = Segment(candidate, hazards, (), profile.difficulty,
                                      self.index + 1,
                                      Validation(attempts, tuple(reasons), False, True),
                                      None,
                                      (),
                                      puzzle_instance)
                    valid, why = self.validate_segment(segment, context)
                if valid:
                    environment = self.environment_generator.generate(
                        candidate, profile,
                        reserved_rects(segment.challenge, segment.hazards))
                    segment = replace(segment, environment=environment)
                    self._accept(segment)
                    return segment
            reasons.extend(why)
            if len(reasons) >= 60:
                reasons = reasons[:60]
        self.fallback_count += 1
        platform = self.create_safe_fallback(self.previous, profile.difficulty)
        fallback = Segment(platform, (), (), profile.difficulty, self.index + 1,
                            Validation(attempts, tuple(reasons), True, True), None)
        fallback = replace(fallback, environment=self.environment_generator.generate(platform, profile))
        self._accept(fallback)
        return fallback

    def _accept(self, segment: Segment):
        self.rejections.append({
            "generation_index": segment.generation_index,
            "difficulty": round(segment.difficulty, 3),
            "attempts": segment.validation.attempts,
            "fallback": segment.validation.fallback_used,
            "reasons": list(segment.validation.rejection_reasons[:8]),
        })
        if len(self.rejections) > 160:
            self.rejections = self.rejections[-160:]
        self.previous = segment.platform
        self.index += 1
        self.next_platform_id += 1


@dataclass
class EnemyState:
    x: float
    direction: int = 1
    stun: float = 0.0


@dataclass
class PuzzleRuntime:
    """Live physics objects and progress for one generated puzzle."""

    instance: PuzzleInstance
    crate: Prop
    plate: Rect
    plate_body: pymunk.Body
    plate_shape: pymunk.Shape
    gate: Rect
    gate_body: pymunk.Body
    gate_shape: pymunk.Shape
    crate_was_grabbed: bool = False
    solved: bool = False
    gate_fraction: float = 0.0


class EndlessWorld(World):
    """A streaming world built entirely by :class:`ProceduralGenerator`."""

    def __init__(self, seed: int = 1, config: GenerationConfig | None = None,
                  challenge_config: ChallengeConfig | None = None,
                  difficulty: DifficultyManager | None = None):
        self.seed = int(seed)
        config = config or GenerationConfig()
        base_width = config.initial_width
        level = Level(
            "ENDLESS / THE UNENDING SIGNAL",
            "The dark keeps building.",
            "Keep moving right. The path is generated ahead and released behind.",
            width=10 ** 9,
            spawn=config.spawn,
            exit=(10 ** 9, 0),
            terrain=(Rect(-80, 460, base_width + 80, 180),),
        )
        super().__init__(0, level=level, bounds=False, iterations=15)  # Lower iterations for endless (no rope/seesaw/magnet)
        self.endless = True
        self.config = config
        self.base_platform = Platform(0, -80, 460, base_width + 80, 180, -1, 1.0)
        challenge_config = challenge_config or ChallengeConfig()
        challenge_generator = ChallengePuzzleGenerator(self.seed, challenge_config)
        self.generator = ProceduralGenerator(
            seed, config=config, previous=self.base_platform,
            challenge_generator=challenge_generator, difficulty=difficulty)
        self.challenge_generator = challenge_generator
        self.generated_platforms: list[Platform] = []
        self.generated_hazards: list[SawHazard] = []
        self.environment_objects: list[EnvironmentSpec] = []
        self.environment_spawned = 0
        self.environment_cleaned = 0
        self._platform_geometry: dict[int, tuple[pymunk.Body, pymunk.Shape]] = {}
        self.generated_until = self.base_platform.right
        self.generation_count = 0
        self.distance = 0.0
        self.furthest_distance = 0.0
        self.difficulty = self.generator.difficulty_manager.calculate(0)

        # Health and lantern are the endless run's two resources.  Both are
        # deliberately visible and both have bounded recovery paths.
        self.max_health = max(1, int(config.max_health))
        self.health = self.max_health
        self.invulnerability = 0.0
        self.lantern_on = True
        self.lantern_energy = max(0.0, min(1.0, config.lantern_start))
        self.lantern_held = False
        self.challenges: list[Challenge] = []
        self.active_switches: set[int] = set()
        self.barrier_geometry: dict[int, tuple[pymunk.Body, pymunk.Shape]] = {}
        self.enemy_states: dict[int, EnemyState] = {}
        self.used_caches: set[int] = set()
        self.puzzle_runtimes: dict[int, PuzzleRuntime] = {}
        self.puzzles_spawned = 0
        self.puzzles_solved = 0
        self.last_challenge_label = ""
        self._damage_flash = 0.0
        self._ensure_generated()

    @property
    def width(self):
        return max(self.generated_until, 960)

    @property
    def lantern_radius(self) -> float:
        if not self.lantern_on or self.lantern_energy <= 0:
            return 46.0
        return 104.0 + 74.0 * self.lantern_energy

    @property
    def health_fraction(self) -> float:
        return self.health / max(1, self.max_health)

    def terrain_rects(self):
        return self.level.terrain + tuple(p.rect for p in self.generated_platforms)

    def saw_positions(self):
        return [(h.x + math.sin(self.time * h.rate) * h.travel, h.y, h.radius)
                for h in self.generated_hazards]

    def challenge_context(self) -> ChallengeContext:
        return ChallengeContext(
            difficulty=self.difficulty,
            health_fraction=self.health_fraction,
            lantern_fraction=self.lantern_energy,
            distance=self.distance,
            capabilities=self.generator.capabilities,
            damage_cap=self.generator.profile(self.furthest_distance).challenge_damage_cap,
            enemy_types=self.config.enemy_types)

    def _spawn_challenge(self, challenge: Challenge):
        self.challenges.append(challenge)
        self.last_challenge_label = challenge.label
        for barrier in challenge.barriers:
            self.barrier_geometry[barrier.id] = self._static_rect(barrier.rect)
        for enemy in challenge.enemies:
            self.enemy_states[enemy.id] = EnemyState(enemy.x)

    def _spawn_segment(self, segment: Segment):
        platform = segment.platform
        body, shape = self._static_rect(platform.rect)
        self._platform_geometry[platform.id] = (body, shape)
        self.generated_platforms.append(platform)
        self.generated_hazards.extend(segment.hazards)
        self.environment_objects.extend(segment.environment)
        self.environment_spawned += len(segment.environment)
        if segment.challenge is not None:
            self._spawn_challenge(segment.challenge)
        
        # Spawn procedural puzzle archetype objects
        if segment.puzzle_instance is not None:
            self._spawn_puzzle(segment.puzzle_instance)
        
        self.generated_until = max(self.generated_until, platform.right)
        self.generation_count += 1

    def _spawn_puzzle(self, puzzle: PuzzleInstance):
        """Spawn the verified crate-plate-gate archetype in the live world."""
        if puzzle.archetype is not PuzzleArchetype.CRATE_PLATE:
            return
        if puzzle.platform_id in self.puzzle_runtimes:
            return
        objects = puzzle_to_endless_world_objects(puzzle)
        if not (len(objects["crates"]) == len(objects["plates"]) == len(objects["gates"]) == 1):
            return

        crate_data = objects["crates"][0]
        plate_data = objects["plates"][0]
        gate_data = objects["gates"][0]
        crate_size = float(crate_data["size"])
        crate = self._prop((crate_data["x"], crate_data["y"]),
                           (crate_size, crate_size), crate_data["mass"])
        self.crates.append(crate)

        plate = Rect(plate_data["x"], plate_data["y"],
                     plate_data["w"], plate_data["h"])
        plate_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        plate_body.position = (plate.x + plate.w / 2, plate.y + plate.h / 2)
        plate_shape = pymunk.Poly.create_box(plate_body, (plate.w, plate.h))
        plate_shape.sensor = True
        plate_shape.filter = pymunk.ShapeFilter(categories=SOLID)
        self.space.add(plate_body, plate_shape)

        gate = Rect(gate_data["x"], gate_data["y"],
                    gate_data["w"], gate_data["h"])
        gate_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        gate_body.position = (gate.x + gate.w / 2, gate.y + gate.h / 2)
        gate_shape = pymunk.Poly.create_box(gate_body, (gate.w, gate.h))
        gate_shape.friction = 0.7
        gate_shape.filter = pymunk.ShapeFilter(categories=SOLID)
        self.space.add(gate_body, gate_shape)

        self.puzzle_runtimes[puzzle.platform_id] = PuzzleRuntime(
            puzzle, crate, plate, plate_body, plate_shape,
            gate, gate_body, gate_shape)
        self.puzzles_spawned += 1

    def _puzzle_crate_on_plate(self, runtime: PuzzleRuntime) -> bool:
        runtime.crate.shape.cache_bb()
        bb = runtime.crate.shape.bb
        plate = runtime.plate
        crate = runtime.crate
        size_x = crate.size[0]
        fully_supported = (
            plate.x + size_x / 2 <= crate.body.position.x
            <= plate.x + plate.w - size_x / 2
        )
        resting = abs(bb.top - (plate.y + plate.h / 2)) <= 12
        return fully_supported and resting

    def _update_puzzles(self, dt: float):
        for runtime in self.puzzle_runtimes.values():
            if self.grabbed is runtime.crate.body:
                runtime.crate_was_grabbed = True
            if not runtime.solved and runtime.crate_was_grabbed:
                runtime.solved = self._puzzle_crate_on_plate(runtime)
                if runtime.solved:
                    self.puzzles_solved += 1
                    self.events.append("gate")
            target = 1.0 if runtime.solved else 0.0
            delta = max(-dt * 1.4, min(dt * 1.4, target - runtime.gate_fraction))
            runtime.gate_fraction += delta
            runtime.gate_body.velocity = (0, -delta * (runtime.gate.h + 20) / dt)

    def _remove_puzzle(self, platform_id: int):
        runtime = self.puzzle_runtimes.pop(platform_id, None)
        if runtime is None:
            return
        if self.grabbed is runtime.crate.body:
            self._release()
        for body, shape in ((runtime.plate_body, runtime.plate_shape),
                            (runtime.gate_body, runtime.gate_shape),
                            (runtime.crate.body, runtime.crate.shape)):
            if body in self.space.bodies:
                self.space.remove(body, shape)
        if runtime.crate in self.crates:
            self.crates.remove(runtime.crate)

    def _ensure_generated(self):
        # A cap makes a broken generator configuration fail loudly instead of
        # hanging the game loop; normal widths need fewer than ten iterations.
        for _ in range(24):
            if self.generated_until >= self.player.position.x + self.config.generation_distance:
                return
            self._spawn_segment(self.generator.generate_next(
                self.furthest_distance, self.challenge_context()))

    def _remove_challenge(self, challenge: Challenge):
        for barrier in challenge.barriers:
            geometry = self.barrier_geometry.pop(barrier.id, None)
            if geometry is not None:
                body, shape = geometry
                if body in self.space.bodies:
                    self.space.remove(body, shape)
        for enemy in challenge.enemies:
            self.enemy_states.pop(enemy.id, None)
        for cache in challenge.caches:
            self.used_caches.discard(cache.id)
        if challenge in self.challenges:
            self.challenges.remove(challenge)

    def _cleanup(self):
        threshold = self.player.position.x - self.config.cleanup_distance
        removed = set()
        for platform in list(self.generated_platforms):
            geometry = self._platform_geometry.get(platform.id)
            if platform.right >= threshold or geometry is None:
                continue
            body, shape = geometry
            if self.support is body:
                continue
            self.space.remove(body, shape)
            del self._platform_geometry[platform.id]
            self.generated_platforms.remove(platform)
            removed.add(platform.id)
        if removed:
            before = len(self.environment_objects)
            self.environment_objects = [e for e in self.environment_objects if e.platform_id not in removed]
            self.environment_cleaned += before - len(self.environment_objects)
            for platform_id in removed:
                self._remove_puzzle(platform_id)
            # Reclaim hazard IDs from cleaned-up hazards
            cleaned_hazard_ids = [h.id for h in self.generated_hazards if h.platform_id in removed]
            self.generated_hazards = [h for h in self.generated_hazards
                                      if h.platform_id not in removed]
            if cleaned_hazard_ids:
                self.generator.reclaim_hazard_ids(cleaned_hazard_ids)
            for challenge in list(self.challenges):
                if challenge.platform_id in removed:
                    self._remove_challenge(challenge)
            self.active_switches = {
                switch.id for challenge in self.challenges
                for switch in challenge.switches
                if switch.id in self.active_switches}

    def _switches(self):
        for challenge in self.challenges:
            yield from challenge.switches

    def _barrier_is_active(self, barrier: LightBarrier) -> bool:
        return barrier.id in self.barrier_geometry

    def activate_switch(self, switch: LightSwitch):
        if switch.id in self.active_switches:
            return
        self.active_switches.add(switch.id)
        for challenge in self.challenges:
            for barrier in challenge.barriers:
                if barrier.switch_id != switch.id:
                    continue
                geometry = self.barrier_geometry.pop(barrier.id, None)
                if geometry is not None:
                    body, shape = geometry
                    if body in self.space.bodies:
                        self.space.remove(body, shape)
        self.events.append("gate")

    def toggle_lantern(self):
        if self.lantern_on:
            self.lantern_on = False
            self.events.append("tick")
        elif self.lantern_energy > 0.012:
            self.lantern_on = True
            self.events.append("gate")

    def interact(self):
        super().interact()
        if self.dead:
            return
        p = self.player.position
        for switch in self._switches():
            if switch.id in self.active_switches:
                continue
            if p.get_distance((switch.x, switch.y)) < switch.radius:
                if self.lantern_on and self.lantern_energy > 0.012:
                    self.activate_switch(switch)
                else:
                    self.events.append("tick")
                return

    def take_damage(self, amount: int, source_x: float | None = None,
                    reason: str = "The dark takes its due.") -> bool:
        if self.dead or self.invulnerability > 0 or amount <= 0:
            return False
        self.health = max(0, self.health - int(amount))
        self.invulnerability = max(0.0, self.config.invulnerability_time)
        self._damage_flash = 0.28
        if source_x is not None:
            direction = 1 if self.player.position.x >= source_x else -1
            vx, vy = self.player.velocity
            self.player.velocity = (
                vx + direction * self.config.knockback_x,
                vy - self.config.knockback_y)
        self.events.append("tick")
        if self.health <= 0:
            self.kill(reason)
        return True

    def _saw_contact(self, x: float):
        self.take_damage(1, source_x=x, reason="The machinery is still hungry.")

    def _fall_death(self):
        self.kill("The dark has no floor.")

    def _update_lantern(self, dt: float):
        if self.lantern_on:
            self.lantern_energy = max(
                0.0, self.lantern_energy - self.config.lantern_drain * dt)
            if self.lantern_energy <= 0:
                self.lantern_on = False
                self.events.append("tick")
        else:
            self.lantern_energy = min(
                1.0, self.lantern_energy + self.config.lantern_recharge * dt)

    def _update_challenges(self, dt: float):
        p = self.player.position
        body = player_rect(p)
        for challenge in list(self.challenges):
            for zone in challenge.shadows:
                if not self.lantern_on and rects_overlap(body, zone.rect):
                    self.take_damage(zone.damage,
                                     source_x=zone.x + zone.width / 2,
                                     reason="The shadow drank the light.")
            for cache in challenge.caches:
                if cache.id in self.used_caches:
                    continue
                if p.get_distance((cache.x, cache.y)) <= cache.radius + 12:
                    self.used_caches.add(cache.id)
                    self.lantern_energy = 1.0
                    self.health = min(self.max_health, self.health + 1)
                    self.events.append("checkpoint")
            for enemy in challenge.enemies:
                state = self.enemy_states.get(enemy.id)
                if state is None:
                    continue
                state.stun = max(0.0, state.stun - dt)
                lit = self.lantern_on and self.lantern_energy > 0
                if lit and p.get_distance((state.x, enemy.y)) < self.config.enemy_light_radius:
                    state.stun = max(state.stun, self.config.enemy_stun_time)
                    # Retreat from the lantern rather than chasing the player.
                    state.direction = 1 if state.x >= p.x else -1
                speed = enemy.speed * (0.18 if state.stun > 0 else 1.0)
                state.x += state.direction * speed * dt
                if state.x < enemy.patrol_left:
                    state.x = enemy.patrol_left
                    state.direction = 1
                elif state.x > enemy.patrol_right:
                    state.x = enemy.patrol_right
                    state.direction = -1
                enemy_rect = enemy.rect_at(state.x)
                # Lantern light holds a sentry back.  The encounter becomes a
                # resource decision: spend light to pass safely, or conserve it
                # and risk contact in the dark.
                if state.stun <= 0 and rects_overlap(body, enemy_rect):
                    self.take_damage(enemy.damage, source_x=state.x,
                                     reason="The hollow sentry found you.")
        if self.dead:
            return

    def step(self, control: Input = Input(), dt: float = 1 / 120):
        if self.dead or self.complete:
            return
        if control.lantern and not self.lantern_held:
            self.toggle_lantern()
        self.lantern_held = control.lantern
        self.invulnerability = max(0.0, self.invulnerability - dt)
        self._damage_flash = max(0.0, self._damage_flash - dt)
        self._update_lantern(dt)
        super().step(control, dt)
        self._update_puzzles(dt)
        if self.dead or self.complete:
            return
        self.distance = max(0.0, self.player.position.x - self.level.spawn[0])
        self.furthest_distance = max(self.furthest_distance, self.distance)
        self.difficulty = self.generator.difficulty_manager.calculate(self.furthest_distance)
        self._update_challenges(dt)
        if self.dead:
            return
        self._ensure_generated()
        self._cleanup()

    def visible_challenge_label(self) -> str:
        if not self.challenges:
            return ""
        x = self.player.position.x
        current = next((platform for platform in self.generated_platforms
                        if platform.x <= x <= platform.right), None)
        if current is not None:
            here = next((challenge for challenge in self.challenges
                         if challenge.platform_id == current.id), None)
            if here is not None:
                return here.label
        ahead = sorted((challenge for challenge in self.challenges
                        if challenge.generation_index >= self.generator.index - 1),
                       key=lambda challenge: challenge.generation_index)
        return ahead[0].label if ahead else ""

    def snapshot(self):
        data = super().snapshot()
        data.update({
            "endless": True,
            "seed": self.seed,
            "distance": round(self.distance, 2),
            "furthest_distance": round(self.furthest_distance, 2),
            "difficulty": round(self.difficulty, 3),
            "active_platforms": len(self.generated_platforms),
            "active_hazards": len(self.generated_hazards),
            "active_environment": len(self.environment_objects),
            "environment_spawned": self.environment_spawned,
            "environment_cleaned": self.environment_cleaned,
            "environment_by_type": dict(self.generator.environment_generator.total_by_type),
            "densities": {"environment": self.config.environment_density,
                          "obstacle": self.config.obstacle_density, "puzzle": self.config.puzzle_density},
            "generated_until": round(self.generated_until, 1),
            "generations": self.generation_count,
            "fallbacks": self.generator.fallback_count,
            "health": self.health,
            "max_health": self.max_health,
            "invulnerability": round(self.invulnerability, 3),
            "lantern_on": self.lantern_on,
            "lantern_energy": round(self.lantern_energy, 4),
            "active_challenges": len(self.challenges),
            "active_puzzles": len(self.puzzle_runtimes),
            "puzzles_spawned": self.puzzles_spawned,
            "puzzles_solved": self.puzzles_solved,
            "puzzle_archetypes": sorted({runtime.instance.archetype.value
                                          for runtime in self.puzzle_runtimes.values()}),
            "active_barriers": len(self.barrier_geometry),
            "active_switches": len(self.active_switches),
            "challenge_stats": self.challenge_generator.stats.as_dict(),
        })
        return data


class EndlessPilot:
    """Deterministic input-only traversal for demos and integration tests."""

    def __init__(self):
        self.last_jump_x = -1e9
        self.hazard_target: SawHazard | None = None
        self.braking = False
        self.last_action = False
        self.puzzle_platform_id: int | None = None
        self.puzzle_phase = ""
        self.puzzle_jump_started = False

    def _platforms(self, world: EndlessWorld):
        return [world.base_platform] + sorted(world.generated_platforms, key=lambda p: p.x)

    def control(self, world: EndlessWorld) -> Input:
        x, y = world.player.position
        grounded = world.grounded
        platforms = self._platforms(world)
        current = None
        for platform in platforms:
            if platform.x <= x <= platform.right and platform.y >= y - 24:
                if current is None or platform.y < current.y:
                    current = platform
        jump = False
        move = 1
        grab = False
        action = False
        lantern_toggle = False
        if grounded:
            # Touching down ends any hazard hop and resumes the rightward run.
            self.hazard_target = None
            self.braking = False
        elif self.braking:
            # Air-brake after clearing a saw, so the hop lands on the current
            # platform instead of sailing off its far lip.
            move = -1 if world.player.velocity.x > 25 else 0

        hazards = [h for h in world.generated_hazards
                   if h.x + h.travel + h.radius > x - 8]
        hazards.sort(key=lambda h: h.x)
        for hazard in hazards:
            sweep = hazard.travel + hazard.radius
            left = hazard.x - sweep
            if grounded and left - 58 < x < hazard.x + sweep:
                jump = True
                self.hazard_target = hazard
                self.braking = False
                break

        if (self.hazard_target is not None and not grounded
                and x > self.hazard_target.x + self.hazard_target.travel
                + self.hazard_target.radius + 10):
            self.braking = True
            move = -1 if world.player.velocity.x > 25 else 0

        # -- Challenges --------------------------------------------------
        # Find a seal on the platform the pilot is currently crossing, plus an
        # inactive light switch that is reachable by walking.
        blocking_barrier = None
        switch_target = None
        for challenge in world.challenges:
            for barrier in challenge.barriers:
                if not world._barrier_is_active(barrier):
                    continue
                linked = next((switch for switch in challenge.switches
                               if switch.id == barrier.switch_id), None)
                if linked is None or linked.id in world.active_switches:
                    continue
                if (current is not None
                        and current.x - 2 <= barrier.x <= current.right + 2
                        and abs(barrier.bottom - current.y) < 2):
                    blocking_barrier = barrier
                    switch_target = linked
                    break
            if blocking_barrier is not None:
                break
        if switch_target is None:
            for switch in world._switches():
                if switch.id in world.active_switches:
                    continue
                if current is None:
                    continue
                if (current.x - 36 <= switch.x <= current.right + 36
                        and abs(switch.y + 22 - current.y) < 8):
                    switch_target = switch
                    break

        if blocking_barrier is not None and switch_target is not None:
            # A closed seal is a hard wall: stand still if the lantern must
            # recharge, otherwise walk to its switch and pulse the action key.
            if not world.lantern_on and world.lantern_energy < 0.12:
                move = 0
                jump = False
            elif abs(x - switch_target.x) <= 34:
                move = 0
                jump = False
                action = not self.last_action
            elif x < switch_target.x:
                move = 1
                jump = False
            else:
                move = -1
                jump = False
        elif switch_target is not None and abs(x - switch_target.x) <= 30:
            action = not self.last_action

        shadow_near = any(
            zone.x - 70 < x + 120 and zone.x + zone.width > x - 40
            for challenge in world.challenges for zone in challenge.shadows)
        seal_ahead = any(
            world._barrier_is_active(barrier) and barrier.x > x - 30
            for challenge in world.challenges for barrier in challenge.barriers)
        if world.lantern_energy <= 0.055:
            want_light = False
        elif shadow_near or seal_ahead:
            want_light = True
        elif world.lantern_energy < 0.22:
            want_light = False
        else:
            want_light = True
        if want_light != world.lantern_on and world.lantern_energy > 0.02:
            lantern_toggle = True

        enemy_near = any(
            abs(world.enemy_states[enemy.id].x - x) < 64
            and abs(enemy.y - y) < 46
            for challenge in world.challenges for enemy in challenge.enemies
            if enemy.id in world.enemy_states)
        if enemy_near and grounded and blocking_barrier is None:
            jump = True

        if (current is not None and grounded and self.hazard_target is None
                and blocking_barrier is None):
            next_platform = next((p for p in platforms if p.x > current.right + 1), None)
            near_edge = x > current.right - 8
            # Do not launch for a gap while a saw still sits in the jump arc;
            # clear the saw first, then take off from the remaining run-up.
            blocked = any(h.x + h.travel + h.radius > x
                          and h.x - h.travel - h.radius < x + 190
                          for h in hazards)
            if next_platform is not None and not blocked:
                # Aim for a shallow landing near the far platform's near edge
                # instead of sprinting off the lip.  The takeoff point follows
                # from the real ballistic flight time for this height delta.
                caps = world.generator.capabilities
                flight = caps.time_to_height(next_platform.y - current.y)
                if flight is None:
                    jump = near_edge
                else:
                    land_x = next_platform.x + max(24.0, caps.width / 2 + 8)
                    takeoff = land_x - caps.horizontal_speed * flight
                    jump = x >= takeoff
            elif next_platform is None and near_edge:
                jump = True

        # Solve the generated crate/plate puzzle instead of treating its gate
        # as another jump obstacle: jump to the crate's far side, grab and pull
        # it back onto the plate, then pass through the opened seal.
        puzzle = next((runtime for runtime in sorted(
            world.puzzle_runtimes.values(), key=lambda item: item.gate.x)
            if not runtime.solved
            and runtime.gate.x + runtime.gate.w > x - 40), None)
        if puzzle is not None:
            puzzle_id = puzzle.instance.platform_id
            if self.puzzle_platform_id != puzzle_id:
                start_x = puzzle.crate.body.position.x - puzzle.crate.size[0] / 2 - 20
                if x >= start_x:
                    self.puzzle_platform_id = puzzle_id
                    self.puzzle_phase = "jump_over_crate"
                    self.puzzle_jump_started = False
            if self.puzzle_platform_id == puzzle_id:
                action = False
                lantern_toggle = False
                if self.puzzle_phase == "jump_over_crate":
                    move = 1
                    grab = False
                    jump = grounded and not self.puzzle_jump_started
                    if jump:
                        self.puzzle_jump_started = True
                    if x > puzzle.crate.body.position.x + puzzle.crate.size[0] / 2 + 14:
                        self.puzzle_phase = "pull_crate"
                elif self.puzzle_phase == "pull_crate":
                    if world._puzzle_crate_on_plate(puzzle):
                        self.puzzle_phase = "cross_open_gate"
                        move, jump, grab = 1, False, False
                    else:
                        move, jump, grab = -1, False, True
                elif self.puzzle_phase == "cross_open_gate":
                    move, jump, grab = 1, False, False
                    if x > puzzle.gate.x + puzzle.gate.w + PLAYER_SIZE[0]:
                        self.puzzle_platform_id = None
                        self.puzzle_phase = ""
                        self.puzzle_jump_started = False
        if jump:
            self.last_jump_x = x
        self.last_action = action
        return Input(move=move, jump=jump, grab=grab, action=action,
                     lantern=lantern_toggle)
