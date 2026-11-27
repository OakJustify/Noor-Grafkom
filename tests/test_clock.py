import noor.config as C
from noor.core.clock import DiseaseClock


def test_forced_stages():
    c = DiseaseClock(stage=1, active_time=0.0)
    c.update(C.CLOCK_DEADLINE[2])  # 480s
    assert c.forced_stage() >= 2
    c2 = DiseaseClock(stage=1, active_time=0.0)
    c2.update(C.CLOCK_DEADLINE[3])
    assert c2.forced_stage() >= 3
    c3 = DiseaseClock(stage=1, active_time=0.0)
    c3.update(C.CLOCK_DEADLINE[4])
    assert c3.forced_stage() >= 4


def test_final():
    c = DiseaseClock(stage=1, active_time=0.0)
    c.update(C.CLOCK_FINAL)
    assert c.is_final()


def test_pause():
    c = DiseaseClock(stage=1, active_time=0.0)
    c.pause()
    c.update(100.0)
    assert c.active_time == 0.0