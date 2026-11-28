"""Runtime vector renderer for procedural creatures.

Draws a ``CreatureDefinition`` directly with pygame primitives every frame, so
the game never needs creature sprites or generated texture files.  The anchor
passed to :meth:`CreatureVector.update` is the feet position for ground plans
and the body centre for floating / winged plans.

This renderer is intentionally simpler than prc-animation's IK rig: it is the
generic fallback that covers all eight body plans, including serpentine and
amorphous shapes that the biped/quadruped rig cannot pose.
"""

from __future__ import annotations

import colorsys
import math
import random
from itertools import pairwise

import pygame

from .archetype_definition import BodyPlanType

GROUND_PLANS = frozenset({
    BodyPlanType.QUADRUPED,
    BodyPlanType.BIPED,
    BodyPlanType.HEXAPOD,
    BodyPlanType.MULTI_LIMBED,
})
AIR_PLANS = frozenset({BodyPlanType.FLOATING, BodyPlanType.WINGED})


def _clamp(value, low, high):
    return low if value < low else min(value, high)


def _shade(color, factor):
    return tuple(_clamp(int(channel * factor), 0, 255) for channel in color)


def _pick(rng, ranges):
    low, high = ranges
    if low > high:
        low, high = high, low
    return _clamp(rng.uniform(low, high), 0.0, 1.0)


def _hsv_color(rng, hue_range, sat_range, val_range):
    hue = _pick(rng, hue_range)
    sat = _pick(rng, sat_range)
    val = _pick(rng, val_range)
    rgb = colorsys.hsv_to_rgb(hue, sat, val)
    return tuple(int(channel * 255) for channel in rgb)


def _ellipse(surface, color, cx, cy, width, height):
    width = max(2, int(width))
    height = max(2, int(height))
    pygame.draw.ellipse(
        surface,
        color,
        (int(cx - width / 2), int(cy - height / 2), width, height),
    )


def _line(surface, color, a, b, width=2):
    pygame.draw.line(
        surface,
        color,
        (int(a[0]), int(a[1])),
        (int(b[0]), int(b[1])),
        max(1, int(width)),
    )


