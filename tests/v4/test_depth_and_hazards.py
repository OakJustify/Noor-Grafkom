from pathlib import Path

import numpy as np
import pygame
import pytest
from scipy.ndimage import find_objects, label

from nur_game.engine import DT
from nur_game.hazards import KINDS
from nur_game.physics import NurInput
from nur_game.scenery import PROP_LIMIT, scenery_tile


def pixels(image):
    return pygame.image.tobytes(image,'RGBA')


def test_scenery_does_not_dissolve_when_region_address_changes(game):
    a=pygame.Surface((960,540))
    b=a.copy()
    game.art.draw_background(a,1850,0,10,player_x=2219)
    game.art.draw_background(b,1850,1,10,player_x=2221)
    assert pixels(a)==pixels(b)


def test_foreground_is_stable_opaque_and_not_erased_around_player(game):
    a=pygame.Surface((960,540),pygame.SRCALPHA)
    b=a.copy()
    game.art.draw_foreground(a,0,0,(75,430),0)
    game.art.draw_foreground(b,0,0,(400,200),0)
    assert pixels(a)==pixels(b)
    assert a.get_at((75,430)).a==255


@pytest.mark.parametrize('chunk',range(6))
def test_layer_three_has_only_small_solid_separate_objects(chunk):
    image=scenery_tile(3,chunk,123,False)
    alpha=pygame.surfarray.array_alpha(image)
    components,count=label(alpha>=128)
    assert count>=5
    for box in find_objects(components):
        width,height=(axis.stop-axis.start for axis in box)
        assert max(width,height)<=PROP_LIMIT
    # Only antialiased contours can have intermediate alpha; solid fills do not.
    assert np.sum((alpha>0)&(alpha<250))/np.sum(alpha>0)<.12


def test_nur_no_longer_imports_or_packages_the_other_game():
    root=Path(__file__).resolve().parents[2]
    assert not (root/'echo_game').exists() and not (root/'tests_echo').exists()
    for file in (root/'src'/'nur_game').rglob('*.py'):
        assert 'from echo_game' not in file.read_text()
        assert 'import echo_game' not in file.read_text()
    assert not (root/'src'/'nur_game'/'companions.py').exists()


def settle_at_machine(game,kind):
    world=game.world
    trap=next(t for t in world.hazards.machines if t.kind==kind)
    world.player.position=(trap.x,438)
    world.player.velocity=(0,0)
    world.space.reindex_shapes_for_body(world.player)
    return world,trap


@pytest.mark.parametrize('kind',(0,3))
def test_weight_button_warns_then_crushes_player_even_with_carried_lantern(game,kind):
    world,trap=settle_at_machine(game,kind)
    world.step(NurInput(),DT)
    assert trap.state=='warning' and trap.trips==1
    assert not world.dead and game.lantern.protects
    for _ in range(90):
        world.step(NurInput(),DT)
        if world.dead:
            break
    assert world.dead and KINDS[kind] in world.death_reason
    assert world.hazards.deaths==1


def test_spikes_are_lethal_on_contact_and_clearable_by_a_real_jump(game):
    world,trap=settle_at_machine(game,1)
    world.step(NurInput(),DT)
    assert world.dead and 'SPIKES' in world.death_reason
    world.dead=False
    world.player.position=(trap.x-80,438)
    world.player.velocity=(190,0)
    world.space.reindex_shapes_for_body(world.player)
    for _ in range(125):
        world.step(NurInput(move=1,jump=world.player.position.x<trap.x-55),DT)
        assert not world.dead
    assert world.player.position.x>trap.x+60


def test_steam_has_a_quiet_window_warning_then_lethal_column(game):
    world,trap=settle_at_machine(game,2)
    trap.phase=0
    world.time=1
    world.step(NurInput(),DT)
    assert not world.dead and trap.lethal_rect(world.time) is None
    world.time=3.15
    world.step(NurInput(),DT)
    assert world.dead and 'STEAM' in world.death_reason


def test_pendulum_ball_is_a_lethal_obstacle_with_position_matching_drawing(game):
    world,trap=settle_at_machine(game,4)
    trap.phase=0
    world.time=0
    assert trap.pendulum(0)==(trap.x,419,24)
    world.step(NurInput(),DT)
    assert world.dead and 'PENDULUM' in world.death_reason


def test_traps_do_not_remove_puzzle_progress_or_replace_space_on_retry(game):
    world,_trap=settle_at_machine(game,0)
    world.quests[4].stage=2
    space=world.space
    for _ in range(90):
        world.step(NurInput(),DT)
    assert world.dead
    game.restart_room()
    assert game.world.space is space and world.quests[4].stage==2
    assert not world.dead
