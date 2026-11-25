"""Data-oriented monster spawning, caps and pooling (Python v4 adaptation of F2)."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .types import MonsterType, PiecewiseCurve, SpawnedMonster, SpawnStats


class MonsterSpawnManager:
    """Spawn near the player on authored standable surfaces.

    ``factory(type_id, variant, x, y, kind)`` returns a pooled record.  The
    default factory returns :class:`SpawnedMonster`; games can inject their own
    prefab-like object without changing the manager.
    """

    def __init__(self, seed: int = 0x4E00):
        self.rng = random.Random(seed)
        self.spawn_rate_by_brightness = PiecewiseCurve(
            ((0.0, 0.4), (0.35, 2.0), (0.7, 7.0), (1.0, 14.0)))
        self.max_concurrent_by_time = PiecewiseCurve(
            ((0.0, 6.0), (120.0, 18.0), (300.0, 40.0), (600.0, 80.0), (900.0, 100.0)))
        self.max_same_type_alive = 3
        self.spawn_radius_min = 300.0
        self.spawn_radius_max = 700.0
        self.prewarm_per_type = 5
        self.factory: Callable[[str, str, float, float, int], SpawnedMonster] = (
            lambda type_id, variant, x, y, kind: SpawnedMonster(type_id, variant, kind, x, y))
        self.library: MonsterLibrary | None = None
        self.world = None
        self.player = (0.0, 0.0)
        self.alive: list[SpawnedMonster] = []
        self.pools: dict[str, list[SpawnedMonster]] = {}
        self.alive_by_type: dict[str, int] = {}
        self.rate_accumulator = 0.0
        self.stats = SpawnStats()

    # ------------------------------------------------------------------ setup
    def initialize(self, library: MonsterLibrary, world, player) -> None:
        self.library = library
        self.world = world
        self.player = player
        self.alive.clear()
        self.pools.clear()
        self.alive_by_type = {entry.type_id: 0 for entry in library.types}
        self.rate_accumulator = 0.0
        self.stats = SpawnStats(alive_by_type=dict(self.alive_by_type))
        for entry in library.types:
            queue: list[SpawnedMonster] = []
            for index in range(self.prewarm_per_type):
                variant = entry.variants[index % len(entry.variants)] if entry.variants else entry.type_id
                queue.append(self.factory(entry.type_id, variant, *player, 0))
                queue[-1].active = False
            self.pools[entry.type_id] = queue

    # ------------------------------------------------------------------- pool
    def get_pooled(self, type_id: str, variant: str | None = None,
                   kind: int = 0) -> SpawnedMonster:
        queue = self.pools.setdefault(type_id, [])
        if queue:
            monster = queue.pop()
            if variant is not None:
                monster.variant = variant
            monster.kind = kind
            monster.active = True
            return monster
        return self.factory(type_id, variant or type_id, 0.0, 0.0, kind)

    def return_to_pool(self, monster: SpawnedMonster) -> None:
        monster.active = False
        self.pools.setdefault(monster.type_id, []).append(monster)

    def _release_dead(self) -> None:
        still_alive = []
        for monster in self.alive:
            if monster.active:
                still_alive.append(monster)
            else:
                self.return_to_pool(monster)
                self.alive_by_type[monster.type_id] = max(
                    0, self.alive_by_type.get(monster.type_id, 0) - 1)
        self.alive = still_alive

    # ------------------------------------------------------------------ spawn
    def _eligible(self, level: int) -> list[MonsterType]:
        if self.library is None:
            return []
        return [entry for entry in self.library.types
                if entry.unlock_level <= level
                and entry.variants
                and self.alive_by_type.get(entry.type_id, 0) < self.max_same_type_alive]

    def _ground_positions(self) -> list[tuple[float, float]]:
        if self.world is None:
            return []
        try:
            rects = self.world.terrain_rects()
        except AttributeError:
            return []
        return [(rect.x + rect.w / 2, float(rect.y)) for rect in rects
                if rect.w >= 24 and rect.h >= 8]

    def _position_is_valid(self, x: float, y: float) -> bool:
        if self.world is None:
            return True
        try:
            rects = self.world.terrain_rects()
        except AttributeError:
            return True
        # Never spawn inside a wall or a collider mass.  The surface point
        # itself is allowed to touch the rect it stands on, so only test the
        # space immediately above the requested ground point.
        for rect in rects:
            if rect.h >= 30 and rect.contains(x, y - 2):
                return False
        for monster in self.alive:
            if monster.active and math.hypot(monster.x - x, monster.y - y) < 48:
                return False
        return True

    def _spawn_once(self, level: int) -> SpawnedMonster | None:
        eligible = self._eligible(level)
        if not eligible:
            self.stats.cap_skips += 1
            return None
        weights = [max(0.001, entry.base_weight) for entry in eligible]
        entry = self.rng.choices(eligible, weights=weights, k=1)[0]
        positions = self._ground_positions()
        if not positions:
            return None
        for _ in range(10):
            self.stats.attempts += 1
            px, py = self.player
            angle = self.rng.random() * math.tau
            distance = self.rng.uniform(self.spawn_radius_min, self.spawn_radius_max)
            x = px + math.cos(angle) * distance
            # Snap to the nearest standable surface; reject when the requested
            # radius leaves the authored terrain entirely.
            candidates = [pos for pos in positions if abs(pos[0] - x) < 260]
            if not candidates:
                self.stats.rejected += 1
                continue
            sx, sy = self.rng.choice(candidates)
            actual_distance = math.hypot(sx - px, sy - py)
            if not (self.spawn_radius_min - 80 <= actual_distance <= self.spawn_radius_max + 80):
                self.stats.rejected += 1
                continue
            if not self._position_is_valid(sx, sy):
                self.stats.rejected += 1
                continue
            variant = self.rng.choice(entry.variants)
            monster = self.get_pooled(entry.type_id, variant, eligible.index(entry) % 8)
            monster.reset(sx, sy, variant)
            monster.kind = eligible.index(entry) % 8
            self.alive.append(monster)
            self.alive_by_type[entry.type_id] = self.alive_by_type.get(entry.type_id, 0) + 1
            self.stats.spawned_total += 1
            return monster
        return None

    def tick(self, dt: float, brightness: float, level: int, time_survived: float,
             player=None, world=None) -> list[SpawnedMonster]:
        if self.library is None:
            return []
        if player is not None:
            self.player = player
        if world is not None:
            self.world = world
        self._release_dead()
        max_alive = max(0, int(self.max_concurrent_by_time.evaluate(time_survived)))
        if len(self.alive) >= max_alive:
            self.stats.cap_skips += 1
            self.stats.active = len(self.alive)
            self.stats.alive_by_type = dict(self.alive_by_type)
            return []
        target_per_minute = (self.spawn_rate_by_brightness.evaluate(1.0 - brightness)
                             * (1.0 + time_survived * 0.02)
                             * (1.0 + level * 0.15))
        self.rate_accumulator += target_per_minute / 60.0 * dt
        spawned: list[SpawnedMonster] = []
        while self.rate_accumulator >= 1.0 and len(self.alive) < max_alive:
            monster = self._spawn_once(level)
            if monster is None:
                break
            self.rate_accumulator -= 1.0
            spawned.append(monster)
        self.stats.active = len(self.alive)
        self.stats.alive_by_type = dict(self.alive_by_type)
        return spawned

    def get_stats(self) -> SpawnStats:
        self.stats.active = len(self.alive)
        self.stats.alive_by_type = dict(self.alive_by_type)
        return self.stats


