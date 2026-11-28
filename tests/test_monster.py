from noor.entities.monster import Monster


class FakePlayer:
    x = 10000.0
    covering = False


def test_ground_monster_falls_and_lands_on_platform():
    monster = Monster("m", "M1", 100, 100)
    platforms = [(0, 500, 400, 40)]
    for _ in range(120):
        monster.update(1 / 60, FakePlayer(), None, platforms)
    assert monster.on_ground
    assert monster.y == 500 - monster.height
    assert monster.vy == 0.0


def test_flying_monster_ignores_gravity():
    monster = Monster("m", "M3", 100, 100)
    platforms = [(0, 500, 400, 40)]
    for _ in range(60):
        monster.update(1 / 60, FakePlayer(), None, platforms)
    assert monster.y == 100.0
    assert not monster.on_ground
