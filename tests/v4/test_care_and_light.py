import numpy as np
import pygame
import pytest

from nur_game.continuum import REGIONS
from nur_game.encounters import Encounter, EncounterDirector
from nur_game.engine import DT
from nur_game.light import LivingLantern
from nur_game.physics import NurInput
from nur_game.refuges import RefugeBook
from nur_game.soundscape import render_drift
from nur_game.wisp import ANIMATIONS, facing_sprite


def test_light_budget_is_gradual_refuges_are_one_use_and_cap_never_increases():
    light=LivingLantern()
    for n in range(1,145):
        previous=light.capacity
        light.milestone(n)
        assert light.capacity<=previous
    assert light.capacity==pytest.approx(.16)
    light.charge=.03
    assert light.kindle('refuge:0') and light.charge==light.capacity
    assert not light.kindle('refuge:0')
    light.collect_fragment()
    assert light.capacity==pytest.approx(.16)


def test_focus_spends_light_but_sprint_only_spends_stamina(game):
    for _ in range(100):
        game.update(DT,NurInput(move=1,sprint=True))
    normal=game.lantern.charge
    assert game.stamina.amount<.85 and game.world.sprinting
    radius=game.lantern.radius
    game.update(.1,NurInput(focus=True))
    assert game.lantern.radius>radius
    assert normal-game.lantern.charge>.0017


def test_unattended_station_unlocks_glide_without_npcs_or_dialogue(game):
    game.update(DT,NurInput(action=True))
    assert game.state=='playing' and game.world.glide_unlocked
    assert not hasattr(game,'companions')
    assert game.refuges.visited=={0}
    assert game.state=='playing' and 'care:0' in game.journal


def test_refuge_inventory_is_deterministic_and_has_no_character_state():
    book=RefugeBook(visited={3,0},threads={4,0},delivered={0})
    assert book.snapshot()=={'visited':[0,3],'threads':[0,4],'delivered':[0]}


def test_memory_ribbon_can_be_collected_and_delivered_for_real_light(game):
    r=REGIONS[0]
    game.world.player.position=(r.start+r.source.level.width+365,328)
    game.update(DT,NurInput(action=True))
    assert game.refuges.threads=={0}
    game.update(DT,NurInput())
    game.world.player.position=r.refuge
    game.lantern.charge=.3
    game.update(DT,NurInput(action=True))
    assert game.refuges.delivered=={0} and game.lantern.charge>.7
    assert 'PITA' in game.notice


def test_glide_limits_descent_and_uses_stamina_instead_of_lantern(game):
    world=game.world
    world.glide_unlocked=True
    world.player.position=(300,230)
    world.player.velocity=(120,180)
    for _ in range(20):
        game.update(DT,NurInput(move=1,jump=True))
    assert world.gliding and 85<=world.player.velocity.y<=95
    assert game.stamina.amount<1 and game.player_animation.pose=='glide'
    game.update(DT,NurInput(move=1))
    assert not world.gliding


@pytest.mark.parametrize('charge,expected',[(1,0),(.65,2),(.35,5),(.12,7)])
def test_monster_kinds_and_size_counts_increase_as_lantern_dims(charge,expected):
    director=EncounterDirector()
    lantern=LivingLantern()
    lantern.charge=charge
    player=(2300,430)
    for _ in range(120):
        assert not director.update(DT,player,lantern,player)
    assert len(director.snapshot()['kinds'])==expected
    assert director.snapshot()['attacks']==0


def test_time_unlocks_eight_monster_forms_and_refilling_does_not_erase_them():
    director=EncounterDirector()
    lantern=LivingLantern()
    counts=[]
    for elapsed in (0,30,100,200,310,430,580,730,910):
        director.update(.1,(1500,430),lantern,(1500,430),elapsed=elapsed)
        counts.append(len(director.unlocked))
    assert counts==list(range(9))
    assert len(director.creatures)==29*8
    for _ in range(100):
        assert not director.update(DT,(1500,430),lantern,(1500,430))
    assert len(director.snapshot()['kinds'])==8
    assert director.snapshot()['attacks']==0


def test_planting_lantern_is_risky_outside_its_light_and_retrieving_cancels_attacks(game):
    game.lantern.charge=.12
    game._plant()
    assert not game.lantern.carried and game.planted is not None
    game.world.player.position=(850,430)
    for _ in range(25):
        game.update(DT,NurInput())
    assert game.threats.snapshot()['warnings']>0
    game.world.player.position=game.planted
    game._plant()
    assert game.lantern.carried and game.planted is None
    game.update(DT,NurInput())
    assert game.threats.snapshot()['warnings']==0 and game.threats.snapshot()['attacks']==0


