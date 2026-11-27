"""Triggers."""

class Trigger:
    def __init__(self, tid, rect, once=True, actions=None):
        self.id = tid
        self.rect = rect
        self.once = once
        self.actions = actions or []
        self.fired = False