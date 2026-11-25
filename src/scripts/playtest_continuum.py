"""Known-solution input-only route through the ONE v4 physics space."""

import argparse
import json
import math
import os
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame

from nur_game.continuum import REGIONS
from nur_game.encounters import BESTIARY
from nur_game.engine import DT
from nur_game.game import Game, _source_hashes
from nur_game.physics import NurInput
from scripts.playtest_nur import JourneyPilot, SlicePilot


class ContinuousPilot:
    def __init__(self,sprint=True,care=True):
        self.journey=JourneyPilot(sprint=sprint)
        self.slice=SlicePilot()
        self.care=care
        self.cared=set()
        self.sprint=sprint
        self.pendulum_crossing=set()

    def control(self,game):
        control=self.route_control(game)
        return self.avoid_machinery(game,control)

    def avoid_machinery(self,game,control):
        """Read the visible machine state, wait or jump using ordinary inputs."""
        px,py=game.world.player.position
        for trap in game.world.hazards.machines:
            distance=trap.x-px
            if not control.move or control.move<0 or not -125<distance<200:
                continue
            if trap.kind in (0,1,3):
                if trap.kind==3 and 95<distance<125 and game.world.grounded:
                    return replace(control,jump=True)
                if 155<distance<185 and game.world.grounded and py<=405:
                    return replace(control,jump=True)
                if 55<distance<90 and py>405:
                    return replace(control,jump=True)
                # Falling from a lookout is already a valid airborne bypass.
                if -110<distance<125 and not game.world.grounded:
                    return replace(control,jump=True)
            elif trap.kind==2:
                phase=trap.vent_phase(game.world.time)
                # Cross only with enough quiet cycle remaining for a walking route.
                if 65<distance<200 and not .05<phase<1.3:
                    return NurInput()
            elif trap.kind==4:
                # Do not jump into the ball. Read its regular visible swing and
                # wait outside the swept envelope for a ground-crossing window.
                if trap.region not in self.pendulum_crossing:
                    if distance>185:
                        if not game.world.grounded or not self.clear_swing(trap,game.world.time,px):
                            return NurInput()
                        self.pendulum_crossing.add(trap.region)
                    else:
                        return NurInput(move=-1)
                return replace(control,jump=False,sprint=False)
        return control

    @staticmethod
    def clear_swing(trap,time,x):
        # Conservative preview of the periodic, visible ball, not a second game
        # simulation. Ordinary walking remains collision-controlled by Pymunk.
        for n in range(260):
            dt=n/120
            px=x+190*max(0,dt-.06)
            if px>trap.x+180:
                break
            bx,by,radius=trap.pendulum(time+dt)
            near_x=max(px-14,min(px+14,bx))
            near_y=max(410,min(463,by))
            if math.hypot(bx-near_x,by-near_y)<radius+9:
                return False
        return True

    def route_control(self,game):
        if game.lantern.charge<=0:
            return NurInput(action=True)
        r=REGIONS[game.room]
        world=game.world
        px,py=world.player.position
        if self.care and game.room not in self.cared and abs(px-r.refuge[0])<70 and abs(py-r.refuge[1])<60:
            self.cared.add(game.room)
            return NurInput(action=True)
        # Completed puzzle pilots must also take the road, rather than climbing
        # lookouts and arriving above a ground-timed machinery crossing.
        if px-r.start>r.source.level.width and (world.quest is None or world.quest.complete):
            return NurInput(move=1,sprint=self.sprint)
        # The old puzzle pilot works directly with translated world coordinates.
        if world.quest:
            view=SimpleNamespace(world=SimpleNamespace(quest=world.quest,player=world.player,
                level=SimpleNamespace(exit=(r.end+35,430),terrain=r.terrain),crates=world.crates,
                phantom_shapes={p:v for p,v in world.phantom_shapes.items() if r.start<=p.x<r.end}),
                room=game.room,boss=game.boss)
            return self.journey.control(view)
        local_x=px-r.start
        if game.room==28 and game.boss:
            boss=game.boss
            if boss.phase==0:
                echo=next(e for e in boss.echoes if not e['taken'])
                target=r.start+echo['x']
                move=1 if target-px>5 else -1 if target-px < -5 else 0
                jump=False
                for rect in r.terrain:
                    edge=rect.x if move>0 else rect.x+rect.w
                    if rect.h<30 and -12<(edge-px)*move<68 and rect.y<py+24:
                        jump=True
                return NurInput(move=move,jump=jump)
            if boss.phase==1:
                return NurInput(move=-1 if local_x>1090 else 1 if local_x<1070 else 0,action=True)
            return NurInput()
        if game.room==3 and world.glide_unlocked and local_x<r.source.level.width:
            # The wick station's glide makes the broad attic gap a new route;
            # don't depend on the rope's old room-reset swing phase.
            return NurInput(move=1,jump=550<local_x<1440)
        # Walk the promenades with ordinary obstacle-aware jumping.
        if local_x>r.source.level.width:
            # Lookouts really are optional: use the road beneath them unless
            # collecting a ribbon. Hazards still require intentional avoidance.
            return NurInput(move=1,sprint=self.sprint)
        # Adapter is read-only: the inherited opening/boss pilot sees local coords.
        crates=[SimpleNamespace(body=SimpleNamespace(position=SimpleNamespace(x=c.body.position.x-r.start,y=c.body.position.y)))
                for c in world.crates if r.start<=c.body.position.x<r.end]
        view=SimpleNamespace(room=game.room,boss=game.boss,
            world=SimpleNamespace(player=SimpleNamespace(position=(local_x,py)),crates=crates,
                                  grab_kind=world.grab_kind,grounded=world.grounded))
        c=self.slice.control(view)
        return NurInput(move=c.move,jump=c.jump,grab=c.grab,action=c.action,climb=c.climb)


