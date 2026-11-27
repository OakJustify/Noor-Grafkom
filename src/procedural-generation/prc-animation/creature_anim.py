"""Procedural 2D creature animation.

Phase-based gait, FABRIK IK with joint limits, terrain foot search, compliance
spring, weight shift, head tracking and secondary motion.  Pure math; rendering
lives in ``creature_draw.py``.

Coordinates are pixels with y pointing down.  ``x, y`` passed to ``update`` is
the ground anchor (feet) for biped/quadruped creatures and the core centre for
floating creatures.  The caller owns movement; this module only poses.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

STATES = ("idle", "walk", "run", "jump", "fall", "attack", "hit", "dead")


def _clamp(value, low, high):
    return low if value < low else min(value, high)


def _spring(value, vel, target, stiffness, damping, dt):
    acc = (target - value) * stiffness - vel * damping
    vel += acc * dt
    value += vel * dt
    return value, vel


def _ease(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _angle(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _rotate_around(point, center, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return (center[0] + dx * ca - dy * sa, center[1] + dx * sa + dy * ca)


def _wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def solve_ik(hip, foot, upper, lower, bend=1.0):
    """Closed-form 2-bone solve, used as the FABRIK seed.

    Returns ``(knee, clamped_foot)``.  ``bend`` flips the knee direction.
    """
    dx = foot[0] - hip[0]
    dy = foot[1] - hip[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return hip, hip
    ux, uy = dx / dist, dy / dist
    dist = _clamp(dist, abs(upper - lower) + 0.01, upper + lower - 0.01)
    foot = (hip[0] + ux * dist, hip[1] + uy * dist)
    a = (upper * upper - lower * lower + dist * dist) / (2.0 * dist)
    h = math.sqrt(max(0.0, upper * upper - a * a))
    knee = (
        hip[0] + ux * a - uy * h * bend,
        hip[1] + uy * a + ux * h * bend,
    )
    return knee, foot


def _apply_limits(positions, limits, base_angle):
    """Clamp relative joint angles and rotate the remaining chain."""
    parent = base_angle
    for i, limit in enumerate(limits):
        if i + 1 >= len(positions):
            break
        angle = _angle(positions[i], positions[i + 1])
        if limit is not None:
            relative = _wrap_angle(angle - parent)
            clamped = _clamp(relative, limit[0], limit[1])
            delta = clamped - relative
            if abs(delta) > 1e-9:
                for j in range(i + 1, len(positions)):
                    positions[j] = _rotate_around(
                        positions[j], positions[i], delta
                    )
        parent = _angle(positions[i], positions[i + 1])


def solve_fabrik(
    root,
    target,
    lengths,
    initial=None,
    limits=None,
    base_angle=0.0,
    max_iter=10,
    tol=0.5,
):
    """Solve a 2-4 bone chain and return joint positions ``[root, ..., end]``.

    ``limits`` is an optional list of ``(min, max)`` radians per segment,
    relative to the parent segment (the first is relative to ``base_angle``).
    ``initial`` seeds the chain so the knee/elbow keeps its previous side.
    """
    count = len(lengths)
    if count == 0:
        return [(float(root[0]), float(root[1]))]
    root = (float(root[0]), float(root[1]))
    target = (float(target[0]), float(target[1]))
    total = sum(lengths)
    dx = target[0] - root[0]
    dy = target[1] - root[1]
    dist = math.hypot(dx, dy)

    if initial is not None and len(initial) == count + 1:
        positions = [(float(p[0]), float(p[1])) for p in initial]
        positions[0] = root
    else:
        if dist < 1e-6:
            ux, uy = 0.0, 1.0
        else:
            ux, uy = dx / dist, dy / dist
        positions = [root]
        for length in lengths:
            positions.append(
                (positions[-1][0] + ux * length, positions[-1][1] + uy * length)
            )

    if dist >= total:
        if dist < 1e-6:
            ux, uy = 0.0, 1.0
        else:
            ux, uy = dx / dist, dy / dist
        positions = [root]
        for length in lengths:
            positions.append(
                (positions[-1][0] + ux * length, positions[-1][1] + uy * length)
            )
        return positions

    for _ in range(max(1, int(max_iter))):
        positions[-1] = target
        for i in range(count - 1, -1, -1):
            seg_x = positions[i][0] - positions[i + 1][0]
            seg_y = positions[i][1] - positions[i + 1][1]
            seg_len = math.hypot(seg_x, seg_y)
            if seg_len < 1e-9:
                seg_x, seg_y, seg_len = 0.0, 1.0, 1.0
            positions[i] = (
                positions[i + 1][0] + seg_x / seg_len * lengths[i],
                positions[i + 1][1] + seg_y / seg_len * lengths[i],
            )

        positions[0] = root
        for i in range(count):
            seg_x = positions[i + 1][0] - positions[i][0]
            seg_y = positions[i + 1][1] - positions[i][1]
            seg_len = math.hypot(seg_x, seg_y)
            if seg_len < 1e-9:
                seg_x, seg_y, seg_len = 0.0, 1.0, 1.0
            positions[i + 1] = (
                positions[i][0] + seg_x / seg_len * lengths[i],
                positions[i][1] + seg_y / seg_len * lengths[i],
            )

        if limits:
            _apply_limits(positions, limits, base_angle)

        end = positions[-1]
        if math.hypot(end[0] - target[0], end[1] - target[1]) < tol:
            break
    return positions


def find_foothold(
    nominal_x,
    nominal_y,
    ground_height,
    radius=32.0,
    step=8.0,
    max_step_height=30.0,
):
    """Search candidate x positions around a nominal foothold.

    The callback is the vertical raycast for this 2D side view.  Candidates
    with no ground, a big height jump or a steep slope are rejected.
    """
    if ground_height is None:
        return nominal_x, nominal_y
    if nominal_y is None:
        nominal_y = 0.0
    best = None
    offsets = [0.0]
    radius = max(0.0, float(radius))
    step = max(1.0, float(step))
    distance = step
    while distance <= radius + 1e-6:
        offsets.extend((distance, -distance))
        distance += step
    for dx in offsets:
        x = nominal_x + dx
        y = ground_height(x)
        if y is None:
            continue
        if abs(y - nominal_y) > max_step_height:
            continue
        slope = 0.0
        left = ground_height(x - 4.0)
        right = ground_height(x + 4.0)
        if left is not None and right is not None:
            slope = abs(right - left) / 8.0
            if slope > 1.2:
                continue
        score = -abs(dx) - abs(y - nominal_y) * 1.5 - slope * 20.0
        if best is None or score > best[0]:
            best = (score, x, y)
    if best is None:
        return nominal_x, nominal_y
    return best[1], best[2]


@dataclass(frozen=True)
class GaitDef:
    name: str
    phase_offsets: tuple
    duty_cycle: float
    freq_range: tuple
    step_height: float


# Leg order for the quadruped is [rear-far, rear-near, front-far, front-near].
# Offsets below are reordered from the blueprint's FL, FR, RL, RR order.
GAITS = {
    "biped_walk": GaitDef("walk", (0.0, 0.5), 0.62, (1.0, 1.8), 9.0),
    "biped_run": GaitDef("run", (0.0, 0.5), 0.40, (2.0, 3.2), 14.0),
    "quad_walk": GaitDef("walk", (0.75, 0.25, 0.0, 0.5), 0.70, (0.9, 1.6), 8.0),
    "quad_trot": GaitDef("trot", (0.5, 0.0, 0.0, 0.5), 0.55, (1.8, 3.0), 12.0),
    "quad_gallop": GaitDef("gallop", (0.5, 0.75, 0.0, 0.25), 0.40, (2.8, 4.2), 16.0),
}


@dataclass(frozen=True)
class CreatureSpec:
    kind: str = "biped"
    color: tuple = (208, 198, 176)
    accent: tuple = (255, 210, 122)
    body_w: float = 18.0
    body_h: float = 42.0
    upper: float = 22.0
    lower: float = 22.0
    arm_len: float = 26.0
    head_r: float = 9.0
    stride: float = 46.0
    step_h: float = 11.0
    max_speed: float = 200.0
    foot_r: float = 4.0
    foot_len: float = 7.0

    def scaled(self, scale):
        if scale == 1.0:
            return self
        return replace(
            self,
            body_w=self.body_w * scale,
            body_h=self.body_h * scale,
            upper=self.upper * scale,
            lower=self.lower * scale,
            arm_len=self.arm_len * scale,
            head_r=self.head_r * scale,
            stride=self.stride * scale,
            step_h=self.step_h * scale,
            foot_r=self.foot_r * scale,
            foot_len=self.foot_len * scale,
        )


_BASE_SPECS = {
    "biped": CreatureSpec(kind="biped", stride=40.0),
    "quadruped": CreatureSpec(
        kind="quadruped",
        body_w=58.0,
        body_h=22.0,
        upper=20.0,
        lower=20.0,
        arm_len=0.0,
        head_r=9.0,
        stride=48.0,
        step_h=9.0,
        max_speed=220.0,
    ),
    "floating": CreatureSpec(
        kind="floating",
        body_w=28.0,
        body_h=28.0,
        upper=0.0,
        lower=0.0,
        arm_len=0.0,
        head_r=14.0,
        stride=1.0,
        step_h=0.0,
        max_speed=170.0,
        foot_len=0.0,
    ),
}


def make_spec(kind="biped", scale=1.0, color=None, accent=None):
    """Build a scaled creature spec. Unknown kinds fall back to biped."""
    spec = _BASE_SPECS.get(kind, _BASE_SPECS["biped"]).scaled(scale)
    if color is not None or accent is not None:
        spec = replace(
            spec,
            color=color or spec.color,
            accent=accent or spec.accent,
        )
    return spec


@dataclass
class Leg:
    hip_dx: float
    hip_dy: float
    upper: float
    lower: float
    bend: float
    depth: int
    foot_x: float = 0.0
    foot_y: float = 0.0
    stepping: bool = False
    in_stance: bool = True
    step_t: float = 0.0
    step_dur: float = 0.2
    from_x: float = 0.0
    from_y: float = 0.0
    to_x: float = 0.0
    to_y: float = 0.0
    lift: float = 0.0
    hip: tuple = (0.0, 0.0)
    knee: tuple = (0.0, 0.0)
    foot: tuple = (0.0, 0.0)
    joints: list | None = field(default=None)
    ik_x: float = 0.0
    ik_y: float = 0.0
    ik_vx: float = 0.0
    ik_vy: float = 0.0
    swing_dur: float = 0.2


class CreatureAnimator:
    """Pose one creature. Feed it the AI's position, velocity and state."""

    def __init__(self, spec, x=0.0, y=0.0, seed=0):
        self.spec = spec
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.state = "idle"
        self.state_time = 0.0
        self.on_ground = True
        self.head_target = None
        self.speed = 0.0
        self._rng = random.Random(seed)
        self.gait = self._rng.random()
        self.breath = self._rng.random() * 10.0
        self.gait_name = "idle"
        self._gait_override = None
        self._reduce_motion = False
        self.body_x = self.x
        self.body_y = self._stand_body_y()
        self.body_angle = 0.0
        self.body_scale_x = 1.0
        self.body_scale_y = 1.0
        self._scale_v = 0.0
        self.blink = 0.0
        self._blink_left = 0.0
        self._blink_next = self._rng.uniform(2.0, 6.0)
        self.tail_angle = 0.0
        self._tail_v = 0.0
        self.hip_center = (self.x, self.body_y)
        self.shoulder = (self.x, self.body_y)
        self.front = (self.x, self.body_y)
        self.rear = (self.x, self.body_y)
        self.head = (self.x, self.body_y)
        self.head_angle = 0.0
        self.legs = self._make_legs()
        self.arms = []
        self.tail = None
        self.trail = []
        self._prev_vx = 0.0
        self._accel = 0.0
        self._shift_x = 0.0
        self._shift_x_v = 0.0
        self._angle_v = 0.0
        self._head_v = 0.0
        self._land = 0.0
        self._land_v = 0.0
        self._was_ground = True
        self._prev_vy = 0.0
        self._init_feet()

    # -- setup ---------------------------------------------------------

    def _stand_body_y(self):
        if self.spec.kind == "floating":
            return self.y
        hip_h = (self.spec.upper + self.spec.lower) * 0.82
        return self.y - hip_h - self.spec.body_h / 2.0

    def _make_legs(self):
        s = self.spec
        if s.kind == "biped":
            return [
                Leg(2.0, s.body_h * 0.5, s.upper, s.lower, -1.0, 0),
                Leg(-2.0, s.body_h * 0.5, s.upper, s.lower, -1.0, 1),
            ]
        if s.kind == "quadruped":
            legs = []
            for depth in (1, 0):
                for side in (-1, 1):
                    legs.append(
                        Leg(
                            side * s.body_w * 0.34 - depth * 2.0,
                            s.body_h * 0.35 - depth * 2.0,
                            s.upper,
                            s.lower,
                            1.0 if side > 0 else -1.0,
                            depth,
                        )
                    )
            return legs
        return []

    def _init_feet(self):
        for leg in self.legs:
            hip = self._hip(leg)
            leg.hip = hip
            knee, foot = solve_ik(
                hip,
                (hip[0], self.y),
                leg.upper,
                leg.lower,
                leg.bend * self.facing,
            )
            leg.knee = knee
            leg.foot = foot
            leg.foot_x = hip[0]
            leg.foot_y = self.y
            leg.ik_x = leg.foot_x
            leg.ik_y = leg.foot_y

    # -- geometry ------------------------------------------------------

    def _local_to_world(self, lx, ly):
        lx *= self.facing
        ca = math.cos(self.body_angle)
        sa = math.sin(self.body_angle)
        return (
            self.body_x + lx * ca - ly * sa,
            self.body_y + lx * sa + ly * ca,
        )

    def _hip(self, leg):
        return self._local_to_world(leg.hip_dx, leg.hip_dy)

    def _leg_limits(self, bend):
        knee = (-2.6, -0.05) if bend > 0 else (0.05, 2.6)
        return [(-1.22, 1.22), knee]

    def _solve_leg(self, leg):
        if leg.upper <= 0.0 or leg.lower <= 0.0:
            return
        target = (leg.ik_x, leg.ik_y)
        bend = leg.bend * self.facing
        # Warm-start from the closed-form solve so FABRIK keeps the knee side.
        knee, end = solve_ik(leg.hip, target, leg.upper, leg.lower, bend)
        seed = [leg.hip, knee, end]
        positions = solve_fabrik(
            leg.hip,
            target,
            (leg.upper, leg.lower),
            initial=seed,
            limits=self._leg_limits(bend),
            base_angle=self.body_angle + math.pi / 2.0,
        )
        leg.joints = positions
        leg.knee = positions[1]
        leg.foot = positions[2]

    # -- gait selection ------------------------------------------------

    def _select_gait(self):
        kind = self.spec.kind
        override = self._gait_override
        if override in ("walk", "run", "trot", "gallop"):
            if kind == "biped" and override in ("walk", "run"):
                return GAITS.get(f"biped_{override}")
            if kind == "quadruped" and override in ("walk", "trot", "gallop"):
                return GAITS.get(f"quad_{override}")
        if kind == "biped":
            if self.state == "run":
                return GAITS["biped_run"]
            if self.state == "walk":
                return GAITS["biped_walk"]
        elif kind == "quadruped":
            if self.state == "run":
                if self.speed > self.spec.max_speed * 0.55:
                    return GAITS["quad_gallop"]
                return GAITS["quad_trot"]
            if self.state == "walk":
                return GAITS["quad_walk"]
        return None

    def _gait_freq(self, gait_def):
        return _clamp(
            self.speed / max(1.0, self.spec.stride),
            gait_def.freq_range[0],
            gait_def.freq_range[1],
        )

    # -- update --------------------------------------------------------

    def update(
        self,
        dt,
        *,
        x=None,
        y=None,
        vx=0.0,
        vy=0.0,
        facing=None,
        state="idle",
        on_ground=True,
        ground_height=None,
        head_target=None,
        gait=None,
        reduce_motion=False,
    ):
        if dt <= 0.0:
            return
        dt = min(dt, 1.0 / 30.0)
        if x is not None:
            self.x = float(x)
        if y is not None:
            self.y = float(y)
        if state not in STATES:
            state = "idle"
        if state != self.state:
            self.state = state
            self.state_time = 0.0
        self.state_time += dt
        self.vx = float(vx)
        self.vy = float(vy)
        if facing is None:
            if abs(vx) > 1.0:
                self.facing = 1 if vx > 0 else -1
        else:
            self.facing = 1 if facing >= 0 else -1
        self.on_ground = bool(on_ground)
        self.head_target = head_target
        self._gait_override = gait
        self._reduce_motion = bool(reduce_motion)

        speed = abs(self.vx)
        self.speed += (speed - self.speed) * min(1.0, 12.0 * dt)
        accel = (self.vx - self._prev_vx) / dt
        self._prev_vx = self.vx
        self._accel += (accel - self._accel) * min(1.0, 10.0 * dt)

        if self.on_ground and not self._was_ground:
            self._land_v += min(55.0, abs(self._prev_vy) * 0.10)
        self._was_ground = self.on_ground
        self._prev_vy = self.vy

        self.breath += dt
        gait_def = self._select_gait()
        moving = (
            self.on_ground
            and self.state in ("walk", "run")
            and self.speed > 4.0
            and gait_def is not None
        )
        if gait_def is not None:
            self.gait_name = gait_def.name
        else:
            self.gait_name = "idle"
        if moving:
            freq = self._gait_freq(gait_def)
            self.gait = (self.gait + freq * dt) % 1.0

        self._update_body(dt)
        if self.spec.kind == "floating":
            self._update_trail()
        else:
            self._update_legs(dt, ground_height, gait_def, moving)
            if self.spec.kind == "biped":
                self._update_arms()
            else:
                self._update_tail(dt)
        self._update_head(dt)
        self._update_secondary(dt)

    # -- body ----------------------------------------------------------

    def _update_body(self, dt):
        s = self.spec
        state = self.state
        if s.kind == "floating":
            hover = math.sin(self.breath * 1.8) * 2.5
            target_y = self.y + hover + _clamp(-self.vy * 0.02, -8.0, 8.0)
            target_x = self.x
            if state == "attack":
                target_x += (
                    self.facing
                    * math.sin(math.pi * min(1.0, self.state_time / 0.35))
                    * 12.0
                )
            elif state == "hit":
                target_x -= self.facing * 8.0
            elif state == "jump":
                target_y -= 6.0
            elif state == "fall":
                target_y += 6.0
            elif state == "dead":
                target_y = self.y + 18.0
        else:
            stand = self._stand_body_y()
            bob = 0.0
            if self.on_ground and state in ("walk", "run"):
                amp = 1.6 if state == "walk" else 3.2
                bob = math.sin(self.gait * math.tau) * amp
            elif state == "idle" and self.on_ground:
                bob = math.sin(self.breath * 1.6) * 1.2
            target_y = stand + bob
            target_x = self.x
            if state == "jump":
                target_y -= 2.0
            elif state == "fall":
                target_y += 2.0
            elif state == "attack":
                target_x += (
                    self.facing
                    * math.sin(math.pi * min(1.0, self.state_time / 0.35))
                    * 10.0
                )
            elif state == "hit":
                target_x -= self.facing * 8.0
            elif state == "dead":
                target_y = self.y - s.body_h * 0.22

        if s.kind == "floating":
            shift_target = _clamp(-self.vx * 0.03, -7.0, 7.0)
        else:
            shift_target = _clamp(-self._accel * 0.012, -6.0, 6.0)
            if state in ("jump", "fall"):
                shift_target *= 0.3
        self._shift_x, self._shift_x_v = _spring(
            self._shift_x, self._shift_x_v, shift_target, 90.0, 16.0, dt
        )
        self._land, self._land_v = _spring(
            self._land, self._land_v, 0.0, 150.0, 18.0, dt
        )
        self.body_x = target_x + self._shift_x
        self.body_y = target_y + self._land

        lean = _clamp(self.vx / max(1.0, s.max_speed), -1.0, 1.0) * 0.10
        if state == "run":
            lean *= 1.7
        elif state == "jump":
            lean += self.facing * 0.10
        elif state == "fall":
            lean -= self.facing * 0.06
        elif state == "hit":
            lean = -self.facing * 0.30
        elif state == "dead":
            lean = self.facing * 1.25
        elif state == "attack":
            lean += (
                self.facing
                * 0.15
                * math.sin(math.pi * min(1.0, self.state_time / 0.35))
            )
        self.body_angle, self._angle_v = _spring(
            self.body_angle, self._angle_v, lean, 110.0, 16.0, dt
        )

        self.hip_center = self._local_to_world(0.0, s.body_h * 0.35)
        self.shoulder = self._local_to_world(0.0, -s.body_h * 0.35)
        self.front = self._local_to_world(s.body_w * 0.45, 0.0)
        self.rear = self._local_to_world(-s.body_w * 0.45, 0.0)

    # -- legs ----------------------------------------------------------

    def _update_legs(self, dt, ground_height, gait_def, moving):
        s = self.spec
        grounded = self.on_ground and self.state not in ("jump", "fall", "dead")
        freq = self._gait_freq(gait_def) if gait_def is not None else 0.0

        for index, leg in enumerate(self.legs):
            hip = self._hip(leg)
            leg.hip = hip

            if self.state == "dead":
                side = -1.0 if leg.hip_dx < 0 else 1.0
                target_x = self.body_x + side * s.body_w * 1.4 * self.facing
                leg.foot_x += (target_x - leg.foot_x) * min(1.0, 8.0 * dt)
                leg.foot_y += (self.y - leg.foot_y) * min(1.0, 8.0 * dt)
                leg.stepping = False
                leg.in_stance = True
            elif not grounded:
                if self.state == "jump":
                    target_y = hip[1] + (s.upper + s.lower) * 0.55
                else:
                    target_y = hip[1] + (s.upper + s.lower) * 0.92
                target_x = hip[0] + self.facing * 2.0
                leg.foot_x += (target_x - leg.foot_x) * min(1.0, 12.0 * dt)
                leg.foot_y += (target_y - leg.foot_y) * min(1.0, 12.0 * dt)
                leg.stepping = False
                leg.in_stance = False
            elif moving:
                offsets = gait_def.phase_offsets
                leg_phase = (
                    self.gait + offsets[index % len(offsets)]
                ) % 1.0
                duty = gait_def.duty_cycle
                if leg_phase < duty:
                    leg.in_stance = True
                    if leg.stepping:
                        leg.foot_x, leg.foot_y = leg.to_x, leg.to_y
                        leg.stepping = False
                else:
                    leg.in_stance = False
                    if not leg.stepping:
                        self._start_swing(leg, hip, gait_def, freq, ground_height)
                    swing_t = (leg_phase - duty) / max(1e-6, 1.0 - duty)
                    self._swing_to(leg, swing_t)
            else:
                leg.in_stance = not leg.stepping
                if leg.stepping:
                    leg.step_t += dt / max(1e-4, leg.swing_dur)
                    if leg.step_t >= 1.0:
                        leg.foot_x, leg.foot_y = leg.to_x, leg.to_y
                        leg.stepping = False
                        leg.in_stance = True
                    else:
                        self._swing_to(leg, leg.step_t)
                else:
                    gy = ground_height(leg.foot_x) if ground_height else self.y
                    if gy is not None:
                        leg.foot_y += (gy - leg.foot_y) * min(1.0, 18.0 * dt)

            if leg.stepping:
                leg.ik_x, leg.ik_y = leg.foot_x, leg.foot_y
                leg.ik_vx = 0.0
                leg.ik_vy = 0.0
            else:
                leg.ik_x, leg.ik_vx = _spring(
                    leg.ik_x, leg.ik_vx, leg.foot_x, 90.0, 16.0, dt
                )
                leg.ik_y, leg.ik_vy = _spring(
                    leg.ik_y, leg.ik_vy, leg.foot_y, 90.0, 16.0, dt
                )
            self._solve_leg(leg)

    def _start_swing(self, leg, hip, gait_def, freq, ground_height):
        s = self.spec
        duty = gait_def.duty_cycle
        freq = max(0.1, freq)
        stance_travel = self.speed * (duty / freq)
        swing_travel = self.speed * ((1.0 - duty) / freq)
        # The body keeps moving during the swing, so the foot must aim past the
        # current hip by that distance or it lands behind the body.
        ahead = swing_travel + stance_travel * 0.5 + s.stride * 0.12
        nominal_x = hip[0] + self.facing * ahead
        nominal_y = ground_height(nominal_x) if ground_height else self.y
        if nominal_y is None:
            nominal_y = leg.foot_y
        target_x, target_y = find_foothold(
            nominal_x,
            nominal_y,
            ground_height,
            radius=s.stride * 0.7,
            max_step_height=gait_def.step_height * 3.0,
        )
        leg.from_x, leg.from_y = leg.foot_x, leg.foot_y
        leg.to_x, leg.to_y = target_x, target_y
        leg.stepping = True
        leg.in_stance = False
        leg.step_t = 0.0
        leg.swing_dur = (1.0 - duty) / freq
        leg.lift = gait_def.step_height * (
            0.8 + 0.4 * min(1.0, self.speed / max(1.0, s.max_speed))
        )

    def _swing_to(self, leg, t):
        t = _clamp(t, 0.0, 1.0)
        eased = _ease(t)
        leg.step_t = t
        leg.foot_x = leg.from_x + (leg.to_x - leg.from_x) * eased
        leg.foot_y = (
            leg.from_y
            + (leg.to_y - leg.from_y) * eased
            - math.sin(math.pi * t) * leg.lift
        )

    # -- arms / tail / head -------------------------------------------

    def _update_arms(self):
        s = self.spec
        swing_base = math.sin(self.gait * math.tau) * 0.08
        if self.state in ("walk", "run"):
            amp = 0.40 if self.state == "walk" else 0.60
            swing_base = math.sin(self.gait * math.tau) * amp
        elif self.state == "jump":
            swing_base = 2.4
        elif self.state == "fall":
            swing_base = 2.1
        elif self.state == "attack":
            swing_base = 1.5
        elif self.state == "dead":
            swing_base = 0.3

        arms = []
        for depth, sign in ((1, -1), (0, 1)):
            shoulder = self._local_to_world(
                sign * s.body_w * 0.55, -s.body_h * 0.35
            )
            swing = swing_base * sign
            if self.state == "attack" and depth == 0:
                swing = 1.6
            hand = (
                shoulder[0] + self.facing * math.sin(swing) * s.arm_len,
                shoulder[1] + math.cos(swing) * s.arm_len,
            )
            elbow = (
                (shoulder[0] + hand[0]) / 2 + self.facing * 3.0,
                (shoulder[1] + hand[1]) / 2,
            )
            arms.append((shoulder, elbow, hand, depth))
        self.arms = arms

    def _update_tail(self, dt):
        target = _clamp(-self._accel * 0.004, -0.5, 0.5)
        if self._reduce_motion:
            target = 0.0
        self.tail_angle, self._tail_v = _spring(
            self.tail_angle, self._tail_v, target, 45.0, 8.0, dt
        )
        rear = self._local_to_world(-self.spec.body_w * 0.5, 0.0)
        sway = 0.0
        if not self._reduce_motion:
            sway = math.sin(self.breath * 2.2) * 0.12
        angle = self.tail_angle + sway
        ca = math.cos(angle)
        sa = math.sin(angle)
        vx = -self.facing * 16.0
        vy = -6.0
        tip = (rear[0] + vx * ca - vy * sa, rear[1] + vx * sa + vy * ca)
        self.tail = (rear, tip)

    def _update_head(self, dt):
        s = self.spec
        if s.kind == "quadruped":
            local = (s.body_w * 0.45, -s.body_h * 0.15)
        elif s.kind == "floating":
            local = (0.0, 0.0)
        else:
            local = (0.0, -s.body_h * 0.5 - s.head_r * 0.7)
        self.head = self._local_to_world(local[0], local[1])
        if (
            not self._reduce_motion
            and self.state in ("walk", "run")
            and self.on_ground
        ):
            self.head = (
                self.head[0],
                self.head[1] + math.sin(self.gait * math.tau) * 1.5,
            )

        if self.state == "dead":
            target = self.facing * 0.9
        elif self.head_target is not None:
            dx = self.head_target[0] - self.head[0]
            dy = self.head_target[1] - self.head[1]
            world = math.atan2(dy, dx)
            base = 0.0 if self.facing > 0 else math.pi
            rel = math.atan2(math.sin(world - base), math.cos(world - base))
            target = _clamp(rel, -0.65, 0.65) - self.body_angle * 0.35
        else:
            target = math.sin(self.breath * 1.3) * 0.06
        self.head_angle, self._head_v = _spring(
            self.head_angle, self._head_v, target, 80.0, 14.0, dt
        )

    def _update_trail(self):
        self.trail = []
        for i in range(3):
            back = (i + 1) * 9.0
            sway = math.sin(self.breath * 2.4 - i * 0.8) * (3.0 + i)
            x = self.body_x - self.facing * back + sway * 0.3
            y = self.body_y + math.cos(self.breath * 1.8 - i * 0.7) * 2.0
            radius = max(2.0, self.spec.head_r * (0.45 - i * 0.1))
            self.trail.append((x, y, radius))

    # -- secondary motion ----------------------------------------------

    def _update_secondary(self, dt):
        target = 1.0 - _clamp(self.vy * 0.001, -0.15, 0.1)
        if self.state == "idle" and self.on_ground:
            target += math.sin(self.breath * 0.5) * 0.02
        if self._reduce_motion:
            target = 1.0
        self.body_scale_y, self._scale_v = _spring(
            self.body_scale_y, self._scale_v, target, 160.0, 18.0, dt
        )
        self.body_scale_y = _clamp(self.body_scale_y, 0.8, 1.2)
        self.body_scale_x = 1.0 / max(0.5, self.body_scale_y)

        if self._reduce_motion:
            self.blink = 0.0
            self._blink_left = 0.0
            return
        if self._blink_left > 0.0:
            self._blink_left -= dt
            self.blink = 1.0 if self._blink_left > 0.0 else 0.0
        else:
            self.blink = 0.0
            self._blink_next -= dt
            if self._blink_next <= 0.0:
                self._blink_left = 0.15
                self._blink_next = self._rng.uniform(2.0, 6.0)
                self.blink = 1.0


class SecondaryMotion:
    """Spring-driven lag for sprite-based characters (hybrid mode)."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0

    def update(self, dt, vx, vy, on_ground):
        if dt <= 0.0:
            return
        dt = min(dt, 1.0 / 30.0)
        target_x = _clamp(-vx * 0.02, -5.0, 5.0)
        target_y = 0.0 if on_ground else _clamp(-vy * 0.012, -7.0, 7.0)
        self.x, self.vx = _spring(self.x, self.vx, target_x, 120.0, 18.0, dt)
        self.y, self.vy = _spring(self.y, self.vy, target_y, 120.0, 18.0, dt)

    def offset(self):
        return (self.x, self.y)


