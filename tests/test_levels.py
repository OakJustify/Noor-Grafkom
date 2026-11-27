import glob
import json

import noor.config as C


def test_levels_valid():
    for path in glob.glob("data/levels/*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "id" in data
        assert data.get("exits")
        cps = sorted(data.get("checkpoints", []), key=lambda c: c["x"])
        prev = None
        for cp in cps:
            if prev is not None:
                assert cp["x"] - prev <= C.LEVEL_CHECKPOINT_MAX_GAP
            prev = cp["x"]


def test_no_huge_jumps():
    for path in glob.glob("data/levels/*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        plats = sorted(data.get("platforms", []), key=lambda p: p["x"])
        for i in range(len(plats) - 1):
            gap = plats[i + 1]["x"] - (plats[i]["x"] + plats[i]["w"])
            if gap > 0:
                assert gap <= C.LEVEL_MAX_JUMP