import pytest

import noor.audio.manager as manager_mod
import noor.config as C
from noor.audio.manager import AudioManager


class _FakeChannel:
    def __init__(self):
        self.volume = 0.0
        self.busy = True

    def set_volume(self, volume):
        self.volume = volume

    def get_busy(self):
        return self.busy

    def stop(self):
        self.busy = False


class _FakeSound:
    def __init__(self, channel):
        self.channel = channel

    def play(self, loops=-1):
        return self.channel


def _fake_manager():
    """A manager whose device is 'ready' but whose beds are fake channels."""
    m = AudioManager(enabled=False)
    m._ready = True
    return m


def test_manager_is_silent_without_a_device():
    m = AudioManager(enabled=False)
    assert m.load_stage(3) is False
    m.set_intensity(0.8, stage=3)
    m.update(1 / 60)
    assert m.play("A01") is False
    m.duck()
    m.stop()
    assert m.stage == 3


def test_reduce_loud_lowers_the_bus():
    m = AudioManager(enabled=False, accessibility={"reduce_loud": True})
    assert m.volumes["music"] < 0.7 and m.volumes["sfx"] < 0.8
    m.apply_accessibility({})
    assert m.volumes["music"] == 0.7 and m.volumes["sfx"] == 0.8


def test_first_bed_does_not_fade_in():
    m = _fake_manager()
    ch = _FakeChannel()
    m._music_cache["L0"] = _FakeSound(ch)
    assert m.play_music("L0")
    assert ch.volume == pytest.approx(m._bed_volume())
    m.update(0.1)
    assert ch.volume == pytest.approx(m._bed_volume())


def test_swapping_beds_crossfades():
    m = _fake_manager()
    old, new = _FakeChannel(), _FakeChannel()
    m._music_cache = {"L0": _FakeSound(old), "S2": _FakeSound(new)}
    assert m.play_music("L0")
    m.update(1.0)
    full = old.volume

    assert m.play_music("S2", volume=C.STAGE_MUSIC_GAIN)
    assert new.volume == 0.0
    assert old.get_busy() and old.volume == pytest.approx(full)

    half = C.CROSSFADE_SECONDS / 2.0
    m.update(half)
    assert 0.0 < new.volume < m._bed_volume()
    assert old.get_busy() and old.volume < full

    m.update(half)
    assert not old.get_busy()
    assert new.volume == pytest.approx(m._bed_volume())
    assert m._fading == []

    m.stop_music()
    assert not new.get_busy() and m._fading == [] and m._music_channel is None


def _stage_manager(monkeypatch):
    """Manager with fake stem sounds and fake beds, so no device is needed."""
    m = _fake_manager()
    made = []

    def fake_to_sound(_arr):
        ch = _FakeChannel()
        made.append(ch)
        return _FakeSound(ch)

    monkeypatch.setattr(m, "_to_sound", fake_to_sound)
    monkeypatch.setattr(manager_mod.ambience, "stems_for_stage", lambda stage: {"drone": [0.0]})
    for stage in (1, 2, 3):
        m._music_cache[f"S{stage}"] = _FakeSound(_FakeChannel())
    return m, made


def test_stage_change_crossfades_the_ambience(monkeypatch):
    m, made = _stage_manager(monkeypatch)
    assert m.load_stage(1)
    m.set_intensity(0.5)
    m.update(1.0)
    old = made[0]
    held = old.volume
    assert held > 0.0

    assert m.load_stage(2)
    new = made[-1]
    assert m._stem_fading and old.get_busy()
    assert old.volume == pytest.approx(held)  # still at full level when the fade starts

    m.update(C.CROSSFADE_SECONDS / 2.0)
    assert old.get_busy() and old.volume < held
    assert new.get_busy() and 0.0 < new.volume < m._gain["drone"]
    assert new.volume <= m._gain["drone"] + 1e-6

    m.update(C.CROSSFADE_SECONDS / 2.0)
    assert not old.get_busy()
    assert m._stem_fading == []
    assert new.volume == pytest.approx(m._gain["drone"], abs=1e-3)
    assert all(c.get_busy() for c in m._channels.values())
    m.stop_music()
    assert not new.get_busy()


def test_fade_out_retires_stems_and_bed(monkeypatch):
    m, made = _stage_manager(monkeypatch)
    bed = _FakeChannel()
    m._music_cache["S1"] = _FakeSound(bed)
    assert m.load_stage(1)
    m.set_intensity(0.5)
    m.update(1.0)
    stem = made[0]
    assert m.playing

    m.fade_out()
    assert m.playing and stem.get_busy() and bed.get_busy()
    m.update(C.CROSSFADE_SECONDS)
    assert not stem.get_busy() and not bed.get_busy()
    assert not m.playing
    assert m._stem_fading == [] and m._fading == []
    assert m._channels == {}


def test_rapid_swaps_do_not_pile_up_beds():
    m = _fake_manager()
    channels = [_FakeChannel() for _ in range(4)]
    for i, ch in enumerate(channels):
        m._music_cache[f"S{i + 1}"] = _FakeSound(ch)
    for i in range(4):
        assert m.play_music(f"S{i + 1}", volume=C.STAGE_MUSIC_GAIN)
        m.update(0.1)
    assert len(m._fading) <= 2
    m.update(C.CROSSFADE_SECONDS)
    assert m._fading == []
    assert channels[-1].get_busy()
    assert sum(1 for ch in channels[:-1] if ch.get_busy()) <= 2
