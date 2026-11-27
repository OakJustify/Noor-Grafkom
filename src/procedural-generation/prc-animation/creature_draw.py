"""Placeholder modular renderer for procedural creatures.

Pieces are drawn through a depth-sorted list so real sprite parts can replace
each shape later without changing the pose contract.  ``offset`` is added to
world coordinates, so pass ``(-camera.x, -camera.y)``.
"""

import math

import pygame


def _shade(color, factor=0.65):
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


def _segment(surface, a, b, width, color, ox, oy):
    pygame.draw.line(
        surface,
        color,
        (int(a[0] + ox), int(a[1] + oy)),
        (int(b[0] + ox), int(b[1] + oy)),
        max(1, int(width)),
    )
    pygame.draw.circle(
        surface,
        color,
        (int(a[0] + ox), int(a[1] + oy)),
        max(1, int(width) // 2),
    )
    pygame.draw.circle(
        surface,
        color,
        (int(b[0] + ox), int(b[1] + oy)),
        max(1, int(width) // 2),
    )


def _shadow(surface, x, ground_y, width, ox, oy):
    pygame.draw.ellipse(
        surface,
        (48, 52, 60),
        (int(x - width / 2 + ox), int(ground_y - 4 + oy), int(width), 8),
    )


def _scale_point(point, cx, cy, sx, sy):
    return (cx + (point[0] - cx) * sx, cy + (point[1] - cy) * sy)


def _eye(surface, anim, ox, oy, head=None, radius=None):
    s = anim.spec
    head = anim.head if head is None else head
    if radius is None:
        radius = s.head_r * 0.5 * (anim.body_scale_x + anim.body_scale_y)
    look = anim.head_angle
    ex = head[0] + anim.facing * math.cos(look) * radius * 0.45
    ey = head[1] + math.sin(look) * radius * 0.45 - radius * 0.08
    if anim.blink > 0.5:
        pygame.draw.line(
            surface,
            (28, 28, 34),
            (int(ex - 3 + ox), int(ey + oy)),
            (int(ex + 3 + ox), int(ey + oy)),
            2,
        )
        return
    pygame.draw.circle(
        surface,
        (28, 28, 34),
        (int(ex + ox), int(ey + oy)),
        max(2, int(radius * 0.18)),
    )


def _hit_ring(surface, anim, ox, oy):
    if anim.state != "hit":
        return
    pygame.draw.circle(
        surface,
        (230, 90, 90),
        (int(anim.body_x + ox), int(anim.body_y + oy)),
        int(anim.spec.body_h * 0.7),
        2,
    )


def _draw_leg(surface, anim, leg, color, width, ox, oy):
    _segment(surface, leg.hip, leg.knee, width, color, ox, oy)
    _segment(surface, leg.knee, leg.foot, max(2, width - 1), color, ox, oy)
    foot_len = anim.spec.foot_len
    if foot_len > 0.0:
        heel = (leg.foot[0] - anim.facing * foot_len * 0.65, leg.foot[1])
        toe = (leg.foot[0] + anim.facing * foot_len * 0.35, leg.foot[1])
        _segment(surface, heel, toe, max(2, width * 0.7), color, ox, oy)
    pygame.draw.circle(
        surface,
        color,
        (int(leg.foot[0] + ox), int(leg.foot[1] + oy)),
        max(2, int(anim.spec.foot_r)),
    )


def _arm(surface, anim, arm, width, color, ox, oy):
    _segment(surface, arm[0], arm[1], width, color, ox, oy)
    _segment(surface, arm[1], arm[2], max(2, width - 1), color, ox, oy)


def _draw_biped(surface, anim, ox, oy):
    s = anim.spec
    far = _shade(s.color)
    leg_w = max(3, int(s.body_w * 0.24))
    arm_w = max(3, int(s.body_w * 0.20))
    sx = anim.body_scale_x
    sy = anim.body_scale_y
    hip = anim.hip_center
    shoulder = (
        hip[0] + (anim.shoulder[0] - hip[0]) * sx,
        hip[1] + (anim.shoulder[1] - hip[1]) * sy,
    )
    head = (
        shoulder[0] + (anim.head[0] - anim.shoulder[0]) * sx,
        shoulder[1] + (anim.head[1] - anim.shoulder[1]) * sy,
    )
    head_r = s.head_r * 0.5 * (sx + sy)
    pieces = []

    def add(z, y, fn):
        pieces.append((z, y, fn))

    add(0, anim.y, lambda: _shadow(
        surface, anim.x, anim.y, s.body_w * 2.2, ox, oy
    ))
    for arm in anim.arms:
        if arm[3] == 1:
            add(1, arm[0][1], lambda a=arm: _arm(
                surface, anim, a, arm_w, far, ox, oy
            ))
    for leg in anim.legs:
        if leg.depth == 1:
            add(2, leg.hip[1], lambda l=leg: _draw_leg(
                surface, anim, l, far, leg_w, ox, oy
            ))
    add(3, hip[1], lambda: _segment(
        surface, hip, shoulder, s.body_w * sx, s.color, ox, oy
    ))
    add(3, hip[1], lambda: pygame.draw.circle(
        surface,
        s.accent,
        (int(hip[0] + ox), int(hip[1] + oy)),
        max(2, int(s.body_w * 0.18 * sx)),
    ))
    for leg in anim.legs:
        if leg.depth == 0:
            add(4, leg.hip[1], lambda l=leg: _draw_leg(
                surface, anim, l, s.color, leg_w, ox, oy
            ))
    add(5, head[1], lambda: _segment(
        surface,
        shoulder,
        head,
        max(3, int(s.body_w * 0.35 * sx)),
        s.color,
        ox,
        oy,
    ))
    add(5, head[1], lambda: pygame.draw.circle(
        surface,
        s.color,
        (int(head[0] + ox), int(head[1] + oy)),
        max(3, int(head_r)),
    ))
    add(6, head[1], lambda: _eye(surface, anim, ox, oy, head, head_r))
    for arm in anim.arms:
        if arm[3] == 0:
            add(7, arm[0][1], lambda a=arm: _arm(
                surface, anim, a, arm_w, s.color, ox, oy
            ))
    add(8, anim.body_y, lambda: _hit_ring(surface, anim, ox, oy))

    for _z, _y, draw in sorted(pieces, key=lambda piece: (piece[0], piece[1])):
        draw()


def _draw_quadruped(surface, anim, ox, oy):
    s = anim.spec
    far = _shade(s.color)
    leg_w = max(3, int(s.body_h * 0.22))
    sx = anim.body_scale_x
    sy = anim.body_scale_y
    rear = anim.rear
    front = (
        rear[0] + (anim.front[0] - rear[0]) * sx,
        rear[1] + (anim.front[1] - rear[1]) * sy,
    )
    head = (
        front[0] + (anim.head[0] - anim.front[0]) * sx,
        front[1] + (anim.head[1] - anim.front[1]) * sy,
    )
    head_r = s.head_r * 0.5 * (sx + sy)
    pieces = []

    def add(z, y, fn):
        pieces.append((z, y, fn))

    add(0, anim.y, lambda: _shadow(
        surface, anim.body_x, anim.y, s.body_w * 1.6, ox, oy
    ))
    for leg in anim.legs:
        if leg.depth == 1:
            add(1, leg.hip[1], lambda l=leg: _draw_leg(
                surface, anim, l, far, leg_w, ox, oy
            ))
    if anim.tail is not None:
        add(2, anim.tail[0][1], lambda: _segment(
            surface, anim.tail[0], anim.tail[1], 3, far, ox, oy
        ))
    add(3, rear[1], lambda: _segment(
        surface, rear, front, s.body_h * sy, s.color, ox, oy
    ))
    add(3, rear[1], lambda: pygame.draw.circle(
        surface,
        s.accent,
        (int(front[0] + ox), int(front[1] + oy)),
        max(2, int(s.body_h * 0.18 * sx)),
    ))
    add(4, head[1], lambda: _segment(
        surface,
        front,
        head,
        max(4, int(s.body_h * 0.45 * sx)),
        s.color,
        ox,
        oy,
    ))
    add(4, head[1], lambda: pygame.draw.circle(
        surface,
        s.color,
        (int(head[0] + ox), int(head[1] + oy)),
        max(3, int(head_r)),
    ))
    add(5, head[1], lambda: _eye(surface, anim, ox, oy, head, head_r))
    for leg in anim.legs:
        if leg.depth == 0:
            add(6, leg.hip[1], lambda l=leg: _draw_leg(
                surface, anim, l, s.color, leg_w, ox, oy
            ))
    add(7, anim.body_y, lambda: _hit_ring(surface, anim, ox, oy))

    for _z, _y, draw in sorted(pieces, key=lambda piece: (piece[0], piece[1])):
        draw()


def _draw_floating(surface, anim, ox, oy):
    s = anim.spec
    cx = int(anim.body_x + ox)
    cy = int(anim.body_y + oy)
    scale = 0.5 * (anim.body_scale_x + anim.body_scale_y)
    radius = max(3, int(s.head_r * scale))
    pieces = []

    def add(z, y, fn):
        pieces.append((z, y, fn))

    add(0, anim.body_y, lambda: _glow(surface, cx, cy, radius, s, ox, oy))
    for i, (tx, ty, tr) in enumerate(anim.trail):
        color = _shade(s.color, 0.55 + i * 0.1)
        add(1 + i, ty, lambda x=tx, y=ty, r=tr, c=color: pygame.draw.circle(
            surface, c, (int(x + ox), int(y + oy)), max(2, int(r))
        ))
    add(5, anim.body_y, lambda: pygame.draw.circle(
        surface, s.color, (cx, cy), radius
    ))
    add(5, anim.body_y, lambda: pygame.draw.circle(
        surface, s.accent, (cx, cy), max(2, int(radius * 0.45))
    ))
    add(6, anim.body_y, lambda: _eye(surface, anim, ox, oy, None, radius))
    add(7, anim.body_y, lambda: _hit_ring(surface, anim, ox, oy))

    for _z, _y, draw in sorted(pieces, key=lambda piece: (piece[0], piece[1])):
        draw()


def _glow(surface, cx, cy, radius, spec, ox, oy):
    glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    pygame.draw.circle(
        glow,
        (*spec.accent, 45),
        (radius * 2, radius * 2),
        int(radius * 1.8),
    )
    surface.blit(glow, (cx - radius * 2, cy - radius * 2))


def draw_creature(surface, anim, offset=(0, 0)):
    """Draw one posed creature to ``surface``."""
    ox, oy = offset
    kind = anim.spec.kind
    if kind == "floating":
        _draw_floating(surface, anim, ox, oy)
    elif kind == "quadruped":
        _draw_quadruped(surface, anim, ox, oy)
    else:
        _draw_biped(surface, anim, ox, oy)
