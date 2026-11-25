"""Light budget and subjective flare states, not a medical disease simulation."""

from .state import Lantern


class LivingLantern(Lantern):
    def __init__(self):
        super().__init__()
        self.refuges_used = set()
        self.recoveries = 0
        self.focus = False
        self.drain_multiplier = 1.0

    def step(self, dt):
        base = 0.00065 + (0.018 if self.focus else 0)
        self.charge = max(0, self.charge - dt * base * max(1.0, self.drain_multiplier))

    def collect_fragment(self):
        self.collections += 1
        self.capacity = max(0.16, self.capacity - 0.025)
        self.charge = min(self.charge, self.capacity)

    def milestone(self, completed):
        self.capacity = min(self.capacity, max(0.16, 1 - completed / 144 * 0.84))
        self.charge = min(self.charge, self.capacity)

    def kindle(self, key):
        if key in self.refuges_used:
            return False
        self.refuges_used.add(key)
        self.charge = min(self.capacity, self.charge + 0.23)
        return True

    def recover(self):
        self.recoveries += 1
        self.capacity = max(0.16, self.capacity - 0.02)
        self.charge = min(self.capacity, 0.28)

    @property
    def radius(self):
        return 0 if self.charge <= 0 else 65 + 400 * self.charge + (90 if self.focus else 0)

    @property
    def band(self):
        return 0 if self.charge > 0.72 else 1 if self.charge > 0.45 else 2 if self.charge > 0.18 else 3

    def snapshot(self):
        return {**super().snapshot(), "band": self.band, "focus": self.focus,
                "refuges_used": sorted(self.refuges_used), "recoveries": self.recoveries,
                "drain_multiplier": round(self.drain_multiplier, 3),
                "radius": round(self.radius, 2)}
