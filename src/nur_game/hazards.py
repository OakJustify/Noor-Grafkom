"""Lethal machines on the actual route, with visible triggers and swept hit tests.

These kill even while the lantern is carried. They are environmental machinery,
not monsters. Coordinates and poses used by drawing are also used by collision.
"""

import math
from dataclasses import dataclass

import pygame

KINDS=("PRESSER", "SPIKES", "STEAM", "FALLING BEAM", "PENDULUM")
METAL=(59,78,84)
EDGE=(150,166,157)
DANGER=(228,123,91)


@dataclass
class Machine:
    kind: int
    x: float
    region: int
    state: str = "armed"
    timer: float = 0
    trips: int = 0
    phase: float = 0

    @property
    def button(self):
        return pygame.Rect(round(self.x)-46,451,92,9)

    @property
    def slab(self):
        fraction=0
        if self.state=='slam':
            fraction=min(1,self.timer/.14)
        elif self.state=='hold':
            fraction=1
        elif self.state=='retract':
            fraction=max(0,1-self.timer/.85)
        return pygame.Rect(round(self.x)-64,round(220+215*fraction),128,25)

    def pendulum(self,time):
        angle=math.sin(time*1.5+self.phase)*1.05
        return self.x+math.sin(angle)*162,257+math.cos(angle)*162,24

    def vent_phase(self,time):
        return (time+self.phase)%4.8

    def lethal_rect(self,time):
        if self.kind in (0,3):
            return self.slab if self.state in ('slam','hold') else None
        if self.kind==1:
            return pygame.Rect(round(self.x)-49,445,98,15)
        if self.kind==2 and 3.1<=self.vent_phase(time)<4.3:
            return pygame.Rect(round(self.x)-30,348,60,112)
        return None