def _two_bone(hip, foot, upper, lower, bend=1.0):
    """Return a knee position for a two-bone chain."""
    dx = foot[0] - hip[0]
    dy = foot[1] - hip[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-4:
        return hip
    ux, uy = dx / dist, dy / dist
    dist = _clamp(dist, abs(upper - lower) + 0.01, upper + lower - 0.01)
    along = (upper * upper - lower * lower + dist * dist) / (2.0 * dist)
    height = math.sqrt(max(0.0, upper * upper - along * along))
    return (
        hip[0] + ux * along - uy * height * bend,
        hip[1] + uy * along + ux * height * bend,
    )


class CreatureVector:
    """Pose and draw one procedurally generated creature."""

    def __init__(self, definition):
        self.definition = definition
        self.plan = definition.body_plan
        self.body = definition.body
        self.visual = definition.visual

        self.body_len = max(8.0, float(self.body.get("length", 80.0)))
        self.body_w = max(4.0, float(self.body.get("width", 30.0)))
        self.body_h = max(4.0, float(self.body.get("height", 30.0)))

        self.legs = [l for l in definition.limbs if l.limb_type == "leg"]
        self.arms = [l for l in definition.limbs if l.limb_type == "arm"]
        self.wings = [l for l in definition.limbs if l.limb_type == "wing"]
        self.tendrils = [l for l in definition.limbs if l.limb_type == "tendril"]
        self.pods = [l for l in definition.limbs if l.limb_type == "pseudopod"]
        self.tail = next(
            (l for l in definition.limbs if l.limb_type == "tail"), None
        )
        self.head_limb = next(
            (l for l in definition.limbs if l.limb_type == "head"), None
        )

        self.leg_len = max(
            (sum(seg.length for seg in leg.segments) for leg in self.legs),
            default=0.0,
        )
        self.head_r = max(
            4.0,
            self.head_limb.segments[0].length * 0.55
            if self.head_limb and self.head_limb.segments
            else self.body_w * 0.4,
        )

        self.rng = random.Random(
            (definition.seed * 1000003) ^ definition.visual.pattern_seed
        )
        self.base = _hsv_color(
            self.rng,
            self.visual.base_hue_range,
            self.visual.base_sat_range,
            self.visual.base_val_range,
        )
        self.accent = _hsv_color(
            self.rng,
            self.visual.accent_hue_range,
            self.visual.accent_sat_range,
            self.visual.accent_val_range,
        )
        self.dark = _shade(self.base, 0.55)
        self.light = _shade(self.base, 1.25)
        self._spots = [
            (
                self.rng.uniform(-0.32, 0.32),
                self.rng.uniform(-0.22, 0.22),
                self.rng.uniform(0.05, 0.12),
            )
            for _ in range(5)
        ]

        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.state = "idle"
        self.on_ground = True
        self.reduce_motion = False
        self.t = 0.0
        self.phase = 0.0

    # -- pose ---------------------------------------------------------

    def update(
        self,
        dt,
        x,
        y,
        vx=0.0,
        vy=0.0,
        state="idle",
        on_ground=True,
        facing=1,
        reduce_motion=False,
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.state = state
        self.on_ground = bool(on_ground)
        if facing:
            self.facing = 1 if facing > 0 else -1
        self.reduce_motion = bool(reduce_motion)
        self.t += max(0.0, float(dt))

        speed = abs(self.vx)
        stride = max(18.0, self.body_len * 0.5)
        if speed > 2.0 and self.on_ground:
            self.phase = (self.phase + speed * dt / stride) % 1.0
        elif state in ("walk", "run"):
            self.phase = (self.phase + dt * 1.2) % 1.0
        else:
            self.phase = (self.phase + dt * 0.25) % 1.0

    # -- draw ---------------------------------------------------------

    def draw(self, surface, offset=(0, 0)):
        ox, oy = offset
        x = self.x + ox
        y = self.y + oy
        if (
            self.visual.glitch_stage >= 3
            and not self.reduce_motion
            and int(self.t * 9.0) % 11 == 0
        ):
            x += 2.0 * self.facing

        if self.plan == BodyPlanType.SERPENTINE:
            self._draw_serpentine(surface, x, y)
        elif self.plan == BodyPlanType.FLOATING:
            self._draw_floating(surface, x, y)
        elif self.plan == BodyPlanType.AMORPHOUS:
            self._draw_amorphous(surface, x, y)
        elif self.plan == BodyPlanType.BIPED:
            self._draw_biped(surface, x, y)
        else:
            self._draw_legged(surface, x, y, winged=self.plan == BodyPlanType.WINGED)

    def _bob(self, amount=2.0):
        if self.reduce_motion:
            return 0.0
        if abs(self.vx) > 4.0:
            return math.sin(self.phase * 2.0 * math.pi * 2.0) * amount
        return math.sin(self.t * 2.0 * math.pi * 0.6) * amount * 0.6

    def _shadow(self, surface, x, y, width):
        if self.plan in AIR_PLANS:
            return
        pygame.draw.ellipse(
            surface,
            (34, 36, 44),
            (int(x - width / 2), int(y - 3), max(8, int(width)), 7),
        )

    def _draw_legged(self, surface, x, y, winged=False):
        body_w = _clamp(self.body_len * 0.62, 26.0, 110.0)
        body_h = _clamp(self.body_h * 1.05, 16.0, 62.0)
        leg_len = max(16.0, self.leg_len * 0.85)
        bob = self._bob()
        body_cy = y - leg_len - body_h * 0.5 + bob
        body_cx = x
        moving = abs(self.vx) > 4.0 or self.state in ("walk", "run")
        stride = _clamp(self.body_len * 0.35, 10.0, 38.0)
        step_h = _clamp(self.body_len * 0.08, 2.0, 10.0)

        self._shadow(surface, x, y, body_w * 1.15)

        if winged:
            self._draw_wings(surface, body_cx, body_cy, body_w, body_h, far=True)

        # Far legs first, then body, then near legs.
        for far in (True, False):
            for index, leg in enumerate(self.legs):
                if (index % 2 == 1) != far:
                    continue
                phase = self.phase + leg.gait_phase_offset
                swing = math.sin(phase * 2.0 * math.pi) * stride * 0.5 if moving else 0.0
                lift = (
                    max(0.0, math.sin(phase * 2.0 * math.pi)) * step_h
                    if moving
                    else 0.0
                )
                pairs = max(1, len(self.legs) // 2)
                pair = index // 2
                frac = (pair + 0.5) / pairs
                hip_x = body_cx + (frac - 0.5) * body_w * 0.9
                hip_y = body_cy + body_h * 0.3
                foot = (hip_x + swing, y - lift)
                upper = max(4.0, leg_len * 0.55)
                lower = max(4.0, leg_len * 0.55)
                knee = _two_bone(
                    (hip_x, hip_y),
                    foot,
                    upper,
                    lower,
                    bend=-self.facing if far else self.facing,
                )
                color = self.dark if far else self.base
                width = max(2, int(leg.segments[0].thickness * 0.9))
                _line(surface, color, (hip_x, hip_y), knee, width)
                _line(surface, color, knee, foot, max(2, width - 1))
                pygame.draw.circle(
                    surface,
                    color,
                    (int(foot[0]), int(foot[1])),
                    max(2, width),
                )

        _ellipse(surface, self.base, body_cx, body_cy, body_w, body_h)
        _ellipse(
            surface,
            self.light,
            body_cx,
            body_cy + body_h * 0.16,
            body_w * 0.62,
            body_h * 0.35,
        )
        self._draw_pattern(surface, body_cx, body_cy, body_w, body_h)

        self._draw_head(surface, body_cx, body_cy, body_w, body_h, upright=False)
        self._draw_tail(surface, body_cx, body_cy, body_w, body_h)

        if winged:
            self._draw_wings(surface, body_cx, body_cy, body_w, body_h, far=False)

        if self.state == "hit":
            pygame.draw.circle(
                surface,
                (230, 90, 90),
                (int(body_cx), int(body_cy)),
                int(max(body_w, body_h) * 0.7),
                2,
            )

    def _draw_biped(self, surface, x, y):
        body_w = _clamp(self.body_w * 0.95, 14.0, 46.0)
        body_h = _clamp(self.body_h * 1.2, 28.0, 90.0)
        leg_len = max(16.0, self.leg_len * 0.85)
        bob = self._bob(1.4)
        body_cy = y - leg_len - body_h * 0.5 + bob
        body_cx = x
        moving = abs(self.vx) > 4.0 or self.state in ("walk", "run")
        stride = _clamp(self.body_len * 0.3, 8.0, 28.0)

        self._shadow(surface, x, y, body_w * 1.4)

        for index, leg in enumerate(self.legs[:2]):
            phase = self.phase + leg.gait_phase_offset + (0.5 if index else 0.0)
            swing = math.sin(phase * 2.0 * math.pi) * stride * 0.5 if moving else 0.0
            lift = (
                max(0.0, math.sin(phase * 2.0 * math.pi)) * 7.0 if moving else 0.0
            )
            hip_x = body_cx + (index * 2 - 1) * body_w * 0.24
            hip_y = body_cy + body_h * 0.44
            foot = (hip_x + swing, y - lift)
            knee = _two_bone(
                (hip_x, hip_y),
                foot,
                max(4.0, leg_len * 0.55),
                max(4.0, leg_len * 0.55),
                bend=self.facing,
            )
            color = self.dark if index == 0 else self.base
            width = max(2, int(leg.segments[0].thickness * 0.9))
            _line(surface, color, (hip_x, hip_y), knee, width)
            _line(surface, color, knee, foot, max(2, width - 1))
            pygame.draw.circle(surface, color, (int(foot[0]), int(foot[1])), width)

        _ellipse(surface, self.base, body_cx, body_cy, body_w, body_h)
        _ellipse(
            surface,
            self.light,
            body_cx,
            body_cy + body_h * 0.1,
            body_w * 0.55,
            body_h * 0.5,
        )
        self._draw_pattern(surface, body_cx, body_cy, body_w, body_h)

        # Arms swing opposite to the legs.
        for index, arm in enumerate(self.arms[:2]):
            phase = self.phase + arm.gait_phase_offset + (0.5 if index else 0.0)
            swing = math.sin(phase * 2.0 * math.pi) * stride * 0.35 if moving else 0.0
            shoulder = (
                body_cx + self.facing * body_w * 0.18,
                body_cy - body_h * 0.22,
            )
            arm_len = max(8.0, sum(seg.length for seg in arm.segments) * 0.75)
            hand = (
                shoulder[0] + self.facing * arm_len * 0.35 + swing,
                shoulder[1] + arm_len * 0.75,
            )
            _line(
                surface,
                self.dark if index == 0 else self.base,
                shoulder,
                hand,
                max(2, int(arm.segments[0].thickness * 0.8)),
            )

        self._draw_head(surface, body_cx, body_cy, body_w, body_h, upright=True)
        self._draw_tail(surface, body_cx, body_cy, body_w, body_h)

        if self.state == "hit":
            pygame.draw.circle(
                surface,
                (230, 90, 90),
                (int(body_cx), int(body_cy)),
                int(max(body_w, body_h) * 0.7),
                2,
            )

    def _draw_head(self, surface, body_cx, body_cy, body_w, body_h, upright):
        head_r = _clamp(self.head_r, 4.0, 15.0)
        if upright:
            head_x = body_cx + self.facing * body_w * 0.08
            head_y = body_cy - body_h * 0.5 - head_r * 0.7
        else:
            neck = _clamp(self.body_len * 0.14, 6.0, 22.0)
            head_x = body_cx + self.facing * (body_w * 0.45 + neck * 0.4)
            head_y = body_cy - body_h * 0.16
        _line(
            surface,
            self.base,
            (body_cx + self.facing * body_w * 0.3, body_cy - body_h * 0.1),
            (head_x, head_y),
            max(2, int(head_r * 0.7)),
        )
        pygame.draw.circle(
            surface, self.base, (int(head_x), int(head_y)), int(head_r)
        )
        pygame.draw.circle(
            surface,
            self.accent,
            (int(head_x + self.facing * head_r * 0.25), int(head_y)),
            max(1, int(head_r * 0.2)),
        )
        eye_x = head_x + self.facing * head_r * 0.35
        eye_y = head_y - head_r * 0.15
        pygame.draw.circle(
            surface,
            (22, 22, 28),
            (int(eye_x), int(eye_y)),
            max(1, int(head_r * 0.18)),
        )

    def _draw_tail(self, surface, body_cx, body_cy, body_w, body_h):
        if self.tail is None:
            return
        length = max(6.0, sum(seg.length for seg in self.tail.segments) * 0.8)
        base = (body_cx - self.facing * body_w * 0.45, body_cy + body_h * 0.1)
        points = [base]
        for i in range(1, 4):
            frac = i / 3.0
            points.append(
                (
                    base[0] - self.facing * length * frac,
                    base[1] + math.sin(self.phase * 2.0 * math.pi + frac * 2.0) * 4.0 * frac,
                )
            )
        width = max(2, int(self.tail.segments[0].thickness * 0.8))
        for a, b in pairwise(points):
            _line(surface, self.dark, a, b, width)

    def _draw_wings(self, surface, body_cx, body_cy, body_w, body_h, far):
        if not self.wings:
            return
        span = _clamp(self.body_len * 0.8, 18.0, 90.0)
        flap = math.sin(self.phase * 2.0 * math.pi * 2.0 + (0.6 if far else 0.0))
        flap = 0.25 + 0.75 * (0.5 + 0.5 * flap)
        shoulder = (body_cx, body_cy - body_h * 0.28)
        tip = (
            body_cx + self.facing * span * (0.45 if far else 0.65),
            body_cy - body_h * 0.5 - span * 0.45 * flap,
        )
        root = (
            body_cx + self.facing * body_w * 0.15,
            body_cy + body_h * 0.12,
        )
        color = self.dark if far else self.light
        pygame.draw.polygon(
            surface,
            color,
            [
                (int(shoulder[0]), int(shoulder[1])),
                (int(tip[0]), int(tip[1])),
                (int(root[0]), int(root[1])),
            ],
        )

    def _draw_pattern(self, surface, cx, cy, body_w, body_h):
        pattern = self.visual.pattern_type
        for dx, dy, radius in self._spots:
            if dx * dx + dy * dy > 0.14:
                continue
            px = cx + dx * body_w
            py = cy + dy * body_h
            if pattern in ("scales", "chitin"):
                _line(
                    surface,
                    self.accent,
                    (px - 3, py),
                    (px + 3, py),
                    1,
                )
            elif pattern in ("fur", "feathers"):
                _line(surface, self.accent, (px, py), (px + 2, py + 3), 1)
            else:
                pygame.draw.circle(
                    surface,
                    self.accent,
                    (int(px), int(py)),
                    max(1, int(radius * body_w)),
                )

    def _draw_serpentine(self, surface, x, y):
        count = max(4, int(self.body.get("segment_count", 10)))
        length = _clamp(self.body_len, 60.0, 240.0)
        width = _clamp(self.body_w, 8.0, 22.0)
        amplitude = width * 0.9
        self._shadow(surface, x, y, length * 0.7)

        points = []
        for i in range(count):
            frac = i / max(1, count - 1)
            px = x + (frac - 0.5) * length * self.facing
            py = (
                y
                - width
                - math.sin(self.phase * 2.0 * math.pi + frac * 5.0)
                * amplitude
                * (0.35 + 0.65 * math.sin(frac * math.pi))
            )
            points.append((px, py))

        for i, point in enumerate(points):
            radius = width * (0.45 + 0.55 * (i / max(1, count - 1)))
            color = self.base if i % 2 == 0 else self.light
            pygame.draw.circle(
                surface, color, (int(point[0]), int(point[1])), int(radius)
            )
        head = points[-1] if self.facing > 0 else points[0]
        pygame.draw.circle(
            surface, self.base, (int(head[0]), int(head[1])), int(width * 1.1)
        )
        eye_x = head[0] + self.facing * width * 0.35
        pygame.draw.circle(
            surface, (22, 22, 28), (int(eye_x), int(head[1] - width * 0.2)), 2
        )
        if self.state == "hit":
            pygame.draw.circle(
                surface, (230, 90, 90), (int(head[0]), int(head[1])), int(width * 2), 2
            )

    def _draw_floating(self, surface, x, y):
        radius = _clamp(self.body_w * 0.5, 8.0, 26.0)
        bob = 0.0 if self.reduce_motion else math.sin(self.t * 1.7) * 3.0
        cy = y + bob

        glow = pygame.Surface((int(radius * 4), int(radius * 4)), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*self.accent, 36),
            (int(radius * 2), int(radius * 2)),
            int(radius * 1.8),
        )
        surface.blit(glow, (int(x - radius * 2), int(cy - radius * 2)))

        for index, tendril in enumerate(self.tendrils[:6]):
            length = max(8.0, sum(seg.length for seg in tendril.segments) * 0.7)
            angle = math.pi / 2.0 + (index - 2.5) * 0.45
            point = (x, cy + radius * 0.6)
            points = [point]
            for step in range(1, 4):
                angle += math.sin(self.t * 2.0 + index + step) * 0.18
                point = (
                    point[0] + math.cos(angle) * length / 3.0,
                    point[1] + math.sin(angle) * length / 3.0,
                )
                points.append(point)
            for a, b in pairwise(points):
                _line(surface, self.dark, a, b, 2)

        _ellipse(surface, self.base, x, cy, radius * 1.5, radius * 1.8)
        _ellipse(surface, self.light, x, cy - radius * 0.15, radius * 0.9, radius * 1.0)
        pygame.draw.circle(
            surface, self.accent, (int(x), int(cy)), max(1, int(radius * 0.35))
        )
        eye_x = x + self.facing * radius * 0.35
        pygame.draw.circle(surface, (22, 22, 28), (int(eye_x), int(cy - radius * 0.2)), 2)
        if self.state == "hit":
            pygame.draw.circle(
                surface, (230, 90, 90), (int(x), int(cy)), int(radius * 2.2), 2
            )

    def _draw_amorphous(self, surface, x, y):
        radius = _clamp(self.body_w * 0.55, 10.0, 30.0)
        self._shadow(surface, x, y, radius * 2.2)
        bob = 0.0 if self.reduce_motion else math.sin(self.t * 1.3) * 2.0
        cy = y - radius * 0.8 + bob

        for index, pod in enumerate(self.pods[:6]):
            length = max(6.0, sum(seg.length for seg in pod.segments) * 0.6)
            angle = math.pi * (0.15 + 0.7 * (index / max(1, len(self.pods[:6]) - 1)))
            point = (x, cy)
            points = [point]
            for step in range(1, 4):
                angle += math.sin(self.t * 1.8 + index + step) * 0.15
                point = (
                    point[0] + math.cos(angle) * length / 3.0,
                    point[1] + math.sin(angle) * length / 3.0,
                )
                points.append(point)
            for a, b in pairwise(points):
                _line(surface, self.dark, a, b, max(2, int(radius * 0.3)))

        for index in range(3):
            ox = math.sin(self.t * 1.4 + index * 2.1) * radius * 0.28
            oy = math.cos(self.t * 1.1 + index * 1.7) * radius * 0.18
            _ellipse(
                surface,
                self.base if index != 1 else self.light,
                x + ox,
                cy + oy,
                radius * (1.5 - index * 0.12),
                radius * (1.2 + index * 0.08),
            )
        pygame.draw.circle(
            surface, self.accent, (int(x), int(cy - radius * 0.2)), max(2, int(radius * 0.25))
        )
        eye_x = x + self.facing * radius * 0.3
        pygame.draw.circle(surface, (22, 22, 28), (int(eye_x), int(cy - radius * 0.25)), 2)
        if self.state == "hit":
            pygame.draw.circle(
                surface, (230, 90, 90), (int(x), int(cy)), int(radius * 2.2), 2
            )
