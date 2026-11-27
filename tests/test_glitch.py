import noor.config as C
from noor.systems.glitch import GlitchSystem, corrupt_text


def test_concurrent_limit():
    g = GlitchSystem(stage=3, accessibility={})
    for _ in range(100):
        g.update(0.5)
    assert len(g.active()) <= C.GLITCH_MAX_CONCURRENT[3]


def test_accessibility_disables():
    g = GlitchSystem(stage=3, accessibility={"reduce_glitch": True})
    g.update(10.0)
    assert g.active() == []


def test_corrupt():
    out = corrupt_text("hello", 1.0, seed=1)
    assert isinstance(out, str)