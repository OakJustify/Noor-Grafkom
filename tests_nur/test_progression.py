"""Input-only traversal regressions: no teleports, altered physics or solver cheats."""

import pytest

from echo_game.physics import DT, Input
from nur_game.game import Game
from nur_game import config


@pytest.mark.parametrize("room", range(4))
def test_authored_rooms_are_traversable_with_normal_inputs(room):
    game = Game(room=room, muted=True, persist=False)
    mode = "approach"
    grabbed_rope = False
    try:
        for _ in range(5000):
            world = game.world
            x, y = world.player.position
            jump, grab = False, False
            if room == 0:
                jump = 400 < x < 980
            elif room == 1:
                jump = 520 < x < 900 or 1030 < x < 1410
            elif room == 2:
                jump = world.crates[0].body.position.x > 925 and x < 1060
                jump = jump or 1130 < x < 1450
            elif room == 3:
                if mode == "approach":
                    jump = 550 < x < 557
                    grab = x > 675
                    if world.grab_kind == "rope":
                        mode = "swing"
                        grabbed_rope = True
                    elif x > 733 and world.grounded:
                        mode = "launch"
                if mode == "launch":
                    jump, grab = True, False
                    mode = "swing"
                elif mode == "swing":
                    jump, grab = False, True
                    if world.grab_kind == "rope" and x > 925:
                        mode = "released"
                        jump, grab = True, False
                elif mode == "released":
                    jump = 1110 < x < 1410
            game.update(DT, Input(move=1, jump=jump, grab=grab))
            assert not world.dead, world.death_reason
            if world.complete:
                break
        assert world.complete, world.snapshot()
        if room == 2:
            assert world.gate_open
        if room == 3:
            assert grabbed_rope
    finally:
        game.audio.close()


def test_final_echoes_and_mercy_are_reachable_with_normal_inputs():
    game = Game(room=config.BOSS_ARENA_ROOM, muted=True, persist=False)
    # The story can reduce charge to zero before the arena; it must still finish.
    game.lantern.charge = 0
    try:
        for _ in range(5000):
            x, y = game.world.player.position
            boss = game.boss
            if boss.phase == 0:
                control = Input(move=1, jump=190 < x < 500 or 1020 < x < 1130)
            elif boss.phase == 1:
                move = -1 if x > 1090 else 1 if x < 1070 else 0
                control = Input(move=move, action=True)
            else:
                control = Input()
            game.update(DT, control)
            assert not game.world.dead
            if game.state == "ending":
                break
        assert game.state == "ending", game.snapshot()
        assert game.boss.name_presses == 3
        assert all(echo["taken"] for echo in game.boss.echoes)
    finally:
        game.audio.close()
