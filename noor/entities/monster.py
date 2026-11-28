"""Monster (Wujud) entity."""

import noor.config as C


class Monster:
    FLYING_TYPES = frozenset({"M3"})

    def __init__(self, mid, mtype, x, y, stage=1):
        self.id = mid
        self.type = mtype
        self.x = float(x)
        self.y = float(y)
        self.stage = int(stage)
        self.width = 40
        self.height = 80
        self.state = "patrol"
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.notice_timer = 0.0
        self.stun_timer = 0.0
        self.reach = False

    def rect(self):
        return (self.x, self.y, self.width, self.height)

    def update(self, dt, player, sanity, platforms=()):
        # simple patrol/chase
        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.vx = 0.0
        else:
            self.vx = 0.0
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
            elif self.state == "patrol":
                speed = C.MONSTER_SPEED.get(self.type, (90, 150))[0]
                self.vx = speed * 0.3
            # reach condition (stationary near player)
            if dist < 90 and self.state != "chase":
                self.reach = True
        if self.type in self.FLYING_TYPES:
            self.x += self.vx * dt
            return
        # gravity + platform landing, same rules as the player
        self.vy += C.GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.on_ground = False
        for px, py, pw, _ph in platforms:
            if (self.x + self.width > px and self.x < px + pw and
                    self.y + self.height >= py and
                    self.y + self.height <= py + max(_ph, 80) and
                    self.vy >= 0):
                self.y = py - self.height
                self.vy = 0
                self.on_ground = True
