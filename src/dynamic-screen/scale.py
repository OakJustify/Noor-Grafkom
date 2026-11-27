"""Scaling helpers for logical 1280x720 to physical screen."""

BASE_W = 1280
BASE_H = 720


def compute_scale(phys_w, phys_h):
    """Uniform scale to fit base resolution into physical size."""
    if phys_w <= 0 or phys_h <= 0:
        return 1.0
    return min(phys_w / BASE_W, phys_h / BASE_H)


def fit_rect(phys_w, phys_h):
    """Return (x, y, w, h) of centered scaled base rect."""
    s = compute_scale(phys_w, phys_h)
    w = int(BASE_W * s)
    h = int(BASE_H * s)
    x = (phys_w - w) // 2
    y = (phys_h - h) // 2
    return x, y, w, h


def scale_point(x, y, s):
    return int(x * s), int(y * s)


def scale_value(v, s):
    return int(v * s)