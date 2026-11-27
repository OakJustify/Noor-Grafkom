"""Player entity."""

import noor.config as C


class Player:
    STAMINA_MAX = 100.0
    STAMINA_REGEN = 30.0
    STAMINA_RUN_COST = 18.0
    STAMINA_JUMP_COST = 8.0

    def __init__(self, x=160, y=600):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.covering = False
        self.flare_cooldown = 0.0
        self.invuln = 0.0
        self.alive = True
        self.width = C.PLAYER_W
        self.height = C.PLAYER_H
        self.stamina = self.STAMINA_MAX
        self.running = False
        self.run_locked = False

    def rect(self):
        return (self.x, self.y, self.width, self.height)

    def update(self, dt, inp, platforms, speed_mult=1.0):
        # horizontal
        move = 0
        if inp.left:
            move -= 1
        if inp.right:
            move += 1
        if move != 0:
            self.facing = 1 if move > 0 else -1
        if self.stamina >= 20.0:
            self.run_locked = False
        self.running = bool(inp.run and move != 0 and self.stamina > 0 and not self.run_locked)
        run_mult = 1.5 if self.running else 1.0
        target_vx = move * C.MOVE_SPEED * speed_mult * run_mult
        self.vx = target_vx
        if self.covering:
            self.vx *= C.COVER_SPEED_MULT
        # jump buffer
        if inp.jump_pressed:
            self.jump_buffer = C.JUMP_BUFFER
        else:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)
        # coyote
        if self.on_ground:
            self.coyote = C.COYOTE
        else:
            self.coyote = max(0.0, self.coyote - dt)
        # gravity
        self.vy += C.GRAVITY * dt
        # jump (requires stamina)
        if self.jump_buffer > 0 and self.coyote > 0 and self.stamina >= self.STAMINA_JUMP_COST:
            self.vy = -C.JUMP_V
            self.stamina = max(0.0, self.stamina - self.STAMINA_JUMP_COST)
            self.jump_buffer = 0.0
            self.coyote = 0.0
        # Ketinggian lompatan konsisten: tidak dipotong saat tombol dilepas.
        # (variabel jump dihapus agar spam tombol Space menghasilkan lompatan sama)
        # apply
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.on_ground = False
        # platforms (including ground platforms provided by level data)
        for p in platforms:
            px, py, pw, _ph = p
            if (self.x + self.width > px and self.x < px + pw and
                    self.y + self.height >= py and self.y + self.height <= py + max(_ph, 80) and
                    self.vy >= 0):
                self.y = py - self.height
                self.vy = 0
                self.on_ground = True
        # bounds
        self.x = max(self.x, 0)
        # stamina drain while running
        if self.running:
            self.stamina = max(0.0, self.stamina - self.STAMINA_RUN_COST * dt)
            if self.stamina <= 0:
                self.running = False
                self.run_locked = True
        # stamina regen when not running (and not mid-jump action)
        if not self.running:
            regen = self.STAMINA_REGEN
            if not self.on_ground:
                regen *= 0.5
            self.stamina = min(self.STAMINA_MAX, self.stamina + regen * dt)
        # cooldowns
        self.flare_cooldown = max(0.0, self.flare_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)

    def try_flare(self, sanity):
        if sanity.s_eff < C.FLARE_MIN_S:
            return False
        if self.flare_cooldown > 0:
            return False
        self.flare_cooldown = C.FLARE_COOLDOWN
        sanity.apply("flare")
        return True

    def try_cover(self, holding):
        self.covering = bool(holding)