def run(output,max_seconds=2400,sprint=True,captures=None):
    game=Game(muted=True,persist=False)
    pilot=ContinuousPilot(sprint=sprint)
    original_space=game.world.space
    elapsed=active=0.
    wall=time.perf_counter()
    solved=shifts=0
    captures_taken=set()
    review_taken=set()
    observed_forms=set()
    unlock_progression=[]
    previous_unlocks=0
    maximum_onscreen=0
    space_preserved=True
    images=[]
    error=None
    stall=0.
    previous_anchor=None
    try:
        for step in range(round(max_seconds/DT)):
            control=pilot.control(game)
            before=sum(q.stage for q in game.world.quests.values())
            phase=game.world.phase
            game.update(DT,control)
            elapsed+=DT
            active+=DT if control.move or control.action or control.jump or control.grab or control.shift else 0
            solved+=sum(q.stage for q in game.world.quests.values())-before
            shifts+=game.world.phase!=phase
            space_preserved &= game.world.space is original_space
            if len(game.threats.unlocked)>previous_unlocks:
                previous_unlocks=len(game.threats.unlocked)
                unlock_progression.append({'seconds':round(elapsed,3),
                    'charge':round(game.lantern.charge,4),
                    'kinds':[BESTIARY[k][0] for k in sorted(game.threats.unlocked)]})
            onscreen=[c for c in game.threats.creatures if c.visible>.5
                      and game.camera-60<c.x<game.camera+1020]
            observed_forms.update(c.kind for c in onscreen)
            if len(onscreen)>maximum_onscreen:
                maximum_onscreen=len(onscreen)
                if captures:
                    captures.mkdir(parents=True,exist_ok=True)
                    pygame.image.save(game.draw(),str(captures/'dense-encounters.png'))
            if game.world.dead:
                if captures:
                    pygame.image.save(game.draw(),str(captures/'failure.png'))
                error=game.world.death_reason
                break
            anchor=(game.room,round(game.world.player.position.x/6),before,game.state)
            stall=stall+DT if anchor==previous_anchor else 0
            previous_anchor=anchor
            if stall>12 and game.state=='playing' and game.boss is None:
                error='Pilot stalled without physics or memory progress (no idle padding).'
                break
            if captures and game.room in (0,4,10,16,22,28) and game.room not in captures_taken:
                captures.mkdir(parents=True,exist_ok=True)
                image=game.draw().copy()
                pygame.image.save(image,str(captures/f'region-{game.room+1:02d}.png'))
                images.append(image)
                captures_taken.add(game.room)
            if captures:
                # Review the actual approach to every mechanical hazard type,
                # not only static region-entry images.
                for trap in game.world.hazards.machines:
                    if 70<trap.x-game.world.player.position.x<160 and trap.kind not in review_taken:
                        from nur_game.hazards import KINDS
                        image=game.draw().copy()
                        pygame.image.save(image,str(captures/f'hazard-{trap.kind+1:02d}.png'))
                        review_taken.add(trap.kind)
                        (captures/f'hazard-{trap.kind+1:02d}.json').write_text(json.dumps({
                            'kind':'Actual-input route frame', 'machine':KINDS[trap.kind],
                            'simulation':game.snapshot()},indent=2,ensure_ascii=False)+'\n')
            if game.state=='ending':
                if captures:
                    pygame.image.save(game.draw(),str(captures/'ending.png'))
                break
        if captures:
            sheet=pygame.Surface((1440,540))
            for i,image in enumerate(images):
                sheet.blit(pygame.transform.smoothscale(image,(480,270)),((i%3)*480,(i//3)*270))
            pygame.image.save(sheet,str(captures/'campaign.png'))
        report={"kind":"known-solution input-only route; visible machinery avoided by waiting/jumping, no NPCs",
                "completed":game.state=='ending',"gameplay_seconds":round(elapsed,3),
                "active_input_seconds":round(active,3),"execution_seconds":round(time.perf_counter()-wall,3),
                "one_space_preserved":space_preserved,"milestones":solved,"perception_shifts":shifts,
                "observed_monster_forms":[BESTIARY[k][0] for k in sorted(observed_forms)],
                "maximum_onscreen_monsters":maximum_onscreen,"unlock_progression":unlock_progression,
                "refuges_visited":sorted(pilot.cared),"sprint":sprint,"error":error,
                "simulation":game.snapshot(),"sources":_source_hashes()}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({k:report[k] for k in ('completed','gameplay_seconds','active_input_seconds','one_space_preserved','milestones','error')}))
        return report
    finally:
        game.audio.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('docs/verification/campaign.json'))
    p.add_argument('--captures',type=Path)
    p.add_argument('--walk',action='store_true')
    p.add_argument('--max-seconds',type=float,default=2400)
    a=p.parse_args()
    return 0 if run(a.output,a.max_seconds,not a.walk,a.captures)['completed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
