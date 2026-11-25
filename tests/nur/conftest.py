import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

# These copied tests describe the preserved room-based v3 reference.
# The live v4 controller has its own fixtures and contract in tests/v4/.
from nur_game.baseline_game import Game


@pytest.fixture
def game():
    instance = Game(room=0, seed=1234, start=True, muted=True, persist=False)
    yield instance
    instance.audio.close()
