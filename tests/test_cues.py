import numpy as np

from noor.audio import recipes
from noor.audio.cues import CUES, play_cue
from noor.audio.manager import AudioManager


class FakeAudio:
    def __init__(self):
        self.played = []
        self.ducks = []
        self.music = []
        self.stages = []

    def play(self, sid, volume=1.0):
        self.played.append((sid, volume))
        return True

    def duck(self, amount=0.6, seconds=0.4):
        self.ducks.append((amount, seconds))

    def play_music(self, name):
        self.music.append(name)
        return True

    def load_stage(self, stage):
        self.stages.append(stage)
        return True


def test_cue_plays_existing_sfx_and_ducks_ambience():
    a = FakeAudio()
    assert play_cue(a, "fragment") is True
    sid, gain = a.played[0]
    assert sid == CUES["fragment"]["sfx"]
    assert 0 < gain <= 1
    assert a.ducks and a.ducks[0][0] > 0


def test_cue_volume_scales_and_stays_in_range():
    a = FakeAudio()
    play_cue(a, "jump", volume=2.0)
    sid, gain = a.played[0]
    assert sid == "A02" and gain <= 1.0


def test_cue_dispatches_music_and_ambience():
    a = FakeAudio()
    assert play_cue(a, "music:L0") is True
    assert a.music == ["L0"]
    assert play_cue(a, "ambience:3") is True
    assert a.stages == [3]
    assert play_cue(a, "ambience:not-a-stage") is False


def test_unknown_cue_is_silent():
    a = FakeAudio()
    assert play_cue(a, "tidak-ada") is False
    assert play_cue(a, "") is False
    assert a.played == [] and a.music == [] and a.stages == []


def _level(cue):
    """Effective short-term loudness of a cue: file RMS times its cue gain."""
    x = recipes.sfx(CUES[cue]["sfx"])
    rms = float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))
    return rms * CUES[cue]["volume"]


def test_cue_levels_ladder_from_footsteps_up_to_death():
    def db(a, b):
        return 20.0 * np.log10(_level(a) / _level(b))

    assert db("death", "land") >= 5.0
    assert db("death", "jump") >= 8.0
    assert _level("contact") > _level("stage") > _level("interact")
    assert min(_level("jump"), _level("land")) < min(
        _level("fragment"), _level("checkpoint"), _level("forget"))
    assert all(spec["volume"] <= 1.0 for spec in CUES.values())


def test_cues_are_safe_without_a_device():
    m = AudioManager(enabled=False)
    assert m.cue("fragment") is False
    assert m.cue("music:L0") is False
    assert m.cue("ambience:2") is False
    m.stop()
