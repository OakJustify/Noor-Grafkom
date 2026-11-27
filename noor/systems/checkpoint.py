"""Checkpoint system."""


class CheckpointSystem:
    def __init__(self):
        self.checkpoints = []
        self.active_id = None
        self.respawn_pos = (160, 600)
        self.deaths_here = 0

    def load(self, cps):
        self.checkpoints = list(cps)
        if cps:
            self.respawn_pos = (cps[0]["x"], cps[0]["y"])

    def activate(self, cid, pos):
        self.active_id = cid
        self.respawn_pos = pos
        self.deaths_here = 0

    def respawn(self):
        self.deaths_here += 1
        return self.respawn_pos

    def mercy_active(self):
        return self.deaths_here >= 3