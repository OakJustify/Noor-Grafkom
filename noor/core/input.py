"""Input state helper."""


class InputState:
    def __init__(self):
        self.left = False
        self.right = False
        self.jump_pressed = False
        self.jump_held = False
        self.interact = False
        self.flare = False
        self.cover = False
        self.run = False

    def reset_frame(self):
        self.jump_pressed = False
        self.interact = False
        self.flare = False