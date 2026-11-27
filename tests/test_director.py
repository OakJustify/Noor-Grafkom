import noor.config as C
from noor.systems.director import SpawnDirector


def test_hard_cap():
    d = SpawnDirector(stage=4)
    for i in range(50):
        d.request_spawn({"id": f"e{i}", "x": 10000 + i * 10}, 0)
    assert len(d.entities) <= C.GLOBAL_ENTITY_CAP


def test_spawn_min_dist():
    d = SpawnDirector(stage=2)
    # too close
    ok = d.request_spawn({"id": "e1", "x": 100}, 0)
    assert ok is False
    # far enough
    ok2 = d.request_spawn({"id": "e2", "x": 2000}, 0)
    assert ok2 is True