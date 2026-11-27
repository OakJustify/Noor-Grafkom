"""Procedural level generator."""

import os
import random
import sys

# allow local imports when run as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from platforms import choose_type, make_platform


def _snap(v, step=config.TILE):
    return int(round(v / step) * step)


def generate_platforms(seed=0, length=config.DEFAULT_LENGTH, difficulty="medium", stage=1):
    rng = random.Random(seed)
    platforms = []
    max_gap = 120 if difficulty == "easy" else 140
    max_h = 80 if difficulty == "easy" else 120

    x = 0
    y = config.GROUND_Y
    # initial ground
    w = _snap(rng.randint(400, 800))
    platforms.append(make_platform(x, y, w, "solid"))
    x += w

    while x < length - 600:
        gap = _snap(rng.randint(40, max_gap))
        # vertical change
        dy = _snap(rng.randint(-max_h, max_h))
        dy = max(-max_h, min(max_h, dy))
        ny = y + dy
        ny = max(config.MIN_Y, min(config.MAX_Y, ny))
        # ensure gap not too large for vertical change
        if abs(ny - y) > 80 and gap > 100:
            gap = 80
        # platform width
        pw = _snap(rng.randint(200, 520))
        # safe zone check done later; for now choose type
        safe = False
        ptype = choose_type(rng, safe=safe)
        # avoid hazard on very small platforms
        if pw < 120 and ptype in ("hazard", "moving"):
            ptype = "solid"
        platforms.append(make_platform(x + gap, ny, pw, ptype))
        x = x + gap + pw
        y = ny

    # final ground to exit
    if x < length:
        platforms.append(make_platform(x, config.GROUND_Y, length - x, "solid"))

    # sort and merge overlapping? keep simple
    platforms.sort(key=lambda p: (p["x"], p["y"]))
    return platforms


def place_checkpoints(platforms, length):
    cps = []
    target = 300
    while target < length - 300:
        # choose a platform near target
        candidates = [p for p in platforms if abs((p["x"] + p["w"] // 2) - target) <= 600]
        if not candidates:
            candidates = [min(platforms, key=lambda p: abs((p["x"] + p["w"] // 2) - target))]
        p = candidates[0]
        cx = p["x"] + min(60, p["w"] // 2)
        cy = p["y"]
        if not cps or cx - cps[-1]["x"] >= 500:
            cps.append({"id": f"CP-{len(cps)+1}", "x": int(cx), "y": int(cy)})
        target += 2800
    if not cps:
        cps.append({"id": "CP-1", "x": 220, "y": config.GROUND_Y})
    return cps


def place_fragments(platforms, count=5):
    frags = []
    rng = random.Random(12345)
    candidates = [p for p in platforms if p["type"] == "solid" and p["w"] >= 120]
    rng.shuffle(candidates)
    for i, p in enumerate(candidates[:count]):
        fid = f"F{i+1}"
        fx = p["x"] + p["w"] // 2
        fy = p["y"] - 20
        frags.append({"id": fid, "x": int(fx), "y": int(fy)})
    return frags


def generate_level(seed=0, length=config.DEFAULT_LENGTH, difficulty="medium", stage=1, level_id="gen_01"):
    platforms = generate_platforms(seed=seed, length=length, difficulty=difficulty, stage=stage)
    checkpoints = place_checkpoints(platforms, length)
    # safe zones: platforms near checkpoints become solid
    for cp in checkpoints:
        for p in platforms:
            if abs(p["x"] - cp["x"]) < config.SAFE_ZONE:
                p["type"] = "solid"
    fragments = place_fragments(platforms, count=5 if stage <= 2 else 3)
    monsters = []
    triggers = [{"id": "e_start", "rect": [0, 0, 120, config.BASE_H], "once": True, "actions": []}]
    level = {
        "id": level_id,
        "stage": stage,
        "name_key": f"level.{level_id}",
        "length_px": int(length),
        "tile": config.TILE,
        "palette": "senja",
        "ambient": {"dark_base": 120},
        "spawn": [160, 600],
        "platforms": platforms,
        "props": [],
        "fragments": fragments,
        "checkpoints": checkpoints,
        "monsters": monsters,
        "triggers": triggers,
        "exits": [{"x": int(length - 80), "to_level": None, "card_key": f"card.{level_id}"}],
    }
    return level


def validate_level(level):
    platforms = sorted(level["platforms"], key=lambda p: p["x"])
    # checkpoint gaps
    cps = sorted(level["checkpoints"], key=lambda c: c["x"])
    prev = None
    for cp in cps:
        if prev is not None:
            assert cp["x"] - prev <= config.CHECKPOINT_GAP, "checkpoint gap too large"
        prev = cp["x"]
    assert level["exits"], "missing exit"
    # jump gaps
    for i in range(len(platforms) - 1):
        a = platforms[i]
        b = platforms[i + 1]
        gap = b["x"] - (a["x"] + a["w"])
        if gap > 0:
            # horizontal reach
            assert gap <= 168, f"gap {gap} too wide"
            # vertical reach
            assert abs(b["y"] - a["y"]) <= 120, f"height {abs(b['y']-a['y'])} too high"
    return True