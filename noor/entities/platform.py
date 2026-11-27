"""Platform definitions."""

class Platform:
    def __init__(self, x, y, w, h, ptype="solid"):
        self.x = x; self.y = y; self.w = w; self.h = h; self.type = ptype

    def rect(self):
        return (self.x, self.y, self.w, self.h)