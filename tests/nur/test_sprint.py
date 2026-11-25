import json
from collections import defaultdict
from dataclasses import replace

import pygame
import pytest

from nur_game.geometry import Rect
from nur_game.engine import DT, MOVE_SPEED
from nur_game import config
from nur_game.levels import NUR_LEVELS
from nur_game.physics import NurInput, NurWorld
from nur_game.state import Stamina
from scripts.playtest_nur import JourneyPilot, run_playtest


def empty_world():
    level = replace(NUR_LEVELS[0].level, width=20000, exit=(19900, 430),
                    terrain=(Rect(-80, 460, 20200, 160),), crates=())
    return NurWorld(0, level)


def test_shift_really_increases_speed_and_spends_stamina_without_touching_echo():
    walk, run = empty_world(), empty_world()
    for _ in range(120):
        walk.step(NurInput(move=1), DT)
        run.step(NurInput(move=1, sprint=True), DT)
    assert 180 <= walk.player.velocity.x <= config.WALK_SPEED + 1
    assert 285 <= run.player.velocity.x <= config.RUN_SPEED + 1
    assert run.player.position.x > walk.player.position.x + 90
    assert 0.7 < run.stamina.amount < 0.8 and walk.stamina.amount == 1
    assert MOVE_SPEED == 190


def test_exhaustion_forces_walk_then_recovers_without_shift_key_spam():
    world = empty_world()
    for _ in range(510):
        world.step(NurInput(move=1, sprint=True), DT)
    assert world.stamina.exhausted and not world.sprinting
    assert world.player.velocity.x <= config.WALK_SPEED + 1
    for _ in range(600):
        world.step(NurInput(move=1, sprint=True), DT)
        if world.sprinting:
            break
    assert world.sprinting and not world.stamina.exhausted
    assert world.stamina.amount >= config.STAMINA_RESTART - 0.01


def test_idle_shift_costs_nothing_and_rest_recovers_faster_than_walking():
    world = empty_world()
    for _ in range(240):
        world.step(NurInput(sprint=True), DT)
    assert not world.sprinting and world.stamina.amount == 1
    resting, walking = Stamina(amount=0.2), Stamina(amount=0.2)
    for _ in range(120):
        resting.step(DT, False, False)
        walking.step(DT, False, True)
    assert resting.amount > walking.amount > 0.2


def test_sprint_does_not_override_crate_pull_speed_or_charge_for_it(game):
    crate = game.world.crates[0]
    game.world.player.position = (crate.body.position.x - 45, 430)
    for _ in range(25):
        game.update(DT, NurInput(move=1, grab=True, sprint=True))
    assert game.world.grab_kind == "crate"
    assert not game.world.sprinting and game.stamina.amount == 1
    assert abs(game.world.player.velocity.x) <= 135


@pytest.mark.parametrize("key", (pygame.K_LSHIFT, pygame.K_RSHIFT))
def test_keyboard_shift_maps_to_sprint_not_the_q_reality_shift(game, monkeypatch, key):
    keys = defaultdict(bool, {pygame.K_d: True, key: True})
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: keys)
    control = game._control()
    assert control.sprint and control.move == 1 and not control.shift
    for _ in range(20):
        game.update(DT, control)
    assert game.world.sprinting and game.player_animation.pose == "run"
    keys[key] = False
    for _ in range(20):
        game.update(DT, game._control())
    assert not game.world.sprinting and game.player_animation.pose == "walk"


def test_pause_and_journal_freeze_stamina_and_zero_charge_still_protects(game):
    game.lantern.charge = 0
    for _ in range(60):
        game.update(DT, NurInput(move=1, sprint=True))
    assert game.lantern.protects and game.lantern.charge == 0 and game.stamina.amount < 1
    before = game.stamina.snapshot()
    for state in ("paused", "journal"):
        game.state = state
        game.update(0.1, NurInput(move=1, sprint=True))
        assert game.stamina.snapshot() == before


def test_stamina_survives_retry_room_change_and_checkpoint(game, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    game.stamina.amount = 0.2
    game.stamina.exhausted = True
    game.stamina.recovery_delay = 0.4
    before = game.stamina.snapshot()
    game.restart_room()
    assert game.stamina.snapshot() == before and game.world.stamina is game.stamina
    game.room = 4
    game.restart_room()
    assert game.stamina.snapshot() == before and game.world.stamina is game.stamina
    game.persist = True
    game._save()
    assert game.load_save()
    assert game.stamina.snapshot() == before and game.world.stamina is game.stamina


@pytest.mark.parametrize("value", (None, {"amount": float("nan")}, {"amount": -1}, {"exhausted": "yes"}))
def test_invalid_stamina_saves_do_not_mutate_game(game, tmp_path, monkeypatch, value):
    monkeypatch.setattr(config, "SAVE_PATH", tmp_path / "nur.json")
    config.SAVE_PATH.write_text(json.dumps({"version": 3, "room": 0, "seed": 1, "stamina": value}))
    before = game.snapshot()
    assert not game.load_save()
    assert game.snapshot() == before


def test_sprinting_campaign_remains_over_fifteen_minutes_input_only(tmp_path):
    report = run_playtest(tmp_path / "sprint.json", pilot=JourneyPilot(sprint=True))
    assert report["completed"] and report["error"] is None
    assert report["gameplay_seconds"] >= 900 and report["active_input_seconds"] >= 900
    assert report["sprint_seconds"] > 120 and report["exhaustions"] > 0
    assert report["quest_steps_solved"] == 144 and report["reality_shifts"] == 92
    assert report["simulation"]["lantern"]["deaths"] == 0
