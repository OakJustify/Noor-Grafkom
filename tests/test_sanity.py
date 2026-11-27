import noor.config as C
from noor.systems.sanity import SanitySystem


def test_cap_decreases():
    s = SanitySystem(stage=1)
    s.update(1.0, stage_progress=1.0)
    assert s.cap <= 100 and s.cap >= 88


def test_decay():
    s = SanitySystem(stage=1, S=100)
    s.update(10.0, stage_progress=0.0)
    assert s.S < 100


def test_floor():
    s = SanitySystem(stage=4, S=3)
    s.update(1000.0)
    assert s.S >= C.S_FLOOR


def test_cost_event():
    s = SanitySystem(stage=1, S=50)
    before = s.S
    s.apply("contact")
    assert s.S == before - C.CONTACT_COST[1]


def test_seff_min():
    s = SanitySystem(stage=2, S=90)
    s.cap = 60
    assert s.s_eff == 60


def test_death_no_recover():
    s = SanitySystem(stage=1, S=50)
    before = s.S
    s.apply("death")
    assert s.S == before - C.DEATH_COST