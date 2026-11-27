"""Camera follow."""

import noor.config as C


class Camera:
    def __init__(self, level_width):
        self.x = 0.0
        self.y = 0.0
        self.level_width = level_width
        self.shake = 0.0
        self.target_x = 0.0
        self.target_y = 0.0

    def update(self, dt, target):
        # target: (x,y)
        tx, ty = target
        # look-ahead
        # simple
        desired_x = tx - C.SCREEN_W / 2
        desired_y = ty - C.SCREEN_H / 2
        self.x += (desired_x - self.x) * min(1.0, C.CAMERA_LERP_X * dt)
        self.y += (desired_y - self.y) * min(1.0, C.CAMERA_LERP_Y * dt)
        # clamp
        self.x = max(self.x, 0)
        if self.x > self.level_width - C.SCREEN_W:
            self.x = max(0, self.level_width - C.SCREEN_W)
        self.y = max(self.y, 0)

    def apply(self, pos):
        return (pos[0] - self.x, pos[1] - self.y)