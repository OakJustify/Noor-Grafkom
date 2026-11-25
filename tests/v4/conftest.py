import os

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pytest

from nur_game.game import Game


@pytest.fixture
def game():
    g=Game(seed=1234,muted=True,persist=False)
    yield g
    g.audio.close()
