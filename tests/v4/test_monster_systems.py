"""F1 adaptation: bilateral animation, state machine, flee and LOS."""

import pygame

from nur_game.encounters import EncounterDirector
from nur_game.engine import DT
from nur_game.geometry import Rect
from nur_game.light import LivingLantern
from nur_game.monsters import (MonsterAI, MonsterAnimator, MonsterFleeBehavior,
                               MonsterState, _walkable, line_of_sight)


class FakeWorld:
    def __init__(self, rects):
        self.rects = rects

    def terrain_rects(self):
        return self.rects


def pixels(surface):
    return pygame.image.tobytes(surface, 'RGBA')


def test_bilateral_animation_uses_separate_left_and_right_images():
    animator = MonsterAnimator()
    animator.set_movement(100, False)
    animator.update(.2)
    right = pixels(animator.sprite(0))
    assert animator.pose == 'walk'
    animator.set_facing_direction((-1, 0))
    left = pixels(animator.sprite(0))
    assert right != left
    animator.set_movement(205, True)
    assert animator.pose == 'run'
    animator.play_flee_end()
    assert not animator.fleeing


def test_flee_turns_in_place_before_running_away():
    flee = MonsterFleeBehavior(flee_speed=200, turn_speed=360)
    # Facing right, threat on the right: a visible 180-degree turn comes first.
    assert flee.flee_from((1000, 425), (1200, 425), .1) == 0
    for _ in range(4):
        assert flee.flee_from((1000, 425), (1200, 425), .1) == 0
    assert flee.flee_from((1000, 425), (1200, 425), .1) < 0
    assert not flee.facing_right

    # Facing away already: run forward without turning backwards.
    flee2 = MonsterFleeBehavior(flee_speed=200)
    assert flee2.flee_from((1000, 425), (800, 425), .1) > 0
    assert flee2.facing_right


def test_ai_patrol_detect_flee_return_and_patrol_cycle():
    ai = MonsterAI()
    ai.reset(1000)
    assert ai.state == MonsterState.PATROL
    move, fleeing = ai.update(.1, 1000, (800, 430), .1, True)
    assert move != 0 and not fleeing

    move, fleeing = ai.update(.1, 1000, (800, 430), .4, True)
    assert ai.state == MonsterState.DETECT and move == 0 and not fleeing

    move, fleeing = ai.update(.1, 1000, (800, 430), .6, True)
    assert ai.state == MonsterState.FLEE and fleeing and move == 0

    ai.update(.1, 1600, (800, 430), .6, False)
    assert ai.state == MonsterState.RETURN

    ai.update(.1, 1004, (800, 430), .1, True)
    assert ai.state == MonsterState.PATROL


def test_line_of_sight_and_walkable_gap_guards():
    world = FakeWorld([Rect(0, 460, 900, 160), Rect(1000, 460, 900, 160),
                       Rect(900, 350, 50, 18)])
    assert not line_of_sight(world, (900, 320), (900, 440))
    assert _walkable(world, 500, 425, 0)
    assert not _walkable(world, 950, 425, 0)
    # Aerial forms ignore floor gaps but still avoid solid masses.
    assert _walkable(world, 950, 425, 4)


def test_director_flees_away_from_carried_lantern_and_faces_away():
    director = EncounterDirector()
    creature = next(c for c in director.creatures if c.kind == 0)
    creature.home = creature.x = 1000
    creature.ai.reset(1000)
    lantern = LivingLantern()
    lantern.charge = .9
    director.unlocked = {0}
    director.update(DT, (1000, 430), lantern, (1000, 430))
    assert creature.ai.state == MonsterState.FLEE
    assert creature.animator.fleeing
    assert creature.x > 1000 and creature.animator.facing_right

    director2 = EncounterDirector()
    other = next(c for c in director2.creatures if c.kind == 0)
    other.home = other.x = 1000
    other.ai.reset(1000)
    director2.unlocked = {0}
    for _ in range(8):
        director2.update(.1, (1200, 430), lantern, (1200, 430))
    assert other.x < 1000 and not other.animator.facing_right


def test_director_still_warns_and_attacks_outside_protection():
    director = EncounterDirector()
    creature = next(c for c in director.creatures if c.kind == 0)
    creature.home = creature.x = 1000
    creature.ai.reset(1000)
    lantern = LivingLantern()
    lantern.charge = .05
    lantern.carried = False
    director.unlocked = {0}
    for _ in range(30):
        director.update(DT, (1000, 430), lantern, (100, 438))
    assert creature.warning > 0 or creature.attack > 0
