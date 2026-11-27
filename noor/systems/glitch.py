"""Glitch system and text corruption."""

import random

import noor.config as C


def corrupt_text(s, r, seed=None):
    if seed is None:
        seed = 0
    rng = random.Random(seed)
    out = []
    r = float(r)
    for ch in s:
        if ch == " " or rng.random() > r:
            out.append(ch)
            continue
        op = rng.choice(["swap", "drop", "dup", "sym"])
        if op == "drop":
            continue
        if op == "dup":
            out.append(ch)
            out.append(ch)
        elif op == "sym":
            out.append(rng.choice("#?~-_"))
        else:
            out.append(rng.choice("abcdefghijklmnopqrstuvwxyz"))
    return "".join(out)


class GlitchSystem:
    def __init__(self, stage=1, intensity=0.0, accessibility=None):
        self.stage = int(stage)
        self.intensity = float(intensity)
        self.accessibility = accessibility or {}
        self.rng = random.Random(0)
        self.active_glitches = []  # list of ids
        self._timer = 0.0

    def set_stage(self, stage):
        self.stage = int(stage)

    def set_intensity(self, intensity):
        self.intensity = float(intensity)

    def set_accessibility(self, accessibility):
        self.accessibility = accessibility or {}

    def _disabled(self):
        return bool(self.accessibility.get("reduce_glitch", False)) or bool(self.accessibility.get("reduce_flash", False) and False)

    def update(self, dt, stage=None, intensity=None):
        if stage is not None:
            self.stage = int(stage)
        if intensity is not None:
            self.intensity = float(intensity)
        if self._disabled():
            self.active_glitches = []
            return self.active_glitches
        dt = float(dt)
        p = C.GLITCH_P[self.stage]
        # accessibility halves probability
        if self.accessibility.get("reduce_glitch"):
            p *= 0.5
        maxc = C.GLITCH_MAX_CONCURRENT[self.stage]
        # decay timers not tracked individually; simple: chance to add
        # remove random if over cap
        while len(self.active_glitches) > maxc:
            self.active_glitches.pop()
        # attempt spawn
        # expected number this frame
        prob_frame = min(1.0, p * dt)
        if self.rng.random() < prob_frame and len(self.active_glitches) < maxc:
            gid = f"G{len(self.active_glitches)+1:02d}"
            self.active_glitches.append(gid)
        # random removal to keep dynamics
        if self.active_glitches and self.rng.random() < 0.1 * dt * 60:
            self.active_glitches.pop(0)
        return list(self.active_glitches)

    def active(self):
        if self._disabled():
            return []
        return list(self.active_glitches)

    def is_active(self, gid):
        return gid in self.active_glitches