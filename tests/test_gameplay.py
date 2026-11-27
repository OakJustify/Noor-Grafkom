import pygame

import noor.config as C
from noor.core.i18n import I18n
from noor.scenes.gameplay import GameplayScene


class FakeAudio:
    def __init__(self):
        self.cues = []

    def load_stage(self, stage):
        pass

    def fade_out(self):
        pass

    def cue(self, name, volume=1.0):
        self.cues.append(name)
        return True

    def set_intensity(self, intensity, stage=None):
        pass

    def update(self, dt):
        pass


class FakeSave:
    def save_progress(self, data):
        pass


class FakeScenes:
    def __init__(self):
        self.replaced = None

    def replace(self, scene):
        self.replaced = scene


class FakeGame:
    def __init__(self):
        self.audio = FakeAudio()
        self.i18n = I18n(lang="id")
        self.save = FakeSave()
        self.scenes = FakeScenes()
        self.state = {
            "S": 100.0,
            "cap": 100.0,
            "clock_seconds": 0.0,
            "fragments_collected": [],
            "checkpoint_id": None,
            "deaths": 0,
            "rng_seed": 0,
            "accessibility": {},
        }


def test_fragment_collected_once():
    pygame.init()
    game = FakeGame()
    scene = GameplayScene(game, "s1_a")
    fr = scene.level["fragments"][0]
    scene.player.x, scene.player.y = fr["x"], fr["y"]
    scene.inp.interact = True
    scene.update(1 / 60)
    scene.inp.interact = True
    scene.update(1 / 60)
    assert len(scene.fragments.slots) == 1
    assert game.audio.cues.count("fragment") == 1


def test_exit_advances_level():
    pygame.init()
    game = FakeGame()
    scene = GameplayScene(game, "s1_a")
    scene.player.x = scene.level["exits"][0]["x"] + 1
    scene.update(1 / 60)
    assert isinstance(game.scenes.replaced, GameplayScene)
    assert game.scenes.replaced.level_id == "s1_b"


def test_final_exit_goes_to_ending():
    pygame.init()
    game = FakeGame()
    scene = GameplayScene(game, "s4_c")
    scene.player.x = scene.level["exits"][0]["x"] + 1
    scene.update(1 / 60)
    assert type(game.scenes.replaced).__name__ == "EndingScene"


def test_draw_not_washed_out():
    pygame.init()
    pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
    game = FakeGame()
    scene = GameplayScene(game, "s1_a")
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    scene.draw(surface)
    assert pygame.surfarray.array3d(surface).astype(float).mean() < 200


def test_procedural_has_ambient_creatures():
    pygame.init()
    game = FakeGame()
    scene = GameplayScene(game, "procedural")
    assert len(scene.ambient) == 3
    assert {c["kind"] for c in scene.ambient} == {"biped", "quadruped", "floating"}
    before = scene.ambient[0]["x"]
    scene.update(1 / 60)
    assert scene.ambient[0]["x"] != before
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    scene.draw(surface)


def test_monster_uses_procedural_animator():
    import os
    import sys

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "procedural-generation", "prc-animation",
    ))
    from creature_anim import CreatureAnimator, make_spec

    from noor.entities.monster import Monster

    pygame.init()
    scene = GameplayScene(FakeGame(), "s1_a")
    monster = Monster("test", "M1", scene.player.x + 200, 576, stage=1)
    scene.monsters.append(monster)
    scene.monster_anims[monster.id] = (
        CreatureAnimator(make_spec("biped"), monster.x + 20, monster.y + 80),
        "biped",
    )
    scene.update(1 / 60)
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    scene.draw(surface)
    assert monster.id in scene.monster_anims