import json

import pytest

from echo_game import progress
from echo_game.levels import LEVELS


@pytest.mark.parametrize("chapter", [3, len(LEVELS) - 1])
def test_checkpoint_round_trip(tmp_path, chapter):
    path = tmp_path / "saves" / "echo.json"
    progress.save(chapter, path)
    assert progress.load(path) == chapter
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize("content", ["", "{bad", "[]", "null", '{"chapter": 99}', '{"chapter": true}', '{"chapter": "1"}'])
def test_corrupt_checkpoint_falls_back_safely(tmp_path, content):
    path = tmp_path / "echo.json"
    path.write_text(content)
    assert progress.load(path) == 0


def test_missing_checkpoint_starts_at_beginning(tmp_path):
    assert progress.load(tmp_path / "missing.json") == 0


@pytest.mark.parametrize("chapter", [7, True, 1.5, "1"])
def test_invalid_checkpoint_not_written(tmp_path, chapter):
    with pytest.raises(ValueError):
        progress.save(chapter, tmp_path / "echo.json")
