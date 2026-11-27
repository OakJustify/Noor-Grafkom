"""Sanity (lantern) system."""

import noor.config as C


class SanitySystem:
    def __init__(self, stage=1, S=None, cap=None, fragments=None):
        self.stage = int(stage)
        self.fragments = fragments
        if S is None:
            S = C.S_MAX
        self.S = float(S)
        if cap is None:
            cap = C.CAP[self.stage][0]
        self.cap = float(cap)
        self.flicker = C.FLICKER_BASE
        self.glow_active = False

    @property
    def s_eff(self):
        return min(self.S, self.cap)

    @property
    def s(self):
        return self.S

    @property
    def S_eff(self):
        return self.s_eff

    def set_stage(self, stage):
        self.stage = int(stage)
        if self.cap > C.CAP[self.stage][1]:
            self.cap = C.CAP[self.stage][0]

    def update(self, dt, stage_progress=0.0, fragments=None, paused=False):
        if paused:
            return
        if fragments is not None:
            self.fragments = fragments
        # cap lerp
        lo, hi = C.CAP[self.stage]
        p = max(0.0, min(1.0, float(stage_progress)))
        self.cap = lo + (hi - lo) * p
        self.cap = max(self.cap, C.S_FLOOR)
        # glow
        glow = False
        if self.fragments is not None and getattr(self.fragments, "glow_active", False):
            glow = True
        self.glow_active = glow
        mult = C.GLOW_DECAY_MULT if glow else 1.0
        decay = C.DECAY[self.stage] * mult
        self.S = max(C.S_FLOOR, self.S - decay * float(dt))
        self.S = min(self.S, self.cap)
        # flicker
        self.flicker = C.FLICKER_BASE + (1.0 - self.S / 100.0) * C.FLICKER_RANGE
        if self.flicker < 0:
            self.flicker = 0.0

    def apply(self, event, amount=None):
        ev = str(event).lower()
        if ev in ("contact", "hit"):
            cost = C.CONTACT_COST[self.stage] if amount is None else amount
            self.S = max(C.S_FLOOR, self.S - float(cost))
        elif ev in ("death", "die"):
            self.S = max(C.S_FLOOR, self.S - C.DEATH_COST if amount is None else self.S - float(amount))
        elif ev in ("flare",):
            cost = C.FLARE_COST if amount is None else amount
            self.S = max(C.S_FLOOR, self.S - float(cost))
        elif ev in ("blankout", "blank"):
            cost = 0 if amount is None else amount
            self.S = max(C.S_FLOOR, self.S - float(cost))
        elif ev in ("forget",):
            penalty = C.FORGET_PENALTY_MIN if amount is None else amount
            self.S = max(C.S_FLOOR, self.S - float(penalty))
        elif ev in ("add", "heal", "fragment"):
            amt = 0 if amount is None else amount
            self.S = min(self.cap, self.S + float(amt))
        else:
            if amount is not None:
                self.S = max(C.S_FLOOR, min(self.cap, self.S + float(amount)))
        self.S = min(self.S, self.cap)

    def radius(self):
        S = self.s_eff
        return C.R_MIN + C.R_RANGE * (S / 100.0) ** C.R_EXP

    def intensity(self):
        S_eff = self.s_eff
        I = (100.0 - S_eff) / 100.0 * 0.6 + (self.stage - 1) / 3.0 * 0.4
        I = max(0.0, min(1.0, I))
        return I

    def color(self):
        # emas -> jingga -> bara
        S = self.s_eff
        if S >= 50:
            t = (100 - S) / 50.0
            # lerp FFD27A -> E39A4D
            return (255, int(210 - 38 * t), int(122 - 27 * t))
        else:
            t = (50 - S) / 40.0
            t = max(0.0, min(1.0, t))
            return (int(227 - 141 * t), int(154 - 119 * t), int(77 - 59 * t))