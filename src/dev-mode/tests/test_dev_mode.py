import os
import sys

import pygame

ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src", "dev-mode"))

import noor.config as C
from noor.core.i18n import I18n
from noor.entities.monster import Monster
from noor.scenes.gameplay import GameplayScene


class FakeAudio:
    def load_stage(self, stage):
        pass

    def cue(self, name, volume=1.0):
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
        pass


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


def make_scene():
    pygame.init()
    return GameplayScene(FakeGame(), "procedural")


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, key=code)


def test_f3_toggles_overlay():
    scene = make_scene()
    assert scene.dev is not None
    scene.handle_event(key(pygame.K_F3))
    assert scene.dev.visible
    scene.handle_event(key(pygame.K_F3))
    assert not scene.dev.visible


def test_overlay_draws_panel_and_world():
    scene = make_scene()
    scene.handle_event(key(pygame.K_F3))
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    surface.fill((0, 0, 0))
    scene.draw(surface)
    assert pygame.surfarray.array3d(surface).max() > 30


def test_god_mode_blocks_contact_damage():
    scene = make_scene()
    monster = Monster("test", "M1", scene.player.x, scene.player.y, stage=1)
    monster.stun_timer = 10.0
    scene.monsters.append(monster)
    scene.handle_event(key(pygame.K_F4))
    scene.update(1 / 60)
    assert scene.dev.god
    assert scene.sanity.S == scene.sanity.cap


def test_refill_restores_sanity_and_stamina():
    scene = make_scene()
    scene.sanity.S = 5.0
    scene.player.stamina = 1.0
    scene.handle_event(key(pygame.K_F5))
    assert scene.sanity.S == scene.sanity.cap
    assert scene.player.stamina == scene.player.STAMINA_MAX


def test_freeze_clock_stops_time():
    scene = make_scene()
    scene.handle_event(key(pygame.K_F7))
    assert scene.clock.paused
    before = scene.clock.active_time
    scene.update(1 / 60)
    assert scene.clock.active_time == before
    scene.handle_event(key(pygame.K_F7))
    assert not scene.clock.paused


def test_spawn_monster_adds_animator():
    scene = make_scene()
    before = len(scene.monsters)
    scene.handle_event(key(pygame.K_F6))
    assert len(scene.monsters) == before + 1
    monster = scene.monsters[-1]
    assert monster.type == "M1"
    assert monster.id in scene.monster_anims
    surface = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
    scene.draw(surface)


def test_spawn_monster_respects_entity_cap():
    scene = make_scene()
    for _ in range(C.GLOBAL_ENTITY_CAP + 1):
        scene.dev.spawn_monster(scene)
    assert len(scene.monsters) == C.GLOBAL_ENTITY_CAP
    # Legacy animators for M1/M2/M3 only; procedural creatures use vector renderer.
    anim_count = len(scene.monster_anims)
    proc_count = sum(1 for m in scene.monsters if hasattr(m, "renderer"))
    assert anim_count + proc_count >= C.GLOBAL_ENTITY_CAP


def test_respawn_teleports_to_checkpoint():
    scene = make_scene()
    scene.checkpoint.respawn_pos = (321.0, 456.0)
    scene.player.x = 999.0
    scene.player.y = 0.0
    scene.handle_event(key(pygame.K_F8))
    assert (scene.player.x, scene.player.y) == (321.0, 456.0)
