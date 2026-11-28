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
        self.flying = mtype in self.FLYING_TYPES
        self.dir = 1
        self.on_ground = False
        self.notice_timer = 0.0
        self.stun_timer = 0.0
        self.reach = False

    def rect(self):
        return (self.x, self.y, self.width, self.height)

    def _walkable_top(self, target_x, platforms):
        """Ground the monster can step onto, or None when a wall/ledge blocks it."""
        # shortcut: no jump/pathfinding; gaps and walls over one tile stop the monster.
        feet = self.y + self.height
        probe = target_x + self.width if target_x > self.x else target_x
        best = None
        for px, py, pw, ph in platforms:
            if not (px <= probe <= px + pw):
                continue
            if py + ph <= self.y:
                continue  # platform is above the body, walk under it
            if py < feet - C.TILE:
                return None  # wall taller than one tile
            if py <= feet + C.TILE and (
                best is None or abs(py - feet) < abs(best - feet)
            ):
                best = py
        return best

    def _move_horizontal(self, dt, platforms, was_grounded):
        dx = self.vx * dt
        if dx == 0.0:
            return
        if not was_grounded:
            self.x += dx
            return
        target_x = self.x + dx
        top = self._walkable_top(target_x, platforms)
        if top is None:
            self.vx = 0.0
            if self.state == "patrol":
                self.dir *= -1
            return
        self.x = target_x
        if top < self.y + self.height:
            self.y = top - self.height
            self.vy = 0.0
            self.on_ground = True

    def update(self, dt, player, sanity, platforms=(), world=None):
        # simple patrol/chase
        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.vx = 0.0
            if self.flying:
                self.vy = 0.0
        else:
            self.vx = 0.0
            if self.flying:
                self.vy = 0.0
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
                self.vx = 0.0 if abs(dx) <= 2.0 else (1 if dx > 0 else -1) * speed
                if self.flying:
                    target_y = player.y + player.height / 2 - self.height / 2
                    self.vy = max(-speed, min(speed, (target_y - self.y) * 8.0))
            elif self.state == "patrol":
                speed = C.MONSTER_SPEED.get(self.type, (90, 150))[0]
                self.vx = speed * 0.3 * self.dir
            # reach condition (stationary near player)
            if dist < 90 and self.state != "chase":
                self.reach = True
        self._apply_physics(dt, platforms)

    def _apply_physics(self, dt, platforms):
        """Move with the same gravity/platform rules as the player."""
        if self.flying:
            self.x += self.vx * dt
            self.y += self.vy * dt
            return
        was_grounded = self.on_ground
        self._move_horizontal(dt, platforms, was_grounded)
        self.vy += C.GRAVITY * dt
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


