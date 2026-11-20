"""Procedural puzzle and obstacle generation for ECHO's endless mode.

This module deliberately builds on top of :mod:`echo_game.procedural` instead
of generating its own level.  The platform generator owns geometry; this layer
receives one *already validated* platform and decorates it with a challenge
made from the courier's real movement limits.

Responsibilities are split the same way the design document asks for:

* :class:`PuzzleCatalog` stores challenge definitions and metadata.
* :class:`PuzzleRules` decides which definitions are currently compatible.
* :class:`PuzzleComposer` positions objects on a platform.
* :class:`PuzzleValidator` checks geometry, state, fairness and reachability.
* :class:`PuzzleGenerator` samples candidates with bounded retries and a safe
  no-challenge fallback.
* :class:`ChallengeContext` carries health, lantern and difficulty state.

The module is data-only.  ``EndlessWorld`` owns Pymunk bodies and runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from .levels import Rect


LOW_HEALTH = 0.28
LOW_LANTERN = 0.20
PLAYER_HALF_WIDTH = 11.0
PLAYER_HALF_HEIGHT = 22.0


@dataclass(frozen=True)
class ChallengeContext:
    """Read-only view of the state used to choose a fair challenge."""

    difficulty: float
    health_fraction: float = 1.0
    lantern_fraction: float = 1.0
    distance: float = 0.0
    capabilities: object | None = None
    damage_cap: int = 2
    enemy_types: tuple[str, ...] = ("sentry",)

    def fair_for_damage(self) -> bool:
        return self.health_fraction > LOW_HEALTH


@dataclass(frozen=True)
class ChallengeDefinition:
    kind: str
    label: str
    tags: tuple[str, ...]
    min_difficulty: float
    min_width: float
    weight: float
    damage: int
    requires_light: bool = False
    description: str = ""


CATALOG: tuple[ChallengeDefinition, ...] = (
    ChallengeDefinition(
        "light_gate", "LIGHT SEAL", ("light", "interactive", "gate"),
        1.0, 220.0, 1.15, 0, True,
        "A sealed field opens when the lantern wakes its switch.",
    ),
    ChallengeDefinition(
        "shadow_run", "SHADOW RUN", ("light", "hazard", "environment"),
        1.35, 248.0, 1.10, 1, True,
        "A cold shadow bites only while the lantern is dark.",
    ),
    ChallengeDefinition(
        "sentry", "HOLLOW SENTRY", ("enemy", "combat"),
        1.55, 225.0, 1.05, 1, False,
        "A patrolling sentry recoils from lantern light.",
    ),
    ChallengeDefinition(
        "dark_gate", "DARK THRESHOLD", ("light", "interactive", "gate", "environment"),
        2.35, 285.0, 0.72, 1, True,
        "Cross a shadow, wake the switch, and unseal the edge.",
    ),
    ChallengeDefinition(
        "lit_gauntlet", "LIT GAUNTLET", ("light", "interactive", "enemy", "gate"),
        3.05, 315.0, 0.62, 1, True,
        "A sentry guards the last stretch before a light seal.",
    ),
    ChallengeDefinition(
        "beacon_charge", "LANTERN CACHE", ("light", "safe", "resource"),
        1.0, 195.0, 0.38, 0, False,
        "A small ember restores lantern energy and one measure of health.",
    ),
)


class PuzzleCatalog:
    """Immutable collection of challenge definitions."""

    def __init__(self, definitions: tuple[ChallengeDefinition, ...] = CATALOG):
        self.definitions = definitions
        self.by_kind = {definition.kind: definition for definition in definitions}
        if len(self.by_kind) != len(definitions):
            raise ValueError("Duplicate challenge definition")

    def get(self, kind: str) -> ChallengeDefinition | None:
        return self.by_kind.get(kind)


@dataclass(frozen=True)
class PuzzleRules:
    """Compatibility and fairness gates applied before composition."""

    low_health: float = LOW_HEALTH
    low_lantern: float = LOW_LANTERN

    def reasons(self, definition: ChallengeDefinition, context: ChallengeContext) -> list[str]:
        reasons: list[str] = []
        if context.difficulty + 1e-9 < definition.min_difficulty:
            reasons.append("challenge above current difficulty")
        if definition.damage and context.health_fraction <= self.low_health:
            reasons.append("damage challenge at low health")
        if definition.requires_light and context.lantern_fraction <= self.low_lantern:
            reasons.append("light challenge at low lantern")
        if "environment" in definition.tags and context.lantern_fraction <= self.low_lantern:
            reasons.append("shadow challenge at low lantern")
        return reasons

    def eligible(self, catalog: PuzzleCatalog, context: ChallengeContext,
                 minimum_width: float) -> list[ChallengeDefinition]:
        return [definition for definition in catalog.definitions
                if definition.min_width <= minimum_width
                and not self.reasons(definition, context)]


@dataclass(frozen=True)
class ChallengeConfig:
    platform_edge_margin: float = 34.0
    switch_margin: float = 38.0
    switch_gap: float = 74.0
    switch_radius: float = 34.0
    barrier_width: float = 18.0
    barrier_height: float = 132.0
    barrier_offset: float = 20.0
    shadow_height: float = 64.0
    shadow_margin: float = 62.0
    enemy_width: float = 24.0
    enemy_height: float = 36.0
    enemy_margin: float = 52.0
    enemy_patrol_margin: float = 56.0
    cache_radius: float = 24.0
    max_attempts: int = 6
    layout_attempts: int = 3
    resource_chance: float = 0.82
    low_health: float = LOW_HEALTH
    low_lantern: float = LOW_LANTERN

    def __post_init__(self):
        if self.max_attempts < 1 or self.layout_attempts < 1:
            raise ValueError("Challenge retry limits must be positive")


@dataclass(frozen=True)
class LightSwitch:
    id: int
    x: float
    y: float
    radius: float
    barrier_id: int
    challenge_id: int

    @property
    def rect(self) -> Rect:
        return Rect(self.x - 8, self.y - 22, 16, 44)


@dataclass(frozen=True)
class LightBarrier:
    id: int
    x: float
    y: float
    width: float
    height: float
    switch_id: int
    challenge_id: int

    @property
    def rect(self) -> Rect:
        return Rect(self.x - self.width / 2, self.y - self.height / 2,
                    self.width, self.height)

    @property
    def bottom(self) -> float:
        return self.y + self.height / 2


@dataclass(frozen=True)
class ShadowZone:
    id: int
    x: float
    y: float
    width: float
    height: float
    damage: int
    challenge_id: int

    @property
    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class EnemySpec:
    id: int
    x: float
    y: float
    width: float
    height: float
    patrol_left: float
    patrol_right: float
    speed: float
    damage: int
    challenge_id: int

    @property
    def rect(self) -> Rect:
        return self.rect_at(self.x)

    def rect_at(self, x: float) -> Rect:
        """Shared centre anchor for validation, runtime damage, and rendering."""
        return Rect(x - self.width / 2, self.y - self.height / 2,
                    self.width, self.height)

    @property
    def patrol_rect(self) -> Rect:
        return Rect(self.patrol_left - self.width / 2, self.y - self.height / 2,
                    self.patrol_right - self.patrol_left + self.width, self.height)


@dataclass(frozen=True)
class LightCache:
    id: int
    x: float
    y: float
    radius: float
    challenge_id: int

    @property
    def rect(self) -> Rect:
        return Rect(self.x - self.radius, self.y - self.radius,
                    self.radius * 2, self.radius * 2)


@dataclass(frozen=True)
class Challenge:
    id: int
    kind: str
    label: str
    tags: tuple[str, ...]
    platform_id: int
    generation_index: int
    difficulty: float
    damage: int
    requires_light: bool = False
    switches: tuple[LightSwitch, ...] = ()
    barriers: tuple[LightBarrier, ...] = ()
    shadows: tuple[ShadowZone, ...] = ()
    enemies: tuple[EnemySpec, ...] = ()
    caches: tuple[LightCache, ...] = ()

    @property
    def damage_cost(self) -> int:
        return max(self.damage, sum(z.damage for z in self.shadows)
                   + sum(e.damage for e in self.enemies))


@dataclass
class ChallengeStats:
    requests: int = 0
    generated: int = 0
    skipped: int = 0
    fallbacks: int = 0
    rejections: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "requests": self.requests,
            "generated": self.generated,
            "skipped": self.skipped,
            "fallbacks": self.fallbacks,
            "rejections": self.rejections,
            "by_kind": dict(sorted(self.by_kind.items())),
        }


def rects_overlap(first: Rect, second: Rect, padding: float = 0.0) -> bool:
    return (first.x < second.x + second.w + padding
            and second.x - padding < first.x + first.w
            and first.y < second.y + second.h + padding
            and second.y - padding < first.y + first.h)


class PuzzleComposer:
    """Place mechanics on a platform without changing its geometry."""

    def __init__(self, config: ChallengeConfig | None = None):
        self.config = config or ChallengeConfig()

    def minimum_width(self, definition: ChallengeDefinition) -> float:
        """Use the same margins for eligibility and actual composition."""
        cfg = self.config
        width = cfg.barrier_offset + cfg.switch_gap + cfg.switch_margin + 24
        if definition.kind == "shadow_run":
            width = (4 * cfg.shadow_margin if cfg.shadow_margin <= 75
                     else 2 * cfg.shadow_margin + 150)
        elif definition.kind == "sentry":
            width = 2 * cfg.enemy_patrol_margin + 78
        elif definition.kind == "dark_gate":
            width = (max(cfg.switch_margin, cfg.shadow_margin + 62 + cfg.switch_gap * .55)
                     + cfg.barrier_offset + cfg.switch_gap + 24)
        elif definition.kind == "lit_gauntlet":
            width = (cfg.switch_margin + cfg.barrier_offset + cfg.enemy_margin
                     + cfg.enemy_patrol_margin + 78 + 24)
        elif definition.kind == "beacon_charge":
            width = 2 * (cfg.cache_radius + cfg.platform_edge_margin)
        return max(definition.min_width, width)

    def compose(self, definition: ChallengeDefinition, platform,
                difficulty: float, rng: random.Random,
                start_id: int) -> tuple[Challenge | None, int]:
        cfg = self.config
        next_id = start_id
        challenge_id = next_id
        next_id += 1
        switches: list[LightSwitch] = []
        barriers: list[LightBarrier] = []
        shadows: list[ShadowZone] = []
        enemies: list[EnemySpec] = []
        caches: list[LightCache] = []

        def add_gate() -> bool:
            nonlocal next_id
            barrier_x = platform.right - cfg.barrier_offset
            low = platform.x + cfg.switch_margin
            high = barrier_x - cfg.switch_gap
            if definition.kind == "dark_gate":
                low = max(low, platform.x + cfg.shadow_margin + 62 + cfg.switch_gap * .55)
            elif definition.kind == "lit_gauntlet":
                high = min(high, barrier_x - cfg.enemy_margin - cfg.enemy_patrol_margin - 78)
            if high - low < 24:
                return False
            switch_x = rng.uniform(low, high)
            barrier_id = next_id
            next_id += 1
            switch_id = next_id
            next_id += 1
            barriers.append(LightBarrier(
                barrier_id, barrier_x, platform.y - cfg.barrier_height / 2,
                cfg.barrier_width, cfg.barrier_height, switch_id, challenge_id))
            switches.append(LightSwitch(
                switch_id, switch_x, platform.y - 22, cfg.switch_radius,
                barrier_id, challenge_id))
            return True

        def add_shadow(left: float, right: float) -> bool:
            nonlocal next_id
            if right - left < 62 - 1e-8:
                return False
            shadows.append(ShadowZone(
                next_id, left, platform.y - cfg.shadow_height,
                right - left, cfg.shadow_height, 1, challenge_id))
            next_id += 1
            return True

        def add_enemy(left: float, right: float) -> bool:
            nonlocal next_id
            if right - left < 78 - 1e-8:
                return False
            enemies.append(EnemySpec(
                next_id, (left + right) / 2, platform.y - cfg.enemy_height / 2,
                cfg.enemy_width, cfg.enemy_height, left, right,
                42.0 + 5.0 * max(0.0, difficulty - 1.0), 1, challenge_id))
            next_id += 1
            return True

        if definition.kind == "light_gate":
            if not add_gate():
                return None, start_id
        elif definition.kind == "shadow_run":
            span = min(150.0, platform.width * 0.5)
            low = platform.x + cfg.shadow_margin
            high = platform.right - cfg.shadow_margin - span
            if high < low:
                return None, start_id
            x = rng.uniform(low, high)
            if not add_shadow(x, x + span):
                return None, start_id
        elif definition.kind == "sentry":
            left = platform.x + cfg.enemy_patrol_margin
            right = platform.right - cfg.enemy_patrol_margin
            if not add_enemy(left, right):
                return None, start_id
        elif definition.kind == "dark_gate":
            barrier_x = platform.right - cfg.barrier_offset
            if not add_gate():
                return None, start_id
            switch = switches[-1]
            if not add_shadow(platform.x + cfg.shadow_margin,
                              switch.x - cfg.switch_gap * 0.55):
                return None, start_id
        elif definition.kind == "lit_gauntlet":
            if not add_gate():
                return None, start_id
            switch = switches[-1]
            left = switch.x + cfg.enemy_patrol_margin
            right = platform.right - cfg.barrier_offset - cfg.enemy_margin
            if not add_enemy(left, right):
                return None, start_id
        elif definition.kind == "beacon_charge":
            caches.append(LightCache(
                next_id, platform.x + platform.width / 2,
                platform.y - cfg.cache_radius, cfg.cache_radius, challenge_id))
            next_id += 1
        else:
            return None, start_id

        return Challenge(
            id=challenge_id, kind=definition.kind, label=definition.label,
            tags=definition.tags, platform_id=platform.id,
            generation_index=platform.generation_index,
            difficulty=difficulty, damage=definition.damage,
            requires_light=definition.requires_light,
            switches=tuple(switches), barriers=tuple(barriers),
            shadows=tuple(shadows), enemies=tuple(enemies),
            caches=tuple(caches)), next_id


class PuzzleValidator:
    """Bounded geometric, state and fairness validation."""

    def __init__(self, config: ChallengeConfig | None = None):
        self.config = config or ChallengeConfig()

    def validate(self, challenge: Challenge, platform, context: ChallengeContext,
                 hazards=()) -> list[str]:
        cfg = self.config
        reasons: list[str] = []
        if challenge.platform_id != platform.id:
            reasons.append("challenge platform mismatch")
        if challenge.generation_index != platform.generation_index:
            reasons.append("challenge generation mismatch")
        if not 0 <= challenge.id:
            reasons.append("invalid challenge id")
        if context.health_fraction <= cfg.low_health and challenge.damage_cost:
            reasons.append("damage challenge at low health")
        if challenge.damage_cost > context.damage_cap:
            reasons.append("challenge exceeds damage budget")
        if challenge.enemies and "sentry" not in context.enemy_types:
            reasons.append("enemy type is disabled")
        if (context.lantern_fraction <= cfg.low_lantern
                and challenge.requires_light):
            reasons.append("light challenge at low lantern")

        barrier_by_id = {barrier.id: barrier for barrier in challenge.barriers}
        switch_by_id = {switch.id: switch for switch in challenge.switches}
        if len(barrier_by_id) != len(challenge.barriers):
            reasons.append("duplicate barrier id")
        if len(switch_by_id) != len(challenge.switches):
            reasons.append("duplicate switch id")
        capabilities = context.capabilities
        max_jump = (getattr(capabilities, "max_jump_height", 94.3)
                    if capabilities is not None else 94.3)
        minimum_seal = max_jump + 30.0
        for barrier in challenge.barriers:
            if barrier.switch_id not in switch_by_id:
                reasons.append("barrier has no switch")
            if barrier.height < minimum_seal:
                reasons.append("barrier can be jumped")
            if barrier.bottom > platform.y + 1:
                reasons.append("barrier hangs below platform")
            if barrier.y + barrier.height / 2 < platform.y - 145:
                reasons.append("barrier leaves playfield")
            if barrier.x - barrier.width / 2 < platform.x + platform.width * 0.45:
                reasons.append("barrier too close to landing")
            if barrier.x + barrier.width / 2 > platform.right + 1:
                reasons.append("barrier leaves platform")
            if rects_overlap(barrier.rect, platform.rect, padding=-1):
                reasons.append("barrier intersects platform")
        for switch in challenge.switches:
            if switch.barrier_id not in barrier_by_id:
                reasons.append("switch has no barrier")
            if not platform.x + 18 <= switch.x <= platform.right - 18:
                reasons.append("switch outside platform")
            if abs(switch.y - (platform.y - 22)) > 2:
                reasons.append("switch is not at courier height")
            barrier = barrier_by_id.get(switch.barrier_id)
            if barrier:
                if switch.x >= barrier.x - 12:
                    reasons.append("switch unreachable behind barrier")
                if abs(switch.x - barrier.x) < cfg.switch_gap - 12:
                    reasons.append("switch too close to barrier")
        for shadow in challenge.shadows:
            if shadow.x < platform.x + 24:
                reasons.append("shadow invades landing zone")
            if shadow.x + shadow.width > platform.right - 24:
                reasons.append("shadow invades takeoff run")
            if abs(shadow.y + shadow.height - platform.y) > 1:
                reasons.append("shadow does not rest on platform")
            if shadow.height < 32 or shadow.height > 90:
                reasons.append("shadow height out of bounds")
        for enemy in challenge.enemies:
            if enemy.patrol_left < platform.x + 24 or enemy.patrol_right > platform.right - 24:
                reasons.append("enemy patrol leaves platform")
            if enemy.patrol_right - enemy.patrol_left < 58:
                reasons.append("enemy patrol too short")
            if enemy.y + enemy.height / 2 > platform.y + 1:
                reasons.append("enemy sinks into platform")
            if not enemy.patrol_left - 1 <= enemy.x <= enemy.patrol_right + 1:
                reasons.append("enemy outside its patrol")
        for cache in challenge.caches:
            if not platform.x + 24 <= cache.x <= platform.right - 24:
                reasons.append("cache outside platform")
            if abs(cache.y - (platform.y - cache.radius)) > 2:
                reasons.append("cache not resting on platform")

        objects = ([("barrier", barrier.rect) for barrier in challenge.barriers]
                   + [("shadow", shadow.rect) for shadow in challenge.shadows]
                   + [("enemy", enemy.patrol_rect) for enemy in challenge.enemies]
                   + [("switch", switch.rect) for switch in challenge.switches]
                   + [("cache", cache.rect) for cache in challenge.caches])
        for index, (first_name, first) in enumerate(objects):
            for second_name, second in objects[index + 1:]:
                if rects_overlap(first, second, padding=4):
                    reasons.append(f"{first_name} overlaps {second_name}")
        for hazard in hazards:
            left = hazard.x - getattr(hazard, "travel", 0.0) - hazard.radius
            right = hazard.x + getattr(hazard, "travel", 0.0) + hazard.radius
            sweep = Rect(left, hazard.y - hazard.radius,
                         max(1.0, right - left), hazard.radius * 2)
            for name, rect in objects:
                if rects_overlap(sweep, rect, padding=8):
                    reasons.append(f"{name} overlaps a saw")
        return reasons


class PuzzleGenerator:
    """Select, compose and validate one challenge for a platform."""

    def __init__(self, seed: int, config: ChallengeConfig | None = None,
                 catalog: PuzzleCatalog | None = None,
                 rules: PuzzleRules | None = None,
                 validator: PuzzleValidator | None = None,
                 composer: PuzzleComposer | None = None):
        self.seed = int(seed)
        # A separate stream means challenge choices never consume the platform
        # generator's random sequence, but every seed still replays exactly.
        self.rng = random.Random((self.seed * 6364136223846793005 + 0x5EED) & 0xFFFFFFFFFFFFFFFF)
        self.config = config or ChallengeConfig()
        self.catalog = catalog or PuzzleCatalog()
        self.rules = rules or PuzzleRules()
        self.validator = validator or PuzzleValidator(self.config)
        self.composer = composer or PuzzleComposer(self.config)
        self.next_object_id = 1
        self.stats = ChallengeStats()

    def _chance(self, profile, context: ChallengeContext) -> float:
        chance = float(getattr(profile, "challenge_probability", 0.28))
        if (context.health_fraction <= self.config.low_health
                or context.lantern_fraction <= self.config.low_lantern):
            chance = self.config.resource_chance
        return max(0.0, min(1.0, chance))

    def generate(self, platform, profile, context: ChallengeContext,
                  previous=None, hazards=()) -> Challenge | None:
        self.stats.requests += 1
        urgent = (context.health_fraction <= self.config.low_health
                   or context.lantern_fraction <= self.config.low_lantern)
        # Independent category controls: safe caches are not counted as puzzles.
        puzzle_roll, obstacle_roll, resource_roll = (self.rng.random() for _ in range(3))
        puzzle_requested = puzzle_roll < self._chance(profile, context)
        obstacle_requested = obstacle_roll < float(getattr(profile, "obstacle_probability", .20))
        combo_requested = (obstacle_requested and self.rng.random()
                           <= float(getattr(profile, "combo_probability", 0)))
        eligible = self.rules.eligible(self.catalog, context, platform.width)
        eligible = [d for d in eligible
                    if platform.width + 1e-8 >= self.composer.minimum_width(d)
                    and d.damage <= min(context.damage_cap, getattr(profile, "challenge_damage_cap", 2))
                    and not ("enemy" in d.tags and "sentry" not in context.enemy_types)]
        if urgent:
            eligible = [d for d in eligible if "resource" in d.tags]
            if resource_roll > self.config.resource_chance:
                eligible = []
        elif puzzle_requested:
            eligible = [d for d in eligible if "interactive" in d.tags
                        and (not d.damage or combo_requested)]
            combos = [d for d in eligible if d.damage]
            if combo_requested and combos:
                eligible = combos
        elif obstacle_requested:
            eligible = [d for d in eligible if d.damage and "interactive" not in d.tags]
        else:
            eligible = [d for d in eligible if "resource" in d.tags and resource_roll <= .08]
        if not eligible:
            self.last_selection = {"puzzle_requested": puzzle_requested, "obstacle_requested": obstacle_requested,
                                   "combo_requested": combo_requested, "urgent_recovery": urgent,
                                   "eligible": [], "reason": "no compatible requested category"}
            self.stats.skipped += 1
            return None
        self.last_selection = {"puzzle_requested": puzzle_requested, "obstacle_requested": obstacle_requested,
                               "combo_requested": combo_requested, "urgent_recovery": urgent,
                               "eligible": [d.kind for d in eligible]}
        remaining = list(eligible)
        layout_counts = {}
        for _ in range(self.config.max_attempts):
            if not remaining:
                break
            weights = [definition.weight for definition in remaining]
            definition = self.rng.choices(remaining, weights=weights, k=1)[0]
            layout_counts[definition.kind] = layout_counts.get(definition.kind, 0) + 1
            if layout_counts[definition.kind] >= self.config.layout_attempts:
                remaining.remove(definition)
            challenge, next_id = self.composer.compose(
                definition, platform, context.difficulty, self.rng,
                self.next_object_id)
            if challenge is None:
                self.stats.rejections += 1
                continue
            reasons = self.validator.validate(
                challenge, platform, context, hazards=hazards)
            if reasons:
                self.stats.rejections += 1
                continue
            self.next_object_id = next_id
            self.stats.generated += 1
            self.stats.by_kind[definition.kind] = (
                self.stats.by_kind.get(definition.kind, 0) + 1)
            return challenge
        self.stats.fallbacks += 1
        return None


def player_rect(position) -> Rect:
    """The collision-sized rectangle used for damage overlap checks."""

    x, y = position
    return Rect(x - PLAYER_HALF_WIDTH, y - PLAYER_HALF_HEIGHT,
                PLAYER_HALF_WIDTH * 2, PLAYER_HALF_HEIGHT * 2)


def distance(first, second) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])
