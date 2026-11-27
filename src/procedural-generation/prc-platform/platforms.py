"""Platform generation helpers."""



def choose_type(rng, safe=False):
    if safe:
        return "solid"
    r = rng.random()
    if r < 0.55:
        return "solid"
    if r < 0.75:
        return "oneway"
    if r < 0.85:
        return "lit_only"
    if r < 0.93:
        return "moving"
    return "hazard"


def make_platform(x, y, w, ptype="solid"):
    return {"x": int(x), "y": int(y), "w": int(w), "h": 20, "type": ptype}