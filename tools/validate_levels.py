"""Validate level JSON files."""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import noor.config as C


def validate(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert "id" in data and "length_px" in data
    # checkpoint gaps
    cps = sorted(data.get("checkpoints", []), key=lambda c: c["x"])
    prev = None
    for cp in cps:
        if prev is not None:
            assert cp["x"] - prev <= C.LEVEL_CHECKPOINT_MAX_GAP, (path, cp["x"] - prev)
        prev = cp["x"]
    assert data.get("exits"), f"no exit in {path}"
    # jumps: platforms sorted; gaps <= 168
    plats = sorted(data.get("platforms", []), key=lambda p: p["x"])
    for i in range(len(plats) - 1):
        gap = plats[i + 1]["x"] - (plats[i]["x"] + plats[i]["w"])
        if gap > 0:
            assert gap <= C.LEVEL_MAX_JUMP, (path, gap)
    return True


def main():
    ok = True
    for path in sorted(glob.glob("data/levels/*.json")):
        try:
            validate(path)
            print("OK", path)
        except Exception as e:  # noqa: BLE001
            ok = False
            print("FAIL", path, e)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()