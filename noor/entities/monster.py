"""Monster (Wujud) entity."""

import noor.config as C


class Monster:
    def __init__(self, mid, mtype, x, y, stage=1):
        self.id = mid
        self.type = mtype
        self.x = float(x)
        self.y = float(y)
        self.stage = int(stage)
        self.state = "patrol"
        self.vx = 0.0
        self.vy = 0.0
        self.notice_timer = 0.0
        self.stun_timer = 0.0
        self.reach = False

    def rect(self):
        return (self.x, self.y, 40, 80)

    def update(self, dt, player, sanity):
        # simple patrol/chase
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        dx = player.x - self.x
        dist = abs(dx)
        # sight
        sight = C.SIGHT_RADIUS
        if getattr(player, "covering", False):
            sight *= C.COVER_SIGHT_MULT
        if dist < sight:
            if self.state in ("patrol", "idle"):
                self.state = "notice"
                self.notice_timer = C.NOTICE_TIME_MAX
            elif self.state == "notice":
                self.notice_timer -= dt
                if self.notice_timer <= 0:
                    self.state = "chase"
        else:
            if self.state == "chase":
                self.state = "patrol"
        if self.state == "chase":
            speed = C.MONSTER_SPEED.get(self.type, (90, 150))[1]
            self.vx = (1 if dx > 0 else -1) * speed
            self.x += self.vx * dt
        elif self.state == "patrol":
            speed = C.MONSTER_SPEED.get(self.type, (90, 150))[0]
            self.vx = speed * 0.3
            self.x += self.vx * dt
        # reach condition (stationary near player)
        if dist < 90 and self.state != "chase":
            self.reach = True