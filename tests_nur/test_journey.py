"""Journey mechanics, checkpoint safety and honest input-only duration checks.

Unit interaction checks position fixtures next to devices. Traversal and duration
checks below use normal inputs only, without modifying solver or quest state.
"""

import json

import pygame
import pytest

from echo_game.physics import DT, Input
from nur_game import config
from nur_game.game import Game
from nur_game.levels import NUR_LEVELS, room_count
from nur_game.physics import NurWorld
from nur_game.quests import QuestState
from scripts.playtest_nur import JourneyPilot, run_playtest


def press(quest, world, x):
    world.player.position = (x, 430)  # Unit fixture, not traversal evidence.
    quest.update(Input(), world)
    return quest.update(Input(action=True), world)


def first_device(family):
    room = next(n for n in NUR_LEVELS if n.quest and n.quest.family == family)
    world = NurWorld(4, room.level)
    quest = QuestState(room.quest)
    # Inspect required sources until reaching the first destination.
    while quest.current.kind == "source":
        press(quest, world, quest.current.x)
    return quest, world, quest.current


def test_campaign_has_four_new_acts_and_six_real_puzzle_families():
    assert room_count() == 29 and config.BOSS_ARENA_ROOM == room_count() - 1
    expanded = NUR_LEVELS[4:-1]
    assert len(expanded) == 24
    assert {room.act for room in expanded} == {2, 3, 4, 5}
    assert {room.quest.family for room in expanded} == {"relay", "valve", "tone", "weight", "mirror", "circuit"}
    assert len({room.quest.story for room in expanded}) == 24
    assert len({tuple(node.x for node in room.quest.nodes) for room in expanded}) == 3
    assert len({room.quest.order for room in expanded}) == 2
    for room in expanded:
        assert room.level.gate and len(room.quest.nodes) == 6
        assert set(room.quest.order) == set(range(6))
    assert len(NUR_LEVELS[-1].echoes) == 3


def test_remote_interaction_and_held_e_cannot_solve_multiple_steps():
    room = NUR_LEVELS[4]
    quest, world = QuestState(room.quest), NurWorld(4, room.level)
    assert quest.update(Input(action=True), world) is None
    assert quest.stage == 0
    press(quest, world, quest.current.x)
    assert quest.stage == 1
    world.player.position = (quest.current.x, 430)
    for _ in range(100):
        assert quest.update(Input(action=True), world) is None
    assert quest.stage == 1


def test_match_requires_the_correct_spatial_slot_not_repeated_e():
    quest, world, node = first_device("relay")
    stage = quest.stage
    wrong = (node.target + 1) % 4
    press(quest, world, node.x + (wrong - 1.5) * 32)
    assert quest.stage == stage
    press(quest, world, node.x + (node.target - 1.5) * 32)
    assert quest.stage == stage + 1


def test_device_journal_entries_keep_the_actual_clue_not_just_success_text():
    quest, world, node = first_device("relay")
    result = press(quest, world, node.x + (node.target - 1.5) * 32)
    assert quest.plan.nodes[0].hint in result["journal"]
    assert node.label in result["journal"]


def test_melody_remembers_prefix_resets_on_wrong_note_and_accepts_sequence():
    quest, world, node = first_device("tone")
    stage = quest.stage
    press(quest, world, node.x + (node.pattern[0] - 1.5) * 32)
    assert quest.values[quest.plan.order[stage]] == 1
    wrong = next(n for n in range(4) if n not in (node.pattern[0], node.pattern[1]))
    press(quest, world, node.x + (wrong - 1.5) * 32)
    assert quest.values[quest.plan.order[stage]] == 0
    for note in node.pattern:
        result = press(quest, world, node.x + (note - 1.5) * 32)
        assert result["note"] == note
    assert quest.stage == stage + 1


@pytest.mark.parametrize("family", ("valve", "circuit"))
def test_three_independent_switches_require_the_requested_flow_or_pattern(family):
    quest, world, node = first_device(family)
    stage = quest.stage
    bits = [bit for bit in range(3) if node.target & (1 << bit)]
    for bit in bits:
        press(quest, world, node.x + (bit - 1) * 42)
    assert quest.stage == stage + 1
    assert quest.values[quest.plan.order[stage]] == node.target


def test_weight_requires_a_real_crate_not_the_player_on_the_plate():
    quest, world, node = first_device("weight")
    world.quest = quest
    stage = quest.stage
    assert not press(quest, world, node.x).get("solved")
    assert quest.stage == stage
    world.crates[0].body.position = (node.plate[0] + 50, 429.15)
    world.crates[0].shape.cache_bb()
    assert press(quest, world, node.x)["solved"]
    assert quest.stage == stage + 1


