import pygame

from echo_game.physics import DT, Input
from nur_game.levels import NUR_LEVELS
from nur_game.physics import NurWorld


def test_memory_candle_requires_nearby_interaction_and_is_single_use(game):
    game.start(room=2)
    game.memory.add("key", false=True)
    candle = NUR_LEVELS[2].candle
    game._collect(130, 430, action=True)
    assert not game.candle_taken
    game._collect(*candle, action=False)
    assert not game.candle_taken
    charge = game.lantern.charge
    game._collect(*candle, action=True)
    assert game.candle_taken
    assert game.memory.truth == 1
    assert game.memory.candles == 0
    assert game.lantern.charge == charge
    game.memory.add("letter", false=True)
    game.restart_room()
    game._collect(*candle, action=True)
    assert game.memory.truth == 1
    assert "letter" in game.memory.false
    game.start(room=2)
    assert not game.candle_taken


def test_e_holds_crate_and_w_climbs_without_releasing_rope(game, monkeypatch):
    class Keys:
        def __getitem__(self, key):
            return key in (pygame.K_e, pygame.K_w)

    monkeypatch.setattr(pygame.key, "get_pressed", lambda: Keys())
    game.world.grab_kind = "rope"
    control = game._control()
    assert control.grab and control.action
    assert control.climb == 1
    assert not control.jump
    game.world.grab_kind = ""
    assert game._control().jump


def test_r_retries_while_playing_without_resetting_memory(game):
    game.memory.add("photo")
    game.lantern.collect_fragment()
    game.world.player.position = (700, 430)
    game.event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    assert game.world.player.position.x == 130
    assert "photo" in game.memory.found
    assert game.lantern.capacity == 0.75


def test_closed_door_blocks_without_contact_death():
    world = NurWorld(2, NUR_LEVELS[2].level)
    world.player.position = (1090, 430)
    for _ in range(240):
        world.step(Input(move=1), DT)
    assert not world.dead
    assert world.player.position.x < world.level.gate.x


def test_kitchen_weight_relay_opens_and_closes():
    world = NurWorld(2, NUR_LEVELS[2].level)
    crate = world.crates[0]
    crate.body.position = (930, 431)
    for _ in range(120):
        world.step(Input(), DT)
    assert world.gate_open
    assert world.gate_fraction > 0.95
    crate.body.position = (570, 431)
    crate.body.velocity = (0, 0)
    for _ in range(120):
        world.step(Input(), DT)
    assert not world.gate_open
    assert world.gate_fraction < 0.05


def test_final_room_exit_does_not_freeze_unfinished_boss():
    from nur_game import config
    world = NurWorld(config.BOSS_ARENA_ROOM, NUR_LEVELS[config.BOSS_ARENA_ROOM].level)
    world.player.position = (1510, 430)
    for _ in range(30):
        world.step(Input(move=-1), DT)
        assert not world.complete
    assert world.player.position.x < 1490
