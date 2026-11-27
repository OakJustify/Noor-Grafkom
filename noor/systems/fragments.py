"""Fragment memory system."""

import noor.config as C


class FragmentSystem:
    def __init__(self, stage=1, sanity=None):
        self.stage = int(stage)
        self.sanity = sanity
        self.slots = []  # list of dict: {id, value, remaining, forgotten}
        self.glow_active = False
        self.glow_timer = 0.0
        self.forgotten_count = 0
        self.last_forget_penalty = 0
        self.collected_ids = set()

    def set_stage(self, stage):
        self.stage = int(stage)

    def _defaults(self):
        return C.FRAGMENT_VALUE[self.stage], C.RETENTION[self.stage]

    def collect(self, fid, value=None, retention=None):
        if value is None or retention is None:
            dv, dr = self._defaults()
            if value is None:
                value = dv
            if retention is None:
                retention = dr
        # if 7th, forget oldest first
        if len(self.slots) >= C.MAX_SLOTS:
            self._forget_oldest()
        slot = {"id": fid, "value": float(value), "remaining": float(retention), "forgotten": False}
        self.slots.append(slot)
        self.collected_ids.add(fid)
        self.glow_active = True
        self.glow_timer = C.GLOW_DURATION
        # sanity boost
        if self.sanity is not None:
            self.sanity.apply("add", value)
            self.sanity.S = min(self.sanity.cap, self.sanity.S)
        return slot

    def _forget_oldest(self):
        if not self.slots:
            return
        slot = self.slots.pop(0)
        slot["forgotten"] = True
        penalty = max(C.FORGET_PENALTY_MIN, slot["value"] * C.FORGET_PENALTY_RATIO)
        penalty = int(penalty) if float(penalty).is_integer() else penalty
        self.last_forget_penalty = penalty
        self.forgotten_count += 1
        if self.sanity is not None:
            self.sanity.apply("forget", penalty)

    def update(self, dt, sanity=None):
        if sanity is not None:
            self.sanity = sanity
        dt = float(dt)
        # glow countdown
        if self.glow_timer > 0:
            self.glow_timer = max(0.0, self.glow_timer - dt)
            self.glow_active = self.glow_timer > 0
        else:
            self.glow_active = False
        # retention countdown
        to_forget = []
        for slot in self.slots:
            slot["remaining"] -= dt
            if slot["remaining"] <= 0:
                to_forget.append(slot)
        for slot in to_forget:
            if slot in self.slots:
                self.slots.remove(slot)
            slot["forgotten"] = True
            penalty = max(C.FORGET_PENALTY_MIN, slot["value"] * C.FORGET_PENALTY_RATIO)
            # keep numeric (int if whole)
            if float(penalty).is_integer():
                penalty = int(penalty)
            self.last_forget_penalty = penalty
            self.forgotten_count += 1
            if self.sanity is not None:
                self.sanity.apply("forget", penalty)

    @property
    def slots_count(self):
        return len(self.slots)