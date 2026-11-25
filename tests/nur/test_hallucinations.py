"""Perceptual rules and dimensional rendering, separate from input-only traversal."""

import math

import pygame
import pytest

from nur_game.engine import DT
from nur_game import config
from nur_game.hallucinations import HallucinationState, hypercube_projection
from nur_game.levels import NUR_LEVELS
from nur_game.physics import NurInput, NurWorld
from nur_game.quests import quest_for


def fixture(family):
    index = next(n for n, room in enumerate(NUR_LEVELS) if room.quest and room.quest.family == family)
    room = NUR_LEVELS[index]
    world = NurWorld(index, room.level)
    world.quest = quest_for(room.quest)
    world.configure_phantoms()
    return world.quest, world


def press(quest, world, x=None, y=430):
    if x is not None:
        world.player.position = (x, y)  # Unit fixture, not traversal evidence.
    quest.update(NurInput(), world, DT)
    result = quest.update(NurInput(action=True), world, DT)
    world.sync_phantoms()
    return result


def shift(quest, world):
    quest.update(NurInput(), world, DT)
    result = quest.update(NurInput(shift=True), world, DT)
    world.sync_phantoms()
    return result


def capture_sources(quest, world):
    if quest.phase == 0:
        shift(quest, world)
    while quest.current.kind == "apparition":
        press(quest, world, quest.current.x)


@pytest.mark.parametrize("dimension", (3, 4, 5))
def test_hypercubes_have_the_correct_vertices_edges_and_finite_projection(dimension):
    for frame in (0, 16, 32, 48):
        points, edges = hypercube_projection(dimension, frame)
        assert len(points) == 2 ** dimension
        assert len(edges) == dimension * 2 ** (dimension - 1)
        assert len(set(edges)) == len(edges)
        assert all(math.isfinite(value) and abs(value) < 8 for point in points for value in point)
    assert hypercube_projection(dimension, 16)[0] != hypercube_projection(dimension, 0)[0]


def test_q_is_edge_triggered_and_never_toggles_lantern_protection(game):
    game.start(4)
    assert game.world.quest.phase == 0
    game.lantern.charge = 0
    for _ in range(10):
        game.update(DT, NurInput(shift=True))
        assert game.lantern.protects and game.lantern.charge == 0
    assert game.world.quest.phase == 1
    game.update(DT, NurInput())
    game.update(DT, NurInput(shift=True))
    assert game.world.quest.phase == 0


def test_real_keyboard_q_reaches_the_game_control(game):
    game.start(4)
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
    control = game._control()
    assert control.shift
    game.update(DT, control)
    assert game.world.quest.phase == 1


def test_apparition_cannot_be_captured_in_the_wrong_plane():
    quest, world = fixture("absence")
    result = press(quest, world, quest.current.x)
    assert not result.get("solved") and quest.stage == 0
    assert "Q" in result["text"]
    shift(quest, world)
    assert press(quest, world, quest.current.x)["solved"]
    assert quest.stage == 1


def test_absence_requires_the_object_to_disappear_before_anchoring():
    quest, world = fixture("absence")
    capture_sources(quest, world)
    node = quest.current
    assert quest.phase == 1
    assert not press(quest, world, node.x).get("solved")
    shift(quest, world)
    assert press(quest, world, node.x)["solved"]
    assert quest.stage == 2


def test_parallax_requires_alignment_not_just_e_near_the_device():
    quest, world = fixture("parallax")
    capture_sources(quest, world)
    shift(quest, world)
    target, stage = quest.interaction_x, quest.stage
    assert not press(quest, world, target + 25).get("solved")
    assert quest.stage == stage
    assert press(quest, world, target)["solved"]


def test_false_witness_does_not_reset_progress_but_cannot_open_the_gate():
    quest, world = fixture("witness")
    capture_sources(quest, world)
    shift(quest, world)
    node, stage = quest.current, quest.stage
    offsets = (-44, 0, 44)
    wrong = (node.target + 1) % 3
    assert not press(quest, world, node.x + offsets[wrong]).get("solved")
    assert quest.stage == stage and not quest.complete
    assert press(quest, world, quest.interaction_x)["solved"]


