from itertools import pairwise

import pytest

from nur_game.continuum import REGIONS, WORLD_WIDTH
from nur_game.engine import DT
from nur_game.physics import NurInput
from scripts.playtest_continuum import run


def test_all_authored_plans_are_translated_without_changing_the_puzzles():
    assert len(REGIONS)==29 and WORLD_WIDTH>100000
    for r in REGIONS:
        if not r.plan:
            continue
        assert r.plan.family==r.source.quest.family and r.plan.order==r.source.quest.order
        for new,old in zip(r.plan.nodes,r.source.quest.nodes):
            assert new.x==old.x+r.start and new.y==old.y and new.kind==old.kind
        assert len(r.plan.platforms)==len(r.source.quest.platforms)
    assert all(a.end==b.start for a,b in pairwise(REGIONS))


def test_crossing_an_area_does_not_reset_player_space_props_camera_or_light(game):
    space,body=game.world.space,game.world.player
    body.position=(REGIONS[0].end-10,438)  # Boundary unit fixture, not playtest evidence.
    game.camera=body.position.x-400
    game.world.crates[0].body.position=(520,431)
    game.lantern.charge=.55
    before=game.camera
    for _ in range(35):
        game.update(DT,NurInput(move=1))
    assert game.room==1 and game.transitions==1
    assert game.world.space is space and game.world.player is body
    assert game.camera>before and game.camera-before<100
    assert game.world.crates[0].body.position.x==pytest.approx(520,abs=1)
    assert .54<game.lantern.charge<.55
    for _ in range(55):
        game.update(DT,NurInput(move=-1))
    assert game.room==0 and game.world.space is space


def test_world_phantoms_change_in_all_regions_without_rebuilding_the_space(game):
    space=game.world.space
    game.world.set_phase(1)
    count=sum(len(q.plan.platforms) for q in game.world.quests.values())
    assert len(game.world.phantom_shapes)==count
    game.world.set_phase(0)
    assert not game.world.phantom_shapes and game.world.space is space


def test_held_q_is_one_global_edge_even_when_crossing_into_another_puzzle(game):
    game.start(4)
    game.world.player.position=(REGIONS[4].end-10,438)
    for _ in range(60):
        game.update(DT,NurInput(move=1,shift=True))
    assert game.room==5 and game.world.phase==1
    game.update(DT,NurInput())
    game.update(DT,NurInput(shift=True))
    assert game.world.phase==0 and game.lantern.protects


def test_checkpoint_retry_keeps_open_paths_and_physics_identity(game):
    game.world.quests[4].stage=6
    game.world._gate(DT)
    assert game.world.gates[4]['open']
    space=game.world.space
    game.last_refuge=4
    game.restart_room()
    assert game.world.space is space and game.world.quests[4].stage==6
    assert game.world.gates[4]['open'] and game.room==4


def test_full_continuous_campaign_is_input_only_and_exceeds_fifteen_minutes(tmp_path):
    report=run(tmp_path/'campaign.json')
    assert report['completed'] and report['error'] is None
    assert report['one_space_preserved']
    # A global phase persists across area borders instead of resetting to NYATA.
    assert report['milestones']==144 and report['perception_shifts']==88
    assert report['gameplay_seconds']>=900 and report['active_input_seconds']>=900
    assert report['simulation']['transitions']==28
    assert report['simulation']['lantern']['deaths']==0
    assert report['simulation']['lantern']['recoveries']==0
    assert len(report['refuges_visited'])==29
    assert len(report['observed_monster_forms'])==8
    assert report['maximum_onscreen_monsters']>=3
    assert len(report['simulation']['threats']['unlocked'])==8
