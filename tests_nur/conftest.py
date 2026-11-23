import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from nur_game.game import Game


@pytest.fixture
def game():
    instance = Game(room=0, seed=1234, start=True, muted=True, persist=False)
    yield instance
    instance.audio.close()
