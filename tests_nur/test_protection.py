import pytest

from echo_game.physics import Input
from nur_game.boss import AlzheimerBoss, Shard
from nur_game.levels import Echo, ThreatSpawn
from nur_game.state import Lantern
from nur_game.threats import Threat, ThreatDirector


@pytest.mark.parametrize("charge", [1.0, 0.5, 0.045, 0.0])
def test_carried_lantern_cancels_attacks_at_every_brightness(charge):
    threat = Threat(ThreatSpawn(100, 425, 80, "memory"), 0.2)
    threat.telegraph, threat.lunge = 0.4, 0.3
    for _ in range(120):
        assert not threat.update(1 / 60, (100, 425), True, charge, lantern_carried=True)
        assert threat.telegraph == threat.lunge == 0
    assert abs(threat.x - 100) >= 140
    assert threat.repelled > 0


def test_shadows_can_only_attack_without_lantern():
    threat = Threat(ThreatSpawn(100, 425, 80, "memory"), 0.2)
    assert threat.update(1 / 60, (100, 425), True, 1.0, lantern_carried=False)
    assert threat.telegraph > 0


@pytest.mark.parametrize("charge", [1.0, 0.0])
def test_boss_neither_fires_nor_hits_carried_lantern(charge):
    boss = AlzheimerBoss((Echo(1600, 200, "memory"),), 5)
    boss.shards.append(Shard(100, 425, 0, 0, telegraph=0))
    for _ in range(600):
        assert boss.update(1 / 60, (100, 425), False, charge, lantern_carried=True) != "hit"
        assert not boss.shards


def test_boss_hit_requires_absent_lantern():
    boss = AlzheimerBoss((Echo(1600, 200, "memory"),), 5)
    boss.shards.append(Shard(100, 425, 0, 0, telegraph=0))
    assert boss.update(1 / 60, (100, 425), False, 1.0, lantern_carried=False) == "hit"


def test_death_does_not_refill_empty_lantern():
    lantern = Lantern()
    for _ in range(4):
        lantern.collect_fragment()
    lantern.die()
    assert lantern.charge == lantern.capacity == 0
    assert lantern.protects


def test_game_can_walk_through_shadow_at_zero_charge(game):
    game.lantern.charge = 0
    game.threats = ThreatDirector((ThreatSpawn(150, 430, 50, "test"),), 2)
    for _ in range(120):
        game.update(1 / 60, Input(move=1))
    assert not game.world.dead
    assert game.world.player.position.x > 400


def test_game_ignores_stale_protected_boss_hit(game):
    before = game.lantern.charge
    game._handle_boss_event("hit")
    assert game.lantern.charge == before
