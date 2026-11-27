"""Timeline/keyframe sequencer (minimal)."""


class Timeline:
    def __init__(self):
        self.queue = []
        self.playing = False

    def play(self, name):
        self.queue.append(name)
        self.playing = True

    def update(self, dt):
        pass

    def is_playing(self):
        return self.playing