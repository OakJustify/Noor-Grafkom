import json
import math

import pygame

from nur_game import config
from nur_game.boss import AlzheimerBoss
from nur_game.game import Game, main
from nur_game.levels import Echo
from nur_game.story import CUTSCENES, FRAGMENTS


def test_fragment_collection_dimms_lantern_and_records_memory(game):
    fragment = FRAGMENTS[0]
    game.world.player.position = (fragment.x, fragment.y)
    game._collect(fragment.x, fragment.y)
    assert fragment.key in game.memory.found
    assert game.lantern.capacity == 0.75
    assert game.lantern.collections == 1


def test_death_restarts_room_without_refilling_lantern(game):
    game.lantern.collect_fragment()
    capacity = game.lantern.capacity
    game.world.player.position = (500.0, 900.0)
    game.world.kill("test")
    for _ in range(90):
        game.update(1 / 60)
    assert game.lantern.deaths == 1
    assert game.lantern.capacity == capacity
    assert game.lantern.charge <= capacity


def test_boss_moves_to_mercy_phase_when_player_stops_name_calling():
    boss = AlzheimerBoss((Echo(100, 400, "a"),), 5)
    boss.echoes[0]["taken"] = True
    event = boss.update(1 / 60, (boss.x, boss.y), False, 0.25)
    assert event == "phase"
    assert boss.phase == 1
    for _ in range(3):
        boss.update(1.2, (boss.x, boss.y), True, 0.25)
    assert boss.phase == 2
    assert boss.update(2.5, (boss.x, boss.y), False, 0.25) == "win"
    assert boss.done is True


def test_assets_exist():
    for cutscene in CUTSCENES:
        assert (config.CUTSCENE_DIR / f"{cutscene.key}.png").exists()
    for name in ("creepy_vocal_ambience.ogg", "creepy_ambience.ogg", "creepy_dungeon_ambience.ogg"):
        assert (config.AUDIO_DIR / name).stat().st_size > 1000
    assert (config.AUDIO_DIR.parent / "CREDITS.md").exists()


def test_headless_report_is_deterministic(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    for report in (first, second):
        assert main(["--headless", "--frames", "2", "--no-save", "--seed", "7", "--report", str(report)]) == 0
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["simulation"]["room_name"] == "RUMAH"
        assert payload["sources"]
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_lighting_overlay_darkens_without_erasing_everything(game):
    surface = pygame.Surface(config.SIZE)
    surface.fill((120, 120, 120))
    game.art.draw_lighting(surface, (480, 270), 0.5, 2, 0.0)
    pixels = pygame.surfarray.array3d(surface)
    assert 0 <= int(pixels.mean()) < 120
    assert int(pixels.std()) > 4