def test_zero_charge_carried_lantern_still_prevents_direct_monster_hits():
    lantern=LivingLantern()
    lantern.charge=0
    director=EncounterDirector()
    for _ in range(600):
        assert not director.update(DT,(780,430),lantern,(155,438))
    assert lantern.protects and director.snapshot()['attacks']==0


@pytest.mark.parametrize('kind',range(8))
def test_each_monster_warns_attacks_and_is_cancelled_by_possession(kind):
    director=EncounterDirector()
    director.creatures=[Encounter(kind,1000,1000)]  # Isolated collision fixture.
    lantern=LivingLantern()
    lantern.charge=.05
    lantern.carried=False
    player=(1000,425)
    for _ in range(100):
        assert not director.update(DT,player,lantern,(100,438))
    assert director.snapshot()['warnings']==1
    assert any(director.update(DT,player,lantern,(100,438)) for _ in range(150))
    lantern.carried=True
    lantern.charge=0
    for _ in range(200):
        assert not director.update(DT,player,lantern,(100,438))
    assert director.snapshot()['warnings']==director.snapshot()['attacks']==0


def test_placed_light_radius_protects_until_player_leaves_then_attack_is_telegraphed():
    lantern=LivingLantern()
    lantern.charge=.12
    lantern.carried=False
    director=EncounterDirector()
    for _ in range(240):
        assert not director.update(DT,(780,430),lantern,(760,430))
    assert director.snapshot()['attacks']==0
    # Fixture aligns an encounter with the player, not traversal evidence.
    director.creatures[0].x=780
    assert not director.update(DT,(780,430),lantern,(155,438))
    assert director.snapshot()['warnings']>0 and director.snapshot()['attacks']==0
    hit=False
    for _ in range(200):
        hit |= director.update(DT,(780,430),lantern,(155,438))
    assert hit


def test_monsters_leave_no_stale_attack_or_visible_count_when_player_backtracks():
    lantern=LivingLantern()
    lantern.charge=.12
    director=EncounterDirector()
    for _ in range(200):
        director.update(DT,(780,430),lantern,(780,430))
    assert director.snapshot()['active']>0
    lantern.charge=1
    director.update(DT,(80000,430),lantern,(80000,430))
    assert director.snapshot()['active']==0 and director.snapshot()['attacks']==0


def test_zero_charge_blacks_out_world_but_e_has_a_non_softlocking_recovery(game):
    space=game.world.space
    game.lantern.charge=0
    image=game.draw()
    pixels=pygame.surfarray.array3d(image)
    assert pixels[10:950,325:480].max()==0  # HUD/caption intentionally exempt.
    game.update(DT,NurInput(action=True))
    assert game.lantern.charge>0 and game.lantern.recoveries==1
    assert game.world.space is space and not game.world.dead


def test_pause_and_atlas_freeze_budget_and_perception(game):
    before=game.lantern.snapshot()
    for state in ('paused','journal'):
        game.state=state
        game.update(.1,NurInput(shift=True,focus=True,sprint=True))
        assert game.lantern.snapshot()==before and game.world.phase==0


def test_light_reactive_sound_targets_and_mute_are_real_mixer_states(game):
    game.audio.set_muted(False)
    game.audio.update(.1,0,1)
    bright=game.audio.drift_targets
    game.audio.update(.1,3,.1)
    dark=game.audio.drift_targets
    assert bright[0]>dark[0] and bright[2]<dark[2]
    game.audio.set_muted(True)
    assert all(c.get_volume()==0 for c in game.audio.drift_channels)


@pytest.mark.parametrize('kind',range(3))
def test_original_drift_pcm_has_headroom_and_smooth_endpoints(kind):
    pcm=render_drift(kind)
    assert pcm.shape==(12*22050,2) and pcm.dtype==np.int16
    assert np.max(np.abs(pcm))<30000
    assert np.max(np.abs(pcm[0]))==0 and np.max(np.abs(pcm[-1]))<5


def test_all_six_action_sets_have_eight_unique_frames_and_planted_lantern_is_not_drawn():
    assert set(ANIMATIONS)=={'idle','walk','run','jump','glide','focus'}
    for pose,spec in ANIMATIONS.items():
        assert spec.frames==8
        frames={pygame.image.tobytes(facing_sprite(pose,n,1),'RGBA') for n in range(8)}
        assert len(frames)==8
    assert pygame.image.tobytes(facing_sprite('idle',0,1,False),'RGBA')!=pygame.image.tobytes(facing_sprite('idle',0,1,True),'RGBA')
