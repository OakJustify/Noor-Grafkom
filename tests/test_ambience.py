import numpy as np

import noor.config as C
from noor.audio import ambience


def test_stems_shape_and_level():
    stems = ambience.stems_for_stage(2)
    assert set(stems) == set(ambience.LAYERS)
    ceiling = 10 ** (C.PEAK_DBFS / 20.0)
    for x in stems.values():
        assert x.ndim == 2 and x.shape[1] == 2
        assert x.shape[0] == ambience.loop_samples()
        assert not np.isnan(x).any()
        assert np.max(np.abs(x)) <= ceiling + 1e-6


def test_stems_loop_without_a_step():
    # periodic by construction: the last sample is the one before the first
    for x in ambience.stems_for_stage(4).values():
        assert np.max(np.abs(x[0] - x[-1])) < 0.02


def test_stages_differ():
    a = ambience.stems_for_stage(1)["drone"]
    b = ambience.stems_for_stage(4)["drone"]
    assert np.max(np.abs(a - b)) > 0.05


def test_mix_weights_follow_intensity():
    quiet = ambience.mix_weights(0.0)
    loud = ambience.mix_weights(0.95)
    assert quiet["pulse"] == 0.0 and quiet["shimmer"] == 0.0
    assert loud["pulse"] > 0.0 and loud["shimmer"] > 0.0
    assert sum(loud.values()) <= 1.0 + 1e-9
    assert sum(quiet.values()) <= 1.0 + 1e-9


def test_mix_weights_ramp_monotonically():
    for layer in ("pulse", "breath", "shimmer"):
        values = [ambience.mix_weights(i / 10)[layer] for i in range(11)]
        import itertools
        assert all(b >= a - 1e-9 for a, b in itertools.pairwise(values))
