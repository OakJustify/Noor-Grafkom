"""JSON export helpers."""

import json


def to_json(level, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(level, f, indent=2, ensure_ascii=False)
    return path