"""Scene stack manager."""


class SceneManager:
    def __init__(self):
        self.stack = []

    def push(self, scene):
        self.stack.append(scene)
        if hasattr(scene, "enter"):
            scene.enter()

    def pop(self):
        if self.stack:
            s = self.stack.pop()
            if hasattr(s, "exit"):
                s.exit()
            return s

    def replace(self, scene):
        self.pop()
        self.push(scene)

    def handle_event(self, event):
        if self.stack:
            self.stack[-1].handle_event(event)

    def update(self, dt):
        if self.stack:
            self.stack[-1].update(dt)

    def draw(self, surface):
        for s in self.stack:
            s.draw(surface)