def test_unfinished_puzzle_cannot_complete_even_past_exit():
    room = NUR_LEVELS[4]
    world = NurWorld(4, room.level)
    world.quest = QuestState(room.quest)
    world.player.position = (3440, 430)
    world.step(Input(), DT)
    assert not world.complete and not world.gate_open


@pytest.mark.parametrize("room", range(4, config.BOSS_ARENA_ROOM))
def test_every_new_room_is_traversable_input_only_with_an_empty_lantern(room):
    game, pilot = Game(room=room, muted=True, persist=False), JourneyPilot()
    game.lantern.charge = 0
    try:
        for _ in range(20000):
            game.update(DT, pilot.control(game))
            assert not game.world.dead, game.snapshot()
            assert game.lantern.protects and game.lantern.charge == 0
            if game.room != room:
                break
        assert game.room == room + 1, game.snapshot()
        assert game.quest_progress[str(room)]["stage"] == 6
        assert len(game.journal) >= 6
    finally:
        game.audio.close()


def test_full_campaign_exceeds_fifteen_minutes_without_idle_padding(tmp_path):
    report = run_playtest(tmp_path / "playtest.json")
    assert report["completed"] and report["error"] is None
    assert 900 <= report["gameplay_seconds"] < 1800
    assert report["active_input_seconds"] >= 900
    assert report["quest_steps_solved"] == 144
    assert len(report["rooms"]) == room_count()
    assert report["simulation"]["lantern"]["deaths"] == 0


def test_checkpoint_preserves_puzzles_clues_candle_and_zero_light(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    game, pilot = Game(room=5, seed=222, muted=True, persist=False), JourneyPilot()
    resumed = None
    try:
        while game.world.quest.stage < 3:
            game.update(DT, pilot.control(game))
        game.lantern.charge = 0
        game.candle_taken = True
        game.memory.add("photo")
        game.memory.candles = 1
        game.persist = True
        game._save()
        before = game.world.quest.snapshot()
        resumed = Game(muted=True, persist=False)
        assert resumed.load_save()
        assert resumed.room == 5 and resumed.seed == 222
        assert resumed.world.quest.snapshot() == before
        assert resumed.journal == game.journal
        assert resumed.memory.snapshot() == game.memory.snapshot()
        assert resumed.lantern.charge == 0 and resumed.lantern.protects
        assert resumed.candle_taken and resumed.play_seconds > 0
        assert resumed.narrative.anchor_index == game.narrative.anchor_index
        for _ in range(15000):
            resumed.update(DT, pilot.control(resumed))
            if resumed.room != 5:
                break
        assert resumed.room == 6
        assert not config.SAVE_PATH.with_suffix(".json.tmp").exists()
    finally:
        game.audio.close()
        if resumed:
            resumed.audio.close()


@pytest.mark.parametrize("data", [
    {}, {"room": 999, "seed": 1}, {"version": 7, "room": 0, "seed": 1},
    {"room": 4, "seed": 1, "memory": None},
    {"room": 4, "seed": 1, "quests": {"4": {"stage": "broken"}}},
    {"room": 4, "seed": 1, "quests": {"4": {"values": ["bad"]}}},
    {"room": 4, "seed": 1, "quests": {"4": {"inspected": [{}]}}},
    {"room": 4, "seed": 1, "journal": {"not-a-room": "broken"}},
    {"room": 4, "seed": 1, "play_seconds": float("nan")},
    {"room": 4, "seed": 1, "narrative": {"shown": None}},
])
def test_bad_saves_fail_without_mutating_the_game(game, tmp_path, monkeypatch, data):
    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    config.SAVE_PATH.write_text(json.dumps(data), encoding="utf-8")
    before = game.snapshot()
    assert not game.load_save()
    assert game.snapshot() == before


def test_legacy_boss_checkpoint_migrates_to_new_final_room(game, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    config.SAVE_PATH.write_text('{"room": 4, "seed": 1234}', encoding="utf-8")
    assert game.load_save()
    assert game.room == config.BOSS_ARENA_ROOM and game.boss is not None


def test_journal_opens_latest_page_and_pauses_gameplay_and_light(game):
    game.start(4)
    game.journal = {f"04:{n}": f"Catatan {n}" for n in range(6)}
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
    assert game.state == "journal" and game.journal_page == 1
    before, seconds = game.lantern.snapshot(), game.play_seconds
    game.update(0.1, Input(move=1))
    assert game.lantern.snapshot() == before and game.play_seconds == seconds
    game.draw()
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert game.journal_page == 0
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert game.state == "playing"


def test_long_campaign_background_cache_is_bounded(game):
    for room in range(room_count()):
        game.art.background(room)
    assert len(game.art._backgrounds) <= 6
