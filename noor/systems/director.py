"""Spawn director for Wujud entities."""

import noor.config as C


class SpawnDirector:
    def __init__(self, stage=1, sanity=None, seed=0):
        self.stage = int(stage)
        self.sanity = sanity
        self.seed = seed
        self.entities = []  # list of dicts
        self.active_count = 0
        self.mercy_deaths = 0
        self.mercy_speed_mult = 1.0
        self._rng = __import__("random").Random(seed)

    def set_stage(self, stage):
        self.stage = int(stage)

    def set_sanity(self, sanity):
        self.sanity = sanity

    def max_active(self):
        base = C.MAX_ACTIVE_BASE[self.stage]
        extra = 0
        thr = C.MAX_ACTIVE_S_THRESHOLD[self.stage]
        s_eff = 100
        if self.sanity is not None:
            s_eff = self.sanity.s_eff
        if thr and s_eff < thr:
            extra = C.MAX_ACTIVE_EXTRA[self.stage]
        crowd = C.CROWD_MAX[self.stage]
        total = base + extra + (crowd if self.stage >= 3 else 0)
        # mercy reduces
        # (handled externally)
        return min(total, C.GLOBAL_ENTITY_CAP)

    def can_spawn(self, x, player_x):
        if abs(x - player_x) < C.SPAWN_MIN_DIST:
            return False
        if self.active_count >= C.GLOBAL_ENTITY_CAP:
            return False
        return not self.active_count >= self.max_active()

    def request_spawn(self, entity, player_x):
        x = entity.get("x", 0)
        if not self.can_spawn(x, player_x):
            return False
        self.entities.append(entity)
        self.active_count = len(self.entities)
        return True

    def spawn(self, entity, player_x=None):
        if player_x is None:
            player_x = entity.get("player_x", 0)
        return self.request_spawn(entity, player_x)

    @property
    def active_entities(self):
        return self.entities

    def update(self, dt, player=None, camera=None):
        # despawn far entities
        if player is not None:
            px = player.x if hasattr(player, "x") else player.get("x", 0)
            self.entities = [e for e in self.entities if abs(e.get("x", 0) - px) <= C.DESPAWN_DIST]
        self.active_count = len(self.entities)
        # enforce hard cap
        if self.active_count > C.GLOBAL_ENTITY_CAP:
            self.entities = self.entities[:C.GLOBAL_ENTITY_CAP]
            self.active_count = len(self.entities)

    def register_death(self):
        self.mercy_deaths += 1
        # speed reduction
        reduction = min(0.4, self.mercy_deaths * C.MERCY_SPEED_PER_DEATH)
        self.mercy_speed_mult = max(C.MERCY_SPEED_MIN, 1.0 - reduction)

    def offer_calm(self):
        return self.mercy_deaths >= C.MERCY_OFFER_DEATHS