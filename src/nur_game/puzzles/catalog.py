"""Loading of the authored puzzle catalog from neutral JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import config


def load_puzzle_catalog(path: str | Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        path = config.CONTENT_DIR / "puzzles" / "puzzle_catalog.json"
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("puzzles", []))