def test_phantom_stairs_have_real_collision_only_in_gaung_and_drop_safely():
    quest, world = fixture("fold")
    assert not world.phantom_shapes
    shift(quest, world)
    assert len(world.phantom_shapes) == len(quest.plan.platforms)
    top = quest.plan.platforms[1]
    world.player.position = (top.x + top.w / 2, top.y - 22)
    world.player.velocity = (0, 0)
    for _ in range(6):
        world.step(NurInput(), DT)
    assert world.grounded
    shift(quest, world)
    assert not world.phantom_shapes and not world.grounded
    for _ in range(180):
        world.step(NurInput(), DT)
    assert not world.dead and world.grounded
    assert world.player.position.y > 430


def test_materialisation_does_not_spawn_a_platform_inside_the_player():
    quest, world = fixture("fold")
    low = quest.plan.platforms[0]
    world.player.position = (low.x + 40, low.y + 8)
    shift(quest, world)
    assert low not in world.phantom_shapes
    world.player.position = (low.x - 50, 430)
    world.sync_phantoms()
    assert low in world.phantom_shapes


def test_empty_floor_below_the_fold_cannot_confirm_the_anchor():
    quest, world = fixture("fold")
    capture_sources(quest, world)
    node, stage = quest.current, quest.stage
    result = press(quest, world, node.x, node.y + 30)
    assert not result.get("solved")
    assert quest.stage == stage


def test_plane_render_changes_and_afterimages_do_not_mutate_simulation(game):
    game.start(4)
    game.notice_timer = 0
    present = pygame.image.tobytes(game.draw(), "RGB")
    game.update(DT, NurInput(shift=True))
    before = game.world.quest.snapshot()
    reflection = pygame.image.tobytes(game.draw(), "RGB")
    assert present != reflection
    assert game.world.quest.snapshot() == before


def test_journal_and_pause_do_not_process_shifts_or_advance_the_hallucination_clock(game):
    game.start(4)
    game.state = "journal"
    before = game.world.quest.clock
    game.update(0.1, NurInput(shift=True))
    assert game.world.quest.phase == 0 and game.world.quest.clock == before
    game.state = "paused"
    game.update(0.1, NurInput(shift=True))
    assert game.world.quest.phase == 0 and game.world.quest.clock == before


def test_legacy_puzzle_milestones_are_credited_without_resetting_the_campaign(game, tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    config.SAVE_PATH.write_text(json.dumps({
        "version": 2, "room": 4, "seed": 2,
        "quests": {"4": {"stage": 2, "values": [0] * 6, "inspected": [0, 3]}},
        "journal": {"04:0": "old oil clue", "04:3": "old slot puzzle"},
    }), encoding="utf-8")
    assert game.load_save()
    assert isinstance(game.world.quest, HallucinationState)
    assert game.world.quest.stage == 2
    assert game.world.quest.snapshot()["schema"] == "hallucination-v1"
    assert "Gaung" in game.journal["04:0"]


def test_saved_gaung_fold_checkpoint_restores_platforms_and_can_continue(game, tmp_path, monkeypatch):
    from scripts.playtest_nur import JourneyPilot

    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    game.start(7)
    pilot = JourneyPilot()
    for _ in range(20000):
        game.update(DT, pilot.control(game))
        if game.world.quest.stage == 2:
            break
    assert game.world.quest.stage == 2 and game.world.quest.phase == 1
    game.persist = True
    game._save()
    assert game.load_save()
    assert game.world.quest.stage == 2 and game.world.quest.phase == 1
    assert len(game.world.phantom_shapes) == len(game.world.quest.plan.platforms)
    for _ in range(15000):
        game.update(DT, pilot.control(game))
        assert not game.world.dead
        if game.room != 7:
            break
    assert game.room == 8
