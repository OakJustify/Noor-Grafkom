import noor.config as C
from noor.systems.fragments import FragmentSystem
from noor.systems.sanity import SanitySystem


def test_retention():
    fs = FragmentSystem(stage=1)
    fs.collect("F1")
    before = fs.slots[0]["remaining"]
    fs.update(10.0)
    assert fs.slots[0]["remaining"] == before - 10.0


def test_forget_penalty():
    sanity = SanitySystem(stage=1, S=50)
    fs = FragmentSystem(stage=1, sanity=sanity)
    fs.collect("F1", value=10, retention=1)
    fs.update(2.0, sanity=sanity)
    assert fs.forgotten_count >= 1
    assert sanity.S == 55.0


def test_max_slots():
    fs = FragmentSystem(stage=1)
    for i in range(7):
        fs.collect(f"F{i}")
    assert len(fs.slots) <= C.MAX_SLOTS


def test_glow():
    fs = FragmentSystem(stage=1)
    fs.collect("F1")
    assert fs.glow_active is True
    fs.update(C.GLOW_DURATION + 1)
    assert fs.glow_active is False
    # decay mult exposed
    assert C.GLOW_DECAY_MULT == 0.4