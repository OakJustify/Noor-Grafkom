"""Layout helpers that adapt UI coordinates to scale."""


def ui_scale(phys_w, phys_h, base_w=1280, base_h=720):
    return min(phys_w / base_w, phys_h / base_h)


def adapt_rect(rect, s):
    x, y, w, h = rect
    return (int(x * s), int(y * s), int(w * s), int(h * s))


def adapt_font_size(size, s, min_size=12):
    return max(min_size, int(size * s))