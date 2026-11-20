"""Room checkpoints, with atomic writes and tolerant reads."""

import json
from pathlib import Path

from .levels import LEVELS

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "saves" / "echo.json"


def load(path: Path = DEFAULT_PATH) -> int:
    try:
        data = json.loads(path.read_text())
        value = data["chapter"]
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(LEVELS):
            return value
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return 0


def save(chapter: int, path: Path = DEFAULT_PATH):
    if not isinstance(chapter, int) or isinstance(chapter, bool) or not 0 <= chapter < len(LEVELS):
        raise ValueError("Invalid checkpoint")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"version": 1, "chapter": chapter}) + "\n")
    temp.replace(path)
