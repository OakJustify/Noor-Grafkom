import hashlib
import json
from itertools import pairwise

import pygame
import pytest

from nur_game import config
from nur_game.continuum import REGIONS
from nur_game.game import main


def digest(image):
    return hashlib.sha256(pygame.image.tobytes(image,'RGB')).hexdigest()


def test_four_layers_are_ordered_and_parallax_foreground_moves_fastest(game):
    assert game.art.layer_order==('large_background','small_objects','interaction','foreground')
    assert game.art.parallax==(0.12,0.82,1,1.12)
    layers=game.art.background(0)
    assert len(layers)==3  # Three scenery planes plus the live interaction plane.
    assert layers[0].get_size()==(960,540)
    assert pygame.surfarray.array_alpha(layers[2]).max()>240


def test_seed_changes_scenery_and_background_cache_is_bounded(game):
    first=digest(game.art.background(0)[0])
    game.art.set_seed(999)
    assert digest(game.art.background(0)[0])!=first
    for i in range(29):
        game.art.background(i)
        assert len(game.art._backgrounds)<=6


def test_dynamic_grade_is_monotonically_darker_at_same_actual_position(game):
    game.notice_timer=0
    luminances=[]
    for amount in (1,.65,.35,.12,0):
        game.lantern.charge=amount
        game.draw()
        luminances.append(pygame.surfarray.array3d(game.canvas)[180:780,180:480].mean())
    assert all(a>b for a,b in pairwise(luminances))


def test_every_region_renders_at_bright_and_dim_light_without_mutating_progress(game):
    for r in REGIONS:
        game.room=r.index
        game.world.player.position=r.refuge
        game.world.quest=game.world.quests.get(r.index)
        game.camera=max(0,r.start-30)
        for light in (1,.12):
            game.lantern.charge=light
            before=game.world.progress()
            image=game.draw()
            assert image.get_size()==config.SIZE
            assert pygame.surfarray.array3d(image).std()>10
            assert game.world.progress()==before


def test_v4_checkpoint_roundtrip_retains_care_light_perception_and_global_location(game,tmp_path,monkeypatch):
    monkeypatch.setattr(config,'SAVE_PATH',tmp_path/'nur-v4.json')
    game.world.quests[4].stage=6
    game.world._gate(1/120)
    game.world.set_phase(1)
    game.world.player.position=(REGIONS[5].start+220,438)
    game.room=5
    game.last_refuge=5
    game.lantern.charge=.44
    game.refuges.threads={0,4}
    game.refuges.delivered={0}
    game.refuges.visited={0,5}
    game.threats.unlocked={0,4,7}
    game.world.glide_unlocked=True
    game.world.crates[0].body.position=(530,431)
    game.persist=True
    game._save()
    assert game.load_save()
    assert game.room==5 and game.world.player.position.x==REGIONS[5].start+220
    assert game.world.phase==1 and game.world.quests[4].complete
    assert game.world.gates[4]['open'] and game.world.glide_unlocked
    assert game.refuges.threads=={0,4} and game.refuges.delivered=={0}
    assert game.refuges.visited=={0,5}
    assert game.threats.unlocked=={0,4,7}
    assert game.lantern.charge==.44 and game.last_refuge==5
    assert game.world.crates[0].body.position.x==530


def test_finale_checkpoint_remembers_specific_echoes_and_completed_ending(game,tmp_path,monkeypatch):
    monkeypatch.setattr(config,'SAVE_PATH',tmp_path/'nur-v4.json')
    game.start(28)
    game.boss.echoes[2]['taken']=True
    game.persist=True
    game._save()
    assert game.load_save()
    assert [e['taken'] for e in game.boss.echoes]==[False,False,True]
    for echo in game.boss.echoes:
        echo['taken']=True
    game.boss.local.phase=2
    game.boss.local.name_presses=3
    game.boss.local.done=True
    game._save()
    assert game.load_save() and game.state=='ending'
    game.draw()


def test_foreground_actually_occludes_the_interaction_plane(game):
    screen=pygame.Surface(config.SIZE)
    screen.fill((255,255,255))
    game.art.draw_foreground(screen,0,0,(400,430),0)
    # Front post lies over the world, including actors, not behind them.
    assert screen.get_at((75,225))[:3]!=(255,255,255)


def test_v4_headless_cli_reports_are_deterministic_and_do_not_write_player_saves(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'SAVE_PATH',tmp_path/'untouched.json')
    reports=[tmp_path/'first.json',tmp_path/'second.json']
    for path in reports:
        assert main(['--headless','--frames','2','--no-save','--mute','--report',str(path)])==0
    assert reports[0].read_text()==reports[1].read_text()
    assert not config.SAVE_PATH.exists()


def test_v4_windowed_launch_has_a_live_display_and_handles_quit_without_saving(monkeypatch,tmp_path):
    monkeypatch.setattr(config,'SAVE_PATH',tmp_path/'untouched.json')
    monkeypatch.setattr(pygame.event,'get',lambda:[pygame.event.Event(pygame.QUIT)])
    assert main(['--no-save','--mute'])==0
    assert not config.SAVE_PATH.exists()


@pytest.mark.parametrize('field,value',[
    ('version',3),('position',[float('nan'),430]),('position',[1e9,430]),
    ('lantern',{'charge':float('nan'),'capacity':1}),('quests',{'4':{'stage':7,'phase':0}}),
    ('last_refuge',99),('planted',[200,float('inf')]),('play_seconds',-1),
    ('lantern',{'charge':.5,'capacity':1,'collections':'invalid'}),
    ('refuges',{'visited':[99],'threads':[],'delivered':[]}),
    ('props',[{'position':[float('nan'),431],'velocity':[0,0],'angle':0}]*2),
    ('open_paths',[4,4]),('seed',float('inf')),('last_refuge',float('inf')),
])
def test_bad_v4_checkpoints_are_rejected_without_mutating_live_game(game,tmp_path,monkeypatch,field,value):
    monkeypatch.setattr(config,'SAVE_PATH',tmp_path/'nur-v4.json')
    game.persist=True
    game._save()
    data=json.loads(config.SAVE_PATH.read_text())
    data[field]=value
    config.SAVE_PATH.write_text(json.dumps(data))
    before=game.snapshot()
    assert not game.load_save() and game.snapshot()==before
