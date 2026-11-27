"""Props / interactive objects."""



class Prop:
    def __init__(self, pid, ptype, x, y, spots=None):
        self.id = pid
        self.type = ptype
        self.x = float(x)
        self.y = float(y)
        self.spots = spots or []
        self.instability = "relocate"

    def interact(self, player):
        return True