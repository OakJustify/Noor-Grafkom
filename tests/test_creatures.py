"""Runtime procedural creature integration tests."""

import numpy as np
import pygame

import noor.config as C
from noor.core.i18n import I18n
from noor.entities.creature import (
    AVAILABLE,
    ProceduralMonster,
    spawn_definition,
)
from noor.scenes.gameplay import GameplayScene

pygame.init()


class FakeAudio:
    def __init__(self):
        self.cues = []

    def load_stage(self, stage):
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


class StillPlayer:
    width = 32
    height = 80

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.covering = False


def _prc():
    from src.procedural_generation import prc_creature

    return prc_creature


def test_definition_is_deterministic():
    prc = _prc()
    kwargs = {
        "archetype": prc.ArchetypeType.PREDATOR,
        "stage": 1,
        "seed": 42,
        "body_plan": prc.BodyPlanType.QUADRUPED,
        "size_class": prc.SizeClass.MEDIUM,
    }
    a = spawn_definition(**kwargs)
    b = spawn_definition(**kwargs)
    assert a.body == b.body
    assert a.visual.pattern_seed == b.visual.pattern_seed
    assert [l.name for l in a.limbs] == [l.name for l in b.limbs]


def test_all_body_plans_render():
    prc = _prc()
    surface = pygame.Surface((400, 300))
    camera = type("Cam", (), {"x": 0, "y": 0})()
    for plan in prc.BodyPlanType:
        definition = spawn_definition(
            prc.ArchetypeType.PREY, 1, 42, plan, prc.SizeClass.MEDIUM
        )
        monster = ProceduralMonster(f"plan_{plan.value}", definition, 200, 260, 1)
        surface.fill((0, 0, 0))
        monster.update(1 / 60, StillPlayer(0, 0), None, [], world=None)
        monster.draw(surface, camera)
        assert pygame.surfarray.array3d(surface).sum() > 0


def test_audio_synthesizes_in_memory():
    prc = _prc()
    definition = spawn_definition(prc.ArchetypeType.PREY, 1, 42)
    gen = prc.CreatureAudioGenerator(seed=42)
    samples = gen.synthesize_call("idle", definition.vocal, seed=definition.seed)
    assert isinstance(samples, np.ndarray)
    assert samples.dtype == np.float32
    assert samples.size > 0


def test_gameplay_spawns_deterministic_creatures():
    if not AVAILABLE:
        return
    first = GameplayScene(FakeGame(), "s1_a")
    second = GameplayScene(FakeGame(), "s1_a")
    assert 3 <= len(first.monsters) <= 6

    def signature(scene):
        return [
            (m.archetype_name, m.plan_name, round(m.x, 3), round(m.y, 3))
            for m in scene.monsters
        ]

    assert signature(first) == signature(second)
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    first.update(1 / 60)
    first.draw(surface)


def test_contact_depends_on_archetype():
    prc = _prc()

    def make(archetype):
        definition = spawn_definition(
            archetype, 1, 42, prc.BodyPlanType.QUADRUPED, prc.SizeClass.MEDIUM
        )
        return ProceduralMonster("m", definition, 100, 500, 1)

    player = StillPlayer(100, 500)
    assert make(prc.ArchetypeType.PREDATOR).contact_damage(player)
    assert not make(prc.ArchetypeType.PREY).contact_damage(player)
    assert not make(prc.ArchetypeType.GENTLE_LIGHT).contact_damage(player)
