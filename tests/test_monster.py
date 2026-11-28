from noor.entities.monster import Monster


class FakePlayer:
    x = 10000.0
    y = 0.0
    height = 80
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


class NearPlayer:
    def __init__(self, x):
        self.x = x
        self.y = 0.0
        self.height = 80
        self.covering = False


def test_flying_monster_chases_player_height():
    monster = Monster("m", "M3", 100, 100)
    player = NearPlayer(200)
    player.y = 300.0
    for _ in range(180):
        monster.update(1 / 60, player, None, [])
    assert abs(monster.y - player.y) < 1.0


def test_monster_stops_at_ledge_instead_of_falling():
    platforms = [(0, 640, 200, 20), (320, 600, 200, 20)]
    monster = Monster("m", "M1", 100, 560)
    for _ in range(180):
        monster.update(1 / 60, NearPlayer(400), None, platforms)
    assert monster.on_ground
    assert monster.y + monster.height == 640
    assert monster.x + monster.width <= 200


def test_monster_steps_up_one_tile():
    platforms = [(0, 640, 200, 20), (200, 600, 200, 20)]
    monster = Monster("m", "M1", 100, 560)
    for _ in range(180):
        monster.update(1 / 60, NearPlayer(350), None, platforms)
    assert monster.on_ground
    assert monster.y + monster.height == 600
    assert monster.x > 200


def test_monster_wall_blocks_high_step():
    platforms = [(0, 640, 200, 20), (200, 560, 200, 20)]
    monster = Monster("m", "M1", 100, 560)
    for _ in range(180):
        monster.update(1 / 60, NearPlayer(350), None, platforms)
    assert monster.on_ground
    assert monster.y + monster.height == 640
    assert monster.x + monster.width <= 200


def test_patrol_turns_at_platform_edge():
    platforms = [(0, 640, 200, 20)]
    monster = Monster("m", "M1", 100, 560)
    directions = set()
    for _ in range(600):
        monster.update(1 / 60, FakePlayer(), None, platforms)
        assert monster.x >= 0
        assert monster.x + monster.width <= 200
        directions.add(monster.dir)
    assert directions == {1, -1}
