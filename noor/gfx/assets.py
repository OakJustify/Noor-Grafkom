"""Asset cache (minimal)."""



class AssetCache:
    def __init__(self):
        self.images = {}

    def get(self, key, factory):
        if key not in self.images:
            self.images[key] = factory()
        return self.images[key]