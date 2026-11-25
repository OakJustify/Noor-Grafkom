"""F2 adaptation: curves, caps, terrain-valid spawns and pooling."""

import math

from nur_game.geometry import Rect
from nur_game.spawn_manager import (
    MonsterLibrary,
    MonsterSpawnManager,
    MonsterType,
    PiecewiseCurve,
)


class FakeWorld:
    def __init__(self, rects):
        self.rects = rects

    def terrain_rects(self):
        return self.rects


def world():
    return FakeWorld([Rect(x, 460, 80, 160) for x in range(0, 6000, 120)])


def dense_world():
    return FakeWorld([Rect(x, y, 26, 8) for y in (300, 340, 380, 420, 460)
                      for x in range(0, 6000, 30)])


def library(count=3):
    return MonsterLibrary(tuple(
        MonsterType(f"type{i}", (f"variant{i}a", f"variant{i}b"), 1.0, 0)
        for i in range(count)))


def test_piecewise_curve_clamps_and_interpolates():
    curve = PiecewiseCurve(((0, 0), (10, 20), (20, 0)))
    assert curve.evaluate(-5) == 0
    assert curve.evaluate(5) == 10
    assert curve.evaluate(15) == 10
    assert curve.evaluate(99) == 0


def test_prewarm_pool_and_reuse():
    manager = MonsterSpawnManager(seed=1)
    manager.initialize(library(1), world(), (3000, 430))
    assert len(manager.pools["type0"]) == 5
    monster = manager.get_pooled("type0", "variant0a", 0)
    assert monster.active
    manager.return_to_pool(monster)
    assert not monster.active
    assert manager.get_pooled("type0", "variant0a", 0) is monster


def test_spawns_are_grounded_and_never_exceed_concurrent_cap():
    manager = MonsterSpawnManager(seed=2)
    manager.spawn_rate_by_brightness = PiecewiseCurve(((0, 600), (1, 600)))
    manager.max_concurrent_by_time = PiecewiseCurve(((0, 6), (1000, 6)))
    manager.initialize(library(3), world(), (3000, 430))
    for _ in range(20):
        manager.tick(1.0, 0.1, 0, 0)
    assert 0 < len(manager.alive) <= 6
    assert all(abs(monster.y - 460) < 1e-6 for monster in manager.alive)
    assert all(220 <= math.hypot(monster.x - 3000, monster.y - 430) <= 780
               for monster in manager.alive)
    assert manager.get_stats().active == len(manager.alive)


def test_same_type_hard_cap_blocks_extra_spawns():
    manager = MonsterSpawnManager(seed=3)
    manager.spawn_rate_by_brightness = PiecewiseCurve(((0, 600), (1, 600)))
    manager.max_concurrent_by_time = PiecewiseCurve(((0, 100), (1000, 100)))
    manager.initialize(library(1), world(), (3000, 430))
    for _ in range(30):
        manager.tick(1.0, 0.1, 0, 0)
    assert manager.get_stats().alive_by_type["type0"] == 3
    assert len(manager.alive) == 3


def test_returns_inactive_monsters_to_the_pool():
    manager = MonsterSpawnManager(seed=4)
    manager.spawn_rate_by_brightness = PiecewiseCurve(((0, 600), (1, 600)))
    manager.max_concurrent_by_time = PiecewiseCurve(((0, 100), (1000, 100)))
    manager.initialize(library(1), world(), (3000, 430))
    for _ in range(20):
        manager.tick(1.0, 0.1, 0, 0)
    assert manager.alive
    first = manager.alive[0]
    first.active = False
    manager.spawn_rate_by_brightness = PiecewiseCurve(((0, 0), (1, 0)))
    manager.rate_accumulator = 0.0
    manager.tick(0.0, 0.1, 0, 0)
    assert first not in manager.alive
    assert first in manager.pools[first.type_id]


def test_hundred_concurrent_monsters_without_duplicate_records():
    manager = MonsterSpawnManager(seed=5)
    manager.spawn_rate_by_brightness = PiecewiseCurve(((0, 2400), (1, 2400)))
    manager.max_concurrent_by_time = PiecewiseCurve(((0, 100), (1000, 100)))
    manager.spawn_radius_min = 200
    manager.spawn_radius_max = 2000
    manager.initialize(library(40), dense_world(), (3000, 430))
    for _ in range(20):
        manager.tick(1.0, 0.1, 0, 0)
    assert len(manager.alive) == 100
    assert len({id(monster) for monster in manager.alive}) == 100
    assert all(monster.active for monster in manager.alive)
    assert math.isfinite(sum(monster.x for monster in manager.alive))
