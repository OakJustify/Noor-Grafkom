"""The input-only campaign pilot must exercise live cinematic progression."""

from nur_game.game import Game
from nur_game.physics import NurInput
from scripts.playtest_continuum import ContinuousPilot


def test_pilot_does_not_count_gameplay_input_while_opening_is_running():
    game = Game(muted=True, persist=False)
    try:
        assert ContinuousPilot().control(game) == NurInput()
    finally:
        game.audio.close()


def test_pilot_walks_new_final_road_without_requesting_removed_boss():
    game = Game(room=28, muted=True, persist=False)
    try:
        assert game.boss is None
        try:
            control = ContinuousPilot(care=False).control(game)
        except AttributeError:
            control = None
        assert control is not None, 'The final pilot still expects the old boss-only adapter'
        assert control.move == 1 and not control.action
    finally:
        game.audio.close()


def test_report_does_not_pad_gameplay_duration_with_opening_seconds(tmp_path):
    from scripts.playtest_continuum import run

    report = run(tmp_path/'short-route.json', max_seconds=1)
    assert report['gameplay_seconds'] == 0
    assert report['cutscene_seconds'] == 1
    assert report['scene_completion_order'] == []
