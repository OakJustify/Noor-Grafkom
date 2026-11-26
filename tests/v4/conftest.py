import os

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pytest

from nur_game.game import Game


@pytest.fixture
def game():
    # Mechanic regressions run without narrative playback; story tests use the live default.
    g=Game(seed=1234,muted=True,persist=False,cinematics=False)
    yield g
    g.audio.close()
