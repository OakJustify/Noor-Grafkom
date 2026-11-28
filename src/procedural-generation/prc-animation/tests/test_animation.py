import math
import os
import sys

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creature_anim import (
    STATES,
    CreatureAnimator,
    SecondaryMotion,
    find_foothold,
    make_spec,
    solve_fabrik,
    solve_ik,
)
from creature_draw import draw_creature


def test_ik_clamps_unreachable_foot():
    knee, foot = solve_ik((0, 0), (100, 0), 20, 20, 1)
    assert math.isclose(math.hypot(*foot), 39.99, rel_tol=1e-3)
    assert math.hypot(*knee) <= 20.01


def test_fabrik_reaches_target():
    joints = solve_fabrik((0, 0), (30, 0), (10, 10, 10), max_iter=20, tol=0.1)
    assert len(joints) == 4
    assert math.hypot(joints[-1][0] - 30, joints[-1][1]) < 0.6
    for a, b, length in zip(joints, joints[1:], (10, 10, 10)):
        assert math.isclose(math.hypot(b[0] - a[0], b[1] - a[1]), length, rel_tol=1e-3)


def test_fabrik_stretches_unreachable_chain():
    joints = solve_fabrik((0, 0), (100, 0), (10, 10, 10))
    assert math.isclose(math.hypot(*joints[-1]), 30.0, rel_tol=1e-3)


def test_fabrik_applies_joint_limit():
    joints = solve_fabrik(
        (0, 0),
        (0, 30),
        (20, 20),
        limits=[None, (0.2, 2.6)],
        base_angle=math.pi / 2,
        max_iter=20,
    )
    thigh = math.atan2(joints[1][1] - joints[0][1], joints[1][0] - joints[0][0])
    shin = math.atan2(joints[2][1] - joints[1][1], joints[2][0] - joints[1][0])
    relative = math.atan2(math.sin(shin - thigh), math.cos(shin - thigh))
    assert 0.2 - 1e-6 <= relative <= 2.6 + 1e-6


def test_foothold_search_avoids_gap():
    x, y = find_foothold(
        100,
        600,
        lambda gx: None if 90 <= gx <= 110 else 600,
        radius=32,
    )
    assert not 90 <= x <= 110
    assert y == 600


def test_walk_moves_feet_and_keeps_them_near_ground():
    anim = CreatureAnimator(make_spec("biped"), 100, 600)
    start = anim.legs[0].foot_x
    stepped = False
    for i in range(90):
        anim.update(
            1 / 60,
            x=100 + i * 2,
            y=600,
            vx=120,
            state="walk",
            on_ground=True,
            ground_height=lambda x: 600,
        )
        stepped = stepped or any(leg.stepping for leg in anim.legs)
    assert stepped
    assert anim.gait_name == "walk"
    assert anim.legs[0].foot_x != start
    assert all(abs(leg.foot_y - 600) < 20 for leg in anim.legs)


def test_stance_foot_is_locked():
    anim = CreatureAnimator(make_spec("biped"), 100, 600)
    previous = {}
    slides = 0
    for i in range(180):
        anim.update(
            1 / 60,
            x=100 + i * 1.5,
            y=600,
            vx=90,
            state="walk",
            on_ground=True,
            ground_height=lambda x: 600,
        )
        for index, leg in enumerate(anim.legs):
            planted = leg.in_stance and not leg.stepping
            if planted and index in previous:
                slides += abs(leg.foot_x - previous[index]) > 1e-6
            if planted:
                previous[index] = leg.foot_x
            else:
                previous.pop(index, None)
    assert slides == 0


def test_stance_ik_and_swing_landing():
    # A planted foot must sit on its IK target, and a swing must land ahead of
    # the hip; otherwise the creature slides or drags its feet.
    for kind in ("biped", "quadruped"):
        for facing in (1, -1):
            for speed in (90, 200):
                anim = CreatureAnimator(make_spec(kind), 100, 600, seed=3)
                was_stepping = [False] * len(anim.legs)
                max_error = 0.0
                min_ahead = math.inf
                landings = 0
                for i in range(240):
                    anim.update(
                        1 / 60,
                        x=100 + facing * i * speed / 60,
                        y=600,
                        vx=facing * speed,
                        facing=facing,
                        state="run" if speed > 120 else "walk",
                        on_ground=True,
                        ground_height=lambda x: 600,
                    )
                    for index, leg in enumerate(anim.legs):
                        if i >= 60 and not leg.stepping:
                            error = math.hypot(
                                leg.foot[0] - leg.ik_x, leg.foot[1] - leg.ik_y
                            )
                            max_error = max(max_error, error)
                        if i >= 60 and was_stepping[index] and not leg.stepping:
                            ahead = (leg.foot_x - leg.hip[0]) * anim.facing
                            min_ahead = min(min_ahead, ahead)
                            landings += 1
                        was_stepping[index] = leg.stepping
                assert landings > 0
                assert min_ahead > 0
                assert max_error < 1.0


def test_idle_feet_stay_planted():
    anim = CreatureAnimator(make_spec("biped"), 100, 600)
    for _ in range(120):
        anim.update(
            1 / 60,
            x=100,
            y=600,
            vx=0,
            state="idle",
            on_ground=True,
            ground_height=lambda x: 600,
        )
    assert abs(anim.legs[0].foot_x - anim.legs[0].hip[0]) < 20
    assert abs(anim.legs[0].foot_y - 600) < 2


