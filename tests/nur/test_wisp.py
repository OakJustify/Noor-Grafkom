import hashlib
import json

import pygame
import pytest

from nur_game.engine import Input, JUMP_SPEED
from nur_game.generate_wisp import export_wisp
from nur_game.physics import NurInput
from nur_game.wisp import (
    ANIMATIONS, FRAME_COUNT, FRAME_SIZE, PIVOT,
    WispAnimation, facing_sprite, jump_frame, movement_pose, wisp_sprite,
)


def digest(image):
    return hashlib.sha256(pygame.image.tobytes(image, "RGBA")).hexdigest()


@pytest.mark.parametrize("pose", ANIMATIONS)
def test_each_action_has_eight_unique_transparent_frames(pose):
    frames = [wisp_sprite(pose, frame) for frame in range(FRAME_COUNT)]
    assert 5 <= len(frames) <= 10
    assert len({digest(image) for image in frames}) == FRAME_COUNT
    for image in frames:
        assert image.get_size() == FRAME_SIZE
        assert image.get_at((0, 0)).a == 0
        assert image.get_bounding_rect().w > 25
        assert image.get_bounding_rect().h > 45
    assert frames[0] is wisp_sprite(pose, 0)


def test_animation_sets_have_distinct_art_not_renamed_frames():
    assert len({digest(wisp_sprite(pose, 0)) for pose in ANIMATIONS}) == len(ANIMATIONS)


@pytest.mark.parametrize("pose,velocity", [("idle", (0, 0)), ("walk", (190, 0)), ("run", (300, 0))])
def test_loop_playback_visits_all_frames_and_wraps(pose, velocity):
    animation = WispAnimation()
    animation.update(0, velocity, True)
    frames = []
    for _ in range(FRAME_COUNT):
        frames.append(animation.frame)
        animation.update(1 / ANIMATIONS[pose].fps, velocity, True)
    assert frames == list(range(FRAME_COUNT))
    assert animation.frame == 0


def test_jump_tracks_takeoff_apex_and_fall_without_looping():
    animation = WispAnimation()
    frames = []
    for frame in range(FRAME_COUNT):
        velocity = -JUMP_SPEED + (frame + 0.1) * 2 * JUMP_SPEED / FRAME_COUNT
        animation.update(0.1, (190, velocity), False)
        frames.append(animation.frame)
    assert frames == list(range(FRAME_COUNT))
    animation.update(3, (190, 1000), False)
    assert animation.pose == "jump" and animation.frame == 7
    animation.update(0.1, (0, 0), True)
    assert animation.pose == "idle" and animation.frame == 0
    assert jump_frame(0) == 4


def test_left_facing_is_cached_mirror_with_consistent_pivot():
    right = facing_sprite("run", 2, 1)
    left = facing_sprite("run", 2, -1)
    assert left is facing_sprite("run", 2, -1)
    assert digest(left) == digest(pygame.transform.flip(right, True, False))
    assert FRAME_SIZE[0] - 1 - (FRAME_SIZE[0] - 1 - PIVOT[0]) == PIVOT[0]


def test_pose_selection_does_not_change_input_or_physics():
    assert movement_pose((-80, 0), True) == "walk"
    assert movement_pose((-190, 0), True) == "walk"
    assert movement_pose((-300, 0), True) == "run"
    assert movement_pose((0, -100), False) == "jump"


def test_exported_sheets_match_every_live_frame_and_are_deterministic(tmp_path):
    manifest = export_wisp(tmp_path)
    first = (tmp_path / "manifest.json").read_bytes()
    for pose, spec in manifest["animations"].items():
        sheet = pygame.image.load(str(tmp_path / spec["sheet"]))
        assert sheet.get_size() == (FRAME_SIZE[0] * FRAME_COUNT, FRAME_SIZE[1])
        assert spec["frame_count"] == 8
        for frame, rect in enumerate(spec["frame_rects"]):
            assert digest(sheet.subsurface(rect)) == digest(wisp_sprite(pose, frame))
    export_wisp(tmp_path)
    assert (tmp_path / "manifest.json").read_bytes() == first
    assert json.loads(first)["pivot"] == list(PIVOT)


def test_game_animates_while_idle_and_freezes_on_pause(game):
    game.update(0.1, Input())
    for _ in range(5):
        game.update(0.1, Input())
    before = game.player_animation.snapshot()
    for _ in range(2):
        game.update(0.1, Input())
    assert game.player_animation.snapshot() != before
    game.state = "paused"
    before = game.player_animation.snapshot()
    game.update(0.1, Input())
    assert game.player_animation.snapshot() == before


def test_game_animation_updates_from_movement_and_restarts(game):
    for _ in range(20):
        game.update(1 / 60, Input(move=1))
    assert game.player_animation.pose == "walk"
    for _ in range(6):
        game.update(1 / 60, NurInput(move=1, sprint=True))
    assert game.player_animation.pose == "run"
    game.update(1 / 60, Input(move=1, jump=True))
    assert game.player_animation.pose == "jump"
    game.restart_room()
    assert game.player_animation.snapshot() == {"pose": "idle", "frame": 0}


def test_game_renderer_draws_selected_frame_without_advancing_animation(game):
    game.player_animation = WispAnimation(pose="run", frame=3)
    before = game.player_animation.snapshot()
    # Drawing is pure; only update() advances playback, including when paused.
    first = digest(game.draw())
    assert digest(game.draw()) == first
    assert game.player_animation.snapshot() == before
    game.player_animation.frame = 4
    assert digest(game.draw()) != first
