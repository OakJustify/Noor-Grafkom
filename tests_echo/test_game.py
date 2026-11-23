import pygame
import pytest

from echo_game.game import Game, SIZE
from echo_game.levels import LEVELS
from echo_game.physics import Input
from echo_game.pilot import Pilot


@pytest.fixture
def game():
    g = Game(persist=False)
    pygame.display.set_mode(SIZE)
    yield g
    g.close()


def key(game, value):
    game.event(pygame.event.Event(pygame.KEYDOWN, key=value))


def test_title_start_pause_help_restart(game):
    assert game.state == "menu"
    key(game, pygame.K_RETURN)
    assert game.state == "playing"
    game.update(1, Input(move=1))
    key(game, pygame.K_ESCAPE)
    pos = tuple(game.world.player.position)
    game.update(1, Input(move=1))
    assert tuple(game.world.player.position) == pos
    assert game.state == "paused"
    key(game, pygame.K_ESCAPE)
    key(game, pygame.K_h)
    game.update(1, Input(move=1))
    assert tuple(game.world.player.position) == pos
    key(game, pygame.K_h)
    key(game, pygame.K_r)
    assert tuple(game.world.player.position) == game.world.level.spawn


def test_focus_loss_pauses(game):
    game.start()
    game.event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    assert game.state == "paused"


def test_audio_state_matches_mute_argument():
    unmuted = Game(persist=False)
    try:
        assert unmuted.audio.enabled
        assert not unmuted.audio.muted
    finally:
        unmuted.close()
    muted = Game(muted=True, persist=False)
    try:
        assert not muted.audio.enabled
        assert muted.audio.muted
    finally:
        muted.close()


def test_ending_clock_advances_and_new_run_restores_sanity(game):
    game.state = "ending"
    game.final_transition_timer = 6.0
    game.update(1.0)
    assert game.final_transition_timer == 7.0

    game.sanity = 0.0
    game.narrative_stage = 3
    key(game, pygame.K_n)
    assert game.state == "playing"
    assert game.sanity == 1.0
    assert game.narrative_stage == 0


def test_pause_freezes_final_countdown(game):
    game.start()
    game.sanity = 0.0
    game.narrative_stage = 3
    game.final_transition_timer = 1.0
    key(game, pygame.K_ESCAPE)
    game.update(2.0)
    assert game.state == "paused"
    assert game.final_transition_timer == 1.0


def test_atmosphere_desaturation_changes_canvas(game):
    game.canvas.fill((0, 0, 0))
    pygame.draw.rect(game.canvas, (255, 0, 0), (0, 0, 320, 540))
    game.desaturation_factor = 1.0
    game._apply_atmosphere_overlay()
    red, green, blue, _ = game.canvas.get_at((160, 270))
    assert red == green == blue


def test_ending_new_journey_restarts_first_room(game):
    game.start(4)
    game.state = "ending"
    key(game, pygame.K_n)
    assert game.state == "playing" and game.checkpoint == 0


def test_muting_and_resuming_does_not_crash(game):
    key(game, pygame.K_m)
    assert game.muted
    key(game, pygame.K_m)
    assert not game.muted


def test_full_application_campaign_transitions_to_ending(game):
    game.start(0)
    pilot = Pilot(0)
    chapters = {0}
    for _ in range(5000):
        if game.world.chapter != pilot.chapter:
            pilot = Pilot(game.world.chapter)
            chapters.add(game.world.chapter)
        game.update(1 / 60, pilot.control(game.world))
        assert not game.world.dead, game.world.snapshot()
        if game.state == "ending":
            break
    assert chapters == set(range(len(LEVELS)))
    assert game.state == "ending"


def test_death_restarts_all_room_state(game):
    game.start(1)
    game.world.kill("Test fall")
    game.update(1.6)
    assert not game.world.dead
    assert tuple(game.world.player.position) == game.world.level.spawn
    assert game.world.grab_joint is None


def test_render_all_rooms_and_ui_states(game):
    for chapter in range(len(LEVELS)):
        game.start(chapter)
        for _ in range(10):
            game.update(1 / 60)
        for state in ("playing", "paused", "menu", "ending"):
            game.state = state
            assert game.draw().get_size() == SIZE


def test_held_action_is_not_repeated_across_fixed_substeps(game):
    game.start(2)
    game.world.player.position = game.world.level.valve
    game.world.space.reindex_shapes_for_body(game.world.player)
    for _ in range(60):
        game.update(1 / 60, Input(action=True))
    assert game.world.water_active
    assert game.world.water_surface == pytest.approx(480)


def test_up_climbs_held_rope_instead_of_releasing_it(game):
    game.start(1)
    game.world.player.position = game.world.ropes[-1].position
    game.world.space.reindex_shapes_for_body(game.world.player)
    game.update(1 / 60, Input(grab=True))
    assert game.world.grab_kind == "rope"
    key(game, pygame.K_UP)
    assert not game.pending_jump
    before = game.world.rope_distance
    game.update(1 / 60, Input(grab=True, climb=1))
    assert game.world.grab_kind == "rope"
    assert game.world.rope_distance < before


@pytest.mark.parametrize("switch", ["magnet_switch", "gravity_switch"])
def test_magnetic_controls_do_not_toggle_repeatedly_when_held(game, switch):
    game.start(5)
    # Switch-contact fixture isolates frame/substep edge semantics.
    game.world.player.position = getattr(game.world.level.magnet, switch)
    game.world.space.reindex_shapes_for_body(game.world.player)
    for _ in range(30):
        game.update(1 / 60, Input(action=True))
    rig = game.world.magnet
    assert rig.enabled == (switch == "magnet_switch")
    assert rig.box_gravity == (-1 if switch == "gravity_switch" else 1)
    game.update(1 / 60, Input())
    game.update(1 / 60, Input(action=True))
    assert not rig.enabled and rig.box_gravity == 1


def test_magnetic_room_restart_resets_constraints_and_controls(game):
    game.start(5)
    pilot = Pilot(5)
    for _ in range(200):
        game.update(1 / 60, pilot.control(game.world))
        if pilot.phase == "cross":
            break
    assert sorted(game.world.magnet.captured) == [0]
    key(game, pygame.K_r)
    assert game.checkpoint == 5
    assert game.world.magnet.snapshot() == {"enabled": False, "box_gravity": 1, "captured": []}
    assert not game.world.magnet.capture_history
    assert tuple(game.world.player.position) == game.world.level.spawn
