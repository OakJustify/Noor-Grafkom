"""Physics wrapper (pymunk optional)."""

try:
    import pymunk
    PYMUNK = True
except Exception:  # noqa: BLE001
    pymunk = None
    PYMUNK = False


class PhysicsWorld:
    def __init__(self):
        if PYMUNK:
            self.space = pymunk.Space()
            self.space.gravity = (0, 2000)
        else:
            self.space = None

    def step(self, dt):
        if self.space is not None:
            self.space.step(dt)