class HazardField:
    def __init__(self,regions):
        self.machines=[Machine(r.index%5,r.start+r.source.level.width+605,r.index,
                               phase=(r.index*1.37)%4.8) for r in regions[:-1]]
        self.deaths=0
        self.last_hit=None

    def reset_near(self,x):
        for trap in self.machines:
            if abs(trap.x-x)<900:
                trap.state='armed'
                trap.timer=0

    def update(self,world,dt):
        world.player_shape.cache_bb()
        bb=world.player_shape.bb
        player=pygame.Rect(math.floor(bb.left),math.floor(bb.bottom),
                           math.ceil(bb.right-bb.left),math.ceil(bb.top-bb.bottom))
        for trap in self.machines:
            if abs(trap.x-world.player.position.x)>950:
                continue
            previous=trap.slab
            if trap.kind in (0,3):
                if trap.state=='armed':
                    button=trap.button
                    on_button=(player.right>button.left and player.left<button.right
                               and 449<=bb.top<=466 and world.player.velocity.y>=-10)
                    tripwire=(trap.kind==3 and player.colliderect(pygame.Rect(round(trap.x)-35,370,5,90)))
                    if on_button or tripwire:
                        trap.state='warning'
                        trap.timer=0
                        trap.trips+=1
                        world.events.append('tick')
                else:
                    trap.timer+=dt
                    duration={'warning':.48,'slam':.14,'hold':.55,'retract':.85,'cooldown':1.5}[trap.state]
                    if trap.timer>=duration:
                        trap.timer-=duration
                        trap.state={'warning':'slam','slam':'hold','hold':'retract',
                                    'retract':'cooldown','cooldown':'armed'}[trap.state]
                        if trap.state=='hold':
                            world.events.append('gate')
            lethal=trap.lethal_rect(world.time)
            if lethal and trap.state=='slam':
                # A rapidly falling beam cannot tunnel through the player's body.
                lethal=lethal.union(previous)
            hit=bool(lethal and player.colliderect(lethal))
            if trap.kind==4:
                x,y,radius=trap.pendulum(world.time)
                near_x=max(bb.left,min(bb.right,x))
                near_y=max(bb.bottom,min(bb.top,y))
                hit=math.hypot(x-near_x,y-near_y)<radius
            if hit and not world.dead:
                self.deaths+=1
                self.last_hit=KINDS[trap.kind]
                world.kill(f"{KINDS[trap.kind]} · mesin membunuhmu. Cahaya tidak menahan besi.")
                break

    def draw(self,screen,camera):
        for trap in self.machines:
            x=round(trap.x-camera)
            if not -220<x<screen.get_width()+220:
                continue
            warning=trap.state=='warning'
            colour=DANGER if warning else EDGE
            if trap.kind in (0,3):
                # Open-frame gantry, not a ghostly rectangle or scenery cabinet.
                for dx in (-79,79):
                    pygame.draw.rect(screen,METAL,(x+dx-5,197,10,263))
                    pygame.draw.line(screen,EDGE,(x+dx-2,203),(x+dx-2,454),2)
                pygame.draw.rect(screen,METAL,(x-90,189,180,20))
                slab=trap.slab.move(-round(camera),0)
                pygame.draw.rect(screen,METAL,slab)
                pygame.draw.rect(screen,colour,slab,2)
                for dx in range(-56,56,22):
                    pygame.draw.line(screen,DANGER,(x+dx,slab.bottom-7),(x+dx+11,slab.bottom-1),4)
                pygame.draw.line(screen,EDGE,(x-32,209),(x-32,slab.top),4)
                pygame.draw.line(screen,EDGE,(x+32,209),(x+32,slab.top),4)
                pygame.draw.rect(screen,DANGER if trap.state!='armed' else (163,76,65),trap.button.move(-round(camera),0))
                if trap.kind==3:
                    pygame.draw.line(screen,DANGER,(x-35,378),(x-35,450),2)
                pygame.draw.circle(screen,DANGER if warning else (220,177,109),(x,200),5)
            elif trap.kind==1:
                pygame.draw.rect(screen,METAL,(x-54,455,108,6))
                for dx in range(-49,49,14):
                    pygame.draw.polygon(screen,EDGE,[(x+dx,455),(x+dx+6,439),(x+dx+12,455)])
                    pygame.draw.line(screen,DANGER,(x+dx+5,442),(x+dx+7,448),2)
            elif trap.kind==2:
                phase=trap.vent_phase(self.time)
                pygame.draw.rect(screen,METAL,(x-35,450,70,10),border_radius=3)
                for dx in range(-25,30,10):
                    pygame.draw.line(screen,EDGE,(x+dx,452),(x+dx,458),2)
                if 2.4<=phase<4.3:
                    height=112 if phase>=3.1 else 24
                    for dx in (-20,-8,8,20):
                        pygame.draw.line(screen,(226,190,144),(x+dx,448),(x+dx-6,448-height),5)
                    pygame.draw.circle(screen,DANGER,(x,432-height),5)
            else:
                px,py,radius=trap.pendulum(self.time)
                pygame.draw.line(screen,METAL,(x,257),(px-camera,py),5)
                pygame.draw.circle(screen,METAL,(round(px-camera),round(py)),radius)
                pygame.draw.circle(screen,EDGE,(round(px-camera),round(py)),radius,2)
                for dx in (-12,0,12):
                    pygame.draw.line(screen,DANGER,(round(px-camera)+dx-5,round(py)-9),
                                     (round(px-camera)+dx+5,round(py)+9),3)
                pygame.draw.rect(screen,METAL,(x-30,245,60,12))
            # Small red triangle warns about danger regardless of lighting band.
            pygame.draw.polygon(screen,DANGER,[(x-120,430),(x-111,412),(x-102,430)])
            pygame.draw.line(screen,(252,223,169),(x-111,417),(x-111,423),2)
            pygame.draw.circle(screen,(252,223,169),(x-111,426),1)

    time=0

    def snapshot(self):
        return {'count':len(self.machines),'kinds':list(KINDS),'deaths':self.deaths,
                'last_hit':self.last_hit,'trips':sum(t.trips for t in self.machines)}