def test_ground_callback_sets_stance_height():
    anim = CreatureAnimator(make_spec("biped"), 100, 600)
    for _ in range(60):
        anim.update(
            1 / 60,
            x=100,
            y=600,
            vx=0,
            state="idle",
            on_ground=True,
            ground_height=lambda x: 580,
        )
    assert abs(anim.legs[0].foot_y - 580) < 1


def test_head_tracking_is_clamped():
    anim = CreatureAnimator(make_spec("biped"), 100, 600)
    for _ in range(30):
        anim.update(
            1 / 60,
            x=100,
            y=600,
            vx=0,
            state="idle",
            on_ground=True,
            ground_height=lambda x: 600,
            head_target=(10000, -10000),
        )
    assert abs(anim.head_angle) <= 0.7


def test_secondary_motion_trails_then_settles():
    motion = SecondaryMotion()
    for _ in range(30):
        motion.update(1 / 60, 200, 0, True)
    assert motion.offset()[0] < 0
    for _ in range(180):
        motion.update(1 / 60, 0, 0, True)
    assert abs(motion.offset()[0]) < 0.5


def test_specs_have_expected_legs():
    assert len(CreatureAnimator(make_spec("biped")).legs) == 2
    assert len(CreatureAnimator(make_spec("quadruped")).legs) == 4
    assert len(CreatureAnimator(make_spec("floating")).legs) == 0


def _walk(kind, facing, vx, frames=60):
    anim = CreatureAnimator(make_spec(kind), 400, 600, seed=2)
    for _ in range(frames):
        anim.update(
            1 / 60,
            x=400,
            y=600,
            vx=vx,
            facing=facing,
            state="walk",
            on_ground=True,
            ground_height=lambda x: 600,
            head_target=(400 + facing * 200, 500),
        )
    return anim


def test_facing_mirrors_head_and_tail():
    for kind in ("biped", "quadruped"):
        right = _walk(kind, 1, 120)
        left = _walk(kind, -1, -120)
        assert right.head[0] > right.body_x
        assert left.head[0] < left.body_x
        if right.tail is not None:
            assert right.tail[1][0] < right.tail[0][0]
            assert left.tail[1][0] > left.tail[0][0]


def test_facing_mirrors_knee_direction():
    def cross(anim):
        leg = anim.legs[0]
        return (leg.knee[0] - leg.hip[0]) * (leg.foot[1] - leg.hip[1]) - (
            leg.knee[1] - leg.hip[1]
        ) * (leg.foot[0] - leg.hip[0])

    right = cross(_walk("biped", 1, 120))
    left = cross(_walk("biped", -1, -120))
    assert right * left < 0


def _run_pose(seed, kind="quadruped"):
    anim = CreatureAnimator(make_spec(kind), 100, 600, seed=seed)
    for i in range(180):
        anim.update(
            1 / 60,
            x=100 + i * 1.2,
            y=600,
            vx=100,
            state="walk",
            on_ground=True,
            ground_height=lambda x: 600,
            head_target=(400, 500),
        )
    return (
        anim.body_x,
        anim.body_y,
        anim.body_scale_y,
        anim.head,
        tuple((leg.foot_x, leg.foot_y) for leg in anim.legs),
    )


def test_same_seed_is_deterministic():
    assert _run_pose(7) == _run_pose(7)


def test_squash_blink_and_reduce_motion():
    anim = CreatureAnimator(make_spec("biped"), 100, 600, seed=3)
    for _ in range(20):
        anim.update(
            1 / 60,
            x=100,
            y=500,
            vx=0,
            vy=400,
            state="fall",
            on_ground=False,
        )
    assert anim.body_scale_y < 1.0
    assert anim.body_scale_x > 1.0

    blinked = False
    for _ in range(500):
        anim.update(
            1 / 60,
            x=100,
            y=600,
            vx=0,
            state="idle",
            on_ground=True,
            ground_height=lambda x: 600,
        )
        blinked = blinked or anim.blink > 0.5
    assert blinked

    reduced = CreatureAnimator(make_spec("biped"), 100, 600, seed=3)
    for _ in range(20):
        reduced.update(
            1 / 60,
            x=100,
            y=500,
            vx=0,
            vy=400,
            state="fall",
            on_ground=False,
            reduce_motion=True,
        )
    assert reduced.body_scale_y == 1.0
    assert reduced.blink == 0.0


def test_draw_all_kinds_and_states():
    pygame.init()
    surface = pygame.Surface((640, 480))
    surface.fill((10, 10, 10))
    for kind in ("biped", "quadruped", "floating"):
        anim = CreatureAnimator(make_spec(kind), 320, 400, seed=1)
        for state in STATES:
            for _ in range(6):
                anim.update(
                    1 / 60,
                    x=320,
                    y=400,
                    vx=60,
                    state=state,
                    on_ground=state not in ("jump", "fall"),
                    ground_height=lambda x: 400,
                    head_target=(500, 200),
                )
            draw_creature(surface, anim)
    assert pygame.surfarray.array3d(surface).max() > 20
